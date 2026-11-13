# Final decision: offline PDM safety mission

2026-11-13. **First Flash, real capture and recovery execution: NO-GO.**
Offline software containment and validation are complete. Publication is blocked
by read-only Git metadata; the changes remain reviewable in this worktree, not
committed or synchronized. This mission grants no physical deployment authority.

## Disposition

| Item | Status | Practical consequence |
|---|---|---|
| P1 | PARTIALLY_MITIGATED_FAIL_CLOSED | Permanent quarantine after stop/partial start prevents a subsequent first-party Capture owner. No successful stop/retry can reopen it. DMA re-arm/quiescence remains OPEN. |
| P2 | VERIFIED_LIMIT | Strengthened ISR model and negative controls test software containment, not the real interrupt/peripheral. |
| P3 | VERIFIED_LIMIT | API success still does not establish progress; a host no-progress case times out and quarantines only while main context runs. |
| P4 | VENDOR_LEVEL_BLOCKED | Boot and FIFO-error ISR can still reach the unbounded ready poll. No justified first-party timeout patch. |
| Host validation | PASS | Eight suites, ordinary + ASan/UBSan: 5,048 assertions; seven compiled mutants and four static mutants rejected. |
| ARC validation | PASS, incremental/offline only | Ten first-party cross-compiles, cached-vendor relink, 28 post-link checks; host-only reset absent. No packaging, execution or clean SDK rebuild claim. |
| Publication | GIT_METADATA_READ_ONLY / UNSYNCED_CHANGES | Normal push of the unchanged HEAD succeeds; new work is absent from both local commit history and remote. |

Read the [R0 contract](R0_BASELINE_AND_CONTRACT.md),
[P1 reasoning](P1_ISR_STOP_RACE_REMEDIATION.md),
[P4 call-path decision](P4_BOOT_ISR_POLLING_DECISION.md),
[test/build matrix](OFFLINE_TEST_AND_BUILD_MATRIX.md), and
[sanitized machine summary](results/summary.json).

The final diff was challenged against the actual vendor ISR in both the original
and newly linked ELF. Detachment remains necessary for owner lifetime, but occurs
after vendor re-arm during a callback. Reset indices or successful stop cannot
prove a clean next run. The chosen code never attempts that next run. Keeping
IRQs masked through stop or inventing an acknowledgment was rejected because it
would not establish the missing hardware contract. No vendor binary/register
patch was attempted. Test fixtures explicitly emulate fresh process state; no
same-device restart soak or physical P4 return test is claimed.

## What must precede a separately human-approved Windows 10 Flash

1. Resolve P1 channel-local stop/drain/ack/in-flight semantics, including pending
   completion after reset, re-arm suppression and safe initial state; supply the
   vendor evidence and qualification required for a real stop. Quarantine alone
   does not close this gate or qualify repeated captures/reboots.
2. Obtain a vendor bounded-open/error-recovery repair and prove every boot/ISR
   path, cleanup and status propagation as detailed in the P4 report. A console
   may never become available if boot or ISR blocks.
3. Close the existing installed BL702 write-mechanism, address/erase, completion,
   verification, preservation/backup or explicit loss-acceptance, and independent
   full-image Himax recovery gates, including damaged loader cases. The Windows
   ten-minute visible read result establishes only limited read stability.
4. Independently review the exact future source/artifact and a staged Windows 10
   write/stop/failure protocol, qualify transport/power and recovery, and obtain
   explicit new owner authorization. Later real capture must separately measure
   progress, microphone/channel/rate, cache/continuity, timing, actual MLI numerics,
   memory/stack, stop quiescence and error behavior. None was measured here.

These prerequisites do not ask for any hardware experiment now. No action on the
separate Windows PC was possible or attempted. No hardware discovery, serial,
MSC, I2C, GPIO, boot/reset, deployment utility, power/service/driver change,
installation, privilege escalation or sandbox-configuration change occurred.
Existing candidate images and the SDK are unchanged; all new binaries/logs stay
ignored and private. Reports and first-party sources contain no raw audio, USB
logs, device identifiers/hashes, credentials, proprietary code or personal paths.

## Git checkpoints and ordinary-terminal completion

Starting and currently observed local HEAD:
`d6b67707251d24791030cd51700830e56330bcdd`.
Normal `git ls-remote` reports the same SHA for
`refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113`.
Requested source baseline remains `5361a74143f909d6cc113f4cf0a9b35e8614240a`.
No branch switch, forced push, reset, clean, rebase or main merge occurred.

R0 staging/commit and the combined R1/R2 staging checkpoint were refused because
`.git/index.lock` cannot be created on this read-only filesystem. The actual R0
commit command therefore failed too; no commit exists for the new work. Normal
pushes returned "Everything up-to-date" and remote comparisons matched the old
HEAD, while status showed the new uncommitted files. This is **not SYNC_OK** and
not NETWORK_BLOCKED. No automatic-approval escalation was attempted or rejected;
the failure is the enforced filesystem restriction itself. It was not bypassed.
The final R3/publication checkpoint is subject to the same restriction and its
observed result is recorded in summary.json.

The owner can review and commit from an ordinary terminal in the same authorized
checkout, without changing sandbox/host permissions. These commands explicitly
stage only this mission's reviewed files; run them on the dedicated branch only:

```sh
git branch --show-current
git diff --check
git diff --stat
git add -- \
  firmware/himax_arc/birdhouse/bh_arc_glue.cc \
  firmware/himax_arc/birdhouse/bh_console.cc \
  firmware/himax_arc/birdhouse/bh_pdm_port.cc \
  firmware/himax_arc/birdhouse/bh_port.h \
  firmware/himax_arc/birdhouse/bh_runtime.cc \
  firmware/himax_arc/birdhouse/bh_runtime.h \
  firmware/himax_arc/tests/fake_aud_lib.cc \
  firmware/himax_arc/tests/fake_aud_lib.h \
  firmware/himax_arc/tests/host_port.cc \
  firmware/himax_arc/tests/host_port.h \
  firmware/himax_arc/tests/test_console.cc \
  firmware/himax_arc/tests/test_pdm_port.cc \
  firmware/himax_arc/tests/test_pdm_lifecycle.cc \
  firmware/himax_arc/tests/test_runtime.cc \
  tools/himax/tests/test_pdm_safety.py \
  docs/research/birdhouse_v1_pdm_safety_20261113/R0_BASELINE_AND_CONTRACT.md \
  docs/research/birdhouse_v1_pdm_safety_20261113/P1_ISR_STOP_RACE_REMEDIATION.md \
  docs/research/birdhouse_v1_pdm_safety_20261113/P4_BOOT_ISR_POLLING_DECISION.md \
  docs/research/birdhouse_v1_pdm_safety_20261113/OFFLINE_TEST_AND_BUILD_MATRIX.md \
  docs/research/birdhouse_v1_pdm_safety_20261113/FINAL_GO_NO_GO.md \
  docs/research/birdhouse_v1_pdm_safety_20261113/results/summary.json
git diff --cached --check
git diff --cached --stat
git commit -m "fix(himax): quarantine unproven PDM restart and validate ISR containment offline"
git push origin HEAD:refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113
git rev-parse HEAD
git ls-remote origin refs/heads/research/birdhouse-v1-pdm-safety-offline-20261113
git status --porcelain
```

Only a new matching local/remote commit SHA **and** empty final status would
establish synchronization of this work. A later commit does not retroactively
change the observed unsynchronized state recorded in this report. If a future
ordinary push encounters DNS restrictions, stop retries and retain the commit;
do not change network/sandbox settings or force push. Git publication itself
never supplies Flash authorization.
