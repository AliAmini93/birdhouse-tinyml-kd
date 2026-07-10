# Birdhouse TinyML KD

Knowledge-distilled TinyML bird/non-bird acoustic classification for the Seeed Studio XIAO ESP32S3.

## Scope

This repository covers the acoustic machine-learning and embedded-inference path only:

```text
5 s audio
-> 16 kHz mono waveform
-> 40 x 249 log-mel input
-> INT8 DS-CNN Student
-> bird / non-bird probability
```

Environmental sensors, LoRaWAN communication, cloud integration, and final battery sizing are outside the current implementation scope.

## Current status

| Stage | Status |
|---|---|
| Teacher audit and binary class mapping | Complete |
| Deterministic Teacher soft-label generation | Complete |
| Hard-label Student baselines | Complete |
| Binary knowledge distillation and weight sweep | Complete |
| Final full-dataset Student training | Complete |
| Full-integer INT8 TFLite export | Complete |
| Python-to-C++ preprocessing parity | Complete |
| Memory-safe ESP-DSP FFT preprocessing | Complete |
| TFLite Micro wrapper and ESP32S3 build tests | Complete |
| Live five-second microphone capture | Blocked by missing hardware |
| On-device runtime latency, RAM, and power measurement | Pending |
| Real bird/non-bird field evaluation | Pending |

## Final model

```text
Selected configuration: 5s_kd_hw08_kw02
Task: binary bird / non-bird
Input: 5 s, 16 kHz, mono
Feature tensor: 40 x 249 x 1
Architecture: compact depthwise-separable CNN
Parameters: 32,097
Hard-loss weight: 0.8
KD weight: 0.2
Recommended decision threshold: 0.673462986946106
INT8 model size: 59,760 bytes
```

The distillation implementation uses soft binary cross-entropy against the Teacher bird probability. For Bernoulli Teacher and Student distributions, this has the same Student-dependent optimization term as `KL(Teacher || Student)` up to the constant Teacher entropy.

## Selected cross-validation evidence

```text
precision@0.5 = 0.7275214834916327
recall@0.5 = 0.8733333333333333
F1@0.5 = 0.7798264367270021
PR-AUC = 0.9051309127292857
ROC-AUC = 0.9859022222222222
recall at target FPR 0.02 = 0.8600000000000001
```

Cross-validation results are the model-selection evidence. Metrics obtained after training the final model on the full dataset are apparent training-set metrics and must not be presented as independent test performance.

## Deployment validation completed

### Quantized model export

```text
FP32 TFLite size = 132,128 bytes
INT8 TFLite size = 59,760 bytes

INT8 input quantization:
  scale = 0.0200184378772974
  zero point = -67

INT8 output quantization:
  scale = 0.00390625
  zero point = -128
```

### INT8 agreement with Keras

```text
mean absolute difference = 0.0011150884674862027
maximum absolute difference = 0.034066736698150635
```

### Optimized preprocessing parity

```text
backend on ESP32S3 = ESP-DSP radix-2 float32 FFT
scratch memory = 5,124 bytes
desktop exact match = 100%
within ±2 INT8 units = 100%
mean absolute INT8 difference = 0
status = PASS
```

### Firmware build status

The following compile and link successfully for ESP32S3:

```text
TFLite Micro direct-input smoke test
preprocessing-to-inference integration test
optimized ESP-DSP FFT preprocessing
```

These build results do not constitute on-device runtime validation.

## Current blocker

The available hardware includes a XIAO ESP32S3, Grove Shield, Grove Sound Sensor v1.7, and other Grove modules. The Grove Sound Sensor is an analog sound-intensity detector and is not suitable for capturing the five-second waveform required by the model.

The missing component is a waveform-capable digital microphone.

## Required next hardware

Preferred path, because it matches the prepared PDM firmware:

```text
Seeed Studio XIAO ESP32S3 Sense kit
including the Sense expansion board with digital PDM microphone
```

If the Sense microphone expansion board cannot be obtained separately, purchase the complete XIAO ESP32S3 Sense kit.

Alternative path:

```text
digital I2S microphone breakout
such as INMP441 / ICS-43434 / SPH0645
```

The alternative requires replacing the Sense-specific PDM driver with a standard I2S microphone driver and defining the wiring pins.

## Next implementation step

After the microphone hardware arrives:

```text
1. Capture exactly 80,000 signed int16 samples at 16 kHz.
2. Verify capture duration, RMS, peak, DC offset, zeros, and clipping.
3. Run the optimized log-mel preprocessing.
4. Run the INT8 TFLite Micro Student.
5. Record preprocessing latency, inference latency, total latency, SRAM, and PSRAM.
6. Test controlled bird and non-bird recordings.
7. Measure current during capture, preprocessing, inference, and sleep.
8. Only then calculate the final six-month battery requirement.
```

## Documentation

- [`docs/PROJECT_STATUS_AND_NEXT_STEP.md`](docs/PROJECT_STATUS_AND_NEXT_STEP.md): complete technical status and hardware blocker
- [`docs/12_final_student_model_card.md`](docs/12_final_student_model_card.md): selected Student model card
- [`docs/19_optimized_fft_preprocessing.md`](docs/19_optimized_fft_preprocessing.md): optimized preprocessing implementation
- [`reports/overleaf_birdhouse_tinyml_kd/`](reports/overleaf_birdhouse_tinyml_kd/): Overleaf-ready technical report
