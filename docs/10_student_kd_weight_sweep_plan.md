# 10 - Student 5 s KD Weight Sweep Plan

This step tests whether the KD/hard-label mixture can improve over binary KD v1.

Fixed setup:

```text
5 s input
16 kHz mono
40-bin log-mel
same compact DS-CNN v2 architecture
same balanced batches
same augmentation
same binary Teacher soft labels
same 5-fold evaluation
```

Sweep:

```text
hard_weight=0.8, kd_weight=0.2
hard_weight=0.7, kd_weight=0.3
hard_weight=0.3, kd_weight=0.7
```

References:

```text
hard-label v2
KD v1: hard_weight=0.5, kd_weight=0.5
```

Decision criteria:

```text
recall at FPR <= 2%
PR-AUC
24wingflapping recall
false positives on rain/treefalling/insect/squirrel
```

