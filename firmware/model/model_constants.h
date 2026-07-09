#ifndef BIRDHOUSE_MODEL_CONSTANTS_H_
#define BIRDHOUSE_MODEL_CONSTANTS_H_

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

constexpr const char* kStudentModelName = "student_5s_kd_hw08_kw02_int8";
constexpr int kStudentModelVersion = 1;

constexpr int kModelInputBatch = 1;
constexpr int kModelInputMels = 40;
constexpr int kModelInputFrames = 249;
constexpr int kModelInputChannels = 1;
constexpr int kModelInputElements = kModelInputMels * kModelInputFrames * kModelInputChannels;

constexpr int kModelOutputElements = 1;

constexpr float kModelInputScale = 0.0200184378772974f;
constexpr int kModelInputZeroPoint = -67;

constexpr float kModelOutputScale = 0.00390625f;
constexpr int kModelOutputZeroPoint = -128;

constexpr float kModelBirdThreshold = 0.673462986946106f;

// Starting value only. Measure/tune on the actual TFLite Micro ESP32S3 build.
constexpr int kTensorArenaSizeBytes = 160 * 1024;

}  // namespace birdhouse

#endif  // BIRDHOUSE_MODEL_CONSTANTS_H_
