#!/usr/bin/env bash
set -euo pipefail

# Minimal example: fuse/process fused stacks after registration/processing
CONFIG=${1:-configs/example_fused.yaml}

python deskewing_pipeline/scripts/fuse_plate.py --config "$CONFIG"

echo "Fusing complete. Check fused output paths defined in $CONFIG."