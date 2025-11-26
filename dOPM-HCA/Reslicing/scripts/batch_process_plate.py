#!/usr/bin/env python3
"""
HPC-ready batch_process_plate.py

Usage:
    python scripts/batch_process_plate.py \
        --config configs/new_config.yaml \
        --well B2
"""

import argparse
import yaml
from dopm.data_converter import DataConverter


def main():
    parser = argparse.ArgumentParser(
        description="Create a per-well BDV dataset using pre-registered bead XML"
    )
    parser.add_argument(
        "--config", required=True, help="Path to YAML config file"
    )
    parser.add_argument(
        "--well", required=True, help="Well ID to process, e.g. B2"
    )
    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    bead_xml_path = config["pipeline_settings"]["registered_bead_xml_path"]

    # Construct converter for the sample dataset
    sample_converter = DataConverter(config["data"])

    print("\n--- HPC Plate Processing ---")
    print(f"Config file       : {args.config}")
    print(f"Well              : {args.well}")
    print(f"Bead registration : {bead_xml_path}")

    # Process this well across all tiles and times
    sample_converter.process_well_with_registration(
        well=args.well,
        bead_xml_path=bead_xml_path,
    )

    print("\n HPC job complete for well:", args.well)


if __name__ == "__main__":
    main()
