# KD Weight Sweep Summary

Ranking is sorted primarily by `recall_at_fpr_target`, then PR-AUC.

| label                  | run_name                 |   hard_weight |   kd_weight |   precision_0p5 |   recall_0p5 |   f1_0p5 |   pr_auc |   roc_auc |   recall_at_fpr_target |   fpr_at_target |   23birdchirping_recall |   24wingflapping_recall |   02rain_fp_rate |   07treefalling_fp_rate |   21insect_fp_rate |   27squirrel_fp_rate |
|:-----------------------|:-------------------------|--------------:|------------:|----------------:|-------------:|---------:|---------:|----------:|-----------------------:|----------------:|------------------------:|------------------------:|-----------------:|------------------------:|-------------------:|---------------------:|
| 5s_kd_binary_hw08_kw02 | 5s_kd_binary_hw08_kw02   |           0.8 |         0.2 |        0.727521 |     0.873333 | 0.779826 | 0.905131 |  0.985902 |               0.86     |       0.0154667 |                0.946667 |                0.8      |        0.0933333 |               0.0266667 |          0.0666667 |            0.0266667 |
| KD v1 0.5/0.5          | 5s_kd_binary_v1          |           0.5 |         0.5 |        0.79508  |     0.833333 | 0.810257 | 0.890517 |  0.981244 |               0.853333 |       0.0154667 |                0.906667 |                0.76     |        0.12      |               0.04      |          0.0666667 |            0.0133333 |
| 5s_kd_binary_hw07_kw03 | 5s_kd_binary_hw07_kw03   |           0.7 |         0.3 |        0.783018 |     0.84     | 0.805629 | 0.886205 |  0.979644 |               0.84     |       0.0138667 |                0.906667 |                0.773333 |        0.106667  |               0.0133333 |          0.08      |            0.0133333 |
| 5s_kd_binary_hw03_kw07 | 5s_kd_binary_hw03_kw07   |           0.3 |         0.7 |        0.755947 |     0.806667 | 0.770722 | 0.881938 |  0.97808  |               0.833333 |       0.0154667 |                0.893333 |                0.72     |        0.0933333 |               0.04      |          0.08      |            0.0266667 |
| hard-label v2          | 5s_hardlabel_baseline_v2 |         nan   |       nan   |        0.536238 |     0.9      | 0.657692 | 0.865938 |  0.973298 |               0.786667 |       0.0128    |                0.973333 |                0.826667 |        0.186667  |               0.146667  |          0.146667  |            0.133333  |

## Decision rule

Prefer the model with the best `recall_at_fpr_target` and PR-AUC without unacceptable false positives on rain, treefalling, insect, and squirrel.

Generated files:

- `student/results/kd_weight_sweep_summary.csv`
- `student/results/kd_weight_sweep_summary.md`
