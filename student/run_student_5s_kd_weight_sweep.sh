#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/media/armin/External/AhmadWorks/audioclassification}"
PYTHON_BIN="${PYTHON_BIN:-/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3}"

cd "$REPO_ROOT"

echo "======================================================================"
echo "Student 5s binary KD weight sweep"
echo "======================================================================"

RUNS=(
  "5s_kd_binary_hw08_kw02 0.8 0.2"
  "5s_kd_binary_hw07_kw03 0.7 0.3"
  "5s_kd_binary_hw03_kw07 0.3 0.7"
)

for spec in "${RUNS[@]}"; do
  read -r RUN_NAME HARD_WEIGHT KD_WEIGHT <<< "$spec"

  echo ""
  echo "======================================================================"
  echo "Run: $RUN_NAME | hard_weight=$HARD_WEIGHT kd_weight=$KD_WEIGHT"
  echo "======================================================================"

  mkdir -p "student/results/$RUN_NAME"

  "$PYTHON_BIN"     student/train_student_5s_kd_binary_sweep_wrapper.py     --run-name "$RUN_NAME"     --hard-weight "$HARD_WEIGHT"     --kd-weight "$KD_WEIGHT"     2>&1 | tee "student/results/$RUN_NAME/train_console.log"
done

"$PYTHON_BIN" student/summarize_student_5s_kd_weight_sweep.py

echo ""
echo "Send:"
echo "  cat student/results/kd_weight_sweep_summary.md"
echo "  git status --short"

