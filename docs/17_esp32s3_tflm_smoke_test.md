# 17 - ESP32S3 TFLite Micro Smoke Test

This document records the first ESP32S3 firmware smoke-test skeleton for the final INT8 bird/non-bird Student model.

## Goal

Validate the firmware-facing inference path without microphone input and without live preprocessing:

```text
reference_input_int8.h
-> BirdModel
-> TFLite Micro Invoke
-> reference_model_output.h comparison
```

This isolates the TFLite Micro model loading/inference path from the audio front-end.

## Files

```text
firmware/esp32s3_tflm_smoke/CMakeLists.txt
firmware/esp32s3_tflm_smoke/main/CMakeLists.txt
firmware/esp32s3_tflm_smoke/main/idf_component.yml
firmware/esp32s3_tflm_smoke/main/main.cc
firmware/esp32s3_tflm_smoke/sdkconfig.defaults

tools/build_esp32s3_tflm_smoke.sh
tools/flash_esp32s3_tflm_smoke.sh
```

The smoke-test firmware uses already generated assets:

```text
firmware/model/student_final_int8_model_data.cc
firmware/model/model_constants.h
firmware/preprocess/testdata/reference_input_int8.h
firmware/inference/testdata/reference_model_output.h
firmware/inference/bird_model.cc
```

## Expected model output

From the Python TFLite reference run:

```text
output_int8 = 116
p_bird = 0.953125
threshold = 0.673462986946106
is_bird = true
```

The ESP32S3 smoke test prints `SMOKE TEST PASS` if the quantized output is within 1 unit of the reference and the bird/non-bird decision matches.

## Dependency

The ESP-IDF project uses the ESP-IDF component manager dependency:

```yaml
dependencies:
  espressif/esp-tflite-micro: "*"
```

If the component API changes, the only file likely to need adjustment is:

```text
firmware/inference/bird_model.cc
```

Specifically the TFLite Micro operator resolver calls.

## Build

First source ESP-IDF in your shell. Example:

```bash
. ~/esp/esp-idf/export.sh
```

Then:

```bash
cd /media/armin/External/AhmadWorks/audioclassification
bash tools/build_esp32s3_tflm_smoke.sh
```

## Flash and monitor

Set the serial port if needed:

```bash
PORT=/dev/ttyACM0 bash tools/flash_esp32s3_tflm_smoke.sh
```

or:

```bash
PORT=/dev/ttyUSB0 bash tools/flash_esp32s3_tflm_smoke.sh
```

## Pass condition

Look for:

```text
SMOKE TEST PASS
```

## If build fails

Most likely causes:

```text
ESP-IDF environment not sourced
component manager cannot fetch esp-tflite-micro
TFLite Micro API mismatch
operator resolver API mismatch
tensor arena too small
```

## Next step after PASS

After the reference-input smoke test passes, connect the validated embedded preprocessing path:

```text
reference PCM
-> C++ preprocessing
-> model input tensor
-> BirdModel Invoke
-> compare with reference output
```

Then move to live I2S microphone capture.
