# 11 - Final Student Training and TFLite Export Plan

This stage converts the selected cross-validation configuration into a deployment candidate.

## Selected configuration

```text
selected_cv_run = 5s_kd_binary_hw08_kw02
hard_weight = 0.8
kd_weight = 0.2
input = 5 s / 16 kHz / 40-bin log-mel
model = compact DS-CNN v2
```

## Why final training is needed

The models saved during cross-validation are fold-specific models. They should not be used as the final deployment model. The final model must be trained once on the full dataset using the selected configuration.

## Steps

```text
1. Train final Student on all FSC22 clips
2. Save Keras model and weights
3. Save the full-dataset log-mel normalizer
4. Export FP32 TFLite
5. Export full-integer INT8 TFLite
6. Compare TFLite outputs against Keras on a validation subset
```

## Output directory

```text
student/final_models/5s_kd_hw08_kw02/
```

## Deployment constants

```text
sample_rate = 16000
duration = 5 s
n_mels = 40
frame length = 25 ms
hop = 20 ms
feature shape = 40 x 249 x 1
normalization = saved mean/std from normalizer.json
threshold = recommended threshold from CV/export summary
```

The final full-dataset training metrics are apparent training-set metrics. The model-selection evidence remains the cross-validation sweep results.
