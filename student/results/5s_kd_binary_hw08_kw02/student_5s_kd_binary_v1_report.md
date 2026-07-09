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
hard_weight = 0.8
kd_weight = 0.2
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

- accuracy_0p5: 0.9590 ± 0.0306
- precision_0p5: 0.7275 ± 0.1586
- recall_0p5: 0.8733 ± 0.0533
- f1_0p5: 0.7798 ± 0.1076
- roc_auc: 0.9859 ± 0.0060
- pr_auc: 0.9051 ± 0.0318
- recall_at_fpr_target: 0.8600 ± 0.0533
- fpr_at_target: 0.0155 ± 0.0031

## Comparison against hard-label v2

| metric | hard-label v2 | KD v1 | delta |
|---|---:|---:|---:|
| accuracy_0p5 | 0.9235 | 0.9590 | +0.0356 |
| precision_0p5 | 0.5362 | 0.7275 | +0.1913 |
| recall_0p5 | 0.9000 | 0.8733 | -0.0267 |
| f1_0p5 | 0.6577 | 0.7798 | +0.1221 |
| pr_auc | 0.8659 | 0.9051 | +0.0392 |
| roc_auc | 0.9733 | 0.9859 | +0.0126 |
| recall_at_fpr_target | 0.7867 | 0.8600 | +0.0733 |

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   steps_per_epoch |   epochs_ran |   best_val_hard_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | weights_path                                                                           | loss                        |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|------------------:|-------------:|-----------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:---------------------------------------------------------------------------------------|:----------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           41 |               0.865494 |       0.965432 |        0.75     |     0.8      | 0.774194 |       24 |        6 |        8 |      367 |  0.980178 | 0.865494 |         0.02 |                  0.546541 |               0.8      |                  0.774194 |       0.0186667 |          -9.19253 |          3.80261 | student/results/5s_kd_binary_hw08_kw02/models/student_5s_kd_binary_v1_fold0.weights.h5 | hard_focal*0.8+soft_bce*0.2 |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           46 |               0.906904 |       0.97284  |        0.787879 |     0.866667 | 0.825397 |       26 |        4 |        7 |      368 |  0.987644 | 0.906904 |         0.02 |                  0.566956 |               0.866667 |                  0.83871  |       0.0133333 |          -9.18274 |          3.79838 | student/results/5s_kd_binary_hw08_kw02/models/student_5s_kd_binary_v1_fold1.weights.h5 | hard_focal*0.8+soft_bce*0.2 |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           60 |               0.948101 |       0.982716 |        0.848485 |     0.933333 | 0.888889 |       28 |        2 |        5 |      370 |  0.994756 | 0.948101 |         0.02 |                  0.549927 |               0.933333 |                  0.875    |       0.0106667 |          -9.1788  |          3.78613 | student/results/5s_kd_binary_hw08_kw02/models/student_5s_kd_binary_v1_fold2.weights.h5 | hard_focal*0.8+soft_bce*0.2 |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           26 |               0.874229 |       0.898765 |        0.41791  |     0.933333 | 0.57732  |       28 |        2 |       39 |      336 |  0.978133 | 0.874229 |         0.02 |                  0.834795 |               0.8      |                  0.8      |       0.016     |          -9.16576 |          3.78992 | student/results/5s_kd_binary_hw08_kw02/models/student_5s_kd_binary_v1_fold3.weights.h5 | hard_focal*0.8+soft_bce*0.2 |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           52 |               0.930926 |       0.975309 |        0.833333 |     0.833333 | 0.833333 |       25 |        5 |        5 |      370 |  0.9888   | 0.930926 |         0.02 |                  0.401652 |               0.9      |                  0.794118 |       0.0186667 |          -9.24762 |          3.76834 | student/results/5s_kd_binary_hw08_kw02/models/student_5s_kd_binary_v1_fold4.weights.h5 | hard_focal*0.8+soft_bce*0.2 |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |    0.0675021  |                      3 |   0.96     |       nan        |            0.04      |
| 02rain          | False            |  75 |    0.108443   |                      7 |   0.906667 |       nan        |            0.0933333 |
| 03thunderstorm  | False            |  75 |    0.00339295 |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |    0.0582745  |                      3 |   0.96     |       nan        |            0.04      |
| 05wind          | False            |  75 |    0.0737477  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 06silence       | False            |  75 |    0.0878512  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 07treefalling   | False            |  75 |    0.0668363  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 08helicopter    | False            |  75 |    0.0561346  |                      5 |   0.933333 |       nan        |            0.0666667 |
| 09vehicleengine | False            |  75 |    0.050691   |                      3 |   0.96     |       nan        |            0.04      |
| 10axe           | False            |  75 |    0.0101148  |                      0 |   1        |       nan        |            0         |
| 11chainsaw      | False            |  75 |    0.0510353  |                      3 |   0.96     |       nan        |            0.04      |
| 12generator     | False            |  75 |    0.0426614  |                      3 |   0.96     |       nan        |            0.04      |
| 13handsaw       | False            |  75 |    0.0333095  |                      0 |   1        |       nan        |            0         |
| 14firework      | False            |  75 |    0.0220399  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 15gunshot       | False            |  75 |    0.00973149 |                      0 |   1        |       nan        |            0         |
| 16woodchop      | False            |  75 |    0.019543   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 17whistling     | False            |  75 |    0.0341626  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 18speaking      | False            |  75 |    0.0664937  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 19footsteps     | False            |  75 |    0.137287   |                      9 |   0.88     |       nan        |            0.12      |
| 20clapping      | False            |  75 |    0.0301883  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 21insect        | False            |  75 |    0.136282   |                      5 |   0.933333 |       nan        |            0.0666667 |
| 22frog          | False            |  75 |    0.0591528  |                      3 |   0.96     |       nan        |            0.04      |
| 23birdchirping  | True             |  75 |    0.878333   |                     71 |   0.946667 |         0.946667 |          nan         |
| 24wingflapping  | True             |  75 |    0.689712   |                     60 |   0.8      |         0.8      |          nan         |
| 25lion          | False            |  75 |    0.0357787  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 26wolfhowl      | False            |  75 |    0.0155075  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 27squirrel      | False            |  75 |    0.0703441  |                      2 |   0.973333 |       nan        |            0.0266667 |

## Interpretation guide

- KD is useful only if it improves PR-AUC, recall at FPR <= 2%, or false-positive behavior over hard-label v2.
- If KD does not improve, this supports the earlier hypothesis that binary soft labels are too close to hard labels.
- If KD improves mainly on `24wingflapping` or reduces rain/insect/squirrel false positives, keep it for the next stage.

## Output Files

- `results/5s_kd_binary_hw08_kw02/metrics_summary.json`
- `results/5s_kd_binary_hw08_kw02/fold_metrics.csv`
- `results/5s_kd_binary_hw08_kw02/per_folder_metrics.csv`
- `results/5s_kd_binary_hw08_kw02/predictions_all_folds.csv`
- `results/5s_kd_binary_hw08_kw02/student_5s_kd_binary_v1_report.md`
