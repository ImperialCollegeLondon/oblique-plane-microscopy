# In scripts/register_beads_pipeline.py

import argparse
import yaml
from src.dopm.data_converter import DataConverter

def main():
    parser = argparse.ArgumentParser(description="Run the full dOPM processing pipeline.")
    parser.add_argument('--config', type=str, required=True, help="Path to the main YAML config file.")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    fiji_path = config['fiji_executable_path']
    well_to_process = config['pipeline_settings']['well_id']

    # --- WORKFLOW STEP 1: Process the Bead Data ---
    print("\n--- Starting Step 1: Bead Data Conversion ---")
    bead_converter = DataConverter(config['bead_data'])
    bead_xml_path = bead_converter.process_well(well=well_to_process)
    print("--- Bead Data Conversion Complete ---")

    # --- WORKFLOW STEP 2: Register the Bead Data ---
    print("\n--- Starting Step 2: Bead Data Registration ---")
    # The registration logic is now part of the DataConverter,
    # but we still need a converter instance to call it.
    bead_converter.register_dataset(bead_xml_path, fiji_path)
    print("--- Bead Data Registration Complete ---")
 
    print("\n Full pipeline finished successfully! ")

if __name__ == "__main__":
    main()