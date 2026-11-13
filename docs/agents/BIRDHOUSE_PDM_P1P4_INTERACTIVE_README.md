# Birdhouse P1/P4 — interactive Codex from GitHub

Dedicated safe-development branch: research/birdhouse-v1-pdm-safety-offline-20261113. Previous validated branch/images are preserved. This starts a LIVE terminal TUI; no ZIP, codex exec or headless run.

On Ubuntu, while the Grove V1 stays on the other Windows 10 PC:

    cd "/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
    git fetch origin
    git switch --track origin/research/birdhouse-v1-pdm-safety-offline-20261113
    git merge --ff-only origin/research/birdhouse-v1-pdm-safety-offline-20261113
    bash scripts/agents/launch_birdhouse_pdm_safety_codex.sh --check
    bash scripts/agents/launch_birdhouse_pdm_safety_codex.sh

If branch already exists locally, use git switch research/birdhouse-v1-pdm-safety-offline-20261113 instead of --track. Do not reset/clean a dirty tree to switch. The launcher verifies clean status, branch identity, mandated HCI Python and local==remote HEAD before starting. It runs interactive codex --approve-for-me --no-daemon, which requires the CLI's sandbox/automatic-review feature. Review all unusual permission requests; this is not an absolute hardware isolation guarantee.

Outputs: only first-party source/tests and sanitized reports; no vendor binaries, private identifiers, or firmware builds on GitHub. Codex attempts normal Git push. If the sandbox has DNS problems, stop agent retries and use a normal Ubuntu terminal after separately reviewing contents:

    git status --short
    git show --stat --oneline HEAD
    git ls-remote origin refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113
    git push origin HEAD:refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113
    git rev-parse HEAD
    git ls-remote origin refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113
    git status --short

Never force push or overwrite conflicts. This is an OFFLINE code-quality milestone, not a Flash authorization.
