# Final artifact decision — 2026-11-13

**BLOCKED: BUBBLEWRAP_NAMESPACE_CREATION_DENIED.** The fresh clean P1 ELF passed
focused regression and postlink/operator checks. The existing isolated packager
exited 1 when bubblewrap reported `No permissions to create new namespace`.
No new image or UF2 was produced. New UF2 location, SHA-256, byte size and block
count are **unavailable**. No older package was substituted or relabeled.

The owner's narrow follow-up resolved the earlier mount-guard policy conflict:
the existing guard remains unchanged and its permitted passive read completed
reliably with no Grove volume detected. The owner explicitly confirmed the board
remains physically connected only to the separate Windows 10 machine. No active
probe or board/Windows operation occurred. No guard removal is proposed now.

## Results of the resumed offline work

| Item | Result |
|---|---|
| Source `3d0fb3fd4c1889d79462bbc404aee722c1811894` | PASS: all 95 firmware/tool files identical; no first-party patch |
| SDK `9dc2370d4dc269dc4bcafcf0354b8f745d08801f` | PASS, clean before/after |
| Focused regressions | PASS: four unittest methods, 16 variants, 5,048 assertions, seven compiled and four static mutants rejected |
| Fresh clean ARC build | PASS, exit 0; no earlier ARC object/ELF used |
| ELF lineage | Whole fresh ELF identical to incremental P1 reference |
| Postlink / model / hooks / resources | 28/28 PASS |
| Operator macros / fresh kernels / linked workers | 83/83 PASS |
| Production host reset/fake/test/sanitizer symbols | Absent |
| Package output-root constraints | PASS: existing, outside and symlink-escaping roots rejected before generation |
| Existing passive mount guard | Preserved; reliable reads; no Grove volume detected |
| Sandbox / image generation | BLOCKED at required namespace creation; generator not launched |
| Deterministic image / SBS reconstruction / new UF2 checks | NOT RUN: no generated image/UF2 |
| Exact-digest owner write approval | Absent; record remains blank |

Fresh ELF, **not a UF2 and not executed**:
`.local-tools/port-himax/first-flash-prep-20261113-OFFLINE_ONLY-3/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf`

Size **1,650,872 bytes**, SHA-256
`bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af`.
The clean build reproduces the exact required P1 source and previously incremental
ELF bytes. It did not reuse that reference as a build input. See
[provenance and resource limits](BUILD_AND_SOURCE_PROVENANCE.md) and
[packaging failure evidence](FIRMWARE_UF2_VALIDATION.md).

The failed package root is preserved privately. Bubblewrap flags, verifier,
source, SDK, old candidates and official factory file remain unchanged. No
sandbox bypass, host generator fallback, OS change or permission escalation was
attempted. The diagnostic's precise kernel/security-policy cause was not probed.

## Windows decision and physical uncertainties

The [inactive text-only kit](WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md) conditionally
recommends **one direct new P1 Birdhouse write** after all artifact gates pass and
the owner signs the exact digest/procedure. Factory rehearsal then Birdhouse
means two potentially destructive full writes; rehearsal adds only evidence for
its particular successful case and does not qualify independent recovery. No
failure probability or physical safety guarantee is supplied. **Zero writes are
currently enabled.**

G1 preservation, G2 installed updater, G3 actual Windows WRITE10/programming and
G4 independent full Himax recovery remain OPEN/unqualified. There is no qualified
independent complete backup. The sole board and installed settings/calibration
could be permanently lost. P1 is first-party one-attempt quarantine, not proven
pending-DMA/stop quiescence. P4 remains `VENDOR_LEVEL_BLOCKED`: boot or ISR can
hang before the main loop/console helps. Real ARC MLI, microphone, timing and
actual stack remain physically unvalidated. Packaged-image boot remains UNKNOWN.

The next human decision concerns an authorized offline environment capable of
starting the **unchanged required sandbox**. This session stops without changing
system policy or weakening isolation. No device command is the next step.
After successful packaging and all remaining independent checks, a later owner
approval must name the new full UF2 SHA-256, exact size and step-by-step one-time
Windows Explorer write, with explicit permanent-loss acceptance in the
[unsigned record](OWNER_RISK_ACCEPTANCE_RECORD.md). No console/AT+ or microphone
access follows automatically; those need a verified console contract and new
explicit scope. Real microphone use remains exactly one future attempt.

## Publication state and ordinary Ubuntu completion

**REPORTS_UNCOMMITTED_AND_UNSYNCED.** The earlier ordinary commit attempt in this
same live mission failed with exit 128 because `.git/index.lock` could not be
created on the read-only filesystem. No permission change or escalation occurred;
this was not an automatic-approval review rejection. After the follow-up, no
Git mutation was retried. All six reports now have updated working-tree content;
the earlier staged snapshot is stale. No new-content push was attempted.

Local and remote branch HEAD remain
`5a94940fcce5708ff686c7aaa18ae5606ee035c6`; matching this old HEAD does not
synchronize the new reports. The worktree is not clean. Raw logs, command arrays,
per-file fingerprints and every binary/vendor input remain ignored and private.
Only the six sanitized reports are eligible for the owner's later commit.

Use the same authorized checkout in an ordinary Ubuntu terminal. Stop if the
branch differs, hashes differ from the [identity table](FIRMWARE_UF2_VALIDATION.md),
or unrelated staged files appear. There is no new UF2 to rehash; this recipe
rehashes the **fresh unpackaged ELF**, official factory and excluded old UF2.
None becomes an approved flash candidate through Git publication.

```sh
git branch --show-current
git status --short
sha256sum -- \
  .local-tools/port-himax/first-flash-prep-20261113-OFFLINE_ONLY-3/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf \
  .local-tools/firmware/grove-ai-v1/factory/grove_ai_v02-00.uf2 \
  .local-tools/port-himax/bh-codex-validated/bh-package/candidate/out/birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2
git diff --check
git add -- \
  docs/research/birdhouse_v1_first_flash_prep_20261113/BUILD_AND_SOURCE_PROVENANCE.md \
  docs/research/birdhouse_v1_first_flash_prep_20261113/FIRMWARE_UF2_VALIDATION.md \
  docs/research/birdhouse_v1_first_flash_prep_20261113/WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md \
  docs/research/birdhouse_v1_first_flash_prep_20261113/OWNER_RISK_ACCEPTANCE_RECORD.md \
  docs/research/birdhouse_v1_first_flash_prep_20261113/FINAL_ARTIFACT_DECISION.md \
  docs/research/birdhouse_v1_first_flash_prep_20261113/results/summary.json
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
git diff --cached
git commit -m "docs: record clean P1 build and namespace-blocked first-flash packaging"
git push origin HEAD:refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git rev-parse HEAD
git ls-remote origin refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git status --porcelain
```

Review the staged content before commit: exactly these six sanitized text files,
no binaries or source changes. Only a new matching local/remote commit and empty
status establish synchronization. No force push, reset, clean, rebase, branch
switch, main merge or permission change is part of the recipe.

See [machine-readable summary](results/summary.json).
