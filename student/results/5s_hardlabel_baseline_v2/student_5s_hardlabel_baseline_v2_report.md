# Student 5 s Hard-Label Baseline v2 Report

Hard-label baseline v2. No Teacher/KD loss used in training.

## What changed from v1

```text
same 5 s / 16 kHz / 40-bin log-mel input
slightly wider compact DS-CNN
balanced batches with positive oversampling
feature-level augmentation
focal loss: alpha=0.75, gamma=2.0
```

## Summary

- Total clips: 2025
- Bird clips: 150
- Non-bird clips: 1875
- Feature shape: [40, 249]
- Parameter count: 32097

## Cross-Validation Metrics

- accuracy_0p5: 0.9235 ± 0.0413
- precision_0p5: 0.5362 ± 0.1381
- recall_0p5: 0.9000 ± 0.0667
- f1_0p5: 0.6577 ± 0.1075
- roc_auc: 0.9733 ± 0.0156
- pr_auc: 0.8659 ± 0.0435
- recall_at_fpr_target: 0.7867 ± 0.0859
- fpr_at_target: 0.0128 ± 0.0054

## Comparison against v1

| metric | v1 mean | v2 mean | delta |
|---|---:|---:|---:|
| accuracy_0p5 | 0.9462 | 0.9235 | -0.0227 |
| precision_0p5 | 0.6388 | 0.5362 | -0.1026 |
| recall_0p5 | 0.6933 | 0.9000 | +0.2067 |
| f1_0p5 | 0.6560 | 0.6577 | +0.0017 |
| pr_auc | 0.7042 | 0.8659 | +0.1618 |
| roc_auc | 0.9416 | 0.9733 | +0.0317 |
| recall_at_fpr_target | 0.6200 | 0.7867 | +0.1667 |

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   steps_per_epoch |   epochs_ran |   best_val_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | model_path                                                                          | loss                         |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|------------------:|-------------:|------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:------------------------------------------------------------------------------------|:-----------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           41 |          0.900433 |       0.91358  |        0.457627 |     0.9      | 0.606742 |       27 |        3 |       32 |      343 |  0.970578 | 0.901234 |         0.02 |                  0.88943  |               0.8      |                  0.923077 |      0.00533333 |          -9.2395  |          3.77432 | student/results/5s_hardlabel_baseline_v2/models/student_5s_hardlabel_v2_fold0.keras | focal(alpha=0.75, gamma=2.0) |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           35 |          0.819901 |       0.935802 |        0.541667 |     0.866667 | 0.666667 |       26 |        4 |       22 |      353 |  0.974578 | 0.821877 |         0.02 |                  0.846959 |               0.633333 |                  0.791667 |      0.0133333  |          -9.15806 |          3.80462 | student/results/5s_hardlabel_baseline_v2/models/student_5s_hardlabel_v2_fold1.keras | focal(alpha=0.75, gamma=2.0) |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           56 |          0.814408 |       0.948148 |        0.615385 |     0.8      | 0.695652 |       24 |        6 |       15 |      360 |  0.9456   | 0.809815 |         0.02 |                  0.752454 |               0.8      |                  0.888889 |      0.008      |          -9.19969 |          3.77855 | student/results/5s_hardlabel_baseline_v2/models/student_5s_hardlabel_v2_fold2.keras | focal(alpha=0.75, gamma=2.0) |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           31 |          0.873141 |       0.849383 |        0.32967  |     1        | 0.495868 |       30 |        0 |       61 |      314 |  0.985067 | 0.875951 |         0.02 |                  0.853323 |               0.8      |                  0.774194 |      0.0186667  |          -9.19094 |          3.79162 | student/results/5s_hardlabel_baseline_v2/models/student_5s_hardlabel_v2_fold3.keras | focal(alpha=0.75, gamma=2.0) |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |                94 |           40 |          0.920005 |       0.97037  |        0.736842 |     0.933333 | 0.823529 |       28 |        2 |       10 |      365 |  0.990667 | 0.920814 |         0.02 |                  0.582254 |               0.9      |                  0.794118 |      0.0186667  |          -9.17924 |          3.79634 | student/results/5s_hardlabel_baseline_v2/models/student_5s_hardlabel_v2_fold4.keras | focal(alpha=0.75, gamma=2.0) |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |     0.181851  |                      9 |   0.88     |       nan        |            0.12      |
| 02rain          | False            |  75 |     0.231417  |                     14 |   0.813333 |       nan        |            0.186667  |
| 03thunderstorm  | False            |  75 |     0.026165  |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |     0.152204  |                      9 |   0.88     |       nan        |            0.12      |
| 05wind          | False            |  75 |     0.158601  |                      6 |   0.92     |       nan        |            0.08      |
| 06silence       | False            |  75 |     0.137164  |                      3 |   0.96     |       nan        |            0.04      |
| 07treefalling   | False            |  75 |     0.23269   |                     11 |   0.853333 |       nan        |            0.146667  |
| 08helicopter    | False            |  75 |     0.0600319 |                      2 |   0.973333 |       nan        |            0.0266667 |
| 09vehicleengine | False            |  75 |     0.082854  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 10axe           | False            |  75 |     0.0550915 |                      0 |   1        |       nan        |            0         |
| 11chainsaw      | False            |  75 |     0.162766  |                      8 |   0.893333 |       nan        |            0.106667  |
| 12generator     | False            |  75 |     0.101068  |                      6 |   0.92     |       nan        |            0.08      |
| 13handsaw       | False            |  75 |     0.119058  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 14firework      | False            |  75 |     0.088612  |                      4 |   0.946667 |       nan        |            0.0533333 |
| 15gunshot       | False            |  75 |     0.066912  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 16woodchop      | False            |  75 |     0.112033  |                      5 |   0.933333 |       nan        |            0.0666667 |
| 17whistling     | False            |  75 |     0.0917102 |                      4 |   0.946667 |       nan        |            0.0533333 |
| 18speaking      | False            |  75 |     0.147023  |                      6 |   0.92     |       nan        |            0.08      |
| 19footsteps     | False            |  75 |     0.238217  |                     12 |   0.84     |       nan        |            0.16      |
| 20clapping      | False            |  75 |     0.0645264 |                      1 |   0.986667 |       nan        |            0.0133333 |
| 21insect        | False            |  75 |     0.235787  |                     11 |   0.853333 |       nan        |            0.146667  |
| 22frog          | False            |  75 |     0.104494  |                      5 |   0.933333 |       nan        |            0.0666667 |
| 23birdchirping  | True             |  75 |     0.922507  |                     73 |   0.973333 |         0.973333 |          nan         |
| 24wingflapping  | True             |  75 |     0.731257  |                     62 |   0.826667 |         0.826667 |          nan         |
| 25lion          | False            |  75 |     0.100429  |                      3 |   0.96     |       nan        |            0.04      |
| 26wolfhowl      | False            |  75 |     0.0339312 |                      1 |   0.986667 |       nan        |            0.0133333 |
| 27squirrel      | False            |  75 |     0.198679  |                     10 |   0.866667 |       nan        |            0.133333  |

## Interpretation

- v2 should primarily improve bird recall, especially `24wingflapping`.
- If v2 improves recall but creates too many false positives, threshold tuning or focal parameters should be adjusted.
- If v2 still misses many wingflapping clips, the next hard-label iteration should focus on feature resolution or targeted augmentation before KD.
- KD should only be tested after this hard-label baseline is understood.

## Output Files

- `results/5s_hardlabel_baseline_v2/metrics_summary.json`
- `results/5s_hardlabel_baseline_v2/fold_metrics.csv`
- `results/5s_hardlabel_baseline_v2/per_folder_metrics.csv`
- `results/5s_hardlabel_baseline_v2/predictions_all_folds.csv`
- `results/5s_hardlabel_baseline_v2/student_5s_hardlabel_baseline_v2_report.md`
