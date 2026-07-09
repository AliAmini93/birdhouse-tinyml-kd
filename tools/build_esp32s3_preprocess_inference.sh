#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PROJECT_DIR="$REPO_ROOT/firmware/esp32s3_preprocess_inference"
PYTHON_BIN="${PYTHON_BIN:-/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3}"

if ! command -v idf.py >/dev/null 2>&1; then
  echo "ERROR: idf.py not found."
  echo "Source your ESP-IDF environment first, for example:"
  echo "  . ~/esp/esp-idf/export.sh"
  exit 2
fi

cd "$REPO_ROOT"

echo "======================================================================"
echo "Regenerate reference PCM/input headers"
echo "======================================================================"
"$PYTHON_BIN" tools/export_preprocess_reference.py

cd "$PROJECT_DIR"

echo ""
echo "======================================================================"
echo "ESP32S3 preprocessing-to-inference build"
echo "======================================================================"
idf.py set-target esp32s3
idf.py build | tee "$REPO_ROOT/firmware/esp32s3_preprocess_inference/build_preprocess_inference.log"

echo ""
echo "Build log:"
echo "  firmware/esp32s3_preprocess_inference/build_preprocess_inference.log"
