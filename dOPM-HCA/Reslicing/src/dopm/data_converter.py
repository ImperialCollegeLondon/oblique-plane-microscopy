# src/dopm/data_converter.py

import os
import math
import numpy as np
import re
import nd2

from src.dopm.metadata import Metadata
from src.dopm.npy2bdv import BdvWriter, BdvEditor
from src.dopm.fiji_bridge import FijiBridge


class DataConverter:
    def __init__(self, config: dict):
        self.config = config
        self.scan_type = config["type"]
        self.input_path = config["input_path"]
        self.output_path = config["output_path"]
        self.hardcoded_vars = config["hardcoded_vars"]

        os.makedirs(self.output_path, exist_ok=True)
        print(" DataConverter initialized.")

    # --- ND2 channel-safe extraction ---
    # def _extract_channel_stack(self, file_path: str, channel_index: int) -> np.ndarray:
        # """
        # Open an ND2 file and return the stack for a given channel index,
        # handling arbitrary axis order using nd2.ND2File.sizes.
        # """
        # with nd2.ND2File(file_path) as ndfile:
            # sizes = ndfile.sizes  # ordered dict, e.g. {'T': 3, 'Z': 5, 'C': 2, 'Y': 512, 'X': 512}
            # arr = ndfile.asarray()  # ndarray, order matches sizes

        # if "C" not in sizes:
            # # No channel axis present, return whole stack
            # return arr

        # channel_axis = list(sizes.keys()).index("C")
        # return np.take(arr, channel_index, axis=channel_axis)

    def _extract_channel_stack(self, file_path: str, channel_index: int) -> np.ndarray:
        """
        Open an ND2 file and return the stack for a given channel index,
        handling arbitrary axis order using nd2.ND2File.sizes.
        Optionally fixes corrupted even Z-planes by backfilling.
        """
        with nd2.ND2File(file_path) as ndfile:
            sizes = ndfile.sizes  # ordered dict, e.g. {'T': 3, 'Z': 5, 'C': 2, 'Y': 512, 'X': 512}
            arr = ndfile.asarray()  # ndarray, order matches sizes

        if "C" not in sizes:
            stack = arr
        else:
            channel_axis = list(sizes.keys()).index("C")
            stack = np.take(arr, channel_index, axis=channel_axis)

        # --- Hardcoded artefact fix toggle ---
        if self.hardcoded_vars.get("fix_corrupt_even_planes", False):
            if "Z" in sizes:
                z_axis = list(sizes.keys()).index("Z")
                stack = np.copy(stack)
                count_fixed = 0
                for z in range(1, stack.shape[z_axis], 2):
                    # Replace even-indexed plane with previous one
                    slicer_prev = [slice(None)] * stack.ndim
                    slicer_curr = [slice(None)] * stack.ndim
                    slicer_prev[z_axis] = z - 1
                    slicer_curr[z_axis] = z
                    stack[tuple(slicer_curr)] = stack[tuple(slicer_prev)]
                    count_fixed += 1
                print(f" Fixed {count_fixed} corrupted even Z-planes in {os.path.basename(file_path)}")
            else:
                print("️ fix_corrupt_even_planes enabled, but no Z axis found in this ND2 file.")

        return stack


    # --- Registration ---
    def register_dataset(self, xml_path: str, fiji_path: str):
        print(f" Registering dataset: {xml_path}")
        sanitized_xml_path = xml_path.replace("\\", "/")

        macro_code = f"""
        run("Detect Interest Points for Registration", 
        "select=[{sanitized_xml_path}] process_angle=[All angles]
        process_channel=[All channels] process_illumination=[All illuminations] process_tile=[All tiles] process_timepoint=[All Timepoints]
        type_of_interest_point_detection=Difference-of-Gaussian label_interest_points=beads subpixel_localization=[3-dimensional quadratic fit]
        interest_point_specification=[Weak & small (beads)] downsample_xy=1x downsample_z=1x compute_on=[CPU (Java)]");
        run("Register Dataset based on Interest Points", 
        "select=[{sanitized_xml_path}] process_angle=[All angles]
        process_channel=[All channels] process_illumination=[All illuminations] process_tile=[Single tile (Select from List)] process_timepoint=[All Timepoints]
        processing_tile=[tile 0] registration_algorithm=[Fast descriptor-based (rotation invariant)]
        registration_in_between_views=[Only compare overlapping views (according to current transformations)]
        interest_points=beads group_channels fix_views=[Fix first view] map_back_views=[Do not map back (use this if views are fixed)]
        transformation=Affine regularize_model model_to_regularize_with=Rigid lamba=0.10 redundancy=0 significance=10 allowed_error_for_ransac=5 number_of_ransac_iterations=Normal");
        """

        bridge = FijiBridge(fiji_path)
        bridge.run_macro(macro_code, timeout_seconds=600)
        print(f" Registration complete. File '{xml_path}' has been updated.")

    # --- Processing wells ---
    def process_well(self, well: str) -> str:
        print(f" Processing all datasets for well '{well}'...")
        dataset_dims = Metadata.get_dataset_dimensions_from_filenames(self.input_path, well)
        if not dataset_dims:
            raise FileNotFoundError(f"No datasets found for well '{well}' in {self.input_path}")

        times = dataset_dims.get("times", [0])
        tiles = dataset_dims.get("tiles", [0])
        angles = dataset_dims.get("angles", [])
        print(f"  - Discovered dimensions: {len(times)} Times, {len(tiles)} Tiles, {len(angles)} Angles")

        sample_file_path = self._find_sample_file(well, times[0], tiles[0])
        meta = Metadata(sample_file_path)
        all_meta = meta.get_all_metadata()
        num_channels = len(all_meta["channel_names"])
        z_step = all_meta["z_step"]

        if self.scan_type == "remote_scanning":
            affine_matrices = self._calculate_remote_scan_affines(all_meta["stack_dimensions"], z_step)
            calibration_z = z_step / self.hardcoded_vars["pix_x"]
        elif self.scan_type == "stage_scanning":
            affine_matrices = self._calculate_stage_scan_affines(all_meta["stack_dimensions"])
            mirror_theta = math.radians(self.hardcoded_vars["mirror_tilt"])
            calibration_z = z_step * math.cos((math.pi / 2) - (2 * mirror_theta)) / self.hardcoded_vars["pix_x"]
        else:
            raise ValueError(f"Scan type '{self.scan_type}' is not supported.")

        xml_path = os.path.join(self.output_path, f"dataset_Well{well}.xml")
        bdv_writer = BdvWriter(
            xml_path,
            subsamp=((1, 1, 1),),
            blockdim=((64, 64, 64),),
            nchannels=num_channels,
            nangles=len(angles),
            ntiles=len(tiles),
            nilluminations=1,
            overwrite=True,
        )
        bdv_writer.set_attribute_labels("angle", tuple(map(str, angles)))
        bdv_writer.set_attribute_labels("channel", tuple(all_meta["channel_names"]))

        for time_index, time_val in enumerate(times):
            for tile_index, tile_val in enumerate(tiles):
                for angle_index, angle_val in enumerate(angles):
                    file_path = self._find_specific_file(well, time_val, tile_val, angle_val)
                    if not file_path:
                        continue
                    print(f"   - Processing: {os.path.basename(file_path)}")

                    for channel_index in range(num_channels):
                        channel_stack = self._extract_channel_stack(file_path, channel_index)

                        bdv_writer.append_view(
                            stack=channel_stack,
                            time=time_index,
                            tile=tile_index,
                            channel=channel_index,
                            angle=angle_index,
                            m_affine=affine_matrices[angle_index],
                            voxel_size_xyz=(self.hardcoded_vars["pix_x"],
                                            self.hardcoded_vars["pix_x"],
                                            z_step),
                            voxel_units="um",
                            calibration=(1, 1, calibration_z),
                            exposure_time=10,
                            exposure_units="ms",
                        )

        bdv_writer.write_xml()
        bdv_writer.close()
        print(f" BDV dataset for well '{well}' created successfully at: {xml_path}")
        return xml_path

    def process_well_with_registration(self, well: str, bead_xml_path: str) -> str:
        print(f" Processing well '{well}' using registrations from '{bead_xml_path}'...")
        affine_transformations = self._read_registration_affines(bead_xml_path)
        dataset_dims = Metadata.get_dataset_dimensions_from_filenames(self.input_path, well)
        times = dataset_dims.get("times", [0])
        tiles = dataset_dims.get("tiles", [0])
        angles = dataset_dims.get("angles", [])

        sample_file_path = self._find_sample_file(well, times[0], tiles[0])
        all_meta_sample = Metadata(sample_file_path).get_all_metadata()
        num_channels = len(all_meta_sample["channel_names"])
        z_step = all_meta_sample["z_step"]

        if self.scan_type == "remote_scanning":
            calibration_z = z_step / self.hardcoded_vars["pix_x"]
        elif self.scan_type == "stage_scanning":
            mirror_theta = math.radians(self.hardcoded_vars["mirror_tilt"])
            calibration_z = z_step * math.cos((math.pi / 2) - (2 * mirror_theta)) / self.hardcoded_vars["pix_x"]
        else:
            raise ValueError(f"Scan type '{self.scan_type}' is not supported.")

        xml_path = os.path.join(self.output_path, f"dataset_Well{well}_registered.xml")
        bdv_writer = BdvWriter(
            xml_path,
            subsamp=((1, 1, 1),),
            blockdim=((64, 64, 64),),
            nchannels=num_channels,
            nangles=len(angles),
            ntiles=len(tiles),
            nilluminations=1,
            overwrite=True,
        )
        bdv_writer.set_attribute_labels("angle", tuple(map(str, angles)))
        bdv_writer.set_attribute_labels("channel", tuple(all_meta_sample["channel_names"]))

        for time_index, time_val in enumerate(times):
            for tile_index, tile_val in enumerate(tiles):
                for angle_index, angle_val in enumerate(angles):
                    file_path = self._find_specific_file(well, time_val, tile_val, angle_val)
                    if not file_path:
                        continue
                    print(f"   - Processing: {os.path.basename(file_path)}")

                    for channel_index in range(num_channels):
                        channel_stack = self._extract_channel_stack(file_path, channel_index)
                        
                        # --- THIS IS THE CORRECTED LOGIC ---
                        # Directly use the final transform from the bead file.
                        angle_key = f'angle_{angle_index}'
                        # if len(tiles) > 1:
                        #     view_key = (channel_index, angle_index, tile_index)
                        # else:
                        #     view_key = (channel_index, angle_index)
                            
                        view_key = (channel_index, angle_index)
                        
                        final_affine = affine_transformations[angle_key][view_key]
                        

                        bdv_writer.append_view(
                            stack=channel_stack,
                            time=time_index,
                            tile=tile_index,
                            channel=channel_index,
                            angle=angle_index,
                            m_affine=final_affine[:3, :4],
                            voxel_size_xyz=(self.hardcoded_vars["pix_x"],
                                            self.hardcoded_vars["pix_x"],
                                            z_step),
                            voxel_units="um",
                            calibration=(1, 1, calibration_z),
                            exposure_time=10,
                            exposure_units="ms",
                        )

        bdv_writer.write_xml()
        bdv_writer.close()
        print(f" Registered BDV dataset for well '{well}' created at: {xml_path}")
        return xml_path

    # --- Helper methods ---
    def _read_registration_affines(self, registered_xml_path: str) -> dict:
        # (This method remains the same)
        print(f" Reading registration affines from: {registered_xml_path}"); bdv_editor = BdvEditor(registered_xml_path); nt, ni, nch, ntiles, nang = bdv_editor.get_attribute_count(); affine_transformations = {'angle_0': {}, 'angle_1': {}}
        def convert_to_4x4(matrix_3x4): return np.vstack([matrix_3x4, [0, 0, 0, 1]])
        if ntiles > 1:
            for itile in range(ntiles):
                for ich in range(nch):
                    for iang in range(nang):
                        affine_list = bdv_editor.read_affine_list(time=0, illumination=0, channel=ich, tile=itile, angle=iang)
                        affine_product = np.linalg.multi_dot([convert_to_4x4(m) for m in affine_list[:-1]]) if len(affine_list) > 1 else np.identity(4)
                        affine_transformations[f'angle_{iang}'][(ich, iang, itile)] = affine_product[:3, :4]
        else:
            for ich in range(nch):
                for iang in range(nang):
                    affine_list = bdv_editor.read_affine_list(time=0, illumination=0, channel=ich, tile=0, angle=iang)
                    affine_product = np.linalg.multi_dot([convert_to_4x4(m) for m in affine_list[:-1]]) if len(affine_list) > 1 else np.identity(4)
                    affine_transformations[f'angle_{iang}'][(ich, iang)] = affine_product[:3, :4]
        bdv_editor.finalize(); print("   Successfully read registration transforms.")
        return affine_transformations

    def _find_sample_file(self, well: str, time: int, tile: int) -> str:
        pattern = re.compile(rf".*?_Time{time:04d}_Tile{tile:04d}_angle(\d+)_{{1,2}}Well{well}.*\.nd2")
        for filename in os.listdir(self.input_path):
            if pattern.match(filename):
                return os.path.join(self.input_path, filename)
        raise FileNotFoundError(f"Could not find a sample file for well {well}")

    def _find_specific_file(self, well: str, time: int, tile: int, angle: int) -> str | None:
        pattern = re.compile(rf".*?_Time{time:04d}_Tile{tile:04d}_angle{angle}_{{1,2}}Well{well}.*\.nd2")
        for filename in os.listdir(self.input_path):
            if pattern.match(filename):
                return os.path.join(self.input_path, filename)
        return None

    def _calculate_stage_scan_affines(self, stack_dims: dict) -> list:
        Y = stack_dims["Y"]
        mirror_tilt = self.hardcoded_vars["mirror_tilt"]
        pix_x = self.hardcoded_vars["pix_x"]
        mirror_theta = math.radians(mirror_tilt)
        shear_y_px = 1 / math.tan(2 * mirror_theta)
        flipy_shift = round(Y * pix_x * math.sin(2 * mirror_theta)) / pix_x
        image_theta = (math.pi / 2) - (2 * mirror_theta)

        affine_matrix_1 = np.array([[1., 0., 0., 0.], [0., -1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        affine_matrix_2 = np.array([[1., 0., 0., 0.], [0., 1., shear_y_px, 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        affine_matrix_3 = np.array([[1., 0., 0., 0.],
                                    [0., math.cos(image_theta), -math.sin(image_theta), 0.],
                                    [0., math.sin(image_theta),  math.cos(image_theta), 0.],
                                    [0., 0., 0., 1.]])
        affine_matrix_4 = np.array([[1., 0., 0., 0.], [0., 1., 0., flipy_shift], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        affine_matrix_5 = np.array([[1., 0., 0., 0.], [0., 1., -shear_y_px, 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        affine_matrix_6 = np.array([[1., 0., 0., 0.],
                                    [0., math.cos(-image_theta), -math.sin(-image_theta), 0.],
                                    [0., math.sin(-image_theta),  math.cos(-image_theta), 0.],
                                    [0., 0., 0., 1.]])
        lab_axis = math.pi / 2
        affine_matrix_7 = np.array([[1., 0., 0., 0.],
                                    [0., math.cos(lab_axis), -math.sin(lab_axis), 0.],
                                    [0., math.sin(lab_axis),  math.cos(lab_axis), 0.],
                                    [0., 0., 0., 1.]])

        combined_matrix_view1 = np.linalg.multi_dot(
            [affine_matrix_7, affine_matrix_4, affine_matrix_3, affine_matrix_2, affine_matrix_1]
        )
        combined_matrix_view2 = np.linalg.multi_dot([affine_matrix_7, affine_matrix_6, affine_matrix_5])
        return [combined_matrix_view1[:3, :4], combined_matrix_view2[:3, :4]]

    def _calculate_remote_scan_affines(self, stack_dims: dict, z_step: float) -> list:
        X, Y, Z = stack_dims["X"], stack_dims["Y"], stack_dims["Z"]
        mirror_tilt = self.hardcoded_vars["mirror_tilt"]
        pix_x = self.hardcoded_vars["pix_x"]
        mirror_theta = math.radians(mirror_tilt)
        shear_y_px = math.tan(mirror_theta)
        zdim_pixels = round(Z * z_step / pix_x)
        flipz_shift = round(zdim_pixels / math.cos(mirror_theta))
        ydim_deskewed = round(Y + zdim_pixels * shear_y_px)
        image_theta = 2 * mirror_theta

        affine_matrix_1 = np.array([[1., 0., 0., 0.], [0., 1., shear_y_px, 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
        affine_matrix_2 = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., -1., 0.], [0., 0., 0., 1.]])
        affine_matrix_3 = np.array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., flipz_shift], [0., 0., 0., 1.]])
        affine_matrix_4 = np.array([[1., 0., 0., -X / 2],
                                    [0., 1., 0., -ydim_deskewed / 2],
                                    [0., 0., 1., -zdim_pixels / 2],
                                    [0., 0., 0., 1.]])
        affine_matrix_5 = np.array([[1., 0., 0., 0.],
                                    [0., math.cos(image_theta), -math.sin(image_theta), 0.],
                                    [0., math.sin(image_theta),  math.cos(image_theta), 0.],
                                    [0., 0., 0., 1.]])
        affine_matrix_6 = np.array([[1., 0., 0., 0.],
                                    [0., math.cos(-image_theta), -math.sin(-image_theta), 0.],
                                    [0., math.sin(-image_theta),  math.cos(-image_theta), 0.],
                                    [0., 0., 0., 1.]])
        affine_matrix_7 = np.array([[1., 0., 0., X / 2],
                                    [0., 1., 0., ydim_deskewed / 2],
                                    [0., 0., 1., zdim_pixels / 2],
                                    [0., 0., 0., 1.]])

        combined_matrix_view1 = np.linalg.multi_dot([affine_matrix_7, affine_matrix_5, affine_matrix_4, affine_matrix_1])
        combined_matrix_view2 = np.linalg.multi_dot(
            [affine_matrix_7, affine_matrix_6, affine_matrix_4, affine_matrix_3, affine_matrix_2, affine_matrix_1]
        )
        return [combined_matrix_view1[:3, :4], combined_matrix_view2[:3, :4]]
