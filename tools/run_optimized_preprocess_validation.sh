#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"

cd "$REPO_ROOT"

echo "======================================================================"
echo "1/2 Desktop optimized-FFT parity validation"
echo "======================================================================"
bash tools/run_preprocess_parity_test.sh

echo ""
echo "======================================================================"
echo "2/2 ESP32S3 optimized preprocessing build"
echo "======================================================================"

if ! command -v idf.py >/dev/null 2>&1; then
  echo "ERROR: idf.py not found."
  echo "Source ESP-IDF first:"
  echo "  . ~/esp/esp-idf/export.sh"
  exit 2
fi

bash tools/build_esp32s3_preprocess_inference.sh

echo ""
echo "======================================================================"
echo "VALIDATION COMMANDS COMPLETE"
echo "======================================================================"
echo "Required evidence:"
echo "  - desktop parity report status: PASS"
echo "  - ESP-IDF output: Project build complete"
echo ""
echo "Runtime timing remains pending until the board is available."
