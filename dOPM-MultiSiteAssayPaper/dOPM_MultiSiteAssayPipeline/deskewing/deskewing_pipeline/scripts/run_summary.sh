#!/usr/bin/env bash
set -euo pipefail

# Create representative summaries for raw and fused outputs.
RAW_PROJ_DIR=${1:-path/to/sample/processed}
FUSED_DIR=${2:-path/to/fused/processed}

python deskewing_pipeline/src/summary_raw.py "$RAW_PROJ_DIR" --output summary_raw
python deskewing_pipeline/src/summary_fused.py "$FUSED_DIR" --output summary_fused

echo "Summaries created: summary_raw/ and summary_fused/"