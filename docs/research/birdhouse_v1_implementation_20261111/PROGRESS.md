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
| M1 | Model-execution blocker reproduced, fixed by overlay, guarded by an automated audit | PASS | see git log |
| M2 | Offline TFLite Micro execution validated on host (reference kernels) | PASS | see git log |
| M3 | Audio capture architecture implemented and host-tested | pending | |
| M4 | Firmware candidate built; post-link audit | pending | |
| M5 | Offline packaging and image validation | pending | |

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
interpreter (TF 2.15.1, reference kernels) on 26 deterministic inputs that both sides generate from
the same integer rules; a hash of every input is checked before it is used.

| Check | Result |
|---|---|
| Model load, operator registration, `AllocateTensors` | PASS |
| Input tensor INT8 `[1,40,249,1]`, 9,960 bytes, scale 0.0200184, zero point −67 | PASS |
| Output tensor INT8, scale 1/256, zero point −128; bird threshold is raw output ≥ 45 | PASS |
| `Invoke` on 26 inputs, raw output equal to TensorFlow Lite | PASS — 26/26, maximum difference 0 |
| Bird / non-bird decision on all inputs (9 bird, 17 non-bird) | PASS |
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

- TensorFlow Lite's own optimised and reference kernels differ by one output step on 2 of the 26
  inputs. One-step differences between kernel implementations are therefore normal for this model;
  the ARC MLI kernels may show the same.
- The input tensor is overwritten during `Invoke` (its memory is reused). The firmware must refill
  it before every inference; the new pipeline does.

**Limitation, stated plainly.** This validates operator coverage, configuration, tensor contracts,
arena sizing and the numeric results of the *reference* kernels. It does not execute the ARC MLI
kernels. ARC numeric behaviour stays unverified until the firmware's built-in self-test runs on the
board or an ARC simulator becomes available.
