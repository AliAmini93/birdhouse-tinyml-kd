# Student 5 s Binary KD v1 Report

Binary KD experiment. Uses Teacher P(bird) soft labels and hard labels.

## Design

```text
input = 5 s / 16 kHz / 40-bin log-mel
model = same compact DS-CNN v2 architecture
sampling = balanced positive/negative batches
augmentation = same feature-level augmentation as hard-label v2
hard loss = focal loss alpha=0.75, gamma=2.0
KD loss = BCE(teacher_p_bird, student_p_bird)
hard_weight = 0.7
kd_weight = 0.3
```

## Teacher soft-label source

```text
soft_label_csv = teacher_kd/soft_labels/fsc22_soft_labels_binary.csv
prob_col = p_bird
path_col = file_path
match_mode = basename
```

## Summary

- Total clips: 2025
- Bird clips: 150
- Non-bird clips: 1875
- Feature shape: [40, 249]
- Parameter count: 32097
- Mean teacher P(bird), bird clips: 0.9075
- Mean teacher P(bird), non-bird clips: 0.0052
- Teacher binary accuracy @0.5 against hard labels: 0.9956

## Cross-Validation Metrics

- accuracy_0p5: 0.9694 ± 0.0100
- precision_0p5: 0.7830 ± 0.0875
- recall_0p5: 0.8400 ± 0.0490
- f1_0p5: 0.8056 ± 0.0452
- roc_auc: 0.9796 ± 0.0095
- pr_auc: 0.8862 ± 0.0176
- recall_at_fpr_target: 0.8400 ± 0.0389
- fpr_at_target: 0.0139 ± 0.0026

## Comparison against hard-label v2

| metric | hard-label v2 | KD v1 | delta |
|---|---:|---:|---:|
| accuracy_0p5 | 0.9235 | 0.9694 | +0.0459 |
| precision_0p5 | 0.5362 | 0.7830 | +0.2468 |
| recall_0p5 | 0.9000 | 0.8400 | -0.0600 |
| f1_0p5 | 0.6577 | 0.8056 | +0.1479 |
| pr_auc | 0.8659 | 0.8862 | +0.0203 |
| roc_auc | 0.9733 | 0.9796 | +0.0063 |
| recall_at_fpr_target | 0.7867 | 0.8400 | +0.0533 |

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   steps_per_epoch |   epochs_ran |   best_val_hard_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | weights_path                                                                           | loss                        |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|------------------:|-------------:|-----------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:---------------------------------------------------------------------------------------|:----------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           53 |               0.857876 |       0.967901 |        0.793103 |     0.766667 | 0.779661 |       23 |        7 |        6 |      369 |  0.978844 | 0.857876 |         0.02 |                  0.56835  |               0.766667 |                  0.821429 |       0.0133333 |          -9.19253 |          3.80261 | student/results/5s_kd_binary_hw07_kw03/models/student_5s_kd_binary_v1_fold0.weights.h5 | hard_focal*0.7+soft_bce*0.3 |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           50 |               0.880241 |       0.975309 |        0.8125   |     0.866667 | 0.83871  |       26 |        4 |        6 |      369 |  0.9624   | 0.880241 |         0.02 |                  0.559814 |               0.866667 |                  0.83871  |       0.0133333 |          -9.18274 |          3.79838 | student/results/5s_kd_binary_hw07_kw03/models/student_5s_kd_binary_v1_fold1.weights.h5 | hard_focal*0.7+soft_bce*0.3 |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           60 |               0.909813 |       0.977778 |        0.83871  |     0.866667 | 0.852459 |       26 |        4 |        5 |      370 |  0.991022 | 0.909813 |         0.02 |                  0.506463 |               0.866667 |                  0.83871  |       0.0133333 |          -9.1788  |          3.78613 | student/results/5s_kd_binary_hw07_kw03/models/student_5s_kd_binary_v1_fold2.weights.h5 | hard_focal*0.7+soft_bce*0.3 |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           35 |               0.884594 |       0.950617 |        0.613636 |     0.9      | 0.72973  |       27 |        3 |       17 |      358 |  0.982311 | 0.884594 |         0.02 |                  0.719071 |               0.866667 |                  0.787879 |       0.0186667 |          -9.16576 |          3.78992 | student/results/5s_kd_binary_hw07_kw03/models/student_5s_kd_binary_v1_fold3.weights.h5 | hard_focal*0.7+soft_bce*0.3 |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           38 |               0.898501 |       0.975309 |        0.857143 |     0.8      | 0.827586 |       24 |        6 |        4 |      371 |  0.983644 | 0.898501 |         0.02 |                  0.490337 |               0.833333 |                  0.862069 |       0.0106667 |          -9.24762 |          3.76834 | student/results/5s_kd_binary_hw07_kw03/models/student_5s_kd_binary_v1_fold4.weights.h5 | hard_focal*0.7+soft_bce*0.3 |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |   0.0182207   |                      0 |   1        |       nan        |            0         |
| 02rain          | False            |  75 |   0.120914    |                      8 |   0.893333 |       nan        |            0.106667  |
| 03thunderstorm  | False            |  75 |   0.000573538 |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |   0.033213    |                      1 |   0.986667 |       nan        |            0.0133333 |
| 05wind          | False            |  75 |   0.042006    |                      1 |   0.986667 |       nan        |            0.0133333 |
| 06silence       | False            |  75 |   0.0403387   |                      0 |   1        |       nan        |            0         |
| 07treefalling   | False            |  75 |   0.0494163   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 08helicopter    | False            |  75 |   0.0285688   |                      3 |   0.96     |       nan        |            0.04      |
| 09vehicleengine | False            |  75 |   0.0251301   |                      2 |   0.973333 |       nan        |            0.0266667 |
| 10axe           | False            |  75 |   0.00950259  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 11chainsaw      | False            |  75 |   0.0517346   |                      2 |   0.973333 |       nan        |            0.0266667 |
| 12generator     | False            |  75 |   0.0134681   |                      0 |   1        |       nan        |            0         |
| 13handsaw       | False            |  75 |   0.0262745   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 14firework      | False            |  75 |   0.0150517   |                      0 |   1        |       nan        |            0         |
| 15gunshot       | False            |  75 |   0.0147653   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 16woodchop      | False            |  75 |   0.020305    |                      2 |   0.973333 |       nan        |            0.0266667 |
| 17whistling     | False            |  75 |   0.0226078   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 18speaking      | False            |  75 |   0.0221763   |                      0 |   1        |       nan        |            0         |
| 19footsteps     | False            |  75 |   0.078914    |                      5 |   0.933333 |       nan        |            0.0666667 |
| 20clapping      | False            |  75 |   0.0154238   |                      0 |   1        |       nan        |            0         |
| 21insect        | False            |  75 |   0.104606    |                      6 |   0.92     |       nan        |            0.08      |
| 22frog          | False            |  75 |   0.0251069   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 23birdchirping  | True             |  75 |   0.859154    |                     68 |   0.906667 |         0.906667 |          nan         |
| 24wingflapping  | True             |  75 |   0.639607    |                     58 |   0.773333 |         0.773333 |          nan         |
| 25lion          | False            |  75 |   0.0191719   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 26wolfhowl      | False            |  75 |   0.00695557  |                      0 |   1        |       nan        |            0         |
| 27squirrel      | False            |  75 |   0.0733931   |                      1 |   0.986667 |       nan        |            0.0133333 |

## Interpretation guide

- KD is useful only if it improves PR-AUC, recall at FPR <= 2%, or false-positive behavior over hard-label v2.
- If KD does not improve, this supports the earlier hypothesis that binary soft labels are too close to hard labels.
- If KD improves mainly on `24wingflapping` or reduces rain/insect/squirrel false positives, keep it for the next stage.

## Output Files

- `results/5s_kd_binary_hw07_kw03/metrics_summary.json`
- `results/5s_kd_binary_hw07_kw03/fold_metrics.csv`
- `results/5s_kd_binary_hw07_kw03/per_folder_metrics.csv`
- `results/5s_kd_binary_hw07_kw03/predictions_all_folds.csv`
- `results/5s_kd_binary_hw07_kw03/student_5s_kd_binary_v1_report.md`
