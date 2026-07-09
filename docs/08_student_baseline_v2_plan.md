# 08 - Student 5 s Hard-Label Baseline v2 Plan

This document defines the second hard-label baseline experiment.

## Why v2

The first 5-second hard-label baseline proved that the pipeline works, but its bird recall was
not high enough for deployment. The main weakness was recall, especially for `24wingflapping`.

v2 keeps the same input definition but changes the training method.

## Fixed design choices

```text
duration = 5 s
sample_rate = 16 kHz
feature = 40-bin log-mel
task = binary bird / non-bird
labels = hard labels only
```

## Changes from v1

```text
balanced batches with positive oversampling
feature-level augmentation
binary focal loss
slightly wider compact DS-CNN
```

## Intended effect

```text
Improve bird recall
Improve 24wingflapping recall
Keep false positives controlled
Improve recall at FPR <= 2%
```

## Evaluation

Compare directly against v1 using:

```text
bird recall @ threshold 0.5
bird precision @ threshold 0.5
PR-AUC
ROC-AUC
recall at FPR <= 2%
per-folder false-positive rate
24wingflapping recall
```

## Decision rule

If v2 improves recall without creating unacceptable false positives, keep it as the stronger
hard-label baseline.

If v2 improves recall but creates too many false positives, tune the focal loss parameters or
threshold.

If v2 does not improve recall, inspect feature resolution, augmentation, and architecture
before moving to KD.

