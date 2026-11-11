# Birdhouse V1 implementation — progress record

Branch: `research/birdhouse-v1-implementation-20261111`
Target: Seeed Studio Grove Vision AI V1 (Himax HX6537-A). Model fixed: 5 s, 16 kHz mono, 249×40 log-mel, INT8.

Hardware boundary for this whole phase: no flash, erase, reset, bootloader update, UF2 transfer,
serial or I2C traffic, or any other interaction with the physical board. Everything below is offline.

Reproduce all checks (project interpreter, existing SDK and ARC toolchain under `.local-tools/`):

```
python3 tools/himax/run_offline_checks.py            # every step
python3 tools/himax/run_offline_checks.py --list     # what the steps are
```

Evidence lives in `results/` next to this file: `summary.md`, `summary.json`, one log per step
(local paths removed) and the operator-audit JSON files.

## Milestones

| # | Milestone | Status | Commit |
|---|---|---|---|
| M0 | Project state recovered; research assessment saved | PASS | `8a4d8df` |
| M1 | Model-execution blocker reproduced, fixed by overlay, guarded by an automated audit | PASS | `b822c5b` |
| M2 | Offline TFLite Micro execution validated on host (reference kernels) | PASS | `9fd8368` |
| M3 | Audio capture architecture implemented and host-tested | PASS | `7cb1d95` |
| M4 | Firmware candidate built; post-link audit | PASS | `ac95ade` |
| M5 | Offline packaging and image validation; final report | PASS | `bffed70` |

## M0 — project state

- Research branch local and remote were identical (`db25a2b`); implementation branch created from it.
- Untracked local files preserved. The derived vendor entry point (`…step48.cc`) is now ignored by
  `.gitignore` so it cannot be published by accident.
- Research assessment: `docs/research/birdhouse_v1_deployment_rethink_20261111/CLAUDE_RESEARCH_REPORT.md`.

## M1 — INT8 FULLY_CONNECTED blocker

**Finding reproduced.** The vendor TFLite Micro tree reads
`tflite-model/trained_model_ops_define.h`, generated for the vendor's bundled camera model. It sets
`EI_TFLITE_DISABLE_FULLY_CONNECTED_IN_I8` and `…_OUT_I8`. With those set, the ARC kernel's `Eval`
compiles to a 46-byte function that returns an error, and `Prepare` rejects MLI-applicable INT8 nodes.

**Fix.** `firmware/himax_arc/birdhouse/tflm_overlay/tflite-model/trained_model_ops_define.h` is put
in front of the vendor include path by the build overlay. It includes the vendor header unchanged
(`#include_next`) and re-enables only the two gates the model needs. No vendor file is edited.

**Audit of the whole operator set** (`tools/himax/verify_tflm_ops.py`), three layers:

1. compatibility — every operator and tensor type against what the kernels accept;
2. configuration — the macro state the ARC compiler really sees, dumped with the firmware flags;
3. objects — each kernel's `Eval` in the compiled object is not a stub.

Model operators (from the tracked model array, sha256 `9e04d177…`): CONV_2D ×6, DEPTHWISE_CONV_2D ×5,
MEAN ×1, FULLY_CONNECTED ×2, LOGISTIC ×1; all INT8 activations, INT8 filters, INT32 bias.
Only FULLY_CONNECTED was gated off. MEAN and LOGISTIC have no per-type gate in the kernel sources.

**Second ARC-only constraint found while fixing.** In the ARC backend the fully-connected fallback
path has no INT8 case, so every INT8 Dense node must be accepted by the MLI kernel. Both nodes of
this model are (output zero point −128 with fused ReLU; no activation on the last). The audit now
checks this from the model's quantisation, so a future model cannot violate it silently.

**Evidence**

| Step | Result |
|---|---|
| `m1_01` manifest reproducible from the tracked array | PASS |
| `m1_02` ARC configuration with overlay passes the audit | PASS |
| `m1_03` vendor configuration is rejected (negative control) | PASS — fails on exactly the two FULLY_CONNECTED gates |
| `m1_04` stage50 build is rejected (negative control) | PASS — gates set, `Eval` size 46 with no worker code |

ARC kernel objects compiled with the overlay: `Eval` dispatches to `EvalMliQuantizedInt8`
(852 bytes), which calls `mli_krn_fully_connected_sa8_sa8_sa32`. The full object and link audit of
the firmware candidate is part of M4.

**Risk left open.** The ARC MLI kernels are compiled and linked but cannot be executed offline; no
ARC simulator is installed. See M2.

## M2 — offline inference

**What ran.** The vendor TFLite Micro sources (157 files, unmodified, compiled in place) built for
x86-64 with the reference kernels, driven through the firmware's own wrapper
`firmware/himax_arc/birdhouse/bh_model.cc`. Reference outputs come from the TensorFlow Lite
interpreter (TF 2.15.1, reference kernels) on 28 deterministic inputs that both sides generate from
the same integer rules; a hash of every input is checked before it is used.

| Check | Result |
|---|---|
| Model load, operator registration, `AllocateTensors` | PASS |
| Input tensor INT8 `[1,40,249,1]`, 9,960 bytes, scale 0.0200184, zero point −67 | PASS |
| Output tensor INT8, scale 1/256, zero point −128; bird threshold is raw output ≥ 45 | PASS |
| `Invoke` on 28 inputs, raw output equal to TensorFlow Lite | PASS — 28/28, maximum difference 0 |
| Bird / non-bird decision on all inputs (12 bird, 16 non-bird) | PASS |
| Tracked reference clip gives 116 (p = 0.953, bird) | PASS |
| Repeated inference, reverse order, re-initialisation in between | PASS — identical outputs |
| Error handling: null arguments, corrupt identifier, use before init, arena too small | PASS |
| Arena guard zones untouched | PASS |
| Negative control: vendor operator configuration | PASS — `Invoke` fails as predicted |

**Arena.** Host measurement (64-bit pointers, reference kernels): 148,800 bytes used; that is also
the minimum that initialises. The previous 160 KiB arena would have left 15,040 bytes on this
measurement. Directly below the minimum there is a window (148,592–148,752 bytes) where TFLite Micro
fails only through a debug assertion; the firmware is built with `NDEBUG`, where that case would
write through a null pointer instead of returning an error. The candidate firmware therefore uses
256 KiB, and reports the measured use at start. The ARC figure will differ (32-bit pointers, plus
MLI bookkeeping) and can only be read on the device.

**Other observations**

- TensorFlow Lite's own optimised and reference kernels differ by one output step on 2 of the 28
  inputs. One-step differences between kernel implementations are therefore normal for this model;
  the ARC MLI kernels may show the same.
- The input tensor is overwritten during `Invoke` (its memory is reused). The firmware must refill
  it before every inference; the new pipeline does.

**Limitation, stated plainly.** This validates operator coverage, configuration, tensor contracts,
arena sizing and the numeric results of the *reference* kernels. It does not execute the ARC MLI
kernels. ARC numeric behaviour stays unverified until the firmware's built-in self-test runs on the
board or an ARC simulator becomes available.

## M3 — audio capture architecture

**Decision: capture-then-process, vendor application kept intact.** The stage50 design (per-sample
queue with interrupt masking, streaming log-mel in the main loop, a modified copy of the vendor
entry point) is replaced. Reasons, each backed by the research evidence:

- The audio library calls the application inside the DMA-complete interrupt and re-arms the next
  block from there. The binding constraint is interrupt latency at block boundaries, not the 20 ms
  feature hop. Doing only a copy in the interrupt and nothing time-critical in the main loop is the
  simplest design that respects it — and it is what the vendor's own ingestion code does.
- About 590 KB of SYSTEM0 RAM is free even after a 256 KiB arena, so a linear 160 KB PCM buffer costs nothing that matters.
- The batch preprocessing (`firmware/preprocess/audio_preprocess.cc`) already matched Python
  exactly on the host. It is reused unchanged; the duplicated streaming FFT is not linked.
- No derived vendor file: the module is attached with two link-time interpositions and registers
  its own AT commands on the vendor console.

**What was implemented** (`firmware/himax_arc/birdhouse/`)

| File | Role |
|---|---|
| `bh_capture` | Interrupt-side core: drops the settle blocks, copies the left channel into the linear buffer, stops at exactly 80,000 samples, keeps timing and channel statistics. Lock-free by ownership rules written in the header. |
| `bh_pdm_port.cc` | Adapter to the prebuilt audio library; validates block address and count; always returns blocks to the library; `stop` never blocks a later `start`. |
| `bh_runtime` | State machine IDLE → CAPTURING → DONE/FAILED, failure stage and detail, repeat runs, timeout, cancel, diagnostics and dumps. |
| `bh_diag` | CRC-32, PCM statistics, base64, deterministic integer test signals. |
| `bh_model` | TFLite Micro wrapper (M2). |
| `bh_arc_glue.cc` | Himax-only: AT commands, the two wrappers, stack high-water mark. |

**Integrity of a recording.** The library hides overruns and FIFO overflows. They are detected here:

- PDM FIFO overflow: the library's recovery path calls `hx_drv_pdm_deinit`; that call is
  interposed and fails the run (`FIFO_OVERFLOW`).
- Stalled callbacks / ring overrun inside the library: callback spacing is measured; irregular
  spacing marks the result `SUSPECT` (a decision is still printed for diagnosis).
- Wrong time base (for example a CPU clock the BSP did not expect): regular spacing that
  disagrees with the nominal 128 ms marks the result `CLOCK`, so it cannot be mistaken for lost audio.
- The vendor clock's one-tick (1 s) reading error is recognised and counted, not treated as loss.
- Block address or count outside the ring, library errors, start/stop failures and a main-loop
  deadline (8 s) each fail the run with their own code.

**Path to continuous monitoring without redesign.** The interrupt side writes into a buffer it is
handed; processing is decoupled from capture. Gapless operation needs a second 160 KB buffer and a
swap at completion instead of a stop (RAM is available: 590 KB free). Not implemented now, to keep
the first image small in risk; nothing in the current structure has to change for it.

**Host tests** (`firmware/himax_arc/tests/`, built with `-Wall -Wextra -Werror`, C++11, address and
undefined-behaviour sanitizers). The audio library is emulated from the disassembly findings
(index rules, contiguous reads, silent overrun reset, callback threshold).

| Suite | Checks | Covers |
|---|---|---|
| `test_diag` | 71 | CRC check value, base64 RFC vectors, statistics, signal determinism |
| `test_capture` | 280 | exact 80,000 samples, settle drop, 1/2/3/mixed blocks per callback, targets on and off block boundaries, guard zones, invalid arguments, incomplete recording, FIFO event before/after completion, stall → SUSPECT, scaled clock → CLOCK, one-tick clock steps, reuse |
| `test_pdm_port` | 75 | ring wraps, start/stop errors, stop failure no longer sticks, library errors, bad address, held-off interrupts (library overrun detected), late callback after stop |
| `test_runtime` | 283 | microphone path equals the direct pipeline bit for bit, nothing printed during capture, 5 queued runs, 40-run soak, timeout, incomplete recording, every failure stage, cancel, model-init failure before audio starts, dumps decode back to the buffers, report format |

**Not provable on the host:** behaviour of the real PDM front end (gain, DC settling, which channel
carries the microphone), real interrupt latency, whether a callback can arrive after `stop`, real
timing. The first image reports each of these (`BIRDHOUSE CAPTURE/TIMING/CHANNELS/PCM` lines).

## M4 — firmware candidate

Built out of tree with `tools/himax/sdk_make.sh` (vendor makefile + `build/birdhouse_overlay.mk`).
The vendor SDK tree is unmodified after every build (checked by `m4_05`).

| Region | Vendor only | Candidate | Size | Free |
|---|---|---|---|---|
| ICCM1 (code) | 269,834 | 300,230 (91.62 %) | 327,680 | 27,450 |
| SYSTEM0 (data, big buffers) | 292,484 | 848,916 (58.96 %) | 1,439,744 | 590,828 |
| DCCM (bss + heap) | 54,672 | 76,960 (30.30 %) | 253,952 | heap 176,992 |
| Stack | 8,188 | 8,188 | — | known inference chain 1,668 bytes (20 %) |

Buffers: tensor arena 262,144 bytes and PCM 160,000 bytes in SYSTEM0; features 9,960 bytes in
SYSTEM0; DMA ring 16,384 bytes in DCCM, 32-byte aligned (same region the vendor firmware uses for
its own DMA buffer).

Post-link audit (`tools/himax/postlink_audit.py`, 24 checks, all PASS):

- every section inside its linker region; margins above policy (16 KiB code, 256 KiB data, 128 KiB heap);
- model bytes inside the ELF are identical to the tracked model array (sha256 `9e04d177…`);
- both wrappers are linked, the vendor main loop calls the wrapper twice and the original zero
  times, the audio library's de-init path calls the wrapper, each wrapper reaches the original;
- no symbol of the stage50 design is linked;
- stack: frame sizes from `-fstack-usage` summed along main loop → wrapper → runtime → interpreter →
  largest kernel worker. Not included: prebuilt MLI assembly, interrupt frames, C start-up. The
  firmware paints the stack and reports the real high-water mark in `AT+BIRDINFO?`.

Operator audit of the candidate (`m4_03`): configuration, kernel objects and registrations in the ELF all PASS.

**Console commands of the candidate** (vendor AT console, 921600 baud in normal mode):
`AT+BIRDINFO?`, `AT+BIRDRUN`, `AT+BIRDRUN=n`, `AT+BIRDSTOP`, `AT+BIRDLAST?`, `AT+BIRDSELFTEST`,
`AT+BIRDSELFTEST=k`, `AT+BIRDSYNTH=k`, `AT+BIRDPCM=offset,count`, `AT+BIRDFEAT=offset,count`.

`AT+BIRDSELFTEST` needs no microphone: eight graded inputs give outputs from −128 to 116 and are
compared with the TensorFlow Lite reference values. That is the first on-device evidence of ARC MLI
numeric behaviour. Expected host values: `results/expected_device_values.json`.

**Open risks after M4**

- ARC MLI execution, real audio, timing and stack depth remain unmeasured (hardware only).
- 27 KB of code space is left; further features must be weighed against it.
- The vendor application's other functions (camera, Edge Impulse ingestion) are untouched but were
  not exercised; starting vendor microphone sampling during a Birdhouse capture would conflict.

## M5 — offline packaging

Procedure (`tools/himax/package_offline.py`): the Linux parts of the vendor image generator are
copied to a work directory and run there inside a bubblewrap sandbox (rest of the filesystem
read-only, no serial or block devices, empty `/media`, no network). The vendor `make flash` target
is not used; it would write into the SDK tree. The vendor `uf2conv.py` is not used either: without
`-c` it searches for a board, switches it into bootloader mode and copies the file to any mounted
bootloader drive, and it installs Python packages if they are missing. UF2 conversion is done by
`tools/himax/uf2_tool.py`, which only converts files.

Validation (40 checks, all PASS; `results/package_candidate.json`):

| Group | What was shown |
|---|---|
| generate | generator 2.5.3 succeeds in the sandbox; two runs on the same ELF give the same image |
| content | exactly `.ivt .vector .text .read_only_data .data .rodata_in_data .sdata` are stored, with ELF sizes and addresses; sections left out hold no initial data (`.gcc_except_table` is dropped by the vendor flow for every build); sampled windows of every stored section and the Birdhouse console strings are present in the image |
| layout | 626,688 bytes; application at 0x22000 in 8 chunks of 64 KiB; ends at 0x99000; no overlap; below the configuration area at 0x1FE000 |
| bootloader | 0x0–0x10000, 0x10000–0x20000 and 0x21000–0x22000 byte-identical to the factory image; both bootloaders equal the SDK binaries for `HX6537-A09TDIG-1111V` |
| uf2 | converter reproduces the factory and the Edge Impulse UF2 byte for byte; candidate UF2 has family 0xEF32C892, 256-byte payloads, contiguous addresses 0x10000000–0x10099000 |

Size in context: factory image 770,816 bytes, candidate 626,688, Edge Impulse prebuilt 486,144.

**Build identity.** The vendor code embeds the build date and time, so every rebuild of the ELF has
a different hash; packaging a given ELF is deterministic. The candidate that passed all checks is
identified by the hashes in `results/package_candidate.json`. Any later hardware step must use that
exact file (verify its SHA-256), not a fresh rebuild, or the checks must be run again on the rebuild.

**Not done, by instruction:** no file was copied to any drive, no device was contacted. The outputs
are under `.local-tools/port-himax/bh-package/candidate/out/` and are named
`…OFFLINE_ONLY_do_not_deploy.uf2`.

See `OFFLINE_VALIDATION_REPORT.md` for the consolidated result and the deployment recommendation.
