#!/usr/bin/env bash
# Run the vendor SDK makefile with the Birdhouse overlay, out of tree.
#
#   tools/himax/sdk_make.sh <out-dir> [make args...]
#
# Examples:
#   tools/himax/sdk_make.sh .local-tools/port-himax/bh-config bh_tflm_config
#   tools/himax/sdk_make.sh .local-tools/port-himax/bh-config-vendor BH_TFLM_OVERLAY=0 bh_tflm_config
#
# This script only compiles and links. It never packages, converts or copies an
# image, and it refuses the vendor targets that talk to tools or hardware.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SDK="${BH_SDK:-$REPO/.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3}"
TOOLCHAIN_BIN="${BH_TOOLCHAIN_BIN:-$REPO/.local-tools/toolchains/arc_gnu_ei_prebuilt_minimal_elf32_le_linux_install/bin}"

if [ $# -lt 1 ]; then
  echo "usage: $0 <out-dir> [make args...]" >&2
  exit 2
fi
OUT="$1"; shift

for forbidden in flash ota run gui menuconfig; do
  for arg in "$@"; do
    if [ "$arg" = "$forbidden" ]; then
      echo "refusing vendor target '$forbidden'" >&2
      exit 2
    fi
  done
done

[ -d "$SDK" ] || { echo "SDK not found: $SDK" >&2; exit 1; }
[ -x "$TOOLCHAIN_BIN/arc-elf32-gcc" ] || { echo "ARC toolchain not found: $TOOLCHAIN_BIN" >&2; exit 1; }

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
case "$OUT" in *" "*) echo "out-dir must not contain spaces: $OUT" >&2; exit 1;; esac
case "$REPO" in *" "*) echo "repository path must not contain spaces" >&2; exit 1;; esac

export PATH="$TOOLCHAIN_BIN:$PATH"
exec make -C "$SDK" -f makefile -f "$REPO/firmware/himax_arc/birdhouse/build/birdhouse_overlay.mk" \
  APP_TYPE=edge_impulse_visionai \
  OUT_DIR_ROOT="$OUT" \
  BH_REPO="$REPO" \
  BH_OBJ="$OUT/birdhouse" \
  "$@"
