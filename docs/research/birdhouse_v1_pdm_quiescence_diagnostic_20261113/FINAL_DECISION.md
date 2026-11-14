# Final decision: opt-in PDM shutdown diagnostic

2026-11-13. **DIAGNOSTIC IMPLEMENTED; P1 OPEN; ARTIFACT BLOCKED.** The diagnostic
can detect sampled busy/IRQ state, changed DMA-buffer words, late callbacks and
enable attempts on audited PDM paths. It cannot establish enabled state, the CPU
pending latch, identity of a request surviving reset, every physical write, or
complete bus drain. Those remain **UNOBSERVABLE**; one quiet capture cannot close
all interrupt interleavings. Permanent P1 quarantine is retained. No hardware
experiment, device probe, flash, reset, recovery or Windows automation occurred.

Exact source: P1 baseline `3d0fb3fd4c1889d79462bbc404aee722c1811894` plus the
reviewable uncommitted diagnostic patch. Working-source inventory SHA-256:
`796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e`. SDK remains clean at
`9dc2370d4dc269dc4bcafcf0354b8f745d08801f`.

## Evidence and resulting behavior

- Channel 4/mask 0x10 is corroborated by board/24, the linked descriptor and
  driver code. DMA completion/error IRQs are 24/40; peripheral PDM IRQs are
  separately 69/70/71. No speculative register or banked-IRQ access was added.
- SDK-supported status reads are limited to busy, completion/error history and
  DMA request state. The new ELF contains three AUX loads and no clear/write
  in the status helper, and an uncached load in the buffer helper.
- `AT+BIRDDMA=1` arms once and queues no capture. The sole existing capture then
  stops with unchanged detachment/quarantine and vendor disable/reset sequence.
  A bounded main-context observer records before/after plus 32 timed samples,
  targeting 512 ms. No new ISR print, unrelated IRQ masking or DMA-buffer write.
- Re-arm wrapper calls the original with unchanged arguments; actual PDM read/
  stop linkage was checked. A post-enable latch means an attempt, not proven
  successful bus progress. Instrumentation adds timing/memory overhead and can
  shift the interleaving it measures.
- Final offline validation: **5,590 assertions**, 18 native variants including
  ASan/UBSan; 13 compiled and four static mutants rejected. Original postlink
  **28/28**, operators **83/83**, diagnostic ELF conditions **14/14 PASS**.

Fresh clean ARC ELF, unexecuted/unpackaged:
`.local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf`

**1,667,964 bytes**, SHA-256
`3e350b171ed79ae9cdc96d635475b9f6de921288adbc29aab34905d96db41eee`.
No previous ARC object/ELF was reused. Static resource/stack margins pass policy;
physical stack, timing, microphone and ARC MLI remain unvalidated.

## Specific artifact blocker

The unchanged packaging workflow attempted its required bubblewrap sandbox.
The existing permitted mount guard read reliably and saw no Grove volume.
Sandbox startup failed: **`bwrap: No permissions to create new namespace`**,
packager exit **1**. The vendor generator was not launched. No sandbox flags,
OS/security setting or permission were changed; no host fallback or retry ran.

**New UF2 path, SHA-256, bytes and block count: NONE.** No deterministic image,
ELF/SBS reconstruction or new-UF2 verification could occur. The failed workspace
is preserved. The old verified UF2, factory firmware and previous ELF remain
unchanged and must not substitute for this diagnostic candidate. No current
artifact can be approved for a new physical experiment.

## Minimum later physical experiment

After a separately validated UF2, exact-digest owner write approval and verified
console-open/DTR/mode contract, the minimum is **one** armed normal capture:
identity review, one arm, one `BIRDRUN=1`, wait without further commands, then one
stored diagnostic query after RESULT. No repeated capture or recovery follows.
See the [precise Windows protocol and acceptance table](WINDOWS10_SINGLE_CAPTURE_PROTOCOL.md).

Any positive busy/IRQ/re-arm/callback/buffer-change witness after Stop is a FAIL
for the specified observation. A complete, valid, quiet window is only
PASS_SAMPLED_ONLY. Missing coverage, clock/progress errors or no return are
INCONCLUSIVE. Full quiescence and pending-event identity remain unresolved even
after a sampled PASS; P4 can still hang boot/ISR. Existing write/recovery/backup
uncertainties from first-flash preparation remain open.

The next human decision is an authorized offline environment capable of running
the **unchanged** required sandbox, followed by artifact review. No board action
is the next step in this session.

## Preservation and synchronization

All six previous uncommitted reports and both index/worktree patches were saved
before modification; the previous reports' working bytes were not changed by
this mission. All older binary references were rehashed unchanged. Source and
new reports contain no vendor source dumps, proprietary binaries, audio, machine
paths, device IDs or credentials. Raw evidence stays ignored/private.

**UNCOMMITTED / UNSYNCED.** An earlier commit attempt in this same live mission
failed creating `.git/index.lock` on the read-only filesystem (exit 128). No
metadata escalation or subsequent commit/push was attempted. HEAD remains
`5a94940fcce5708ff686c7aaa18ae5606ee035c6`; matching that old remote HEAD does not
publish this work. The earlier six staged reports remain untouched and stale.

For ordinary Ubuntu-terminal review, the recipe below deliberately commits only
this mission's named source/tests and new reports, preserving the earlier staged
reports for a separate owner decision. Run in the same checkout on the stated
branch. Stop on a hash mismatch or unrelated content. No binary path is staged.

```bash
git branch --show-current
git status --short
sha256sum -- \
  .local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf \
  .local-tools/firmware/grove-ai-v1/factory/grove_ai_v02-00.uf2 \
  .local-tools/port-himax/bh-codex-validated/bh-package/candidate/out/birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2
mission_paths=(
  firmware/himax_arc/birdhouse/bh_pdm_diag.h
  firmware/himax_arc/birdhouse/bh_pdm_port.cc
  firmware/himax_arc/birdhouse/bh_arc_glue.cc
  firmware/himax_arc/birdhouse/bh_console.cc
  firmware/himax_arc/birdhouse/build/birdhouse_overlay.mk
  firmware/himax_arc/tests/Makefile
  firmware/himax_arc/tests/fake_aud_lib.cc
  firmware/himax_arc/tests/fake_aud_lib.h
  firmware/himax_arc/tests/host_port.cc
  firmware/himax_arc/tests/host_port.h
  firmware/himax_arc/tests/test_pdm_diag.cc
  firmware/himax_arc/tests/test_console.cc
  tools/himax/tests/test_pdm_safety.py
  tools/himax/tests/test_pdm_quiescence.py
  docs/research/birdhouse_v1_pdm_quiescence_diagnostic_20261113
)
git diff --check
git add -- "${mission_paths[@]}"
git diff --cached --check
git diff --cached --stat -- "${mission_paths[@]}"
git diff --cached -- "${mission_paths[@]}"
git commit --only -m "feat(himax): add opt-in one-capture PDM shutdown observer" -- "${mission_paths[@]}"
git push origin HEAD:refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git rev-parse HEAD
git ls-remote origin refs/heads/research/birdhouse-v1-first-flash-prep-20261113
git status --short
```

Review the exact staged mission content before commit and do not edit it between
review and commit. Remaining old-report modifications mean the global worktree
will still be dirty after a mission-only commit; review/commit those separately
if desired. Verify the new local/remote SHA before claiming synchronization.
No force push, reset, clean, rebase, branch switch, main merge or permission change.
Publication never supplies hardware authorization.

See [observability evidence](OBSERVABILITY_AND_DESIGN.md),
[offline validation](OFFLINE_VALIDATION.md) and [summary](results/summary.json).
