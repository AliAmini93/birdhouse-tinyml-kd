#!/usr/bin/env bash
# LIVE INTERACTIVE Codex only. Offline build/package for a possible FIRST flash.
set -Eeuo pipefail
ROOT="/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
REPO="AliAmini93/birdhouse-tinyml-kd"
BRANCH="research/birdhouse-v1-first-flash-prep-20261113"
MISSION="docs/agents/CODEX_BIRDHOUSE_FIRST_FLASH_OFFLINE_PREP_20261113.md"
PYTHON_FIXED="/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3"
stop() { printf 'BIRDHOUSE_FLASH_PREP_STOP: %s\n' "$*" >&2; exit 2; }

[[ $# -eq 0 || ( $# -eq 1 && "$1" == "--check" ) ]] || stop "Only --check is accepted."
[[ -d "$ROOT/.git" ]] || stop "Expected Git checkout absent."
cd "$ROOT"
command -v git >/dev/null 2>&1 || stop "git is missing."
command -v codex >/dev/null 2>&1 || stop "Codex CLI is missing."
command -v bwrap >/dev/null 2>&1 || stop "bubblewrap is missing. Do not remove the packaging sandbox."
[[ -x "$PYTHON_FIXED" ]] || stop "Fixed HCI Python absent. Do not create a venv."
[[ "$(git branch --show-current)" == "$BRANCH" ]] || stop "Wrong branch; switch manually without reset."
case "$(git remote get-url origin)" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO.git") ;;
  *) stop "Unexpected remote origin." ;;
esac
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]] || stop "Working tree dirty. Never clean/reset it."
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote origin "refs/heads/$BRANCH" | awk 'NR==1 {print $1}')"
[[ -n "$REMOTE_SHA" && "$LOCAL_SHA" == "$REMOTE_SHA" ]] || stop "Local and remote HEAD differ, or GitHub unreachable."
[[ -f "$MISSION" ]] || stop "Mission document missing."
grep -Fq 'OWNER-AUTHORIZED INTERACTIVE OFFLINE FIRST-FLASH PREPARATION MISSION' "$MISSION" || stop "Mission identity mismatch."
codex --help 2>&1 | grep -Fq -- '--approve-for-me' || stop "Required sandbox/approval preset unsupported. Do not use yolo or headless mode."
printf 'BIRDHOUSE_FIRST_FLASH_PREP_PREFLIGHT=PASS\nBRANCH=%s\nHEAD=%s\nMODE=INTERACTIVE_CODEX_SANDBOX\n' "$BRANCH" "$LOCAL_SHA"
if [[ "$#" -eq 1 ]]; then exit 0; fi
[[ -t 0 && -t 1 ]] || stop "Real interactive terminal required."
printf 'Prepare files OFFLINE only. This program cannot flash a device or contact Windows.\n'
read -r -p 'Confirm Grove V1 is NOT connected to this Ubuntu machine (type YES): ' REPLY
[[ "$REPLY" == YES ]] || stop "Keep physical board on the separate Windows computer."
export BH_PYTHON="$PYTHON_FIXED"
exec codex --approve-for-me --no-daemon "$(cat "$MISSION")"
