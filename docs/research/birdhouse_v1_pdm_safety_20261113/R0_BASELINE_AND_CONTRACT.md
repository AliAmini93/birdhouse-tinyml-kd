# R0 baseline and acceptance contract

2026-11-13. **Offline research only. Flash and real capture: NO-GO.**
This file was created before any firmware or test change in this mission.
Interactive foreground work only; the owner can steer or interrupt. No agents,
Codex exec, hardware operations, installs, vendor execution or packaging.

## Frozen source and evidence

- Repository: public `AliAmini93/birdhouse-tinyml-kd`.
- Dedicated branch: `research/birdhouse-v1-pdm-safety-offline-20261113`.
- Requested source baseline: `5361a74143f909d6cc113f4cf0a9b35e8614240a`.
- Observed starting HEAD: `d6b67707251d24791030cd51700830e56330bcdd`.
  Its only changes since the baseline are three mission/launcher files. Firmware
  and tools are identical to the requested baseline. Initial worktree is clean.
- Existing ELF: SHA-256 `8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f`.
  It and previous candidate images/results will remain untouched and unpublished.
- SDK checkout is local, ignored and read-only. Vendor source/disassembly is
  inspected as data, never reproduced in these reports or committed.

Read first: [deployment assessment](../birdhouse_v1_deployment_barriers_20261111/ASSESSMENT.md),
[static evidence](../birdhouse_v1_deployment_barriers_20261111/results/barrier_audit.json),
[Windows decision](../birdhouse_v1_windows_uf2_write_audit_20261113/FINAL_GO_NO_GO.md),
[recovery gates](../birdhouse_v1_windows_uf2_write_audit_20261113/RECOVERY_AND_ROLLBACK_GATES.md),
[write mechanism](../birdhouse_v1_windows_uf2_write_audit_20261113/UF2_WRITE_MECHANISM_AUDIT.md),
[predeployment handoff](../birdhouse_v1_codex_predeployment_20261111/HANDOFF_REPORT.md),
[validated summary](../birdhouse_v1_codex_predeployment_20261111/results/validated/summary.json),
and [implementation report](../birdhouse_v1_implementation_20261111/OFFLINE_VALIDATION_REPORT.md).
Earlier claims that a successful retry establishes restart safety, or that a
console will always be available, are explicitly not adopted.

Source links: [adapter](../../../firmware/himax_arc/birdhouse/bh_pdm_port.cc),
[capture ownership](../../../firmware/himax_arc/birdhouse/bh_capture.h),
[runtime](../../../firmware/himax_arc/birdhouse/bh_runtime.cc),
[glue](../../../firmware/himax_arc/birdhouse/bh_arc_glue.cc),
[fake](../../../firmware/himax_arc/tests/fake_aud_lib.cc),
[original analyzer](../../../tools/himax/audit_deployment_barriers.py).
Binary addresses below refer only to the frozen ELF, not to a rebuilt artifact:

| Evidence | Frozen symbol / address | Consequence |
|---|---|---|
| P1 | `pdm_rx0_rx_ISR`, 0x1002a018 | RX callback precedes completion acknowledgment. |
| P1 | `hx_lib_audio_rx_callback`, 0x10024024 | Re-arm precedes application callback. |
| P1 | `io_pdm_rx_stop`, 0x1002a460 | Disable/reset, no explicit completion clear. Reset semantics unknown. |
| P1 | adapter stop, 0x10002620 | Restore interrupts before vendor stop; detach protects only Capture. |
| P3 | `hx_lib_audio_start`, 0x10024200 | Lower transfer status is discarded. Success does not prove DMA progress. |
| P4 | `io_pdm_rx_open`, 0x1002a0f8 | Ready-bit loop has no software bound. Boot and error ISR can reach it. |

## Acceptance criteria and alternatives (fixed before patching)

1. Examine at least two approaches: a channel-local synchronized stop/ack/restart
   protocol using documented APIs; and permanent fail-closed lifecycle quarantine
   after a transfer attempt if that hardware contract cannot be proved. A
   first-party wrapper is also evaluated for P4, with a complete boot/ISR path.
2. Retain the intentional start IRQ mask around DMA enable, queue publication
   and owner publication. Restore the exact caller IRQ state on every path.
   Stop detachment must remain brief; do not mask PCM copies or unbounded vendor
   calls. No guessed registers, global DMA clear, channel reset assumption or
   changes to other channels.
3. No old completion can attach to a subsequent first-party Capture. If physical
   quiescence is unknown, a successful vendor stop/retry must never reopen start.
   Partial-start failure, stop failure and destroyed owners must remain safe.
   Quarantine is containment, not proof that DMA stopped, nor a safe reboot plan.
4. Strengthen the model with peripheral completion pending state, IRQ exclusion,
   re-arm before application callback, acknowledgment after callback, stop
   interleavings, both reset/pending hypotheses, start-without-progress, failures,
   and ring wrap. Clearly distinguish modeled order from unknown hardware.
5. Adversarial tests must reject deliberately broken restart/owner/mask behavior
   with failing test assertions, not a compile error. Keep existing capture,
   diagnostics, runtime, console, model and preprocessing regressions where
   applicable; revise restart expectations explicitly if quarantine is selected.
   Any test-only lifecycle reset must be absent from production ARC objects.
6. P4 closes only with a genuine bounded implementation on *all* boot and ISR
   paths and meaningful error propagation. A deadline in the main loop, fake
   success, watchdog or clock in another context is insufficient. If unavailable,
   report `VENDOR_LEVEL_BLOCKED` and precise vendor prerequisites.
7. Offline passes never claim peripheral quiescence, measured timing, real MLI
   numerics, USB write qualification, recovery readiness or Flash authorization.

## Command audit and exact reproduction plan

Every research/test Python invocation uses the existing owner-mandated interpreter
in `BH_PYTHON`, with `-I -B` where supported. No interpreter install or environment
creation. Local absolute personal paths must not appear in published outputs.
Raw command/build/disassembly logs stay in ignored storage or temporary files.

Reviewed `tests/Makefile`: native compilation, static archiving and host test
execution only. Its dependency-discovery stderr redirection names a system null
path, so direct compiler invocations are preferred for this strict mission.
Reviewed `sdk_make.sh` and overlay: default ELF only; argument allowlist, inherited
make injection cleared, separate output root. Vendor rules distinguish `all`/ELF
from forbidden flash/image/OTA/run targets. ARC work remains conditional on audit
of the exact expanded compiler/link commands and all operands before execution;
no automatic full vendor build is authorized merely by this note.

Do **not** run `run_offline_checks.py`, `package_offline.py`, `test_offline_tools.py`
or broad unittest discovery: the older runner inspects mount state and invokes
packaging; the packager can inspect USB metadata and executes a vendor generator.
The old barrier CLI also reads cached private logs and unrelated loader material;
its CLI/full suite is unnecessary. Reuse its pure PDM analysis functions only,
with explicit import path under isolated Python, if needed.

Exact focused command (new test module will state its compiler operand lists):

```sh
"$BH_PYTHON" -I -B -m unittest discover -s tools/himax/tests -p test_pdm_safety.py -v
```

Native focused build, from repository root (new output; no device paths):

```sh
mkdir -p .local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH/host
g++ -std=c++11 -O2 -g -Wall -Wextra -Werror -DBIRDHOUSE_HOST_BUILD=1 -I. firmware/himax_arc/tests/test_pdm_port.cc firmware/himax_arc/tests/fake_aud_lib.cc firmware/himax_arc/tests/host_port.cc firmware/himax_arc/birdhouse/bh_pdm_port.cc firmware/himax_arc/birdhouse/bh_capture.cc -o .local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH/host/test_pdm_port
.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH/host/test_pdm_port
```

Sanitizers add `-fsanitize=address,undefined -fno-omit-frame-pointer` and
`ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1`. Leak detection is not
claimed. Full native regression commands and any audited ARC commands will be
recorded verbatim in the build matrix before they are executed. New source lists
and model tests may use existing validated host kernel archives as inert link
inputs; provenance and instrumentation must be checked.

## Publication and phase checkpoints

Only authorized first-party source/tests and the six new sanitized reports may
be committed. No vendor excerpts, binaries, raw/private logs, audio, device
identifiers or their hashes. Explicit-file staging, diff/JSON/link/privacy checks,
then a normal commit/push to this branch at each logical phase. No hook scripts
are active in the inspected repository. On sandbox DNS failure stop network
retries, retain local commits and report `NETWORK_BLOCKED`, never `SYNC_OK`.
No branch switch, forced push, destructive git command, main merge, privileged
command or sandbox escalation.

## Baseline SHA-256 (first-party regular source files)

| Repository-relative file | SHA-256 |
|---|---|
| `firmware/himax_arc/birdhouse/bh_pdm_port.cc` | `400a48acdfcf713993faaccae1ca195c2e193331fc6398228b4470109c9ee376` |
| `firmware/himax_arc/birdhouse/bh_capture.cc` | `a61a1af02a84b5d0fcdb3d8d590455fe842293954c5708617d20ba357583d6e3` |
| `firmware/himax_arc/birdhouse/bh_capture.h` | `cba9f40d822567f0a9dcf0a71b21f90a35a0c53535001488c9c6708a29dbebff` |
| `firmware/himax_arc/birdhouse/bh_port.h` | `e47c6d2f6dfdfd4670d9ec11efc7553d5723e56984fa13cd8784f7d01c330d1f` |
| `firmware/himax_arc/birdhouse/bh_runtime.cc` | `992101c6f5fe72076613d9968fd6a2636965426fd7f7578a5c5cd5df6fd370bd` |
| `firmware/himax_arc/birdhouse/bh_arc_glue.cc` | `f8bf3ae273f6f24473cf54515531a31683e9575f6aa86631071a5e992006987d` |
| `firmware/himax_arc/birdhouse/bh_config.h` | `529a30b24286bac2e2f3483f5ff4a9849145da511a51e37f8aa53d87ea2c196c` |
| `firmware/himax_arc/tests/fake_aud_lib.cc` | `a5fbff21c52f708d62ee4c61c9217929c0b6b2bdc546d7f997746c35bb4433ee` |
| `firmware/himax_arc/tests/fake_aud_lib.h` | `c625eacbb3e68cdb158f53bf61f2aaddbade72cdaddb98c199d5244ae7661ce5` |
| `firmware/himax_arc/tests/test_pdm_port.cc` | `8a347a73ddcbed16d7ab261c3240430b2656b282c550cf40449ee44ba80d9fb8` |
| `firmware/himax_arc/tests/test_capture.cc` | `07491270d50fb3a1a1e739ac1b1b92156b40cdbf88e169cc200a41e0bf05b01f` |
| `firmware/himax_arc/tests/test_runtime.cc` | `75535163054b3f24c3f5851b5636af6805efbed888d539a71e2325d335507fa4` |
| `firmware/himax_arc/tests/host_port.cc` | `c8b949927891a28c912e50a1722aaf5cdf02ea80d4da5745dcfe2fab348f08d2` |
| `firmware/himax_arc/tests/Makefile` | `f5e1f1ff8b8efdf8c49ae88a2ae499f183bd102698198264fd20fd333a39c5a4` |
| `tools/himax/audit_deployment_barriers.py` | `036ad76d9498091faef7be0194a7056b867727c4b2d51cf57d6a0fc4cd0b46e9` |
| `tools/himax/tests/test_deployment_barriers.py` | `47e01033a72ec3238b7ae9e5f5096cba758330e0c56b151de91f5460c82d2982` |
