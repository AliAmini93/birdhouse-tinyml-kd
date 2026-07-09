#include "firmware/preprocess/audio_preprocess.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>

#include "firmware/preprocess/mel_filterbank.h"
#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {
namespace {

constexpr float kPi = 3.14159265358979323846f;

inline float ClampFloat(float x, float lo, float hi) {
  return std::max(lo, std::min(hi, x));
}

inline int8_t ClampInt8(int x) {
  if (x < -128) return static_cast<int8_t>(-128);
  if (x > 127) return static_cast<int8_t>(127);
  return static_cast<int8_t>(x);
}

inline int8_t QuantizeNormalizedFeature(float normalized_value) {
  const float q = std::round(normalized_value / kInputScale) +
                  static_cast<float>(kInputZeroPoint);
  return ClampInt8(static_cast<int>(q));
}

void ComputePowerSpectrumNaiveDft(
    const float* pcm,
    size_t num_samples,
    int frame_index,
    float* power_spectrum) {
  const int frame_start = frame_index * kHopLength;

  for (int k = 0; k < kFftBins; ++k) {
    float real = 0.0f;
    float imag = 0.0f;

    for (int n = 0; n < kFftSize; ++n) {
      const int sample_index = frame_start + n;
      const float sample =
          (sample_index >= 0 && static_cast<size_t>(sample_index) < num_samples)
              ? pcm[sample_index]
              : 0.0f;

      const float windowed = sample * kPaddedHannWindow[n];
      const float angle = -2.0f * kPi * static_cast<float>(k) *
                          static_cast<float>(n) / static_cast<float>(kFftSize);

      real += windowed * std::cos(angle);
      imag += windowed * std::sin(angle);
    }

    power_spectrum[k] = real * real + imag * imag;
  }
}

bool PreprocessFloatInternal(
    const float* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len) {
  if (pcm == nullptr || output == nullptr) return false;
  if (output_len < static_cast<size_t>(kFeatureElements)) return false;

  float power_spectrum[kFftBins];

  for (int frame = 0; frame < kExpectedFrames; ++frame) {
    ComputePowerSpectrumNaiveDft(pcm, num_samples, frame, power_spectrum);

    for (int mel = 0; mel < kNumMels; ++mel) {
      float mel_energy = 0.0f;
      const int mel_offset = mel * kFftBins;

      for (int bin = 0; bin < kFftBins; ++bin) {
        mel_energy += kMelFilterbank[mel_offset + bin] * power_spectrum[bin];
      }

      mel_energy = std::max(0.0f, mel_energy);
      const float logmel = std::log(mel_energy + kLogEps);
      const float normalized = (logmel - kNormalizerMean) / kNormalizerStd;
      const int out_index = mel * kExpectedFrames + frame;
      output[out_index] = QuantizeNormalizedFeature(normalized);
    }
  }

  return true;
}

}  // namespace

bool PreprocessInt16PcmToInt8ModelInput(
    const int16_t* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len) {
  if (pcm == nullptr) return false;

  static float pcm_float[kTargetSamples];

  const size_t copy_n = std::min(num_samples, static_cast<size_t>(kTargetSamples));
  for (size_t i = 0; i < copy_n; ++i) {
    pcm_float[i] = ClampFloat(static_cast<float>(pcm[i]) / 32768.0f, -1.0f, 1.0f);
  }
  for (size_t i = copy_n; i < static_cast<size_t>(kTargetSamples); ++i) {
    pcm_float[i] = 0.0f;
  }

  return PreprocessFloatInternal(
      pcm_float,
      static_cast<size_t>(kTargetSamples),
      output,
      output_len);
}

bool PreprocessFloatPcmToInt8ModelInput(
    const float* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len) {
  return PreprocessFloatInternal(pcm, num_samples, output, output_len);
}

float DequantizeBirdProbability(int8_t output_value) {
  return (static_cast<int>(output_value) - kOutputZeroPoint) * kOutputScale;
}

bool IsBirdFromQuantizedOutput(int8_t output_value) {
  return DequantizeBirdProbability(output_value) >= kBirdThreshold;
}

}  // namespace birdhouse

