#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PROJECT_DIR="$REPO_ROOT/firmware/esp32s3_preprocess_inference"
PORT="${PORT:-/dev/ttyACM0}"

if ! command -v idf.py >/dev/null 2>&1; then
  echo "ERROR: idf.py not found."
  echo "Source your ESP-IDF environment first, for example:"
  echo "  . ~/esp/esp-idf/export.sh"
  exit 2
fi

cd "$PROJECT_DIR"

echo "======================================================================"
echo "Flash ESP32S3 preprocessing-to-inference test"
echo "======================================================================"
echo "Port: $PORT"
idf.py -p "$PORT" flash monitor
