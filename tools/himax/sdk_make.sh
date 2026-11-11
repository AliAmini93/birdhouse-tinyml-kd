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

for arg in "$@"; do
  case "$arg" in
    bh_tflm_config|BH_LINK=[01]|BH_TFLM_OVERLAY=[01]|BH_STACK_USAGE=[01]) ;;
    -j[1-9]*) [[ "$arg" =~ ^-j[1-9][0-9]*$ ]] || exit 2 ;;
    *) echo "refusing non-allowlisted make argument '$arg'" >&2; exit 2 ;;
  esac
done
# Inherited make options can inject makefiles/recipes even with no CLI target.
unset MAKEFLAGS MFLAGS GNUMAKEFLAGS MAKEFILES
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1794355200}"
[[ "$SOURCE_DATE_EPOCH" =~ ^[0-9]+$ ]] || { echo "invalid SOURCE_DATE_EPOCH" >&2; exit 2; }
export LC_ALL=C TZ=UTC

[ -d "$SDK" ] || { echo "SDK not found: $SDK" >&2; exit 1; }
[ -x "$TOOLCHAIN_BIN/arc-elf32-gcc" ] || { echo "ARC toolchain not found: $TOOLCHAIN_BIN" >&2; exit 1; }

OUT="$(realpath -m -- "$OUT")"
case "$OUT" in "$REPO"/.local-tools/port-himax/*) ;;
  *) echo "out-dir must resolve below .local-tools/port-himax" >&2; exit 2;;
esac
mkdir -p "$OUT"
case "$OUT" in *" "*) echo "out-dir must not contain spaces: $OUT" >&2; exit 1;; esac
case "$REPO" in *" "*) echo "repository path must not contain spaces" >&2; exit 1;; esac

export PATH="$TOOLCHAIN_BIN:$PATH"
exec make -C "$SDK" -f makefile -f "$REPO/firmware/himax_arc/birdhouse/build/birdhouse_overlay.mk" \
  APP_TYPE=edge_impulse_visionai \
  OUT_DIR_ROOT="$OUT" \
  BH_REPO="$REPO" \
  BH_OBJ="$OUT/birdhouse" \
  "$@"
