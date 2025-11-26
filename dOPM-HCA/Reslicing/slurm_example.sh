#!/bin/bash
#SBATCH --job-name=process_plate
#SBATCH --output=logs/process_plate_%A_%a.out
#SBATCH --error=logs/process_plate_%A_%a.err
#SBATCH --time=12:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8

# Usage:
# sbatch --array=0-399 slurm_process_plate_auto.sh configs/config.yaml
# or
# sbatch slurm_process_plate_auto.sh configs/config.yaml B8

CONFIG=$1
MANUAL_WELL=$2

if [ -z "$CONFIG" ]; then
    echo "❌ Error: No config file provided."
    echo "Usage: sbatch [--array=0-N] $0 configs/my_config.yaml [WELL]"
    exit 1
fi

PYTHON=/nemo/lab/frenchp/data/CALM/dOPM/conda_envs/dopm_processing/bin/python
if [ ! -x "$PYTHON" ]; then
    echo "❌ Error: Python not found at $PYTHON"
    exit 1
fi

INPUT_PATH=$(grep "input_path:" "$CONFIG" | sed -E 's/.*input_path:[[:space:]]*"?([^"]+)"?/\1/' | tr -d '\r')
echo "[DEBUG] INPUT_PATH='$INPUT_PATH'"

if [ ! -d "$INPUT_PATH" ]; then
    echo "❌ Error: input_path $INPUT_PATH not found."
    exit 1
fi

WELLS=($(ls ${INPUT_PATH}/*Well*.nd2 2>/dev/null | sed -E 's/.*Well([A-Z0-9]+).*/\1/' | sort -u))
if [ ${#WELLS[@]} -eq 0 ]; then
    echo "❌ No ND2 files found in $INPUT_PATH"
    exit 1
fi

# --- Determine well ---
if [ -n "$MANUAL_WELL" ]; then
    WELL=$MANUAL_WELL
    echo "🔹 Running single well manually: ${WELL}"
elif [ -n "$SLURM_ARRAY_TASK_ID" ]; then
    if [ ${SLURM_ARRAY_TASK_ID} -ge ${#WELLS[@]} ]; then
        echo "Array index ${SLURM_ARRAY_TASK_ID} out of range (only ${#WELLS[@]} wells)."
        exit 0
    fi
    WELL=${WELLS[$SLURM_ARRAY_TASK_ID]}
    echo "🔹 Running array well: ${WELL}"
else
    echo "❌ No WELL specified and no SLURM_ARRAY_TASK_ID found."
    echo "Use: sbatch $0 config.yaml <WELL>"
    exit 1
fi

cd /nemo/lab/frenchp/data/CALM/dOPM/projects/software/dopm_processing
export PYTHONPATH=$PWD/src:$PYTHONPATH

$PYTHON -m scripts.batch_process_plate --config "${CONFIG}" --well "${WELL}"
EXITCODE=$?

echo "[DONE] $(date) | Well=${WELL} | Exit code: ${EXITCODE}"
exit $EXITCODE
