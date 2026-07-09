# Final Student 5 s KD Training Report

This model is trained on the full FSC22 dataset using the selected KD sweep configuration.

## Selected configuration

```text
final_name = 5s_kd_hw08_kw02
selected_cv_run = 5s_kd_binary_hw08_kw02
hard_weight = 0.8
kd_weight = 0.2
epochs = 46
batch_size = 32
input = 5 s / 16 kHz / 40-bin log-mel / shape 40 x 249 x 1
```

## Full-dataset apparent metrics

These metrics are measured on the full training set. The model-selection evidence remains the CV sweep.

### Threshold 0.5

- threshold: 0.5
- accuracy: 0.9955555555555555
- precision: 0.9548387096774194
- recall: 0.9866666666666667
- f1: 0.9704918032786886
- tn: 1868
- fp: 7
- fn: 2
- tp: 148
- fpr: 0.0037333333333333333

### Recommended CV threshold

- recommended_threshold: 0.673462986946106
- threshold: 0.673462986946106
- accuracy: 0.9950617283950617
- precision: 0.9861111111111112
- recall: 0.9466666666666667
- f1: 0.9659863945578231
- tn: 1873
- fp: 2
- fn: 8
- tp: 142
- fpr: 0.0010666666666666667

## Selected CV reference

- precision_0p5_mean: 0.7275214834916327
- recall_0p5_mean: 0.8733333333333333
- f1_0p5_mean: 0.7798264367270021
- pr_auc_mean: 0.9051309127292857
- roc_auc_mean: 0.9859022222222222
- recall_at_fpr_target_mean: 0.8600000000000001

## Saved files

- `student_final.keras`
- `student_final.weights.h5`
- `normalizer.json`
- `final_training_summary.json`
- `final_training_report.md`
