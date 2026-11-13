#!/usr/bin/env bash
# INTERACTIVE Codex, no headless fallback. Offline PDM safety only.
set -Eeuo pipefail
ROOT="/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
REPO="AliAmini93/birdhouse-tinyml-kd"
BRANCH="research/birdhouse-v1-pdm-safety-offline-20261113"
MISSION="docs/agents/CODEX_BIRDHOUSE_PDM_P1P4_OFFLINE_INTERACTIVE_20261113.md"
PYTHON_FIXED="/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3"
stop() { printf 'BIRDHOUSE_PDM_STOP: %s\n' "$*" >&2; exit 2; }
[[ $# -eq 0 || ( $# -eq 1 && "$1" == "--check" ) ]] || stop "Use without arguments or --check."
[[ -d "$ROOT/.git" ]] || stop "Repository checkout missing."
cd "$ROOT"
command -v git >/dev/null 2>&1 || stop "Git missing."
command -v codex >/dev/null 2>&1 || stop "Codex CLI missing."
[[ -x "$PYTHON_FIXED" ]] || stop "Required HCI Python absent. No environment creation."
[[ "$(git branch --show-current)" == "$BRANCH" ]] || stop "Wrong branch. Switch manually."
case "$(git remote get-url origin)" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO.git") ;;
  *) stop "Unexpected remote origin." ;;
esac
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]] || stop "Worktree dirty. Do not clean/reset."
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote origin "refs/heads/$BRANCH" | awk 'NR==1 {print $1}')"
[[ -n "$REMOTE_SHA" && "$LOCAL_SHA" == "$REMOTE_SHA" ]] || stop "Local/remote HEAD mismatch or GitHub DNS unavailable."
[[ -f "$MISSION" ]] || stop "Mission document missing."
grep -Fq 'OWNER-AUTHORIZED INTERACTIVE OFFLINE PDM SAFETY MISSION' "$MISSION" || stop "Mission identity mismatch."
codex --help 2>&1 | grep -Fq -- '--approve-for-me' || stop "Current Codex CLI does not support --approve-for-me; no fallback."
printf 'BIRDHOUSE_PDM_PREFLIGHT=PASS\nBRANCH=%s\nHEAD=%s\nMODE=INTERACTIVE_AUTO_REVIEW_SANDBOX\n' "$BRANCH" "$LOCAL_SHA"
if [[ "$#" -eq 1 ]]; then exit 0; fi
[[ -t 0 && -t 1 ]] || stop "Interactive terminal required."
printf 'Offline source/build/test only; Grove V1 must remain on Windows 10, NOT Ubuntu.\n'
read -r -p 'Confirm Grove V1 is NOT connected to this Ubuntu computer (type YES): ' REPLY
[[ "$REPLY" == YES ]] || stop "Hardware must be physically separate."
export BH_PYTHON="$PYTHON_FIXED"
printf 'Opening Codex interactive TUI. No USB, Serial, I2C, Flash, reset or host changes.\n'
exec codex --approve-for-me --no-daemon "$(cat "$MISSION")"
