# 09 - Student 5 s Binary KD v1 Plan

This document defines the first Student KD comparison experiment.

## Purpose

Compare binary KD against the stronger hard-label baseline v2.

The comparison must be fair:

```text
same 5-second input
same 16 kHz / 40-bin log-mel feature
same compact DS-CNN v2 architecture
same 5-fold split strategy
same balanced batches
same feature augmentation
```

Only the supervision/loss changes.

## Teacher target

Use the collapsed binary Teacher probability:

```text
P(bird) = P(23birdchirping) + P(24wingflapping)
```

The expected file is:

```text
teacher_kd/soft_labels/fsc22_soft_labels_binary.csv
```

## Loss

```text
total_loss =
  hard_weight * focal_loss(hard_label, student_p_bird)
  +
  kd_weight   * BCE(teacher_p_bird, student_p_bird)
```

Initial weights:

```text
hard_weight = 0.5
kd_weight = 0.5
```

## Evaluation

Compare against hard-label v2 using:

```text
bird recall @ threshold 0.5
bird precision @ threshold 0.5
PR-AUC
ROC-AUC
recall at FPR <= 2%
per-folder false-positive rate
23birdchirping recall
24wingflapping recall
rain / treefalling / insect / squirrel false positives
```

## Decision rule

KD is useful only if it improves at least one of the following without unacceptable regressions:

```text
PR-AUC
recall at FPR <= 2%
24wingflapping recall
false positives on rain / insect / squirrel / treefalling
```

If KD does not improve the baseline, the conclusion is still useful: binary soft labels are too close
to hard labels for meaningful KD gains in this setup.

