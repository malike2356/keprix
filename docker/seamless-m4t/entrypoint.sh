#!/bin/bash
set -e

MODEL=${MODEL:-seamlessM4T_v2_large}
DEVICE=${DEVICE:-cpu}
DTYPE=${DTYPE:-fp16}

echo "SeamlessM4T sidecar starting..."
echo "  Model:  $MODEL"
echo "  Device: $DEVICE"
echo "  Dtype:  $DTYPE"

export SM4T_MODEL="$MODEL"
export SM4T_DEVICE="$DEVICE"
export SM4T_DTYPE="$DTYPE"

exec uvicorn server:app --host 0.0.0.0 --port 7810
