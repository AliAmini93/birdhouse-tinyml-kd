# 18 - ESP32S3 Preprocessing-to-Inference Integration Test

This document records the firmware integration test that connects the embedded preprocessing reference path to the final INT8 TFLite Micro bird/non-bird model.

## Goal

The earlier ESP32S3 smoke test verified:

```text
reference_input_int8
-> BirdModel
-> TFLite Micro Invoke
-> reference output comparison
```

This test verifies the longer path:

```text
reference PCM float32
-> C++ preprocessing
-> generated int8 input tensor
-> BirdModel
-> TFLite Micro Invoke
-> reference output comparison
```

The board runtime test is still postponed until the ESP32S3 board is available, but this project can be built without the board.

## Files

```text
firmware/esp32s3_preprocess_inference/CMakeLists.txt
firmware/esp32s3_preprocess_inference/main/CMakeLists.txt
firmware/esp32s3_preprocess_inference/main/idf_component.yml
firmware/esp32s3_preprocess_inference/main/main.cc
firmware/esp32s3_preprocess_inference/sdkconfig.defaults

tools/build_esp32s3_preprocess_inference.sh
tools/flash_esp32s3_preprocess_inference.sh
```

The reference export tool now also creates:

```text
firmware/preprocess/testdata/reference_pcm_float32.h
```

## Build

```bash
. ~/esp/esp-idf/export.sh

cd /media/armin/External/AhmadWorks/audioclassification
bash tools/build_esp32s3_preprocess_inference.sh
```

## Flash later

```bash
PORT=/dev/ttyACM0 bash tools/flash_esp32s3_preprocess_inference.sh
```

## Expected serial output

```text
INPUT PARITY PASS
PREPROCESSING-INFERENCE TEST PASS
```

The expected reference model output remains:

```text
output_int8 = 116
p_bird = 0.953125
is_bird = true
```

## Important limitation

This test still uses the naive C++ DFT in `audio_preprocess.cc`. It is suitable for functional verification but not optimized for final ESP32S3 runtime latency.

The final production path should replace the DFT with an optimized FFT backend while preserving the same numerical contract.
