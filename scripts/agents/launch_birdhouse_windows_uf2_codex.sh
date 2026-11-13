#!/usr/bin/env bash
# INTERACTIVE Codex TUI only. No codex exec / -p, no headless fallback.
# This is an offline RESEARCH mission, not an authorization to contact hardware.
set -Eeuo pipefail

ROOT="/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
REPO="AliAmini93/birdhouse-tinyml-kd"
BRANCH="research/birdhouse-v1-predeployment-codex-20261111"
PYTHON_FIXED="/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3"
MISSION="docs/agents/CODEX_BIRDHOUSE_WINDOWS_UF2_OFFLINE_20261113.md"

stop() { printf 'BIRDHOUSE_CODEX_PREFLIGHT_STOP: %s\n' "$*" >&2; exit 2; }

[[ $# -eq 0 || ( $# -eq 1 && "$1" == "--check" ) ]] || stop "Only --check is supported."
[[ -d "$ROOT/.git" ]] || stop "Birdhouse Git checkout not found."
cd "$ROOT"
command -v git >/dev/null 2>&1 || stop "git not found."
command -v codex >/dev/null 2>&1 || stop "Codex CLI not found. Check 'command -v codex' without installing anything automatically."
[[ -x "$PYTHON_FIXED" ]] || stop "Mandatory existing HCI Python missing (never create another venv)."
[[ "$(git branch --show-current)" == "$BRANCH" ]] || stop "Wrong branch. Switch deliberately, do not reset."
case "$(git remote get-url origin)" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO.git") ;;
  *) stop "Origin is not the expected GitHub repository." ;;
esac
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]] || stop "Uncommitted files detected; review them without reset or clean."
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote origin "refs/heads/$BRANCH" | awk 'NR==1 {print $1}')"
[[ -n "$REMOTE_SHA" && "$LOCAL_SHA" == "$REMOTE_SHA" ]] || stop "Branch is not synchronized. Run git fetch and git merge --ff-only manually."
[[ -f "$MISSION" ]] || stop "Versioned mission file absent."
grep -Fq 'OWNER-AUTHORIZED INTERACTIVE OFFLINE AUDIT MISSION' "$MISSION" || stop "Mission identity mismatch."

# Fail closed if this version cannot provide sandboxed automatic approval review.
codex --help 2>&1 | grep -Fq -- '--approve-for-me' || stop "Installed Codex lacks --approve-for-me; do not switch to --yolo or a headless mode."

printf 'BIRDHOUSE_CODEX_PREFLIGHT=PASS\n'
printf 'REPO=%s\nBRANCH=%s\nHEAD=%s\n' "$REPO" "$BRANCH" "$LOCAL_SHA"
printf 'PYTHON=%s\nMODE=INTERACTIVE_CODEX_TUI_AUTOMATIC_REVIEW_WITH_WORKSPACE_SANDBOX\n' "$PYTHON_FIXED"
if [[ "${1:-}" == "--check" ]]; then exit 0; fi

[[ -t 0 && -t 1 ]] || stop "Interactive terminal required. Never run via nohup, cron, or a pipe."
printf '\nThis mission may ONLY examine offline evidence. Grove V1 must remain connected to the other Windows 10 PC, not Ubuntu.\n'
read -r -p 'Confirm Grove V1 is NOT connected to this Ubuntu computer (type YES): ' CONFIRM
[[ "$CONFIRM" == YES ]] || stop "Physical separation not confirmed."
export BH_PYTHON="$PYTHON_FIXED"
printf 'Opening the INTERACTIVE Codex TUI with the versioned mission.\n'
printf 'Do not approve requests for hardware access, host changes, flashing or sandbox bypass.\n'
printf 'If the built-in sandbox is unavailable, stop rather than weakening permissions.\n'

# PROMPT is an argument to interactive codex, not 'codex exec'.
# --approve-for-me enables automatic approval review + workspace-write sandbox.
# No --sandbox/--ask-for-approval flags because these conflict with this preset.
exec codex --approve-for-me --no-daemon "$(cat "$MISSION")"
