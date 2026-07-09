#ifndef BIRDHOUSE_PREPROCESS_CONSTANTS_H_
#define BIRDHOUSE_PREPROCESS_CONSTANTS_H_

#include <cstddef>
#include <cstdint>

namespace birdhouse {

constexpr int kSampleRate = 16000;
constexpr float kDurationSeconds = 5.0f;
constexpr int kTargetSamples = 80000;

constexpr int kNumMels = 40;
constexpr float kFrameMs = 25.0f;
constexpr float kHopMs = 20.0f;

constexpr int kFftSize = 512;
constexpr int kWinLength = 400;
constexpr int kHopLength = 320;
constexpr int kExpectedFrames = 249;
constexpr int kFftBins = (kFftSize / 2) + 1;

constexpr float kFMinHz = 50.0f;
constexpr float kFMaxHz = 8000.0f;
constexpr float kLogEps = 1.0e-6f;

constexpr int kFeatureElements = kNumMels * kExpectedFrames;

constexpr float kNormalizerMean = -9.193479537963867f;
constexpr float kNormalizerStd = 3.789201021194458f;

constexpr float kInputScale = 0.0200184378772974f;
constexpr int kInputZeroPoint = -67;

constexpr float kOutputScale = 0.00390625f;
constexpr int kOutputZeroPoint = -128;

constexpr float kBirdThreshold = 0.673462986946106f;

}  // namespace birdhouse

#endif  // BIRDHOUSE_PREPROCESS_CONSTANTS_H_

