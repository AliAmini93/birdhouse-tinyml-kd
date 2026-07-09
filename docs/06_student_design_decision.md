# 06 - Student Design Decision

Design decision document for the Birdhouse TinyML bird / non-bird Student model.

This document updates and overrides the earlier recommendation that the first deployable
Student should use a 2-second input window. The first implementation will use **5-second
input windows**.

---

## 1. Final Decision

### Primary Student v1

```text
Input duration: 5 s
Sample rate: 16 kHz
Channels: mono
Feature: compact log-mel
Initial mel bins: 40
Model family: small DS-CNN / compact CNN
Output: single binary bird / non-bird logit
Target deployment: full INT8 TensorFlow Lite Micro
```

The first Student should be trained and evaluated at the same clip duration as the current
FSC22 data and Teacher-derived soft labels.

### Secondary Student

```text
Input duration: 5 s
Sample rate: 16 kHz
Feature: MFCC or smaller log-mel
Model family: small CNN
Purpose: lower-compute ablation / fallback
```

### Fallback Only If Needed

```text
Input duration: 2 s
Feature: compact log-mel
Model family: DS-CNN
Use only if 5 s fails memory, latency, or energy constraints.
```

### Avoid For Now

```text
1 s windows
naively inherited segment labels
raw waveform Conv1D as the primary model
27-class Student for deployment
```

The edge task is binary:

```text
bird / non-bird
```

Therefore the deployed Student should stay binary unless the project requirement changes.

---

## 2. Why 2 Seconds Is Rejected as the First Implementation

The earlier design review recommended a 2-second DS-CNN as the primary deployment candidate.
That recommendation is not adopted for the first implementation.

Reasoning:

1. **Teacher labels are 5-second clip-level.**  
   The Teacher operates on the FSC22 clip as a whole.

2. **FSC22 clips are 5 seconds.**  
   The current dataset unit is already 5 seconds, so using 5-second Student inputs preserves
   the natural label granularity.

3. **Current soft labels are 5-second outputs.**  
   The generated Teacher soft labels are tied to 5-second clips and a fixed deterministic
   inference order.

4. **Shorter windows introduce weak-label noise.**  
   If a 5-second bird clip is split into 1-second or 2-second windows, not every segment
   necessarily contains bird sound. Assigning the whole-clip label to every segment risks
   corrupting the positive class.

5. **Energy/memory savings from shorter windows are speculative until measured.**  
   Reducing input length may help energy and RAM, but we do not yet know whether a 5-second
   compact Student is actually too expensive for the XIAO ESP32S3.

6. **The first priority is a clean baseline.**  
   A 5-second Student gives a scientifically cleaner baseline. If it is accurate and fits
   deployment constraints, there is no need to introduce window-label mismatch.

Decision:

```text
Start with 5 s.
Profile it.
Only shorten if the 5 s model fails practical constraints.
```

---

## 3. Candidate 5-Second Student Designs

### A. 5 s log-mel 40 bins + DS-CNN

Recommended first architecture.

```text
Input: 5 s, 16 kHz mono
Feature map: 40 mel bins x ~249 frames with 20 ms hop
Model: depthwise-separable CNN
Output: binary sigmoid / single logit
```

Advantages:

```text
Good spectral representation
Compact enough for INT8 deployment
Compatible with TensorFlow Lite Micro
Avoids 5 s -> 2 s weak-label mismatch
```

Risks:

```text
Larger feature map than 1 s / 2 s models
Must be profiled for tensor arena, latency, and current consumption
```

### B. 5 s log-mel 32 bins + DS-CNN

Smaller variant of the primary architecture.

```text
Input: 5 s, 16 kHz mono
Feature map: 32 mel bins x ~249 frames with 20 ms hop
Model: DS-CNN
Output: binary
```

Advantages:

```text
Lower RAM and compute than 40-bin log-mel
Still keeps local time-frequency structure for CNN
```

Use this if the 40-bin version is too expensive or shows no clear accuracy advantage.

### C. 5 s MFCC 20 coefficients + small CNN

Lower-cost feature alternative.

```text
Input: 5 s, 16 kHz mono
Feature: 20 MFCC coefficients over time
Model: small CNN
Output: binary
```

Advantages:

```text
Smaller feature size
Cheaper preprocessing
Useful embedded baseline
```

Risks:

```text
MFCC may discard local spectral structure useful for CNNs
Potentially weaker for rain/squirrel/wingflapping discrimination
```

### D. 5 s log-mel + small TCN

Temporal model variant.

```text
Input: 5 s, 16 kHz mono
Feature: log-mel
Model: small temporal convolutional network
Output: binary
```

Advantages:

```text
Can model event timing across 5 s
May help with wingflapping or intermittent bird events
```

Risks:

```text
More implementation complexity than DS-CNN
Needs careful quantization/profiling
```

### E. Raw waveform Conv1D

Ablation only.

```text
Input: raw waveform
Model: Conv1D
```

Do not use as the primary design. With only 150 bird clips, raw waveform learning is likely
less data-efficient and more sensitive to microphone/channel/domain shift than spectral
features.

---

## 4. Recommended First Architecture

### Feature Pipeline

```text
Audio duration: 5 s
Sample rate: 16 kHz
Channels: mono
Frame length: 25 ms
Hop: 20 ms initially
Feature: log-mel
n_mels: 40 initially
Smaller variant: 32 mel bins
```

Expected feature shape:

```text
40 x ~249 frames
```

with 20 ms hop, or approximately:

```text
40 x ~499 frames
```

with 10 ms hop.

### Hop Size Decision

Initial recommendation:

```text
hop = 20 ms
```

Reason:

```text
Lower frame count
Lower RAM
Lower feature extraction cost
Likely enough temporal resolution for bird/non-bird detection
```

A 10 ms hop can be tested later if recall on `24wingflapping` is poor.

### DS-CNN Proposal

Example compact architecture:

```text
Input: 40 x 249 x 1

Conv2D 3x3, 16 channels, stride 2
BatchNorm / ReLU6

DepthwiseConv2D 3x3
PointwiseConv2D 24 channels
BatchNorm / ReLU6

DepthwiseConv2D 3x3, stride 2
PointwiseConv2D 32 channels
BatchNorm / ReLU6

DepthwiseConv2D 3x3
PointwiseConv2D 48 channels
BatchNorm / ReLU6

DepthwiseConv2D 3x3, stride 2
PointwiseConv2D 64 channels
BatchNorm / ReLU6

GlobalAveragePooling2D
Dense 32 / ReLU6
Dense 1
Output: binary logit
```

Target:

```text
Parameters: approximately 25k-80k
Quantized model size: roughly 40-150 KB
Output activation during inference: sigmoid
Training loss: BCE / weighted BCE / focal
Quantization: full INT8
```

Exact parameter count and tensor arena must be measured after implementation.

---

## 5. Training Plan

### Stage 1: Hard-Label Baseline

Train the 5-second Student using only folder-derived hard labels:

```text
bird = 1 for:
  23birdchirping
  24wingflapping

non-bird = 0 for all other FSC22 folders
```

This baseline is mandatory. Distillation is only useful if it improves over this baseline.

### Stage 2: Binary Soft Labels

Use the current deterministic Teacher soft labels:

```text
P(bird) = P[12] + P[20]
```

Compare:

```text
hard labels only
binary soft labels only
mixed hard + soft loss
```

### Stage 3: Temperature-Softened 27-Class Collapse

Because the binary soft labels are nearly hard, richer KD should use the saved 27-class logits:

```text
softmax(logits_27 / T)
then collapse:
P_soft(bird) = P_T[12] + P_T[20]
```

Test:

```text
T = 2, 3, 4
alpha = 0.3, 0.5
```

where:

```text
Loss = alpha * BCE(student, P_soft_bird) + (1 - alpha) * hard_label_loss
```

### Imbalance Handling

The dataset is imbalanced:

```text
bird clips: 150
non-bird clips: 1875
ratio: 12.5 : 1
```

Use at least one of:

```text
weighted BCE with positive class weight
focal loss
bird oversampling
class-balanced batches
```

Do not discard non-bird clips, because the non-bird set contains important confusers such as
rain, squirrel, treefalling, insects, frogs, and wind.

### Augmentation

Use moderate augmentation:

```text
time shift
small gain change
background noise mix
SpecAugment time/frequency masking
mild pitch shift for bird clips only if it does not distort realism
```

Give special attention to:

```text
24wingflapping
27squirrel
02rain
07treefalling
```

because these were identified as difficult or confusable classes in the Teacher soft-label
analysis.

### Splitting

Use group-by-clip splitting.

Important:

```text
All derived features/windows from one 5-second clip must stay in the same split.
```

For the first 5-second model this is straightforward because there are no sub-windows.

Use:

```text
5-fold cross-validation
plus an untouched held-out test split if possible
```

---

## 6. Evaluation Plan

Evaluate with metrics that reflect class imbalance and deployment needs.

Required metrics:

```text
binary accuracy
bird recall
bird precision
F1-score
PR-AUC
ROC-AUC
recall at fixed non-bird FPR
```

More important than raw accuracy:

```text
bird recall at low false-positive rate
PR-AUC
false positives per non-bird class
```

Class-specific analysis:

```text
23birdchirping recall
24wingflapping recall
27squirrel false-positive rate
02rain false-positive rate
07treefalling false-positive rate
wind / insect / frog false-positive rate
```

Threshold tuning:

```text
Do not assume threshold = 0.5 for deployment.
Choose threshold from PR curve based on desired false-positive rate.
Retune threshold after INT8 quantization.
```

Float vs INT8 comparison:

```text
Compare float Student vs full-INT8 Student.
If INT8 bird recall drops by more than 3 percentage points, try QAT.
```

---

## 7. Deployment and Profiling Plan

Do not shorten the input window until the 5-second model has been measured.

Deployment profiling order:

```text
1. Train 5 s float model offline
2. Export to TFLite
3. Quantize to full INT8
4. Test TFLite on host
5. Estimate tensor arena
6. Deploy to XIAO ESP32S3
7. Measure:
   - feature extraction time
   - inference time
   - tensor arena
   - flash usage
   - active current
   - average current under duty cycling/gating
8. Decide whether 5 s is acceptable
```

Keep 5 seconds if:

```text
tensor arena fits
latency is acceptable
average power is acceptable with duty cycling/gating
accuracy/recall is better than shorter variants
```

Move to 2 seconds only if:

```text
5 s model fails memory constraints
5 s model fails latency constraints
5 s model fails energy constraints
field testing requires faster event localization
```

---

## 8. Energy Strategy

The main energy reduction should come from system design, not prematurely shortening the model
input.

Primary energy controls:

```text
environmental gating
time-of-day gating
RMS / spectral-flux acoustic pre-gate
duty cycling
event-driven radio transmission
low-power sleep between listen windows
```

The 5-second model can still be energy-feasible if it runs only when necessary.

The correct order is:

```text
measure 5 s model
profile energy
then decide whether shorter windows are necessary
```

---

## 9. Go / No-Go Criteria for Keeping 5 Seconds

Keep the 5-second Student if:

```text
CV bird recall >= 0.90 at non-bird FPR <= 2%
INT8 recall drop < 3 percentage points
TFLM tensor arena fits target memory
feature + inference latency is acceptable
average current meets battery target with gating/duty cycling
field false-positive rate is acceptable
```

Move to a 2-second Student only if:

```text
5 s fails memory, latency, or energy constraints
or field testing requires faster localization
```

Do not move to a shorter window merely because it is theoretically cheaper.

---

## 10. Final Roadmap

### Stage 1: 5 s Hard-Label Baseline

```text
Train 5 s log-mel DS-CNN using hard labels.
Evaluate with group-by-clip CV.
```

### Stage 2: 5 s KD Comparison

```text
Compare hard-label baseline against:
- binary soft labels
- mixed hard/soft labels
- temperature-softened 27-class collapsed labels
```

Keep KD only if it improves relevant metrics.

### Stage 3: 5 s INT8 Export and Profiling

```text
Export the best 5 s model to TFLite.
Quantize to INT8.
Check float-vs-INT8 parity.
Profile on XIAO ESP32S3.
```

### Stage 4: 2 s Fallback Only If Needed

```text
If 5 s fails memory/latency/energy constraints, design a 2 s fallback.
Use positive-window mining and avoid naive inherited labels.
```

### Stage 5: Field Data Collection and Threshold Tuning

```text
Collect birdhouse-like real recordings.
Evaluate real false-positive rate.
Evaluate real bird recall.
Tune threshold.
Expand dataset if field performance is poor.
```

---

## 11. Final Statement

The first Student implementation will be 5 seconds.

This decision overrides the earlier recommendation of using a 2-second model as the primary
Student. Shorter windows remain a fallback, not the starting point.

The guiding principle is:

```text
Do not introduce weak-label risk before proving that 5 seconds is actually too expensive.
```

