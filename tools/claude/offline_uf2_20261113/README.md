# Claude Code audit launcher — GitHub-first

**Purpose:** reproducible automatic *offline* research for the Birdhouse Grove Vision AI V1 Windows UF2 write/recovery qualification, not hardware authorization.

1. On the Ubuntu workstation, confirm Grove V1 is connected to the *other Windows 10 computer*, not Ubuntu.
2. On Ubuntu once, check the sandbox dependencies: `command -v bwrap; command -v socat`. If `socat` is missing, review and install `sudo apt-get install socat`; Ubuntu Claude Code sandbox depends on both `bubblewrap` and `socat`. These are **host package installations** the owner performs explicitly, never by Claude.
3. In your existing checkout, switch to the intended research branch only if it is already your research worktree, confirm clean status, and `git pull --ff-only`.
4. From the repository root: `bash tools/claude/offline_uf2_20261113/run.sh --check`.
5. Then: `bash tools/claude/offline_uf2_20261113/run.sh`.

The launcher checks required dependencies, expected research branch, existing HCI interpreter, clean worktree, and local HEAD == remote HEAD. It starts Claude Code in Auto + restricted mode with a mandatory fail-closed sandbox. No bypass permissions. Each session logs privately under `~/birdhouse-private`. If the sandbox is unavailable or an operation is denied, it stops; do not weaken the policy.

The script and prompt are versioned in GitHub. For subsequent tasks, add a **new task directory** with its own launcher/prompt/settings, rather than sending ZIP files. The owner uses `git pull --ff-only` and runs the task-specific script. Public commits must contain no proprietary firmware, vendor binaries, serial values, personal paths, raw logs, or private recordings.
