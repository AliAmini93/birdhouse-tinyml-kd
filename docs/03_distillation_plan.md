# 03 - Distillation Plan

## Target

Train a small binary Student model:

```text
bird / non-bird
```

## Teacher

Use the recovered 27-class Teacher output mapping:

```text
bird_indices = [12, 20]
P_bird = P[12] + P[20]
P_non_bird = 1 - P_bird
```

## Soft-Label Generation Constraints

Teacher inference must be deterministic:

```text
checkpoint = output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth
batch_size = 32
shuffle = False
fixed clip ordering
same preprocessing as dissertation
same recovered label map
```

## Student Candidate

The Student should be small and embedded-friendly:

```text
input: 1 s or 2 s audio window
feature: MFCC or compact log-mel
model: small CNN / DS-CNN / TCN
output: sigmoid bird probability
quantization: INT8
target: TensorFlow Lite Micro / ESP32S3
```

## Do Not Do Yet

```text
Do not train Student before generating verified soft labels.
Do not use local bird indices [2, 6].
Do not use 27-class Student for deployment.
```
