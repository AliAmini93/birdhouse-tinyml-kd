# 19 - Optimized FFT and Memory-Safe Five-Second Preprocessing

## Scope

This step replaces the reference-only direct DFT with an optimized FFT path suitable for continued deployment work on the Seeed Studio XIAO ESP32S3.

The acoustic contract is unchanged:

```text
5 s mono PCM
16 kHz
80,000 samples
512-point FFT
400-sample centered Hann window
320-sample hop
249 frames
40 Slaney mel bins
log(mel + 1e-6)
global normalization
INT8 quantization
40 x 249 x 1 model input
```

## Backend selection

### ESP32S3 firmware

```text
ESP-DSP radix-2 float32 FFT
```

The ESP-IDF project pins:

```text
espressif/esp-dsp = 1.8.2
```

and selects:

```text
CONFIG_DSP_OPTIMIZED=y
CONFIG_DSP_MAX_FFT_SIZE_512=y
```

### Desktop regression tests

```text
portable iterative radix-2 float32 FFT
```

The portable backend exists only to preserve the existing host parity workflow.

## Memory change

The former int16 path allocated a full static float copy:

```text
80,000 float samples = 320,000 bytes
```

That copy has been removed.

The optimized implementation reuses one frame workspace:

```text
complex FFT frame:
  2 x 512 x 4 bytes = 4096 bytes

power spectrum:
  257 x 4 bytes = 1028 bytes

total implementation scratch:
  5124 bytes
```

The caller still owns the original PCM buffer and the 9,960-byte INT8 feature tensor.

## Re-entrancy

The preprocessing functions reuse one static FFT workspace. They must not be called concurrently from multiple tasks.

## Validation

Run:

```bash
cd /media/armin/External/AhmadWorks/audioclassification

. ~/esp/esp-idf/export.sh

bash tools/run_optimized_preprocess_validation.sh
```

Acceptance evidence:

```text
desktop parity:
  status: PASS
  mean_abs_diff_int8 <= 2
  within_2_pct >= 95

ESP32S3:
  Project build complete
```

Runtime evidence will be collected when the board is available:

```text
preprocessing_time_ms
inference_time_ms
free_internal
free_psram
largest_internal
INPUT PARITY PASS
OPTIMIZED PREPROCESSING-INFERENCE TEST PASS
```

## Remaining work

This step does not yet capture live microphone audio. The next implementation step is:

```text
XIAO ESP32S3 Sense PDM microphone
-> 5-second int16 buffer
-> optimized preprocessing
-> INT8 Student model
```
