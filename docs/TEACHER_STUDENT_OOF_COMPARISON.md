# Teacher OOF vs Student OOF Comparison

## Final status

Teacher out-of-fold predictions were reconstructed from the five existing
`Swint_LSTM_0.pth` through `Swint_LSTM_4.pth` checkpoints. No Teacher
retraining was performed.

Both models are evaluated on the same 2,025 FSC22 files and the same binary
ground truth. Every Teacher prediction comes from the checkpoint associated
with that sample's original held-out fold. Every Student prediction is the
previously stored Student OOF prediction.

## Integrity checks

- Total clips: 2,025
- Bird clips: 150
- Non-bird clips: 1,875
- Teacher folds: 5 × 405 clips
- Teacher inference batch size: 32
- Teacher preprocessing: exact recovered original preprocessing
- Recovered bird output indices: `[12, 20]`
- Aggregate recovered-mapping 27-class OOF top-1 accuracy: 93.78%
- Teacher retraining: **not performed**
- Student retraining: **not performed**

The Teacher and Student fold memberships were produced by different splitting
procedures. Therefore both prediction sets are genuinely OOF, but their
training subsets are not identical for every sample. This is an unbiased
aggregate OOF comparison, not a fold-identical retraining experiment.

## Per-fold Teacher verification

| Fold | Checkpoint | N | Mapped 27-class top-1 accuracy | Binary sensitivity @0.5 | Binary specificity @0.5 |
|---:|---|---:|---:|---:|---:|
| 0 | `2025_07_21_16_06_03_Swint_LSTM_0.pth` | 405 | 92.59% | 96.67% | 99.73% |
| 1 | `2025_07_21_16_35_14_Swint_LSTM_1.pth` | 405 | 94.81% | 96.67% | 100.00% |
| 2 | `2025_07_21_17_00_24_Swint_LSTM_2.pth` | 405 | 94.32% | 100.00% | 100.00% |
| 3 | `2025_07_21_17_23_53_Swint_LSTM_3.pth` | 405 | 92.59% | 96.67% | 100.00% |
| 4 | `2025_07_21_17_49_00_Swint_LSTM_4.pth` | 405 | 94.57% | 96.67% | 99.73% |

## Comparison at the same threshold: 0.5

| Model | Threshold | Sensitivity | Specificity | Precision | NPV | F1 | Accuracy | Balanced accuracy | MCC | ROC-AUC | PR-AUC | TP | FN | TN | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Teacher OOF | 0.500000000 | 97.33% | 99.89% | 98.65% | 99.79% | 97.99% | 99.70% | 98.61% | 0.9783 | 99.97% | 99.75% | 146 | 4 | 1873 | 2 |
| Student OOF | 0.500000000 | 87.33% | 96.59% | 67.18% | 98.96% | 75.94% | 95.90% | 91.96% | 0.7450 | 98.24% | 87.68% | 131 | 19 | 1811 | 64 |

### Change after compression/distillation

| Metric | Teacher | Student | Student − Teacher |
|---|---:|---:|---:|
| sensitivity | 97.33% | 87.33% | -10.00 pp |
| specificity | 99.89% | 96.59% | -3.31 pp |
| precision | 98.65% | 67.18% | -31.47 pp |
| f1 | 97.99% | 75.94% | -22.04 pp |
| accuracy | 99.70% | 95.90% | -3.80 pp |
| balanced_accuracy | 98.61% | 91.96% | -6.65 pp |
| mcc | 0.9783 | 0.7450 | -0.2333 |
| roc_auc | 99.97% | 98.24% | -1.73 pp |
| pr_auc | 99.75% | 87.68% | -12.06 pp |
| brier | 0.0036 | 0.0307 | +0.0271 |

### Paired bootstrap uncertainty for Student − Teacher

| Metric | Mean delta | 95% paired-bootstrap CI |
|---|---:|---:|
| sensitivity | -9.94 pp | [-15.33, -4.67] pp |
| specificity | -3.30 pp | [-4.16, -2.45] pp |
| precision | -31.32 pp | [-36.87, -25.29] pp |
| f1 | -21.95 pp | [-26.77, -17.12] pp |
| accuracy | -3.79 pp | [-4.69, -2.91] pp |
| balanced_accuracy | -6.62 pp | [-9.56, -3.80] pp |
| mcc | -0.2322 | [-0.2845, -0.1817] |
| roc_auc | -1.72 pp | [-2.48, -1.09] pp |
| pr_auc | -11.92 pp | [-16.08, -8.26] pp |
| brier | +0.0270 | [+0.0220, +0.0321] |

At this threshold:

- Both correct: 1937
- Teacher only correct: 82
- Student only correct: 5
- Both wrong: 1
- Prediction disagreements: 87
- Exact McNemar p-value: 5.07754e-19

## Comparison at the common firmware threshold: 0.673462986946106

| Model | Threshold | Sensitivity | Specificity | Precision | NPV | F1 | Accuracy | Balanced accuracy | MCC | ROC-AUC | PR-AUC | TP | FN | TN | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Teacher OOF | 0.673462987 | 92.67% | 100.00% | 100.00% | 99.42% | 96.19% | 99.46% | 96.33% | 0.9598 | 99.97% | 99.75% | 139 | 11 | 1875 | 0 |
| Student OOF | 0.673462987 | 80.00% | 98.08% | 76.92% | 98.39% | 78.43% | 96.74% | 89.04% | 0.7669 | 98.24% | 87.68% | 120 | 30 | 1839 | 36 |

| Metric | Teacher | Student | Student − Teacher |
|---|---:|---:|---:|
| sensitivity | 92.67% | 80.00% | -12.67 pp |
| specificity | 100.00% | 98.08% | -1.92 pp |
| precision | 100.00% | 76.92% | -23.08 pp |
| f1 | 96.19% | 78.43% | -17.76 pp |
| accuracy | 99.46% | 96.74% | -2.72 pp |
| balanced_accuracy | 96.33% | 89.04% | -7.29 pp |
| mcc | 0.9598 | 0.7669 | -0.1930 |
| roc_auc | 99.97% | 98.24% | -1.73 pp |
| pr_auc | 99.75% | 87.68% | -12.06 pp |
| brier | 0.0036 | 0.0307 | +0.0271 |

## Actual operating thresholds

Teacher uses 0.5 and the deployed Student uses 0.673462986946106.

| Model | Threshold | Sensitivity | Specificity | Precision | NPV | F1 | Accuracy | Balanced accuracy | MCC | ROC-AUC | PR-AUC | TP | FN | TN | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Teacher OOF | 0.500000000 | 97.33% | 99.89% | 98.65% | 99.79% | 97.99% | 99.70% | 98.61% | 0.9783 | 99.97% | 99.75% | 146 | 4 | 1873 | 2 |
| Student OOF | 0.673462987 | 80.00% | 98.08% | 76.92% | 98.39% | 78.43% | 96.74% | 89.04% | 0.7669 | 98.24% | 87.68% | 120 | 30 | 1839 | 36 |

At these operating thresholds:

- Both correct: 1954
- Teacher only correct: 65
- Student only correct: 5
- Both wrong: 1
- Prediction disagreements: 70
- Exact McNemar p-value: 2.21535e-14

## Matched FPR operating point

The threshold for each model was selected descriptively from its OOF
predictions to maximize recall while keeping FPR at or below 2.00%.
These thresholds must not be treated as independently validated calibration
values.

- Teacher threshold: 0.300526828
- Student threshold: 0.673462987

| Model | Threshold | Sensitivity | Specificity | Precision | NPV | F1 | Accuracy | Balanced accuracy | MCC | ROC-AUC | PR-AUC | TP | FN | TN | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Teacher OOF | 0.300526828 | 99.33% | 99.63% | 95.51% | 99.95% | 97.39% | 99.60% | 99.48% | 0.9719 | 99.97% | 99.75% | 149 | 1 | 1868 | 7 |
| Student OOF | 0.673462987 | 80.00% | 98.08% | 76.92% | 98.39% | 78.43% | 96.74% | 89.04% | 0.7669 | 98.24% | 87.68% | 120 | 30 | 1839 | 36 |

| Metric | Teacher | Student | Student − Teacher |
|---|---:|---:|---:|
| sensitivity | 99.33% | 80.00% | -19.33 pp |
| specificity | 99.63% | 98.08% | -1.55 pp |
| precision | 95.51% | 76.92% | -18.59 pp |
| f1 | 97.39% | 78.43% | -18.95 pp |
| accuracy | 99.60% | 96.74% | -2.86 pp |
| balanced_accuracy | 99.48% | 89.04% | -10.44 pp |
| mcc | 0.9719 | 0.7669 | -0.2051 |
| roc_auc | 99.97% | 98.24% | -1.73 pp |
| pr_auc | 99.75% | 87.68% | -12.06 pp |
| brier | 0.0036 | 0.0307 | +0.0271 |

## Interpretation boundary

This report answers the question: how much binary bird/non-bird OOF
performance was retained by the Student relative to the Teacher on FSC22?

It does not estimate field performance under a new microphone, birdhouse
acoustics, weather, unseen species, or other deployment domain shifts.
