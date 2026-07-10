# Project Status, Verified Results, Hardware Blocker, and Next Step

**Project:** Birdhouse TinyML KD  
**Deployment platform:** Seeed Studio XIAO ESP32S3  
**Task:** five-second binary bird/non-bird acoustic classification  
**Status date:** 2026-07-10

## 1. Scope boundary

The completed work concerns only the acoustic TinyML path:

```text
audio model development
knowledge distillation
INT8 quantization
embedded preprocessing
TFLite Micro integration
ESP32S3 build validation
```

The following are not part of the current scope and have not been implemented:

```text
environmental sensor integration
LoRaWAN communication
cloud/backend integration
deployment scheduling
final battery sizing
```

They must not be presented as completed project outputs.

## 2. End-to-end development completed so far

### 2.1 Teacher audit

The offline Teacher is a 27-class FSC22 model:

```text
SWinT-BiLSTM
repository class name: Swint_LSTM
```

The local dataset folder order did not match the Teacher output order. The recovered Teacher output indices used for binary collapse are:

```text
23birdchirping -> output index 12
24wingflapping -> output index 20
```

The binary Teacher probability is therefore:

```text
p_teacher_bird = P_teacher[12] + P_teacher[20]
p_teacher_non_bird = 1 - p_teacher_bird
```

Because the Teacher implementation is sensitive to batch ordering, deterministic soft-label generation fixes the batch size, clip order, preprocessing, checkpoint, and output mapping.

### 2.2 Student model development

The progression was:

```text
hard-label Student v1
-> improved hard-label Student v2
-> binary knowledge distillation
-> KD-weight sweep
-> selected configuration
-> full-dataset final training
```

Selected configuration:

```text
name = 5s_kd_hw08_kw02
hard_weight = 0.8
kd_weight = 0.2
focal_alpha = 0.75
focal_gamma = 2.0
```

The final loss is:

```text
0.8 * focal_loss(hard labels, Student)
+
0.2 * binary_cross_entropy(Teacher soft probability, Student)
```

For Bernoulli Teacher and Student distributions, soft BCE differs from `KL(Teacher || Student)` only by the Teacher entropy, which is constant with respect to Student parameters. The implementation should therefore be described as soft-BCE knowledge distillation, with KL-equivalent Student optimization in the binary case.

### 2.3 Model input and architecture

```text
duration = 5.0 s
sample rate = 16,000 Hz
channels = mono
samples = 80,000
FFT size = 512
frame length = 25 ms
hop = 20 ms
mel bins = 40
expected frames = 249
model input = 40 x 249 x 1
```

Normalization:

```text
mean = -9.193479537963867
standard deviation = 3.789201021194458
```

Student:

```text
compact depthwise-separable CNN
parameters = 32,097
output = sigmoid p_bird
```

### 2.4 Model-selection results

Selected cross-validation results:

| Metric | Value |
|---|---:|
| Precision at threshold 0.5 | 0.7275214835 |
| Recall at threshold 0.5 | 0.8733333333 |
| F1 at threshold 0.5 | 0.7798264367 |
| PR-AUC | 0.9051309127 |
| ROC-AUC | 0.9859022222 |
| Recall at target FPR 0.02 | 0.8600000000 |

These cross-validation results are the valid model-selection evidence.

The final model was subsequently trained on the complete dataset. Metrics measured on that same full training set are apparent training metrics and must not be used as independent generalization evidence.

### 2.5 Final export and quantization

```text
FP32 TFLite = 132,128 bytes
INT8 TFLite = 59,760 bytes
recommended threshold = 0.673462986946106
```

Quantization:

```text
input int8:
  scale = 0.0200184378772974
  zero point = -67

output int8:
  scale = 0.00390625
  zero point = -128
```

Agreement with Keras:

| Export | Mean absolute difference | Maximum absolute difference |
|---|---:|---:|
| FP32 TFLite | 1.05979e-08 | 5.06639e-07 |
| INT8 TFLite | 0.00111509 | 0.03406674 |

### 2.6 Embedded preprocessing

A C++ implementation reproduces:

```text
five-second waveform
-> Hann-windowed 512-point spectrum
-> 40-bin mel filterbank
-> log compression
-> global normalization
-> INT8 quantization
```

Initial Python-to-C++ parity:

```text
exact = 99.9598%
within ±1 = 100%
mean absolute INT8 difference = 0.000401606
maximum difference = 1
status = PASS
```

The direct DFT reference was then replaced with a memory-safe radix-2 FFT. On ESP32S3 the implementation uses ESP-DSP. It processes one frame at a time and removes the previous 320,000-byte full float waveform copy.

Optimized implementation:

```text
FFT workspace = 4,096 bytes
power-spectrum workspace = 1,028 bytes
total preprocessing scratch = 5,124 bytes
```

Optimized desktop parity:

```text
exact = 100%
within ±2 = 100%
mean absolute INT8 difference = 0
status = PASS
```

### 2.7 TFLite Micro and ESP32S3 integration

Completed:

```text
embedded model byte asset
TFLite Micro wrapper
direct-input smoke-test firmware
preprocessing-to-inference integration firmware
ESP-DSP optimized preprocessing firmware
```

The ESP32S3 projects compile and link successfully. The optimized integration image was successfully generated within the one-megabyte application partition.

## 3. What has not been verified

The following claims must not yet be made:

```text
the model has run successfully on the physical ESP32S3 board
the board has captured a valid five-second waveform
the measured on-device inference latency is known
the measured SRAM/PSRAM peak is known
the measured energy per classification is known
the six-month battery capacity is final
field bird/non-bird performance is known
```

Build success and numerical parity are necessary, but they are not substitutes for physical runtime validation.

## 4. Hardware inspection and blocker

Available relevant hardware:

```text
XIAO ESP32S3
Grove Shield for XIAO
Grove Sound Sensor v1.7
```

The Grove Sound Sensor v1.7 exposes an analog sound-intensity signal. It is suitable for a future sound/no-sound trigger, but not for recording the waveform used by the classifier.

The existing live-audio firmware was prepared for the digital PDM microphone on the XIAO ESP32S3 Sense expansion board:

```text
PDM data = GPIO41
PDM clock = GPIO42
```

That expansion board is not currently available. Consequently, live five-second capture and physical end-to-end inference are blocked.

## 5. Required purchase

### Preferred

Purchase the complete:

```text
Seeed Studio XIAO ESP32S3 Sense kit
```

and confirm that it includes the Sense expansion board with the digital microphone. This is the preferred option because it matches the prepared PDM firmware.

If the expansion board is sold separately and its compatibility is confirmed, purchasing only that board is sufficient.

### Alternative

Purchase a digital I2S microphone breakout, for example:

```text
INMP441
ICS-43434
SPH0645
```

This alternative is technically valid but requires a new standard-I2S capture backend and explicit wiring.

## 6. Exact next test after procurement

```text
digital microphone
-> capture 80,000 int16 samples at 16 kHz
-> report capture statistics
-> optimized ESP-DSP log-mel preprocessing
-> INT8 TFLite Micro inference
-> p_bird and bird/non-bird decision
```

Required runtime measurements:

```text
capture duration
sample count
RMS
peak
DC offset
zero samples
clipped samples
preprocessing latency
inference latency
total pipeline latency
free and minimum internal RAM
free PSRAM
```

Acceptance is not based only on a program completion marker. Audio statistics, memory, timing, and output behavior must all be inspected.

## 7. Work deferred until live inference succeeds

```text
microphone gain calibration
controlled bird/non-bird playback tests
field recordings
power profiling
deep-sleep design
battery sizing
environmental sensors
LoRaWAN
```

## 8. Repository checkpoint

The repository checkpoint documenting the completed optimized preprocessing work is:

```text
e50c24e - Track optimized preprocessing validation script
```

The working tree was clean and synchronized with `origin/main` after that commit.
