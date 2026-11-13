#!/usr/bin/env bash
# Deprecated Claude launcher. Preserve INTERACTIVE-only policy: redirect to Codex TUI.
set -Eeuo pipefail
ROOT="$(git -C "$(dirname -- "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
exec bash "$ROOT/scripts/agents/launch_birdhouse_windows_uf2_codex.sh" "$@"
