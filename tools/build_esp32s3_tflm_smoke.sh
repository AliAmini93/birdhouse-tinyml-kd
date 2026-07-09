#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PROJECT_DIR="$REPO_ROOT/firmware/esp32s3_tflm_smoke"

if ! command -v idf.py >/dev/null 2>&1; then
  echo "ERROR: idf.py not found."
  echo "Source your ESP-IDF environment first, for example:"
  echo "  . ~/esp/esp-idf/export.sh"
  exit 2
fi

cd "$PROJECT_DIR"

echo "======================================================================"
echo "ESP32S3 TFLite Micro smoke-test build"
echo "======================================================================"
idf.py set-target esp32s3
idf.py build | tee "$REPO_ROOT/firmware/esp32s3_tflm_smoke/build_smoke.log"

echo ""
echo "Build log:"
echo "  firmware/esp32s3_tflm_smoke/build_smoke.log"
echo ""
echo "Next, flash with:"
echo "  PORT=/dev/ttyACM0 bash tools/flash_esp32s3_tflm_smoke.sh"
