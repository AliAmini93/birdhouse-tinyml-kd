# Final Student TFLite Export Report

## Model files

- FP32 TFLite: `student/final_models/5s_kd_hw08_kw02/student_final_fp32.tflite`
- INT8 TFLite: `student/final_models/5s_kd_hw08_kw02/student_final_int8.tflite`

## Size

- FP32 size bytes: 132128
- INT8 size bytes: 59760

## INT8 quantization

- Input dtype: `<class 'numpy.int8'>`
- Input quantization: `(0.0200184378772974, -67)`
- Output dtype: `<class 'numpy.int8'>`
- Output quantization: `(0.00390625, -128)`

## Validation against Keras

- FP32 mean abs diff: 1.0597911881404798e-08
- FP32 max abs diff: 5.066394805908203e-07
- INT8 mean abs diff: 0.0011150884674862027
- INT8 max abs diff: 0.034066736698150635

## Deployment constants

```text
sample_rate = 16000
duration_s = 5.0
n_mels = 40
frame_ms = 25.0
hop_ms = 20.0
expected_frames = 249
normalizer_mean = -9.193479537963867
normalizer_std = 3.789201021194458
recommended_threshold = 0.673462986946106
```
