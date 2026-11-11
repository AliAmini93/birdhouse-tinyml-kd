# Birdhouse on the Himax HX6537-A (Seeed Grove Vision AI V1)

Status: firmware candidate built and validated **offline**. It has not been flashed; no result in
this directory comes from the physical board.

## Layout

| Path | Content |
|---|---|
| `birdhouse/` | The module linked into the vendor firmware: capture, PDM adapter, runtime, model wrapper, diagnostics, Himax glue, operator overlay, build overlay |
| `tests/` | Host tests: emulation of the vendor audio library, capture/adapter/runtime suites, inference test on the vendor TFLite Micro sources |
| `experiments/` | Earlier step-by-step experiments (stage 24–50). Superseded and kept for history; not part of the candidate. The stage50 build could not run the model (see the reports). |

Tools live in `tools/himax/`. Reports and evidence live in
`docs/research/birdhouse_v1_implementation_20261111/`.

## How it attaches to the vendor firmware

The vendor Edge Impulse application is built unmodified from the SDK under `.local-tools/` (not
published). The module is added by `birdhouse/build/birdhouse_overlay.mk`:

- an include directory placed before the vendor include path re-enables the INT8
  `FULLY_CONNECTED` kernel that the vendor configuration disables;
- two functions are interposed with the linker's `--wrap`: the vendor main loop's
  `is_inference_running()` (used as the poll hook) and `hx_drv_pdm_deinit()` (to see PDM FIFO
  recoveries);
- `AT+BIRD*` commands are registered on the vendor console.

## Commands

```
python3 tools/himax/run_offline_checks.py     # everything: audits, host tests, build, packaging checks
make -C firmware/himax_arc/tests run-all      # host tests only
tools/himax/sdk_make.sh <out-dir> -j8         # firmware ELF only (out of tree)
```

None of these commands programs a device. The packaging step runs in a sandbox, refuses to run
while a Grove device is attached, and leaves its output under `.local-tools/`.

## What is and is not verified

Verified offline: operator coverage and configuration, inference on the vendor TFLite Micro
sources with reference kernels (28 inputs, bit-exact with TensorFlow Lite), capture logic against
an emulated audio library, memory map, hooks at their call sites, image layout and UF2 format.

Not verified: execution of the ARC MLI kernels, real PDM audio, timing, interrupt behaviour,
stack depth, and every step that involves the board. The candidate carries self-tests and
diagnostics to answer those on first use.

Do not flash without the gates in `OFFLINE_VALIDATION_REPORT.md` section 9.
