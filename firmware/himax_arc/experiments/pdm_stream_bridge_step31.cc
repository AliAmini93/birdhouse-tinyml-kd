#include <cstddef>
#include <cstdint>

#include "streaming_logmel_step29.cc"

namespace birdhouse {

constexpr size_t kStereoFramesPerBlock = 1024;
constexpr size_t kStartupFramesToDrop = 2048;

class PdmStereoBridge {
 public:
  void Reset() {
    stream_.Reset();
    seen_ = 0;
    accepted_ = 0;
  }

  void FeedBlock(const int16_t* stereo,
                 size_t frames,
                 int8_t* features) {
    if (!stereo || !features) return;

    for (size_t i = 0; i < frames; ++i) {
      if (seen_ < kStartupFramesToDrop) {
        ++seen_;
        continue;
      }

      ++seen_;

      if (accepted_ >= kTargetSamples) continue;

      // Select first of two interleaved channels.
      stream_.Push(stereo[2 * i], features,
                   kFeatureElements);
      ++accepted_;
    }
  }

  size_t Accepted() const { return accepted_; }
  int Frames() const { return stream_.FrameCount(); }

 private:
  StreamingLogMel stream_;
  size_t seen_ = 0;
  size_t accepted_ = 0;
};

static PdmStereoBridge bridge;

}  // namespace birdhouse

extern "C" void birdhouse_pdm_reset() {
  birdhouse::bridge.Reset();
}

extern "C" void birdhouse_pdm_feed(
    const int16_t* samples,
    size_t frames,
    int8_t* features) {
  birdhouse::bridge.FeedBlock(samples, frames, features);
}

extern "C" size_t birdhouse_pdm_accepted() {
  return birdhouse::bridge.Accepted();
}

extern "C" int birdhouse_pdm_frames() {
  return birdhouse::bridge.Frames();
}

#ifdef BIRDHOUSE_PDM_HOST_TEST

#include <cstdlib>
#include <iostream>
#include <vector>

static int16_t GeneratePcm(size_t index) {
  const int v = static_cast<int>(
      (index * 37u) % 30001u);
  return static_cast<int16_t>(v - 15000);
}

int main() {
  using namespace birdhouse;

  std::vector<int16_t> pcm(kTargetSamples);
  std::vector<int8_t> reference(kFeatureElements);
  std::vector<int8_t> features(kFeatureElements);

  for (size_t i = 0; i < pcm.size(); ++i) {
    pcm[i] = GeneratePcm(i);
  }

  if (!PreprocessInt16PcmToInt8ModelInput(
          pcm.data(), pcm.size(),
          reference.data(), reference.size())) {
    std::cout << "FAIL: reference preprocess\n";
    return 1;
  }

  bridge.Reset();

  int16_t block[2 * kStereoFramesPerBlock];

  // Simulate 81 DMA blocks, each containing
  // 1024 interleaved stereo frames.
  for (size_t b = 0; b < 81; ++b) {
    for (size_t i = 0;
         i < kStereoFramesPerBlock; ++i) {
      const size_t global =
          b * kStereoFramesPerBlock + i;

      const int16_t left =
          global < kStartupFramesToDrop
              ? 777
              : GeneratePcm(
                    global - kStartupFramesToDrop);

      block[2 * i] = left;
      block[2 * i + 1] = -1234;
    }

    bridge.FeedBlock(
        block, kStereoFramesPerBlock,
        features.data());
  }

  size_t mismatches = 0;

  for (size_t i = 0; i < features.size(); ++i) {
    if (features[i] != reference[i]) {
      ++mismatches;
    }
  }

  std::cout << "DMA blocks: 81\n";
  std::cout << "Startup dropped samples: "
            << kStartupFramesToDrop << "\n";
  std::cout << "Accepted PCM samples: "
            << bridge.Accepted() << "\n";
  std::cout << "Generated Mel frames: "
            << bridge.Frames() << "\n";
  std::cout << "INT8 mismatches: "
            << mismatches << "\n";
  std::cout << "Bridge workspace bytes: "
            << sizeof(bridge) << "\n";

  if (bridge.Accepted() != kTargetSamples ||
      bridge.Frames() != kExpectedFrames ||
      mismatches != 0) {
    std::cout << "FAIL: PDM streaming bridge\n";
    return 1;
  }

  std::cout << "PASS: PDM streaming bridge\n";
  return 0;
}

#endif
