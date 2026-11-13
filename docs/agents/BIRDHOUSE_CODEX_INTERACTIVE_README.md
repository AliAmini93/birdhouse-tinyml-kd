# Birdhouse — Interactive Codex launcher (GitHub-first)

**Only interactive agent sessions are authorized for this project's agent workflows.** Do NOT use `codex exec`, `claude -p`, cron, nohup or background agents for tasks launched through this workflow.

One-time requirement: Codex CLI must be installed and logged in on Ubuntu and support the documented `--approve-for-me` option. This provides automatic approval review together with the `workspace-write` sandbox; it is not an unrestricted bypass. If unavailable, the launcher stops rather than silently switching modes.

On Ubuntu (board remains on the separate Windows 10 PC):

```bash
cd "/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
git fetch origin
git switch research/birdhouse-v1-predeployment-codex-20261111
git merge --ff-only origin/research/birdhouse-v1-predeployment-codex-20261111
bash scripts/agents/launch_birdhouse_windows_uf2_codex.sh --check
bash scripts/agents/launch_birdhouse_windows_uf2_codex.sh
```

The script requires a real TTY, verifies the exact clean research branch, GitHub remote HEAD and the existing HCI Python binary. It asks the owner to confirm the device is not attached to Ubuntu. It then `exec`s **interactive** `codex --approve-for-me` with the versioned task prompt as its initial user input. No `codex exec`, no redirection of the TUI output to a log, no non-interactive fallback.

The automatic approval reviewer and OS sandbox **do not guarantee that every unsafe action is impossible**. Keep the board on Windows and decline any attempt to change host settings, bypass the sandbox or interact with hardware. Only sanitized findings may be committed and pushed. GitHub sync is checked by comparing local/remote HEAD and clean worktree.

An old Claude launch script at `tools/claude/offline_uf2_20261113/run.sh` redirects to the interactive Codex launcher for backwards compatibility. The old Claude prompt files are historical and do not run.

For future tasks: publish a new versioned mission file and interactive Codex launcher to the research branch; then fetch/fast-forward and run locally. No ZIP distribution.
