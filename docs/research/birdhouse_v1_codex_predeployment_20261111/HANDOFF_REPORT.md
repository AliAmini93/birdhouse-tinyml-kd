# Birdhouse Grove Vision AI V1 — Codex predeployment handoff

2026-11-11. Starting source: `120a72831db4d36904848a2b92e5a366d3ae5451`.
Branch: `research/birdhouse-v1-predeployment-codex-20261111`. No merge to main.

Follow-up from `1095349`: [independent deployment-barrier assessment](../birdhouse_v1_deployment_barriers_20261111/ASSESSMENT.md)
narrows normal PDM startup risk, qualifies the late-callback evidence, adds cached
recovery analysis and proposes an observer-only session. The candidate is unchanged.

**Offline checks: PASS, 22/22. Physical deployment: NO-GO. Recovery readiness:
BLOCKED.** No serial, USB-device enumeration, I2C, JTAG, board reset, flash,
UF2 transfer or mounted-device access was performed. Only reviewed source and
public-safe summaries are published; SDK, toolchain, binaries, raw logs and audio
remain local.

## Findings and repairs

- **Interrupt ownership:** detach the ISR target under saved/restored IRQ state
  before stopping. Failed stop quarantines restart until an explicit successful
  stop retry. Partial start gets cleanup. Late callbacks cannot dereference a
  former/destroyed capture, change its stats, or access the library ring. Main
  cancellation/timeout latches errors only after detachment. ARC call sites use
  real IRQ primitives; host tests inject the relevant API interleavings.
- **Result validity:** CLOCK/SUSPECT audio retains raw diagnostic inference but
  prints `decision=NONE` and cancels queued runs. Tick-sized gaps cannot be assumed
  harmless; unexpected batch sizes invalidate timing. Backward BSP readings no
  longer underflow the deadline. Dumps expose only this sequence's valid samples
  or features, including only an aborted capture's prefix.
- **Serial integration:** first-party handlers now run in host tests through the
  actual vendor AT server/parser. Fixed signed/overflowing counts, ignored extra
  arguments, silent busy requests, queued-work clobbering, and an all-whitespace
  parser exception. The pinned parser ABI interposition is checked in the ARC
  ELF. Vendor sampling/camera AT starts are guarded while Birdhouse owns work;
  Birdhouse refuses active vendor inference/streaming. Concurrent I2C operation
  is outside the qualified scope.
- **Evidence quality:** vendor TFLM objects now receive ASan/UBSan instrumentation
  and dependency tracking. The legacy preprocessing test now exits nonzero on
  failed parity. Reference regeneration checks all three files without rewriting
  tracked sources. Partial runs cannot inherit old passes. Warning attribution
  handles interleaved parallel-make output. ARC selection must equal 1, and the
  final ELF must retain real INT8 MLI workers.
- **Build/package isolation:** safe make arguments are allowlisted and inherited
  make injection options cleared. Previous candidates/results are preserved.
  Packaging supplies the existing ARC tools explicitly, runs with devices,
  USB metadata, media, host sockets and network hidden, and verifies every stored
  ELF byte and destination from the image's binary descriptors. Corruption
  mutations fail. File conversion rejects invalid/empty images and unsafe or
  existing output paths. No auto-deployment utility was used.

## Evidence and exact candidate

[Complete fresh results](results/validated/summary.json),
[operator audit](results/validated/ops_candidate.json),
[post-link audit](results/validated/postlink_candidate.json),
[packaging checks](results/validated/package_candidate.json).

- **796 assertions** across six sanitized suites; real vendor kernel/parser
  instrumentation independently checked. Leak detection was disabled because
  LeakSanitizer cannot operate under the sandbox tracer; no leak claim is made.
- **28/28** model outputs bit-exact against TensorFlow Lite reference kernels;
  586 model-test assertions. These execute host reference kernels, not ARC MLI.
- Preprocessing matches all **9,960** stored Python-oracle feature elements.
  The integration tests also compare captured PCM/features, run a 40-capture
  soak, and exercise errors, stop retry, cancellation and dump provenance.
- **83 operator checks, 28 post-link checks, 41 packaging checks PASS.**
- Two independent clean ARC builds produce the identical ELF. Pinning
  `SOURCE_DATE_EPOCH=1794355200` fixes vendor date/time strings. Two independent
  packaging runs on that ELF produce the identical image.

| Artifact, local only | Bytes | SHA-256 |
|---|---:|---|
| ELF | 1,650,872 | `8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f` |
| Image | 628,016 | `c2d7e176436433f714633bc817cec3bc232c8fabd62389567be518358b6de388` |
| UF2 | 1,256,448 | `009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae` |

ELF: `.local-tools/port-himax/bh-codex-validated/bh-candidate/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf`.
Packaged files: `.local-tools/port-himax/bh-codex-validated/bh-package/candidate/out/`;
UF2 is named `birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2`.
The source fingerprint in the complete results matches the final reviewed inputs;
HEAD alone would not identify the uncommitted tree used during validation.

## Practical limits and gates

Static capacity fits: ICCM1 code 301,310 / 327,680 bytes; SYSTEM0 849,188 /
1,439,744 bytes; heap capacity 176,992 bytes. The linked allocator checks the
linker heap end. Capacity is not current free heap. Host arena use is 148,800
bytes versus a 262,144-byte candidate arena; ARC allocation remains unmeasured.
The actual linker stack is **8,188 bytes**, regardless of larger compiler macros.
Its partial frame sum is **1,664 bytes**, not a bound or a measured peak; prebuilt
MLI, nested helpers, preprocessing/libm, serial allocation and interrupt paths
are omitted. Stack painting measures only use since painting.

Unresolved physical gates: actual ARC/MLI and newlib numerical results, PDM
channel/gain/settling/sample rate, DMA continuity and cache behavior, interrupt
latency/rearm/pending-stop behavior, an externally checked clock and deadlines,
latency, allocator/stack headroom and sustained error recovery. Timestamp-based
CLEAN is a diagnostic heuristic, not proof that no samples were lost. The model
wrapper assumes the compiled, hash-verified model; it is not a general parser for
untrusted external flatbuffers. The vendor console is a diagnostic interface;
arbitrary input/heap-exhaustion hardening is not claimed.

Two factory fallback copies are verified, but neither backs up this board.
BL702 recovery binary, audited Arduino repair source and its toolchain are absent.
Matching bootloader bytes does not prove safe erase ranges or power-loss recovery.
[Recovery review and proposed future protocol](RECOVERY_REVIEW.md) lists the
owner/ChatGPT review, asset, preservation and transport gates. No hardware action
is approved by this handoff, and offline success does not close those gates.

## Reproduce offline

From the repository root, set `BH_PYTHON` to the session-mandated existing absolute
HCI Python executable. Use new result/work directory names on each full run:

```sh
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 "$BH_PYTHON" -u tools/himax/run_offline_checks.py --results-dir docs/research/birdhouse_v1_codex_predeployment_20261111/results/recheck --work-root .local-tools/port-himax/bh-codex-recheck
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 make -C firmware/himax_arc/tests -j8 run-unit SAN=1
make -C firmware/himax_arc/tests -j8 run-tflm
tools/himax/sdk_make.sh .local-tools/port-himax/bh-codex-rebuild -j8
"$BH_PYTHON" -m unittest discover -s tools/himax/tests -v
```

Bubblewrap namespace creation requires the separately approved execution context
used here. Do not weaken its isolation if the outer sandbox prevents it. Exact
commands, milestones, repaired negative controls and prior synchronization checks
are recorded in [PROGRESS.md](PROGRESS.md). Raw build/test logs remain local.
