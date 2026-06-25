# In src/dopm/fusion.py

import os
from dopm.fiji_bridge import FijiBridge
from dopm.npy2bdv import BdvEditor

class FusionProcessor:
    def __init__(self, fiji_path: str, fusion_settings: dict):
        self.bridge = FijiBridge(fiji_path)
        self.settings = fusion_settings
        self.binning = str(self.settings.get('binning', 1))

    def fuse_volumes(self, xml_path: str, output_prefix: str = "fused"):
        # This method's logic is correct and does not need to change
        sanitized_xml_path = xml_path.replace('\\', '/')
        base_output_dir = os.path.dirname(sanitized_xml_path)
        
        fused_output_path = os.path.join(base_output_dir, f"fused_binning_{self.binning}").replace('\\', '/')
        os.makedirs(fused_output_path, exist_ok=True)
   
        # # include prefix in path to isolate wells
        # fused_output_path = os.path.join(
        #     base_output_dir,
        #     f"fused_binning_{self.binning}",
        #     output_prefix
        # ).replace('\\', '/')

        # os.makedirs(fused_output_path, exist_ok=True)


        print(f" Discovering all tiles in dataset: {xml_path}")
        editor = BdvEditor(xml_path)
        nt, ni, nch, ntiles, nang = editor.get_attribute_count()
        editor.finalize()
        tile_list = list(range(ntiles))
        print(f"   Found {ntiles} tiles. Generating a looping macro to fuse each separately.")

        macro_code = self._generate_looping_fuse_macro(sanitized_xml_path, fused_output_path, tile_list, output_prefix)
        
        print(" Generated the following looping macro for Fiji:")
        print("--------------------")
        print(macro_code.strip())
        print("--------------------")

        self.bridge.run_macro(macro_code)
        
        print(f" Fusion complete. Output saved in: {fused_output_path}")

    # --- THIS METHOD IS NOW CORRECTED ---
    def _generate_looping_fuse_macro(self, xml_path: str, output_path: str, tile_list: list, prefix: str) -> str:
        """
        Generates a single ImageJ macro string that contains a for-loop
        to process a specific list of tiles individually.
        """
        tile_array_str = ", ".join(map(str, tile_list))
        
        # This string builds the options for the "Fuse" command with corrected parameters.
        options_template = (
            ' "select=[{xml_path}]"' +
            ' + " process_tile=[Single tile (Select from List)]"' +
            ' + " processing_tile=[tile " + tileId + "]"' +
            ' + " image=[Precompute Image]"' + 
            ' + " fused_image=[Save as (compressed) TIFF stacks]"' + 
            ' + " output_file_directory=[{output_path}]"' +
            ' + " filename_addition=[{prefix}_tile_" + tileId + "]"' +
            ' + " process_angle=[All angles] process_channel=[All channels] process_illumination=[All illuminations] process_timepoint=[All Timepoints]"' +
            ' + " bounding_box=[All Views] downsampling={binning} pixel_type=[16-bit unsigned integer] interpolation=[Linear Interpolation]"' +
            ' + " interest_points_for_non_rigid=[-= Disable Non-Rigid =-] blend produce=[Each timepoint & channel]"'
        ).format(xml_path=xml_path, output_path=output_path, prefix=prefix, binning=self.binning)

        # Build the final macro with the ImageJ for-loop
        macro = f"""
        tilesToProcess = newArray({tile_array_str});
        print("--- Starting Batch Fusion in Fiji for " + tilesToProcess.length + " tiles ---");
        for (i = 0; i < tilesToProcess.length; i++) {{
            tileId = tilesToProcess[i];
            print("Fusing tile " + tileId + "...");
            run("Fuse", {options_template});
        }}
        print("--- Batch Fusion in Fiji Complete ---");
        run("Quit");
        """
        return macro