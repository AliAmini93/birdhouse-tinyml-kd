# Audit preservation and publication

Only this new audit directory is part of the current read-only investigation.
The existing six first-flash reports, diagnostic source/tests and diagnostic
reports were already pending when it started. Their contents are preserved;
this audit does not silently include them in its own commit or discard them to
obtain an artificial clean worktree.

The public evidence is limited to the
[aggregate findings](FORENSIC_CONSOLE_AUDIT.md) and
[structured parameters/hash manifest](results/summary.json). All binaries, maps,
vendor source, actual command arrays and raw logs remain ignored under
`.local-tools/`. No firmware input or output was regenerated or modified.

Validation passed: JSON parsing, report links, privacy scan, all 60 evidence-file
digests, all 98 recorded source identities, unchanged preexisting pending file
contents, repeated artifact hashes and a new independent full 2,461-block UF2
parse/image comparison. Existing package and postlink results were inspected;
no build/test/generation workflow was rerun. Tracked worktree and staged diff
whitespace checks passed. The UF2 and raw evidence paths are ignored.

**UNCOMMITTED / UNSYNCED: Git metadata is read-only.** The ordinary `git add` of
only this audit directory returned 0, but `git commit --only` returned 128:
`.git/index.lock: Read-only file system`. No permission change, escalation or
push followed. This was a filesystem failure, not an automatic approval-review
rejection. The updated publication record and summary now differ from their
earlier staged snapshot, so re-add them before committing.

Local HEAD and the dedicated branch's GitHub HEAD were independently read as
`5a94940fcce5708ff686c7aaa18ae5606ee035c6`. The GitHub check used the commits API
with this branch as `sha`, not a stale local remote-tracking ref. That equality
does not publish pending reports or diagnostic source. The worktree remains
dirty, including preexisting changes; no synchronization/clean-worktree success
is claimed.

In an ordinary Ubuntu terminal, review and commit only this audit as follows.
Run each stage deliberately; stop on a different branch, either digest mismatch,
unexpected staged content or command failure. No binary path is added to Git.

```bash
git branch --show-current
git status --short
sha256sum -- \
  .local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/package-native-terminal-01/out/birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2 \
  .local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf
```

Required branch: `research/birdhouse-v1-first-flash-prep-20261113`.
Required UF2: `0eb316e68ba5b88c407d9f2f907891bab722820077e40de8d93f167d746f9cf8`.
Required ELF: `3e350b171ed79ae9cdc96d635475b9f6de921288adbc29aab34905d96db41eee`.

```bash
audit_paths=(docs/research/birdhouse_v1_console_forensic_20261114)
git diff --check
git add -- "${audit_paths[@]}"
git diff --cached --check
git diff --cached --stat -- "${audit_paths[@]}"
git diff --cached -- "${audit_paths[@]}"
git commit --only -m "docs(himax): audit exact diagnostic UF2 console and bridge assumptions" -- "${audit_paths[@]}"
git push origin HEAD:refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git rev-parse HEAD
git ls-remote origin refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git status --short
```

Verify the two newly read HEAD values are equal. This audit-only recipe preserves
the previously staged reports and pending diagnostic source; it will not by
itself produce a globally clean worktree. Review and commit that earlier work
separately, using the explicit source/test list in the
[diagnostic publication record](../birdhouse_v1_pdm_quiescence_diagnostic_20261113/FINAL_DECISION.md)
and the six-report list in the
[first-flash publication record](../birdhouse_v1_first_flash_prep_20261113/FINAL_ARTIFACT_DECISION.md).
Those dated reports describe their historical packaging failures; the new
[forensic audit](FORENSIC_CONSOLE_AUDIT.md) supplies the later exact artifact
evidence. After all reviewed work is committed, repeat a normal push, compare
local/remote HEAD and require empty `git status --porcelain` before declaring
global synchronization complete. Do not discard existing changes to obtain that
result. No force push, reset, clean, rebase, branch switch or main merge is needed.
Git publication does not provide hardware authorization.
