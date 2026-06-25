#!/usr/bin/env bash
set -euo pipefail

# Run bead BDV conversion and Fiji registration (use relative paths for publication)
CONFIG=${1:-configs/example_raw.yaml}

python deskewing_pipeline/scripts/register_beads_pipeline.py --config "$CONFIG"

echo "Bead registration complete. Bead BDV XML should match registration.registered_bead_xml_path in the config."