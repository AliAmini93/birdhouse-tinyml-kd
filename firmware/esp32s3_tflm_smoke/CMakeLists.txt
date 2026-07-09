cmake_minimum_required(VERSION 3.16)

# Minimal ESP32S3 smoke-test project for the final bird/non-bird INT8 model.
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(birdhouse_tflm_smoke)
