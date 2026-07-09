# 12 - Final Student Model Card

This document describes the final TinyML Student model selected for bird/non-bird detection.

## 1. Model purpose

The final Student model is a compact binary acoustic classifier for deployment-oriented bird detection.

```text
Task: binary bird / non-bird detection
Output: p_bird in [0, 1]
Deployment target: TinyML / Seeed Studio XIAO ESP32S3 path
Selected final model: 5s_kd_hw08_kw02
```

The model is not a 27-class FSC22 classifier. The 27-class Teacher is used only offline to provide soft supervision.

## 2. Binary label definition

The FSC22 classes are collapsed into a binary target:

```text
bird = 1:
  23birdchirping
  24wingflapping

non-bird = 0:
  all other FSC22 classes
```

## 3. Input and preprocessing

The Student does not consume raw waveform directly. Each audio clip is converted to a fixed-size log-mel feature.

```text
audio duration = 5.0 s
sample rate = 16000 Hz
channels = mono
target samples = 80000
n_fft = 512
frame length = 25 ms
hop = 20 ms
n_mels = 40
fmin = 50 Hz
fmax = 8000 Hz
mel power = 2.0
log compression = log(mel + eps)
center = False
feature shape = 40 x 249
model input shape = 40 x 249 x 1
```

Final deployment normalization:

```text
normalizer_mean = -9.193479537963867
normalizer_std = 3.789201021194458
```

The firmware/front-end must reproduce this preprocessing closely. Mismatch between Python log-mel preprocessing and embedded feature extraction can degrade performance more than small changes in the neural network.

## 4. Student architecture

The final Student architecture is a compact depthwise-separable CNN.

```text
Input: 40 x 249 x 1

Stem:
  Conv2D, 3 x 3, 24 filters, stride 2, no bias
  BatchNorm
  ReLU6

Block 1:
  DepthwiseConv2D, 3 x 3, stride 1
  BatchNorm
  ReLU6
  Pointwise Conv2D, 1 x 1, 32 filters
  BatchNorm
  ReLU6

Block 2:
  DepthwiseConv2D, 3 x 3, stride 2
  BatchNorm
  ReLU6
  Pointwise Conv2D, 1 x 1, 48 filters
  BatchNorm
  ReLU6

Block 3:
  DepthwiseConv2D, 3 x 3, stride 1
  BatchNorm
  ReLU6
  Pointwise Conv2D, 1 x 1, 64 filters
  BatchNorm
  ReLU6

Block 4:
  DepthwiseConv2D, 3 x 3, stride 2
  BatchNorm
  ReLU6
  Pointwise Conv2D, 1 x 1, 96 filters
  BatchNorm
  ReLU6

Block 5:
  DepthwiseConv2D, 3 x 3, stride 1
  BatchNorm
  ReLU6
  Pointwise Conv2D, 1 x 1, 96 filters
  BatchNorm
  ReLU6

Classifier:
  GlobalAveragePooling2D
  Dense 64, ReLU
  Dropout 0.25
  Dense 1, Sigmoid

Output:
  p_bird
```

Model size before TFLite export:

```text
trainable/inference parameters = 32097
```

## 5. Why DS-CNN

A standard CNN would be larger and more expensive for embedded inference. A depthwise-separable block separates spatial filtering and channel mixing:

```text
Depthwise convolution:
  spatial filtering is applied independently per channel.

Pointwise 1 x 1 convolution:
  channels are mixed after spatial filtering.
```

This reduces parameter count and multiply-accumulate cost compared with regular convolutions, while preserving a CNN structure suitable for log-mel spectrogram features.

## 6. Teacher and soft-label construction

The offline Teacher is a 27-class FSC22 model. For binary Student training, the Teacher output is collapsed into one bird probability:

```text
p_teacher_bird =
  P_teacher(23birdchirping)
  +
  P_teacher(24wingflapping)
```

The resulting binary soft-label file is:

```text
teacher_kd/soft_labels/fsc22_soft_labels_binary.csv
```

The KD script matches soft labels to dataset clips by file basename and uses the `p_bird` column as the Teacher probability.

## 7. Training objective

The final Student was trained with a combination of hard-label focal loss and binary soft-label distillation.

Selected loss weights:

```text
hard_weight = 0.8
kd_weight = 0.2
focal_alpha = 0.75
focal_gamma = 2.0
```

Final loss:

```text
TotalLoss =
  0.8 * FocalLoss(y_hard, p_student)
  +
  0.2 * BCE(p_teacher_bird, p_student)
```

The hard-label focal loss is used because the dataset is imbalanced:

```text
bird clips = 150
non-bird clips = 1875
```

The KD term uses Teacher confidence rather than only hard binary labels.

## 8. BCE/KL relationship for binary KD

The implementation uses binary cross-entropy against the Teacher soft probability, not an explicit `KLDivLoss` layer.

Let:

```text
q = p_teacher_bird
p = p_student_bird
```

The Teacher and Student define Bernoulli distributions:

```text
Teacher = [q, 1 - q]
Student = [p, 1 - p]
```

The KL divergence from Teacher to Student is:

```text
KL(Teacher || Student)
=
q * log(q / p) + (1 - q) * log((1 - q) / (1 - p))
```

This can be decomposed as:

```text
KL(Teacher || Student)
=
BCE(q, p) - H(q)
```

where:

```text
BCE(q, p) =
- q * log(p) - (1 - q) * log(1 - p)
```

and `H(q)` is the entropy of the Teacher distribution, which is constant with respect to the Student parameters. Therefore, minimizing soft BCE is equivalent to minimizing binary Bernoulli KL up to a constant.

So the precise statement is:

```text
The model was trained with soft BCE.
For binary distillation, this optimizes the same Student-dependent term as KL(Teacher || Student).
```

## 9. Batch construction

Training uses balanced mini-batches to compensate for class imbalance.

```text
batch_size = 32
approximately 16 bird samples per batch
approximately 16 non-bird samples per batch
```

Because the bird class is small, positive samples are oversampled during training.

## 10. Feature-level augmentation

Augmentation is applied in normalized log-mel space.

Used augmentations:

```text
time shift
log-energy gain jitter
small Gaussian feature noise
time masking
frequency masking
```

Positive clips receive stronger augmentation probabilities than non-bird clips to improve bird recall and robustness.

## 11. Model-selection history

The model was selected through the following progression:

```text
hard-label v1:
  first 5 s binary baseline

hard-label v2:
  wider compact DS-CNN
  balanced batches
  feature augmentation
  focal loss

binary KD v1:
  same architecture as v2
  hard focal loss + Teacher soft BCE
  hard_weight = 0.5
  kd_weight = 0.5

KD weight sweep:
  tested 0.8/0.2, 0.7/0.3, 0.3/0.7
  selected 0.8/0.2
```

Selected cross-validation run:

```text
student/results/5s_kd_binary_hw08_kw02
```

## 12. Selected CV metrics

The selected configuration achieved:

```text
precision_0p5 = 0.7275214834916327
recall_0p5 = 0.8733333333333333
f1_0p5 = 0.7798264367270021
pr_auc = 0.9051309127292857
roc_auc = 0.9859022222222222
recall_at_fpr_target = 0.8600000000000001
target_fpr = 0.02
```

Important: these cross-validation metrics are the model-selection evidence.

## 13. Final full-dataset training

After selecting the configuration, the final model was trained once on the full FSC22 dataset.

```text
final_name = 5s_kd_hw08_kw02
selected_cv_run = 5s_kd_binary_hw08_kw02
epochs = 46
batch_size = 32
hard_weight = 0.8
kd_weight = 0.2
```

The final full-dataset metrics are apparent training-set metrics, not independent validation metrics.

### Threshold 0.5

```text
TN = 1868
FP = 7
FN = 2
TP = 148

accuracy = 0.9955555555555555
precision = 0.9548387096774194
recall = 0.9866666666666667
f1 = 0.9704918032786886
fpr = 0.0037333333333333333
```

### Recommended CV threshold

Recommended threshold:

```text
threshold = 0.673462986946106
```

Confusion matrix on full training set:

```text
TN = 1873
FP = 2
FN = 8
TP = 142

accuracy = 0.9950617283950617
precision = 0.9861111111111112
recall = 0.9466666666666667
f1 = 0.9659863945578231
fpr = 0.0010666666666666667
```

## 14. TFLite export

Final exported files:

```text
student/final_models/5s_kd_hw08_kw02/student_final_fp32.tflite
student/final_models/5s_kd_hw08_kw02/student_final_int8.tflite
```

Model sizes:

```text
FP32 TFLite = 132128 bytes = 129.03 KiB
INT8 TFLite = 59760 bytes = 58.36 KiB
```

INT8 quantization details:

```text
input dtype = int8
input quantization = (scale=0.0200184378772974, zero_point=-67)

output dtype = int8
output quantization = (scale=0.00390625, zero_point=-128)
```

Validation against Keras on a subset:

```text
FP32 mean abs diff vs Keras = 1.0597911881404798e-08
FP32 max abs diff vs Keras = 5.066394805908203e-07

INT8 mean abs diff vs Keras = 0.0011150884674862027
INT8 max abs diff vs Keras = 0.034066736698150635
```

The INT8 model is small enough for embedded deployment experiments. The larger deployment risk is the audio front-end and log-mel feature extraction memory/latency, not the neural network file size.

## 15. Deployment constants

The embedded implementation should use:

```text
sample_rate = 16000
duration_s = 5.0
n_mels = 40
frame_ms = 25.0
hop_ms = 20.0
expected_frames = 249
normalizer_mean = -9.193479537963867
normalizer_std = 3.789201021194458
recommended_threshold = 0.673462986946106
```

## 16. Important limitations

1. The final full-dataset metrics are apparent training-set metrics. Use CV metrics for model-selection claims.
2. The current Teacher soft labels are binary collapsed probabilities. They may not contain rich multi-class dark knowledge.
3. For paper-grade KD, out-of-fold Teacher soft labels are preferable to avoid any Teacher-side leakage concerns.
4. Embedded performance depends strongly on reproducing the Python preprocessing pipeline.
5. The current model detects only the collapsed bird/non-bird target, not bird species or bird-event subtype.
6. The current model has not yet been benchmarked on-device for RAM, latency, and power.
7. Deployment threshold may need adjustment based on the real operating environment and acceptable false-alarm rate.

## 17. Related repository files

```text
student/train_student_5s_hardlabel_baseline.py
student/train_student_5s_hardlabel_baseline_v2.py
student/train_student_5s_kd_binary_v1.py
student/train_student_5s_kd_binary_sweep_wrapper.py
student/run_student_5s_kd_weight_sweep.sh
student/summarize_student_5s_kd_weight_sweep.py
student/train_student_5s_final_kd_export.py
student/export_student_5s_final_to_tflite.py

docs/07_student_baseline_plan.md
docs/08_student_baseline_v2_plan.md
docs/09_student_kd_binary_v1_plan.md
docs/10_student_kd_weight_sweep_plan.md
docs/11_final_student_export_plan.md
docs/12_final_student_model_card.md
```

