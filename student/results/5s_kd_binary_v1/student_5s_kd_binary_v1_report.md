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
hard_weight = 0.5
kd_weight = 0.5
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

- accuracy_0p5: 0.9704 ± 0.0121
- precision_0p5: 0.7951 ± 0.1070
- recall_0p5: 0.8333 ± 0.0422
- f1_0p5: 0.8103 ± 0.0667
- roc_auc: 0.9812 ± 0.0115
- pr_auc: 0.8905 ± 0.0555
- recall_at_fpr_target: 0.8533 ± 0.0581
- fpr_at_target: 0.0155 ± 0.0039

## Comparison against hard-label v2

| metric | hard-label v2 | KD v1 | delta |
|---|---:|---:|---:|
| accuracy_0p5 | 0.9235 | 0.9704 | +0.0469 |
| precision_0p5 | 0.5362 | 0.7951 | +0.2588 |
| recall_0p5 | 0.9000 | 0.8333 | -0.0667 |
| f1_0p5 | 0.6577 | 0.8103 | +0.1526 |
| pr_auc | 0.8659 | 0.8905 | +0.0246 |
| roc_auc | 0.9733 | 0.9812 | +0.0079 |
| recall_at_fpr_target | 0.7867 | 0.8533 | +0.0667 |

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   steps_per_epoch |   epochs_ran |   best_val_hard_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | weights_path                                                                    | loss                        |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|------------------:|-------------:|-----------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:--------------------------------------------------------------------------------|:----------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           44 |               0.822428 |       0.967901 |        0.774194 |     0.8      | 0.786885 |       24 |        6 |        7 |      368 |  0.973867 | 0.822428 |         0.02 |                  0.496662 |               0.833333 |                  0.78125  |       0.0186667 |          -9.19253 |          3.80261 | student/results/5s_kd_binary_v1/models/student_5s_kd_binary_v1_fold0.weights.h5 | hard_focal*0.5+soft_bce*0.5 |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           43 |               0.826723 |       0.962963 |        0.741935 |     0.766667 | 0.754098 |       23 |        7 |        8 |      367 |  0.962578 | 0.826723 |         0.02 |                  0.617774 |               0.766667 |                  0.793103 |       0.016     |          -9.18274 |          3.79838 | student/results/5s_kd_binary_v1/models/student_5s_kd_binary_v1_fold1.weights.h5 | hard_focal*0.5+soft_bce*0.5 |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           47 |               0.954263 |       0.982716 |        0.896552 |     0.866667 | 0.881356 |       26 |        4 |        3 |      372 |  0.9936   | 0.954263 |         0.02 |                  0.312695 |               0.933333 |                  0.8      |       0.0186667 |          -9.1788  |          3.78613 | student/results/5s_kd_binary_v1/models/student_5s_kd_binary_v1_fold2.weights.h5 | hard_focal*0.5+soft_bce*0.5 |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           32 |               0.912323 |       0.953086 |        0.634146 |     0.866667 | 0.732394 |       26 |        4 |       15 |      360 |  0.985244 | 0.912323 |         0.02 |                  0.874048 |               0.833333 |                  0.892857 |       0.008     |          -9.16576 |          3.78992 | student/results/5s_kd_binary_v1/models/student_5s_kd_binary_v1_fold3.weights.h5 | hard_focal*0.5+soft_bce*0.5 |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           61 |               0.936849 |       0.985185 |        0.928571 |     0.866667 | 0.896552 |       26 |        4 |        2 |      373 |  0.990933 | 0.936849 |         0.02 |                  0.416439 |               0.9      |                  0.818182 |       0.016     |          -9.24762 |          3.76834 | student/results/5s_kd_binary_v1/models/student_5s_kd_binary_v1_fold4.weights.h5 | hard_focal*0.5+soft_bce*0.5 |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |    0.0217415  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 02rain          | False            |  75 |    0.12484    |                      9 |   0.88     |       nan        |            0.12      |
| 03thunderstorm  | False            |  75 |    0.00067059 |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |    0.0304345  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 05wind          | False            |  75 |    0.0213512  |                      0 |   1        |       nan        |            0         |
| 06silence       | False            |  75 |    0.0325911  |                      0 |   1        |       nan        |            0         |
| 07treefalling   | False            |  75 |    0.059609   |                      3 |   0.96     |       nan        |            0.04      |
| 08helicopter    | False            |  75 |    0.032579   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 09vehicleengine | False            |  75 |    0.0263607  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 10axe           | False            |  75 |    0.00604402 |                      0 |   1        |       nan        |            0         |
| 11chainsaw      | False            |  75 |    0.0558658  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 12generator     | False            |  75 |    0.0212149  |                      0 |   1        |       nan        |            0         |
| 13handsaw       | False            |  75 |    0.0117681  |                      0 |   1        |       nan        |            0         |
| 14firework      | False            |  75 |    0.0167815  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 15gunshot       | False            |  75 |    0.0145043  |                      0 |   1        |       nan        |            0         |
| 16woodchop      | False            |  75 |    0.0133029  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 17whistling     | False            |  75 |    0.0298032  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 18speaking      | False            |  75 |    0.0259977  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 19footsteps     | False            |  75 |    0.0595855  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 20clapping      | False            |  75 |    0.0174991  |                      0 |   1        |       nan        |            0         |
| 21insect        | False            |  75 |    0.0909877  |                      5 |   0.933333 |       nan        |            0.0666667 |
| 22frog          | False            |  75 |    0.0166534  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 23birdchirping  | True             |  75 |    0.878262   |                     68 |   0.906667 |         0.906667 |          nan         |
| 24wingflapping  | True             |  75 |    0.64693    |                     57 |   0.76     |         0.76     |          nan         |
| 25lion          | False            |  75 |    0.0151243  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 26wolfhowl      | False            |  75 |    0.00619021 |                      0 |   1        |       nan        |            0         |
| 27squirrel      | False            |  75 |    0.0469591  |                      1 |   0.986667 |       nan        |            0.0133333 |

## Interpretation guide

- KD is useful only if it improves PR-AUC, recall at FPR <= 2%, or false-positive behavior over hard-label v2.
- If KD does not improve, this supports the earlier hypothesis that binary soft labels are too close to hard labels.
- If KD improves mainly on `24wingflapping` or reduces rain/insect/squirrel false positives, keep it for the next stage.

## Output Files

- `results/5s_kd_binary_v1/metrics_summary.json`
- `results/5s_kd_binary_v1/fold_metrics.csv`
- `results/5s_kd_binary_v1/per_folder_metrics.csv`
- `results/5s_kd_binary_v1/predictions_all_folds.csv`
- `results/5s_kd_binary_v1/student_5s_kd_binary_v1_report.md`
