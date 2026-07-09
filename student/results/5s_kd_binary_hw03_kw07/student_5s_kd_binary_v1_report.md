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
hard_weight = 0.3
kd_weight = 0.7
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

- accuracy_0p5: 0.9635 ± 0.0122
- precision_0p5: 0.7559 ± 0.1203
- recall_0p5: 0.8067 ± 0.0680
- f1_0p5: 0.7707 ± 0.0528
- roc_auc: 0.9781 ± 0.0105
- pr_auc: 0.8819 ± 0.0382
- recall_at_fpr_target: 0.8333 ± 0.0632
- fpr_at_target: 0.0155 ± 0.0026

## Comparison against hard-label v2

| metric | hard-label v2 | KD v1 | delta |
|---|---:|---:|---:|
| accuracy_0p5 | 0.9235 | 0.9635 | +0.0400 |
| precision_0p5 | 0.5362 | 0.7559 | +0.2197 |
| recall_0p5 | 0.9000 | 0.8067 | -0.0933 |
| f1_0p5 | 0.6577 | 0.7707 | +0.1130 |
| pr_auc | 0.8659 | 0.8819 | +0.0160 |
| roc_auc | 0.9733 | 0.9781 | +0.0048 |
| recall_at_fpr_target | 0.7867 | 0.8333 | +0.0467 |

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   steps_per_epoch |   epochs_ran |   best_val_hard_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | weights_path                                                                           | loss                        |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|------------------:|-------------:|-----------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:---------------------------------------------------------------------------------------|:----------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           52 |               0.833364 |       0.960494 |        0.733333 |     0.733333 | 0.733333 |       22 |        8 |        8 |      367 |  0.972267 | 0.833364 |         0.02 |                  0.607099 |               0.733333 |                  0.814815 |       0.0133333 |          -9.19253 |          3.80261 | student/results/5s_kd_binary_hw03_kw07/models/student_5s_kd_binary_v1_fold0.weights.h5 | hard_focal*0.3+soft_bce*0.7 |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           38 |               0.838379 |       0.962963 |        0.702703 |     0.866667 | 0.776119 |       26 |        4 |       11 |      364 |  0.961422 | 0.838379 |         0.02 |                  0.580135 |               0.8      |                  0.774194 |       0.0186667 |          -9.18274 |          3.79838 | student/results/5s_kd_binary_hw03_kw07/models/student_5s_kd_binary_v1_fold1.weights.h5 | hard_focal*0.3+soft_bce*0.7 |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           43 |               0.909261 |       0.97037  |        0.846154 |     0.733333 | 0.785714 |       22 |        8 |        4 |      371 |  0.988978 | 0.909261 |         0.02 |                  0.436298 |               0.833333 |                  0.833333 |       0.0133333 |          -9.1788  |          3.78613 | student/results/5s_kd_binary_hw03_kw07/models/student_5s_kd_binary_v1_fold2.weights.h5 | hard_focal*0.3+soft_bce*0.7 |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           38 |               0.92457  |       0.94321  |        0.574468 |     0.9      | 0.701299 |       27 |        3 |       20 |      355 |  0.989156 | 0.92457  |         0.02 |                  0.757497 |               0.9      |                  0.794118 |       0.0186667 |          -9.16576 |          3.78992 | student/results/5s_kd_binary_hw03_kw07/models/student_5s_kd_binary_v1_fold3.weights.h5 | hard_focal*0.3+soft_bce*0.7 |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           55 |               0.904116 |       0.980247 |        0.923077 |     0.8      | 0.857143 |       24 |        6 |        2 |      373 |  0.978578 | 0.904116 |         0.02 |                  0.240365 |               0.9      |                  0.84375  |       0.0133333 |          -9.24762 |          3.76834 | student/results/5s_kd_binary_hw03_kw07/models/student_5s_kd_binary_v1_fold4.weights.h5 | hard_focal*0.3+soft_bce*0.7 |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |   0.0339955   |                      2 |   0.973333 |       nan        |            0.0266667 |
| 02rain          | False            |  75 |   0.105263    |                      7 |   0.906667 |       nan        |            0.0933333 |
| 03thunderstorm  | False            |  75 |   0.000444981 |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |   0.0336649   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 05wind          | False            |  75 |   0.0220653   |                      0 |   1        |       nan        |            0         |
| 06silence       | False            |  75 |   0.028872    |                      1 |   0.986667 |       nan        |            0.0133333 |
| 07treefalling   | False            |  75 |   0.0545592   |                      3 |   0.96     |       nan        |            0.04      |
| 08helicopter    | False            |  75 |   0.0266657   |                      2 |   0.973333 |       nan        |            0.0266667 |
| 09vehicleengine | False            |  75 |   0.0369297   |                      3 |   0.96     |       nan        |            0.04      |
| 10axe           | False            |  75 |   0.00554035  |                      0 |   1        |       nan        |            0         |
| 11chainsaw      | False            |  75 |   0.0737136   |                      5 |   0.933333 |       nan        |            0.0666667 |
| 12generator     | False            |  75 |   0.0353213   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 13handsaw       | False            |  75 |   0.0205027   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 14firework      | False            |  75 |   0.0291106   |                      2 |   0.973333 |       nan        |            0.0266667 |
| 15gunshot       | False            |  75 |   0.0110337   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 16woodchop      | False            |  75 |   0.0168923   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 17whistling     | False            |  75 |   0.0134639   |                      0 |   1        |       nan        |            0         |
| 18speaking      | False            |  75 |   0.0278952   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 19footsteps     | False            |  75 |   0.0802441   |                      5 |   0.933333 |       nan        |            0.0666667 |
| 20clapping      | False            |  75 |   0.0100361   |                      0 |   1        |       nan        |            0         |
| 21insect        | False            |  75 |   0.110719    |                      6 |   0.92     |       nan        |            0.08      |
| 22frog          | False            |  75 |   0.0155812   |                      0 |   1        |       nan        |            0         |
| 23birdchirping  | True             |  75 |   0.865813    |                     67 |   0.893333 |         0.893333 |          nan         |
| 24wingflapping  | True             |  75 |   0.645002    |                     54 |   0.72     |         0.72     |          nan         |
| 25lion          | False            |  75 |   0.00948958  |                      0 |   1        |       nan        |            0         |
| 26wolfhowl      | False            |  75 |   0.0089418   |                      1 |   0.986667 |       nan        |            0.0133333 |
| 27squirrel      | False            |  75 |   0.0418318   |                      2 |   0.973333 |       nan        |            0.0266667 |

## Interpretation guide

- KD is useful only if it improves PR-AUC, recall at FPR <= 2%, or false-positive behavior over hard-label v2.
- If KD does not improve, this supports the earlier hypothesis that binary soft labels are too close to hard labels.
- If KD improves mainly on `24wingflapping` or reduces rain/insect/squirrel false positives, keep it for the next stage.

## Output Files

- `results/5s_kd_binary_hw03_kw07/metrics_summary.json`
- `results/5s_kd_binary_hw03_kw07/fold_metrics.csv`
- `results/5s_kd_binary_hw03_kw07/per_folder_metrics.csv`
- `results/5s_kd_binary_hw03_kw07/predictions_all_folds.csv`
- `results/5s_kd_binary_hw03_kw07/student_5s_kd_binary_v1_report.md`
