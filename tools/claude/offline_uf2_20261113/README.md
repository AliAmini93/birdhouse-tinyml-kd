# Legacy Claude offline UF2 audit launcher

This directory records the earlier Claude Code (headless) audit setup for provenance. **It is superseded** by the interactive Codex workflow in `scripts/agents/launch_birdhouse_windows_uf2_codex.sh`. Its `run.sh` now redirects to the new interactive launcher (including `--check`). Do not use the historical Claude command or `claude -p`: all agent-led Birdhouse tasks are to be interactive.

See `docs/agents/BIRDHOUSE_CODEX_INTERACTIVE_README.md` for the current GitHub-first workflow.
