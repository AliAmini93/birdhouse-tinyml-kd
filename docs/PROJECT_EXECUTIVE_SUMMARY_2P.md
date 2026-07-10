# Birdhouse TinyML KD - Two-Page Executive Summary

## Objective

Deploy a five-second binary bird/non-bird acoustic classifier on the Seeed Studio XIAO ESP32S3:

```text
5 s, 16 kHz mono audio
-> 40 x 249 log-mel
-> INT8 DS-CNN
-> p_bird and binary decision
```

Environmental sensors, LoRaWAN, cloud integration, scheduling, and final battery sizing are outside the current scope.

## Completed work

- Audited the 27-class FSC22 SWinT-BiLSTM Teacher and recovered the correct bird indices: `12` and `20`.
- Generated deterministic binary Teacher probabilities.
- Developed hard-label Student baselines and binary knowledge-distillation models.
- Selected `hard_weight=0.8`, `kd_weight=0.2` after a weight sweep.
- Trained the final 32,097-parameter DS-CNN Student.
- Exported FP32 and full-integer INT8 TFLite models.
- Implemented C++ log-mel preprocessing and verified Python/C++ parity.
- Replaced direct DFT with a memory-safe ESP-DSP FFT implementation.
- Added TFLite Micro assets, wrappers, smoke tests, and preprocessing-to-inference firmware.
- ESP32S3 compile/link validation passed.

## Key results

| Item | Result |
|---|---:|
| Precision at 0.5 | 0.728 |
| Recall at 0.5 | 0.873 |
| F1 at 0.5 | 0.780 |
| PR-AUC | 0.905 |
| ROC-AUC | 0.986 |
| Recall at FPR 0.02 | 0.860 |
| INT8 model size | 59,760 bytes |
| Recommended threshold | 0.6734629869 |
| Optimized preprocessing parity | 100% exact |
| Preprocessing scratch | 5,124 bytes |

Cross-validation results are the valid model-selection evidence. Full-dataset final-training metrics are not independent test results.

## Verified vs pending

Verified: training, KD sweep, quantization, Keras/TFLite agreement, Python/C++ parity, optimized FFT, TFLite Micro integration, ESP32S3 compile/link.

Pending: physical live capture, on-device execution, measured latency, RAM/PSRAM, field evaluation, current measurement, and final battery sizing.

## Current blocker

The available Grove Sound Sensor v1.7 is an analog sound-intensity detector and is not suitable for waveform recording. The prepared firmware requires the digital PDM microphone on the XIAO ESP32S3 Sense expansion board:

```text
DATA = GPIO41
CLK  = GPIO42
```

That board is not currently available.

## Required purchase and next step

Preferred purchase: **Seeed Studio XIAO ESP32S3 Sense kit**, including the digital microphone expansion board.

After procurement:

1. capture 80,000 int16 samples at 16 kHz;
2. verify RMS, peak, DC offset, zeros, and clipping;
3. run ESP-DSP log-mel preprocessing;
4. run the INT8 TFLite Micro model;
5. measure latency, internal RAM, PSRAM, and stability;
6. test controlled bird/non-bird playback;
7. measure energy and only then finalize battery sizing.

No environmental-sensor or LoRaWAN work is required before this milestone passes.
