# 15 - Preprocess Parity Test

This document describes the parity test between the Python preprocessing pipeline and the embedded-oriented C++ preprocessing reference.

## Goal

The final INT8 TFLite model expects a quantized input tensor:

```text
shape = 40 x 249 x 1
layout = [mel][frame][channel]
dtype = int8
```

The C++ preprocessing implementation must reproduce the Python preprocessing closely enough before it can be used on-device.

## Files added

```text
firmware/preprocess/test_preprocess_parity.cc
tools/run_preprocess_parity_test.sh
tools/export_preprocess_reference.py
```

The reference export tool now produces binary files for the C++ test:

```text
firmware/preprocess/testdata/reference_pcm_float32.bin
firmware/preprocess/testdata/reference_input_int8.bin
```

These binary files are generated locally and do not need to be committed.

## Run

From repository root:

```bash
bash tools/run_preprocess_parity_test.sh
```

The script performs:

```text
1. export Python reference PCM and int8 model input
2. compile the C++ preprocessing parity test
3. run C++ preprocessing on the reference PCM
4. compare C++ int8 output against Python int8 reference
```

## Report

The output report is written to:

```text
firmware/preprocess/testdata/preprocess_parity_report.txt
```

The report includes:

```text
exact_match_pct
within_1_pct
within_2_pct
within_4_pct
mean_abs_diff_int8
rmse_int8
max_abs_diff_int8
max_diff_mel
max_diff_frame
status
```

## Initial acceptance rule

The first practical rule is:

```text
mean_abs_diff_int8 <= 2
within_2_pct >= 95
```

This is not a final deployment certification. It is a sanity check that the C++ front-end is close to the Python front-end.

## If parity is poor

Most likely causes:

```text
Hann window padding differs from librosa
FFT scaling differs
power spectrum scaling differs
mel filterbank differs
flatten layout mismatch: [mel][frame] vs [frame][mel]
log epsilon differs
normalization differs
input quantization differs
```

## Important note

The current C++ implementation uses a naive DFT reference. This is intentionally simple for verification. The final ESP32S3 version should replace the DFT with an optimized FFT backend while keeping the same numerical contract.
