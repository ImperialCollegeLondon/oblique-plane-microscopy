#!/usr/bin/env bash
set -euo pipefail

# Minimal example: process raw data after bead registration
CONFIG=${1:-configs/example_raw.yaml}

# Ensure beads registered first (register script can be run separately)
python deskewing_pipeline/scripts/process_plate.py --config "$CONFIG"

echo "Processing complete. Check output paths defined in $CONFIG."