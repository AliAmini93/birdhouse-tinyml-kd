# 14 - Embedded Preprocessing v0 Plan

This document records the first embedded preprocessing implementation for the final bird/non-bird Student model.

## Status

Python preprocessing is already implemented and was used for training, evaluation, and TFLite export.

This step adds an embedded-oriented C++ reference implementation:

```text
firmware/preprocess/preprocess_constants.h
firmware/preprocess/audio_preprocess.h
firmware/preprocess/audio_preprocess.cc
firmware/preprocess/mel_filterbank.h       generated
firmware/preprocess/mel_filterbank.cc      generated
tools/generate_mel_filterbank.py
tools/export_preprocess_reference.py
```

## What is implemented in v0

The C++ reference path performs:

```text
int16 or float PCM
-> 5 s / 16 kHz mono assumption
-> 512-point frame extraction
-> padded Hann window matching librosa
-> naive DFT power spectrum
-> Slaney mel filterbank
-> log(mel + eps)
-> normalization
-> INT8 quantization for the final TFLite model input
```

## Important limitation

The DFT implementation in `audio_preprocess.cc` is a reference implementation, not the final optimized ESP32S3 implementation.

For real deployment, replace the naive DFT with an optimized FFT backend such as ESP-DSP. The rest of the pipeline must stay numerically aligned:

```text
windowing
power spectrum scale
mel filterbank
log eps
normalization
input quantization
```

## Python training preprocessing

```text
sample_rate = 16000
duration_s = 5.0
n_fft = 512
win_length = 400
hop_length = 320
n_mels = 40
fmin = 50
fmax = 8000
power = 2.0
center = False
log = log(mel + 1e-6)
shape = 40 x 249
```

## Deployment constants

```text
normalizer_mean = -9.193479537963867
normalizer_std = 3.789201021194458

input_scale = 0.0200184378772974
input_zero_point = -67

output_scale = 0.00390625
output_zero_point = -128

recommended_threshold = 0.673462986946106
```

## Generate mel filterbank

```bash
"/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" tools/generate_mel_filterbank.py
```

This generates:

```text
firmware/preprocess/mel_filterbank.h
firmware/preprocess/mel_filterbank.cc
firmware/preprocess/mel_filterbank_summary.json
```

## Export a Python reference input

```bash
"/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" tools/export_preprocess_reference.py
```

This exports:

```text
firmware/preprocess/testdata/reference_logmel.npy
firmware/preprocess/testdata/reference_normalized.npy
firmware/preprocess/testdata/reference_input_int8.npy
firmware/preprocess/testdata/reference_input_int8.h
firmware/preprocess/testdata/reference_preprocess_summary.json
```

The `.npy` files are useful for desktop parity testing and do not need to be committed unless needed.

## Next verification step

Compare:

```text
Python reference log-mel / int8 input
vs.
C++ reference preprocessing output
```

Exact bitwise equality is not required at first, because FFT/windowing backends may introduce small numerical differences. The first target is close agreement after quantization.

## Next firmware step

```text
1. Convert INT8 TFLite model to C array
2. Build TFLite Micro inference skeleton
3. Feed reference_input_int8.h to the model on desktop/firmware
4. Validate output dequantization and thresholding
5. Replace reference input with live preprocessing output
6. Add microphone/audio capture path
```

