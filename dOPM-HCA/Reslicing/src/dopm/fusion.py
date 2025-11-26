"""
Fusion module: orchestrates Fiji-based BDV tile fusion for workstation and HPC modes.

Supports:
 - Standard multi-tile, all-timepoint fusion (default)
 - Per-tile fusion for HPC job arrays
 - Partial fusion over timepoint ranges for requeue/resume
"""

import os
from src.dopm.fiji_bridge import FijiBridge
from src.dopm.npy2bdv import BdvEditor


class FusionProcessor:
    def __init__(self, fiji_path: str, fusion_settings: dict):
        self.bridge = FijiBridge(fiji_path)
        self.settings = fusion_settings
        self.binning = str(self.settings.get("binning", 1))

    # --------------------------------------------------------------------------
    # Default fusion (unchanged, but now with safe macro generation)
    # --------------------------------------------------------------------------
    def fuse_volumes(self, xml_path: str, output_prefix: str = "fused", single_tile: int = None):
        """
        Default full-volume fusion across all tiles and all timepoints.
        Supports HPC mode via `single_tile` (to process one tile only).
        """
        sanitized_xml_path = xml_path.replace("\\", "/")
        base_output_dir = os.path.dirname(sanitized_xml_path)

        fused_output_path = os.path.join(base_output_dir, f"fused_binning_{self.binning}").replace("\\", "/")
        os.makedirs(fused_output_path, exist_ok=True)

        print(f" Discovering all tiles in dataset: {xml_path}")
        editor = BdvEditor(xml_path)
        nt, ni, nch, ntiles, nang = editor.get_attribute_count()
        editor.finalize()

        # Restrict to one tile if in HPC mode
        if single_tile is not None:
            tile_list = [single_tile]
            print(f"   HPC mode: processing only tile {single_tile}/{ntiles}")
        else:
            tile_list = list(range(ntiles))
            print(f"   Found {ntiles} tiles. Processing all.")

        print(f"   Generating a looping macro to fuse each separately.")
        macro_code = self._generate_looping_fuse_macro(
            sanitized_xml_path, fused_output_path, tile_list, output_prefix
        )

        print(" Generated the following looping macro for Fiji:")
        print("--------------------")
        print(macro_code.strip())
        print("--------------------")

        self.bridge.run_macro(macro_code)
        print(f" Fusion complete. Output saved in: {fused_output_path}")

    # --------------------------------------------------------------------------
    # Fixed macro generator (indentation-safe)
    # --------------------------------------------------------------------------
    def _generate_looping_fuse_macro(self, xml_path: str, output_path: str, tile_list: list, prefix: str) -> str:
        """
        Generates a single ImageJ macro string that contains a for-loop
        to process a specific list of tiles individually.
        """
        # ✅ Explicitly quote each tile index for ImageJ newArray()
        tile_array_str = ", ".join(f'"{t}"' for t in tile_list)

        options_template = (
            '"select=[{xml_path}]" '
            '+ " process_angle=[All angles]" '
            '+ " process_channel=[All channels]" '
            '+ " process_illumination=[All illuminations]" '
            '+ " process_tile=[Single tile (Select from List)]" '
            '+ " processing_tile=[tile " + tileId + "]" '
            '+ " process_timepoint=[All Timepoints]" '
            '+ " bounding_box=[All Views]" '
            '+ " downsampling={binning}" '
            '+ " pixel_type=[16-bit unsigned integer]" '
            '+ " interpolation=[Linear Interpolation]" '
            '+ " image=[Precompute Image]" '
            '+ " fused_image=[Save as (compressed) TIFF stacks]" '
            '+ " output_file_directory=[{output_path}]" '
            '+ " filename_addition=[{prefix}_tile" + tileId + "]" '
            '+ " interest_points_for_non_rigid=[-= Disable Non-Rigid =-]" '
            '+ " blend produce=[Each timepoint & channel]"'
        ).format(xml_path=xml_path, output_path=output_path, prefix=prefix, binning=self.binning)

        macro = (
            f'tilesToProcess = newArray({tile_array_str});\n'
            'print("--- Starting Batch Fusion in Fiji for " + tilesToProcess.length + " tiles ---");\n'
            'for (i = 0; i < tilesToProcess.length; i++) {\n'
            '    tileId = tilesToProcess[i];\n'
            '    print("Fusing tile " + tileId + "...");\n'
            f'    run("Fuse", {options_template});\n'
            '}\n'
            'print("--- Batch Fusion in Fiji Complete ---");\n'
            'run("Quit");\n'
        )
        return macro


    # --------------------------------------------------------------------------
    # Partial fusion over timepoint ranges
    # --------------------------------------------------------------------------
    def fuse_single_tile_range(
        self, xml_path: str, output_path: str, well_id: str, tile_id: int,
        tp_start: int, tp_end: int
    ):
        """
        Runs Fiji fusion for a single tile and a specified range of timepoints.
        Useful for cluster requeue/resume mode or partial fusion jobs.
        """
        sanitized_xml = xml_path.replace("\\", "/")
        fused_output_path = os.path.join(output_path, f"fused_binning_{self.binning}").replace("\\", "/")
        os.makedirs(fused_output_path, exist_ok=True)

        macro_code = self._generate_fuse_macro_for_tile_and_timepoints(
            xml_path=sanitized_xml,
            output_path=fused_output_path,
            well_id=well_id,
            tile_id=tile_id,
            tp_start=tp_start,
            tp_end=tp_end,
        )

        print(f"--- Launching Fiji fusion for {well_id} tile {tile_id}, timepoints {tp_start}-{tp_end} ---")
        print(macro_code)
        self.bridge.run_macro(macro_code)
        print(f"✅ Fusion complete for {well_id} tile {tile_id} ({tp_start}-{tp_end})")

    def _generate_fuse_macro_for_tile_and_timepoints(
        self, xml_path: str, output_path: str, well_id: str,
        tile_id: int, tp_start: int, tp_end: int
    ) -> str:
        """
        Builds a macro that fuses one tile for a specific range of timepoints.
        Example: process_timepoint=[Range of Timepoints (Specify by Name)]
        """
        options = (
            f'select=[{xml_path}] '
            f'process_angle=[All angles] '
            f'process_channel=[All channels] '
            f'process_illumination=[All illuminations] '
            f'process_tile=[Single tile (Select from List)] '
            f'process_timepoint=[Range of Timepoints (Specify by Name)] '
            f'processing_tile=[tile {tile_id}] '
            f'process_following_timepoints={tp_start}-{tp_end} '
            f'bounding_box=[All Views] '
            f'downsampling={self.binning} '
            f'pixel_type=[16-bit unsigned integer] '
            f'interpolation=[Linear Interpolation] '
            f'image=[Precompute Image] '
            f'interest_points_for_non_rigid=[-= Disable Non-Rigid =-] '
            f'blend produce=[Each timepoint & channel] '
            f'fused_image=[Save as (compressed) TIFF stacks] '
            f'output_file_directory=[{output_path}] '
            f'filename_addition=[{well_id}_tile{tile_id:03d}]'
        )

        macro = (
            f'print("--- Starting range fusion for tile {tile_id} ({tp_start}-{tp_end}) ---");\n'
            f'run("Fuse", "{options}");\n'
            'print("--- Range fusion complete ---");\n'
            'run("Quit");\n'
        )
        return macro
