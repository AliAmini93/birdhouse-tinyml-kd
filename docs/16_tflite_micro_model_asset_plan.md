# 16 - TFLite Micro Model Asset Plan

This document records the first firmware-facing model asset export for the final INT8 Student model.

## Goal

Prepare the final INT8 TFLite model for TFLite Micro integration.

The deployment path is:

```text
audio
-> embedded preprocessing
-> int8 input tensor 40 x 249 x 1
-> TFLite Micro Invoke
-> int8 output
-> dequantize p_bird
-> threshold
```

## Files

```text
tools/export_tflite_micro_model.py
tools/run_export_tflite_micro_asset.sh

firmware/model/student_final_int8_model_data.h
firmware/model/student_final_int8_model_data.cc
firmware/model/model_constants.h
firmware/model/model_asset_summary.json

firmware/inference/bird_model.h
firmware/inference/bird_model.cc
firmware/inference/reference_inference_example.cc
firmware/inference/testdata/reference_model_output.h
```

## Generate assets

```bash
bash tools/run_export_tflite_micro_asset.sh
```

This will:

```text
1. regenerate the Python preprocessing reference input
2. convert student_final_int8.tflite to a C array
3. write firmware/model/model_constants.h
4. run reference inference in Python TFLite
5. write firmware/inference/testdata/reference_model_output.h
6. write firmware/model/model_asset_summary.json
```

## Important limitation

`bird_model.cc` is a TFLite Micro integration wrapper. It requires TensorFlow Lite Micro headers and libraries in the real firmware build.

It is not expected to compile with plain `g++` unless TFLite Micro is available.

## Tensor arena

`kTensorArenaSizeBytes = 160 * 1024` is only a starting value. It must be measured and tuned on the actual ESP32S3 firmware build.

## Next step

After this asset export, the next task is a minimal TFLite Micro build that:

```text
1. creates tensor arena
2. initializes BirdModel
3. copies reference_input_int8 into the input tensor
4. invokes the model
5. compares output to reference_model_output.h
```

Only after that should the reference input be replaced by live preprocessing output.
