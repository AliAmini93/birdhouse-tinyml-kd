#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PYTHON_BIN="${PYTHON_BIN:-/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3}"
CXX="${CXX:-g++}"

cd "$REPO_ROOT"

echo "======================================================================"
echo "Generate Python reference preprocessing tensors"
echo "======================================================================"
"$PYTHON_BIN" tools/export_preprocess_reference.py

echo ""
echo "======================================================================"
echo "Build C++ preprocessing parity test"
echo "======================================================================"
mkdir -p build/preprocess

"$CXX" -std=c++17 -O2 -I. \
  firmware/preprocess/test_preprocess_parity.cc \
  firmware/preprocess/audio_preprocess.cc \
  firmware/preprocess/mel_filterbank.cc \
  -o build/preprocess/preprocess_parity_test \
  -lm

echo ""
echo "======================================================================"
echo "Run C++ preprocessing parity test"
echo "======================================================================"
build/preprocess/preprocess_parity_test \
  firmware/preprocess/testdata/reference_pcm_float32.bin \
  firmware/preprocess/testdata/reference_input_int8.bin \
  | tee firmware/preprocess/testdata/preprocess_parity_report.txt

echo ""
echo "Report:"
echo "  firmware/preprocess/testdata/preprocess_parity_report.txt"
