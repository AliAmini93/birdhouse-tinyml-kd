#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PYTHON_BIN="${PYTHON_BIN:-/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3}"

cd "$REPO_ROOT"

echo "======================================================================"
echo "Ensure preprocessing reference input exists"
echo "======================================================================"
"$PYTHON_BIN" tools/export_preprocess_reference.py

echo ""
echo "======================================================================"
echo "Export TFLite Micro model assets"
echo "======================================================================"
"$PYTHON_BIN" tools/export_tflite_micro_model.py

echo ""
echo "Summary:"
cat firmware/model/model_asset_summary.json
