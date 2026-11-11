# Birdhouse V1 — offline validation report and deployment recommendation

Date: 2026-11-11. Branch: `research/birdhouse-v1-implementation-20261111`.
Target: Seeed Studio Grove Vision AI V1 (Himax HX6537-A). Model fixed: 5 s of 16 kHz mono PCM,
249×40 log-mel, INT8 TFLite Micro.

**Nothing in this phase touched the board.** No flash, erase, reset, bootloader update, UF2
transfer, serial or I2C traffic. A firmware image was produced and validated offline; it has not
been deployed and this report does not authorise deploying it.

Per-milestone detail: `PROGRESS.md`. Machine-readable evidence: `results/`.

## 1. Architecture and justification

```
 vendor Edge Impulse application (unmodified source, unmodified entry point)
   │  main loop calls is_inference_running()            AT console (vendor)
   ▼                                                        │ AT+BIRD* commands
 __wrap_is_inference_running ── bh::RuntimePoll ◄───────────┘
                                   │ start / stop
   PDM mic ─► prebuilt audio library ─► interrupt ─► bh_pdm_port ─► bh_capture
                                                      (copy left channel, 80,000 samples, timing stats)
                                   │ after the last sample, in the main loop
                                   ▼
                    batch log-mel (existing, unchanged) ─► TFLite Micro + ARC MLI ─► decision + report
```

| Choice | Why |
|---|---|
| Keep the vendor application intact | Its boot path, console and microphone initialisation are exercised by other users; if Birdhouse code fails, the vendor part still reports on the hardware. |
| Attach by link-time interposition (`--wrap`) | No vendor file is edited or copied, so nothing derived from vendor code has to be published or maintained. |
| Capture-then-process | The audio library calls back in interrupt context and re-arms each block there; a copy in the interrupt and no time-critical work in the main loop is the simplest design that respects that. RAM is plentiful (590 KB free). |
| Reuse the batch preprocessing unchanged | It already matched the Python reference exactly on the host. |
| Model compiled in, 256 KiB arena | Model is fixed for this phase; the measured requirement is 148.8 KB with an unsafe failure window just below it. |
| Operator overlay header | Re-enables INT8 FULLY_CONNECTED without touching the vendor tree. |
| Diagnostics built in | One flash must yield as much evidence as possible: graded model self-test, synthetic pipeline test, PCM/feature dumps, timing, channel levels, stack high-water mark. |

Changes from the research-phase recommendation, made on implementation evidence: one PCM buffer
instead of two (the gapless path is kept open but not built); no external model slot (model is
fixed); timing irregularities mark a result `SUSPECT`/`CLOCK` instead of aborting, so a wrong
clock assumption cannot block the first demonstration.

## 2. Branch and commits

| Milestone | Commit |
|---|---|
| M0 research assessment | `8a4d8df` |
| M1 operator blocker fix and audit | `b822c5b` |
| M2 host inference validation | `9fd8368` |
| M3 capture architecture and host tests | `7cb1d95` |
| M4 firmware candidate and post-link audit | `ac95ade` |
| M5 packaging validation and this report | the commit that adds this file |

## 3. Source files

New, all own code:

- `firmware/himax_arc/birdhouse/` — `bh_capture`, `bh_pdm_port.cc`, `bh_runtime`, `bh_model`,
  `bh_diag`, `bh_arc_glue.cc`, `bh_config.h`, `bh_port.h`, `bh_selftest_expected.h` (generated),
  `model_manifest.json` (generated), `tflm_overlay/…/trained_model_ops_define.h`,
  `build/birdhouse_overlay.mk`, `build/tflm_config_probe.cc`
- `firmware/himax_arc/tests/` — audio-library emulation, four test suites, inference test, Makefile
- `tools/himax/` — `sdk_make.sh`, `model_manifest.py`, `verify_tflm_ops.py`,
  `gen_tflm_reference.py`, `postlink_audit.py`, `package_offline.py`, `uf2_tool.py`,
  `run_offline_checks.py`

Reused unchanged: `firmware/preprocess/*`, `firmware/model/*`.
Superseded, kept for history: `firmware/himax_arc/experiments/*`.
Not published: vendor SDK, toolchain, build outputs, images, the derived vendor entry file.

## 4. Reproduce

Prerequisites already present locally: vendor SDK and ARC GNU toolchain under `.local-tools/`,
host `g++`, `make`, `bwrap`, and the project Python interpreter (TensorFlow 2.15.1).

```
python3 tools/himax/run_offline_checks.py          # all 19 steps, writes results/
python3 tools/himax/run_offline_checks.py --list
make -C firmware/himax_arc/tests run-all           # host tests only
tools/himax/sdk_make.sh .local-tools/port-himax/bh-candidate -j8   # firmware ELF only
```

The runner refuses to start while a bootloader drive is mounted; the packager also refuses while
any Grove device is attached.

## 5. The INT8 execution blocker is resolved

| Evidence | Result |
|---|---|
| Vendor configuration, compiler-visible macros | FULLY_CONNECTED INT8 gates set (audit fails, as it must) |
| stage50 objects | `Eval` is 46 bytes, no worker code (audit fails, as it must) |
| Host run with vendor configuration | model blocked at `Invoke` |
| Overlay configuration, ARC compiler | gates clear |
| Candidate objects and ELF | `Eval` reaches `EvalMliQuantizedInt8` → `mli_krn_fully_connected_sa8_sa8_sa32`; all five kernels real; registrations linked |
| Host run with overlay configuration | model runs, 28/28 outputs correct |

The audit covers every operator and data type of the model (15 operators, 5 kinds), and an
ARC-only rule found on the way: INT8 Dense nodes must be accepted by the MLI kernel because the
ARC fallback has no INT8 path. Both nodes of this model are.

## 6. Inference validation and its limits

Host, vendor TFLite Micro sources, reference kernels:

- 28 deterministic inputs, raw outputs from −128 to 116, all equal to the TensorFlow Lite
  reference kernels; decisions correct (12 bird, 16 non-bird); tracked reference clip gives 116.
- Arena: 148,800 bytes needed; firmware provides 262,144.
- End to end: emulated audio library → adapter → capture → log-mel → model gives bit-identical
  PCM, features and output to calling preprocessing and the model directly; 40-run soak clean.
- 709 checks in the capture/runtime suites under address and undefined-behaviour sanitizers.

**Not validated, and not claimable from this work:**

- Execution of the ARC MLI kernels (no ARC simulator is installed). TensorFlow Lite's own two
  kernel sets already differ by one output step on 2 of 28 inputs, so small differences on ARC
  would be normal; large ones would not.
- Log-mel on ARC: newlib maths and a software divide may shift some INT8 features by one step.
- Everything about the real microphone, timing and interrupts.

## 7. Memory and packaging

| Region | Used | Size | Free |
|---|---|---|---|
| ICCM1 (code) | 300,230 (91.62 %) | 327,680 | 27,450 |
| SYSTEM0 (data, arena, PCM) | 848,916 (58.96 %) | 1,439,744 | 590,828 |
| DCCM (bss) | 76,960 (30.30 %) | 253,952 | heap 176,992 |
| Stack | known inference chain 1,668 | 8,188 | prebuilt MLI and interrupt frames not counted |

Arena 262,144 bytes; PCM 160,000; features 9,960; DMA ring 16,384 (DCCM, as in the vendor firmware).

Packaging (vendor image generator 2.5.3, run in a sandbox on a copy; vendor `make flash` and
`uf2conv.py` not used):

- image 626,688 bytes (factory image 770,816; Edge Impulse prebuilt 486,144), identical across two runs;
- stored sections exactly `.ivt .vector .text .read_only_data .data .rodata_in_data .sdata`, sizes
  and addresses equal to the ELF; sections left out hold no initial data;
- flash regions 0x0–0x20000 (both Himax bootloaders) and 0x21000–0x22000 byte-identical to the
  factory image;
- application from 0x22000 in 8 chunks, ends at 0x99000, far below the configuration area at 0x1FE000;
- UF2: family 0xEF32C892, 256-byte payloads, 0x10000000–0x10099000; the converter reproduces the
  factory and Edge Impulse UF2 files byte for byte.

The vendor code embeds the build date and time, so each rebuild of the ELF has a different hash;
packaging a given ELF is deterministic. The validated candidate is the one whose ELF, image and UF2
SHA-256 values are recorded in `results/package_candidate.json`. A later hardware step must use
exactly that file, or repeat the checks on the rebuild. The files stay under `.local-tools/` and
are named "OFFLINE_ONLY_do_not_deploy".

## 8. What only hardware can answer

| Question | How the first image answers it |
|---|---|
| Do the ARC MLI kernels compute the same numbers? | `AT+BIRDSELFTEST` (8 graded inputs, expected values built in) |
| Does log-mel on ARC match the host? | `AT+BIRDSYNTH=k`, compare `feature_crc`, else `AT+BIRDFEAT` dump |
| Is audio continuous for 5 s? | `BIRDHOUSE TIMING` (interval min/max, anomalies), `fifo=`, `quality=` |
| Which channel carries the microphone, level, DC settling? | `BIRDHOUSE CHANNELS`, `BIRDHOUSE PCM`, `AT+BIRDPCM` dump |
| Is the CPU clock what the BSP assumes? | `span_us` against `nominal_span_us` |
| Inference and preprocessing time? | `preprocess_us`, `invoke_us` |
| Real arena use and stack depth? | `arena_used`, `stack_peak` in `AT+BIRDINFO?` |
| Does a callback arrive after stop? | `inactive=` |

Still open and resolvable offline with more effort: whether the Himax first-stage bootloader burns
after the full XMODEM transfer or while streaming, and whether it rewrites its own regions.

## 9. Recommendation

**Offline validation gate: PASS.** The candidate is ready for independent review.

**First hardware deployment: NO-GO today.** Not because of a defect found in the candidate, but
because the conditions for a safe write are not met yet:

| Gate | State |
|---|---|
| G1 installed application identified; owner decides what must be preservable | open |
| G2 offline checks on the exact image to be flashed | met (this report) |
| G3 one transport rehearsed without writing (bootloader attach with automount off, ModemManager ignoring the device, passive USB capture) | open |
| G4 recovery kit: factory image verified (done); I2C repair host built and its link proven read-only; BL702 bootloader binary available | partly |
| G5 direct USB port, stable power, nothing else holding the serial port | at deployment time |
| G6 explicit owner approval for that specific action | open |

If and when those are met, the proposed first-session protocol is: boot banner and vendor prompt →
`AT+BIRDINFO?` → `AT+BIRDSELFTEST` → `AT+BIRDSYNTH=0..3` → `AT+BIRDRUN` in silence and with a known
sound → `AT+BIRDPCM=0,80000` and recompute on the host → `AT+BIRDRUN=10`. Stop at the first
unexpected line; every line names its stage.

Known limits of the candidate: 27 KB of code space left; gapless monitoring not implemented;
starting the vendor's own microphone sampling during a Birdhouse capture would conflict; vendor
camera and Edge Impulse functions are linked but were not exercised.
