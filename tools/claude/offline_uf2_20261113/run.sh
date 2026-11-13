#!/usr/bin/env bash
# Birdhouse: offline-only Claude Code audit. No hardware or system configuration changes.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
BRANCH="research/birdhouse-v1-predeployment-codex-20261111"
export BH_PYTHON="${BH_PYTHON:-$(dirname "$ROOT")/HCI Tagging Database/HCI/bin/python3}"
fail() { printf 'BLOCKED: %s\n' "$*" >&2; exit 2; }
for exe in claude git bwrap socat; do
  if ! command -v "$exe" >/dev/null 2>&1; then
    fail "Missing $exe. On Ubuntu, review and install sandbox dependencies: sudo apt-get install bubblewrap socat. Never disable sandbox to continue."
  fi
done
[[ -x "$BH_PYTHON" ]] || fail 'Mandatory existing HCI Python interpreter not found. Set BH_PYTHON to that existing interpreter; do not create an environment.'
[[ "$(git -C "$ROOT" branch --show-current)" == "$BRANCH" ]] || fail 'Wrong research branch; no automatic checkout.'
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=normal)" ]] || fail 'Working tree is not clean; inspect changes manually.'
LOCAL="$(git -C "$ROOT" rev-parse HEAD)"
REMOTE="$(git -C "$ROOT" ls-remote --heads origin "$BRANCH" | awk 'NR==1{print $1}')"
[[ -n "$REMOTE" && "$LOCAL" == "$REMOTE" ]] || fail 'Local HEAD is not synchronized with the research branch on GitHub.'
[[ -s "$SCRIPT_DIR/CLAUDE_AUDIT_PROMPT.md" && -s "$SCRIPT_DIR/SAFETY_SYSTEM_PROMPT.md" && -s "$SCRIPT_DIR/claude_session_settings.json" ]] || fail 'Missing prompt, boundary or settings.'
if [[ "${1:-}" == "--check" ]]; then
  printf 'CHECK_OK: sandbox dependencies, HCI Python, clean branch and matching remote HEAD.\n'
  exit 0
fi
[[ $# == 0 ]] || fail 'Supported argument: --check'
printf '%s\n' 'OFFLINE AUDIT ONLY: do not connect Grove V1 to this Ubuntu computer.'
read -r -p 'Confirm Grove V1 is NOT connected to this Ubuntu computer (type YES): ' REPLY
[[ "$REPLY" == YES ]] || fail 'Physical separation not confirmed.'
RUN_DIR="$HOME/birdhouse-private/claude-offline-$(date -u +%Y%m%dT%H%M%SZ)"
(umask 077; mkdir -p "$RUN_DIR")
chmod 700 "$RUN_DIR"
printf 'Starting Claude Code in Auto mode with mandatory sandbox.\nPrivate output: %s\n' "$RUN_DIR/claude-output.txt"
cd "$ROOT"
set +e
claude -p "$(cat "$SCRIPT_DIR/CLAUDE_AUDIT_PROMPT.md")" \
  --permission-mode auto --restricted \
  --tools 'Bash,Read,Edit,Write,Glob,Grep,WebFetch,WebSearch' \
  --disallowedTools 'mcp__*' \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-chrome \
  --settings "$SCRIPT_DIR/claude_session_settings.json" \
  --append-system-prompt-file "$SCRIPT_DIR/SAFETY_SYSTEM_PROMPT.md" \
  --permission-prompts none --max-turns 110 --output-format text 2>&1 \
  | tee "$RUN_DIR/claude-output.txt"
RC=${PIPESTATUS[0]}
set -e
printf 'Claude exit code: %s\n' "$RC"
printf 'Local HEAD: %s\n' "$(git rev-parse HEAD)"
printf 'Remote HEAD: %s\n' "$(git ls-remote --heads origin "$BRANCH" | awk 'NR==1{print $1}')"
git status --short
[[ "$RC" == 0 ]] || fail 'Claude was blocked/failed. Inspect private log; no automatic recovery.'
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || fail 'Review uncommitted changes; never clean automatically.'
[[ "$(git rev-parse HEAD)" == "$(git ls-remote --heads origin "$BRANCH" | awk 'NR==1{print $1}')" ]] || fail 'Remote synchronization needs review.'
printf 'SESSION_FINISHED: repository synchronized and worktree clean; physical Flash remains NO-GO.\n'
