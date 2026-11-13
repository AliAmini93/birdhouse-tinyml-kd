# Birdhouse first-flash preparation — live interactive Codex

This dedicated GitHub-first mission generates and validates a NEW P1-mitigated firmware ELF/image/UF2 **offline**. It does not write to, probe, reset or communicate with the Grove Vision AI V1. The existing board stays on a separate Windows 10 PC. The output UF2 is private under the ignored local .local-tools tree, NOT published in this public repository.

Ubuntu launch:

    cd "/mnt/HDD/AliWorks/birdhouse-tinyml-kd"
    git fetch origin
    git switch --track origin/research/birdhouse-v1-first-flash-prep-20261113
    git merge --ff-only origin/research/birdhouse-v1-first-flash-prep-20261113
    bash scripts/agents/launch_birdhouse_first_flash_prep_codex.sh --check
    bash scripts/agents/launch_birdhouse_first_flash_prep_codex.sh

If branch exists locally, use git switch research/birdhouse-v1-first-flash-prep-20261113 instead of the --track command; do not reset or discard edits. The launcher verifies branch, HEAD parity, clean worktree, required fixed HCI Python, bubblewrap, and Codex CLI; starts LIVE interactive Codex with automatic approval review and restricted workspace sandbox. No codex exec, no ZIP installation, no headless fallback.

Codex must inspect source and test exact new files, then use the existing audited offline SDK build and sandboxed packaging tools. It must not copy to GROVEAI or run any device/flash utility. Packaging vendor generator is sandboxed separately and may be blocked under the Codex sandbox; that is an explicit BLOCKED finding, not a reason to loosen security.

If Codex reports that .git is read-only, use an ordinary Ubuntu terminal to review the six new text reports and stage/commit/push them. Do not add .local-tools or generated ELF/image/UF2 to public GitHub; a successful git push only publishes sanitized evidence and does NOT transport the private UF2 to Windows.

This milestone ends with ARTIFACT_READY_FOR_OWNER_RISK_DECISION or BLOCKED. Before any actual Windows flash, require a reviewed UF2 SHA-256, separately explicit acceptance of potential irreversible damage to the only board, and operator-controlled one-time manual transfer under a new go/no-go review. P1 permanent quarantine and P4 vendor deadlock risk remain, and factory UF2 is not guaranteed recovery.
