#!/bin/bash
set -e

MODEL=${MODEL:-facebook/nllb-200-distilled-600M}
DEVICE=${DEVICE:-cpu}

echo "NLLB-200 sidecar starting..."
echo "  Model:  $MODEL"
echo "  Device: $DEVICE"

export NLLB_MODEL="$MODEL"
export NLLB_DEVICE="$DEVICE"

exec uvicorn server:app --host 0.0.0.0 --port 7811
