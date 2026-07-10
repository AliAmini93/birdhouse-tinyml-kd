#include "firmware/preprocess/audio_preprocess.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <utility>

#include "firmware/preprocess/mel_filterbank.h"
#include "firmware/preprocess/preprocess_constants.h"

#if defined(ESP_PLATFORM)
#include "esp_dsp.h"
#endif

namespace birdhouse {
namespace {

constexpr float kPi = 3.14159265358979323846f;

// One complex FFT frame: Re[0], Im[0], Re[1], Im[1], ...
alignas(16) float g_fft_data[2 * kFftSize];
alignas(16) float g_power_spectrum[kFftBins];

#if defined(ESP_PLATFORM)
bool g_fft_initialized = false;
#endif

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

#if !defined(ESP_PLATFORM)

// Portable iterative radix-2 complex FFT used only by desktop regression tests.
// ESP32S3 firmware uses the optimized ESP-DSP backend below.
void PortableComplexFft(float* data, int n) {
  // In-place bit reversal.
  for (int i = 1, j = 0; i < n; ++i) {
    int bit = n >> 1;
    for (; j & bit; bit >>= 1) {
      j ^= bit;
    }
    j ^= bit;
    if (i < j) {
      std::swap(data[2 * i], data[2 * j]);
      std::swap(data[2 * i + 1], data[2 * j + 1]);
    }
  }

  for (int len = 2; len <= n; len <<= 1) {
    const float angle = -2.0f * kPi / static_cast<float>(len);
    const float wlen_r = std::cos(angle);
    const float wlen_i = std::sin(angle);

    for (int start = 0; start < n; start += len) {
      float wr = 1.0f;
      float wi = 0.0f;

      for (int j = 0; j < len / 2; ++j) {
        const int even = start + j;
        const int odd = even + len / 2;

        const float ur = data[2 * even];
        const float ui = data[2 * even + 1];
        const float oraw = data[2 * odd];
        const float oimag = data[2 * odd + 1];

        const float vr = oraw * wr - oimag * wi;
        const float vi = oraw * wi + oimag * wr;

        data[2 * even] = ur + vr;
        data[2 * even + 1] = ui + vi;
        data[2 * odd] = ur - vr;
        data[2 * odd + 1] = ui - vi;

        const float next_wr = wr * wlen_r - wi * wlen_i;
        wi = wr * wlen_i + wi * wlen_r;
        wr = next_wr;
      }
    }
  }
}

#endif  // !ESP_PLATFORM

bool RunComplexFft() {
#if defined(ESP_PLATFORM)
  if (!InitializeAudioPreprocessor()) return false;

  if (dsps_fft2r_fc32(g_fft_data, kFftSize) != ESP_OK) {
    return false;
  }
  if (dsps_bit_rev_fc32(g_fft_data, kFftSize) != ESP_OK) {
    return false;
  }
#else
  PortableComplexFft(g_fft_data, kFftSize);
#endif
  return true;
}

template <typename SampleReader>
bool PreprocessInternal(
    size_t num_samples,
    SampleReader read_sample,
    int8_t* output,
    size_t output_len) {
  if (output == nullptr) return false;
  if (output_len < static_cast<size_t>(kFeatureElements)) return false;
  if (!InitializeAudioPreprocessor()) return false;

  for (int frame = 0; frame < kExpectedFrames; ++frame) {
    const int frame_start = frame * kHopLength;

    for (int n = 0; n < kFftSize; ++n) {
      const int sample_index = frame_start + n;
      const float sample =
          (sample_index >= 0 &&
           static_cast<size_t>(sample_index) < num_samples)
              ? read_sample(static_cast<size_t>(sample_index))
              : 0.0f;

      g_fft_data[2 * n] = sample * kPaddedHannWindow[n];
      g_fft_data[2 * n + 1] = 0.0f;
    }

    if (!RunComplexFft()) return false;

    for (int bin = 0; bin < kFftBins; ++bin) {
      const float real = g_fft_data[2 * bin];
      const float imag = g_fft_data[2 * bin + 1];
      g_power_spectrum[bin] = real * real + imag * imag;
    }

    for (int mel = 0; mel < kNumMels; ++mel) {
      float mel_energy = 0.0f;
      const int mel_offset = mel * kFftBins;

      for (int bin = 0; bin < kFftBins; ++bin) {
        mel_energy +=
            kMelFilterbank[mel_offset + bin] * g_power_spectrum[bin];
      }

      mel_energy = std::max(0.0f, mel_energy);
      const float logmel = std::log(mel_energy + kLogEps);
      const float normalized =
          (logmel - kNormalizerMean) / kNormalizerStd;
      const int out_index = mel * kExpectedFrames + frame;
      output[out_index] = QuantizeNormalizedFeature(normalized);
    }
  }

  return true;
}

}  // namespace

bool InitializeAudioPreprocessor() {
#if defined(ESP_PLATFORM)
  if (g_fft_initialized) return true;

  const esp_err_t err = dsps_fft2r_init_fc32(nullptr, kFftSize);
  if (err != ESP_OK && err != ESP_ERR_DSP_REINITIALIZED) {
    return false;
  }

  g_fft_initialized = true;
#endif
  return true;
}

const char* AudioPreprocessBackendName() {
#if defined(ESP_PLATFORM)
  return "esp-dsp-radix2-fc32";
#else
  return "portable-radix2-fc32";
#endif
}

size_t AudioPreprocessScratchBytes() {
  return sizeof(g_fft_data) + sizeof(g_power_spectrum);
}

bool PreprocessInt16PcmToInt8ModelInput(
    const int16_t* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len) {
  if (pcm == nullptr) return false;

  const auto read_sample = [pcm](size_t index) -> float {
    return static_cast<float>(pcm[index]) / 32768.0f;
  };

  return PreprocessInternal(
      num_samples, read_sample, output, output_len);
}

bool PreprocessFloatPcmToInt8ModelInput(
    const float* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len) {
  if (pcm == nullptr) return false;

  const auto read_sample = [pcm](size_t index) -> float {
    return pcm[index];
  };

  return PreprocessInternal(
      num_samples, read_sample, output, output_len);
}

float DequantizeBirdProbability(int8_t output_value) {
  return (static_cast<int>(output_value) - kOutputZeroPoint) *
         kOutputScale;
}

bool IsBirdFromQuantizedOutput(int8_t output_value) {
  return DequantizeBirdProbability(output_value) >= kBirdThreshold;
}

}  // namespace birdhouse
