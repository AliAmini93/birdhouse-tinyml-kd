# Student 5 s Hard-Label Baseline Report

Hard-label baseline only. No Teacher/KD loss used in training.

## Configuration

```text
sample_rate = 16000
duration_s = 5.0
feature = log-mel
n_mels = 40
frame_ms = 25.0
hop_ms = 20.0
n_fft = 512
batch_size = 32
epochs = 80
patience = 12
folds = 5
model = compact DS-CNN
loss = weighted binary crossentropy
```

## Summary

- Total clips: 2025
- Bird clips: 150
- Non-bird clips: 1875
- Parameter count: 10313

## Cross-Validation Metrics

- accuracy_0p5: 0.9462 ± 0.0093
- precision_0p5: 0.6388 ± 0.0818
- recall_0p5: 0.6933 ± 0.0879
- f1_0p5: 0.6560 ± 0.0415
- roc_auc: 0.9416 ± 0.0160
- pr_auc: 0.7042 ± 0.0500
- recall_at_fpr_target: 0.6200 ± 0.0933
- fpr_at_target: 0.0149 ± 0.0021

## Fold Metrics

|   fold |   n_train |   n_val |   train_pos |   train_neg |   val_pos |   val_neg |   pos_weight |   epochs_ran |   best_val_pr_auc |   accuracy_0p5 |   precision_0p5 |   recall_0p5 |   f1_0p5 |   tp_0p5 |   fn_0p5 |   fp_0p5 |   tn_0p5 |   roc_auc |   pr_auc |   target_fpr |   threshold_at_fpr_target |   recall_at_fpr_target |   precision_at_fpr_target |   fpr_at_target |   normalizer_mean |   normalizer_std | model_path                                                                    |
|-------:|----------:|--------:|------------:|------------:|----------:|----------:|-------------:|-------------:|------------------:|---------------:|----------------:|-------------:|---------:|---------:|---------:|---------:|---------:|----------:|---------:|-------------:|--------------------------:|-----------------------:|--------------------------:|----------------:|------------------:|-----------------:|:------------------------------------------------------------------------------|
|      0 |      1620 |     405 |         120 |        1500 |        30 |       375 |         12.5 |           41 |          0.680212 |       0.953086 |        0.677419 |     0.7      | 0.688525 |       21 |        9 |       10 |      365 |  0.949511 | 0.67605  |         0.02 |                  0.655893 |               0.6      |                  0.72     |       0.0186667 |          -9.19522 |          3.80212 | student/results/5s_hardlabel_baseline/models/student_5s_hardlabel_fold0.keras |
|      1 |      1620 |     405 |         120 |        1500 |        30 |       375 |         12.5 |           52 |          0.749396 |       0.950617 |        0.631579 |     0.8      | 0.705882 |       24 |        6 |       14 |      361 |  0.9288   | 0.737501 |         0.02 |                  0.646883 |               0.8      |                  0.827586 |       0.0133333 |          -9.19322 |          3.78795 | student/results/5s_hardlabel_baseline/models/student_5s_hardlabel_fold1.keras |
|      2 |      1620 |     405 |         120 |        1500 |        30 |       375 |         12.5 |           26 |          0.685929 |       0.953086 |        0.761905 |     0.533333 | 0.627451 |       16 |       14 |        5 |      370 |  0.920356 | 0.689344 |         0.02 |                  0.486774 |               0.566667 |                  0.772727 |       0.0133333 |          -9.21344 |          3.77845 | student/results/5s_hardlabel_baseline/models/student_5s_hardlabel_fold2.keras |
|      3 |      1620 |     405 |         120 |        1500 |        30 |       375 |         12.5 |           45 |          0.775031 |       0.945679 |        0.611111 |     0.733333 | 0.666667 |       22 |        8 |       14 |      361 |  0.966133 | 0.780825 |         0.02 |                  0.712125 |               0.6      |                  0.782609 |       0.0133333 |          -9.18553 |          3.79687 | student/results/5s_hardlabel_baseline/models/student_5s_hardlabel_fold3.keras |
|      4 |      1620 |     405 |         120 |        1500 |        30 |       375 |         12.5 |           43 |          0.628604 |       0.928395 |        0.512195 |     0.7      | 0.591549 |       21 |        9 |       20 |      355 |  0.943289 | 0.637217 |         0.02 |                  0.889123 |               0.533333 |                  0.727273 |       0.016     |          -9.18004 |          3.78048 | student/results/5s_hardlabel_baseline/models/student_5s_hardlabel_fold4.keras |

## Per-Folder Metrics @ Threshold 0.5

| source_folder   | is_bird_folder   |   n |   mean_p_bird |   positive_predictions |   accuracy |   recall_if_bird |   fp_rate_if_nonbird |
|:----------------|:-----------------|----:|--------------:|-----------------------:|-----------:|-----------------:|---------------------:|
| 01fire          | False            |  75 |    0.0608046  |                      3 |   0.96     |       nan        |            0.04      |
| 02rain          | False            |  75 |    0.111069   |                      7 |   0.906667 |       nan        |            0.0933333 |
| 03thunderstorm  | False            |  75 |    0.00949769 |                      0 |   1        |       nan        |            0         |
| 04waterdrops    | False            |  75 |    0.0527099  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 05wind          | False            |  75 |    0.0693439  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 06silence       | False            |  75 |    0.110231   |                      5 |   0.933333 |       nan        |            0.0666667 |
| 07treefalling   | False            |  75 |    0.0419583  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 08helicopter    | False            |  75 |    0.0526097  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 09vehicleengine | False            |  75 |    0.0236482  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 10axe           | False            |  75 |    0.0298707  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 11chainsaw      | False            |  75 |    0.0436244  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 12generator     | False            |  75 |    0.0367372  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 13handsaw       | False            |  75 |    0.0450231  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 14firework      | False            |  75 |    0.0536641  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 15gunshot       | False            |  75 |    0.0196901  |                      0 |   1        |       nan        |            0         |
| 16woodchop      | False            |  75 |    0.0495442  |                      3 |   0.96     |       nan        |            0.04      |
| 17whistling     | False            |  75 |    0.0301868  |                      2 |   0.973333 |       nan        |            0.0266667 |
| 18speaking      | False            |  75 |    0.0480235  |                      1 |   0.986667 |       nan        |            0.0133333 |
| 19footsteps     | False            |  75 |    0.164807   |                      9 |   0.88     |       nan        |            0.12      |
| 20clapping      | False            |  75 |    0.0329754  |                      3 |   0.96     |       nan        |            0.04      |
| 21insect        | False            |  75 |    0.0979304  |                      6 |   0.92     |       nan        |            0.08      |
| 22frog          | False            |  75 |    0.0424593  |                      3 |   0.96     |       nan        |            0.04      |
| 23birdchirping  | True             |  75 |    0.794684   |                     60 |   0.8      |         0.8      |          nan         |
| 24wingflapping  | True             |  75 |    0.520131   |                     44 |   0.586667 |         0.586667 |          nan         |
| 25lion          | False            |  75 |    0.0204914  |                      0 |   1        |       nan        |            0         |
| 26wolfhowl      | False            |  75 |    0.00177125 |                      0 |   1        |       nan        |            0         |
| 27squirrel      | False            |  75 |    0.0691146  |                      5 |   0.933333 |       nan        |            0.0666667 |

## Output Files

- `results/5s_hardlabel_baseline/metrics_summary.json`
- `results/5s_hardlabel_baseline/fold_metrics.csv`
- `results/5s_hardlabel_baseline/per_folder_metrics.csv`
- `results/5s_hardlabel_baseline/predictions_all_folds.csv`
- `results/5s_hardlabel_baseline/student_5s_hardlabel_baseline_report.md`

## Interpretation Notes

- This is the mandatory hard-label baseline. KD is only useful if it beats this baseline.
- Metrics should be judged primarily by bird recall at low non-bird false-positive rate, PR-AUC, and per-class false positives.
- If 5 s accuracy is good, the next step is KD comparison. If 5 s is too expensive on-device, then test a 2 s fallback.
