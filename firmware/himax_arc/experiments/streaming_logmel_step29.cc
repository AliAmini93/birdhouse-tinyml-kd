#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <utility>

#include "firmware/preprocess/audio_preprocess.h"
#include "firmware/preprocess/mel_filterbank.h"

namespace birdhouse {

class StreamingLogMel {
 public:
  void Reset() {
    received_ = 0;
    frames_ = 0;
  }

  int FrameCount() const { return frames_; }

  bool Push(int16_t sample, int8_t* output, size_t len) {
    if (!output || len < kFeatureElements ||
        received_ >= kTargetSamples) return false;

    ring_[received_ % kFftSize] = sample;
    ++received_;

    if (frames_ >= kExpectedFrames) return false;

    const uint32_t start = frames_ * kHopLength;

    if (received_ != start + kFftSize) return false;

    for (int n = 0; n < kFftSize; ++n) {
      const int16_t pcm = ring_[(start + n) % kFftSize];
      const float normalized_pcm =
          static_cast<float>(pcm) / 32768.0f;

      fft_[2 * n] =
          normalized_pcm * kPaddedHannWindow[n];
      fft_[2 * n + 1] = 0.0f;
    }

    ComputeFft();

    for (int bin = 0; bin < kFftBins; ++bin) {
      const float re = fft_[2 * bin];
      const float im = fft_[2 * bin + 1];
      power_[bin] = re * re + im * im;
    }

    for (int mel = 0; mel < kNumMels; ++mel) {
      float energy = 0.0f;
      const int offset = mel * kFftBins;

      for (int bin = 0; bin < kFftBins; ++bin) {
        energy +=
            kMelFilterbank[offset + bin] * power_[bin];
      }

      energy = std::max(0.0f, energy);

      const float logmel = std::log(energy + kLogEps);
      const float normalized =
          (logmel - kNormalizerMean) / kNormalizerStd;

      const float q =
          std::round(normalized / kInputScale) +
          static_cast<float>(kInputZeroPoint);

      int value = static_cast<int>(q);
      if (value < -128) value = -128;
      if (value > 127) value = 127;

      output[mel * kExpectedFrames + frames_] =
          static_cast<int8_t>(value);
    }

    ++frames_;
    return true;
  }

 private:
  void ComputeFft() {
    constexpr float kPi = 3.14159265358979323846f;

    for (int i = 1, j = 0; i < kFftSize; ++i) {
      int bit = kFftSize >> 1;

      for (; j & bit; bit >>= 1) {
        j ^= bit;
      }

      j ^= bit;

      if (i < j) {
        std::swap(fft_[2 * i], fft_[2 * j]);
        std::swap(fft_[2 * i + 1], fft_[2 * j + 1]);
      }
    }

    for (int length = 2; length <= kFftSize;
         length <<= 1) {

      const float angle =
          -2.0f * kPi / static_cast<float>(length);

      const float wlen_r = std::cos(angle);
      const float wlen_i = std::sin(angle);

      for (int start = 0; start < kFftSize;
           start += length) {

        float wr = 1.0f;
        float wi = 0.0f;

        for (int j = 0; j < length / 2; ++j) {
          const int even = start + j;
          const int odd = even + length / 2;

          const float ur = fft_[2 * even];
          const float ui = fft_[2 * even + 1];
          const float oraw = fft_[2 * odd];
          const float oimag = fft_[2 * odd + 1];

          const float vr = oraw * wr - oimag * wi;
          const float vi = oraw * wi + oimag * wr;

          fft_[2 * even] = ur + vr;
          fft_[2 * even + 1] = ui + vi;
          fft_[2 * odd] = ur - vr;
          fft_[2 * odd + 1] = ui - vi;

          const float next_wr = wr * wlen_r - wi * wlen_i;
          wi = wr * wlen_i + wi * wlen_r;
          wr = next_wr;
        }
      }
    }
  }

  int16_t ring_[kFftSize] = {};
  float fft_[2 * kFftSize] = {};
  float power_[kFftBins] = {};
  uint32_t received_ = 0;
  int frames_ = 0;
};

}  // namespace birdhouse

#ifdef BIRDHOUSE_HOST_TEST

#include <iostream>
#include <vector>

int main() {
  using namespace birdhouse;

  static StreamingLogMel stream;

  std::vector<int16_t> pcm(kTargetSamples);
  std::vector<int8_t> reference(kFeatureElements);
  std::vector<int8_t> output(kFeatureElements);

  for (int test = 0; test < 3; ++test) {
    uint32_t rng = 0x12345678u;

    for (int i = 0; i < kTargetSamples; ++i) {
      if (test == 0) {
        pcm[i] = 0;
      } else if (test == 1) {
        rng = rng * 1664525u + 1013904223u;
        pcm[i] = static_cast<int16_t>(rng >> 16);
      } else {
        pcm[i] = (i % 200 == 0) ? 22000 :
                 (i % 200 == 100) ? -22000 : 0;
      }
    }

    if (!PreprocessInt16PcmToInt8ModelInput(
            pcm.data(), pcm.size(),
            reference.data(), reference.size())) {
      std::cout << "FAIL: reference preprocess\n";
      return 1;
    }

    stream.Reset();

    for (int i = 0; i < kTargetSamples; ++i) {
      stream.Push(pcm[i], output.data(), output.size());
    }

    int mismatches = 0;
    int max_difference = 0;

    for (int i = 0; i < kFeatureElements; ++i) {
      const int difference = std::abs(
          static_cast<int>(reference[i]) -
          static_cast<int>(output[i]));

      if (difference != 0) ++mismatches;
      if (difference > max_difference)
        max_difference = difference;
    }

    std::cout << "Test " << test
              << " frames=" << stream.FrameCount()
              << " mismatches=" << mismatches
              << " max_difference=" << max_difference
              << "\n";

    if (stream.FrameCount() != kExpectedFrames ||
        mismatches != 0) {
      std::cout << "FAIL: streaming parity\n";
      return 1;
    }
  }

  std::cout << "PASS: exact INT8 streaming parity\n";
  std::cout << "Streaming workspace bytes: "
            << sizeof(stream) << "\n";

  return 0;
}

#endif
