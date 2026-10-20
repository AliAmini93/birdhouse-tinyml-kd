#include <cstddef>
#include <cstdint>

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

struct AudioWindowRing {
    int16_t samples[kFftSize];
    uint32_t received;
    uint16_t frames;
};

void ResetAudioWindowRing(AudioWindowRing* ring) {
    ring->received = 0;
    ring->frames = 0;
}

bool PushAudioSample(AudioWindowRing* ring,
                     int16_t sample,
                     int16_t* window) {
    if (!ring || !window) return false;

    ring->samples[ring->received % kFftSize] = sample;
    ++ring->received;

    if (ring->frames >= kExpectedFrames) return false;

    const uint32_t start =
        static_cast<uint32_t>(ring->frames) * kHopLength;

    if (ring->received != start + kFftSize) return false;

    for (int i = 0; i < kFftSize; ++i) {
        window[i] = ring->samples[(start + i) % kFftSize];
    }

    ++ring->frames;
    return true;
}

}  // namespace birdhouse

#ifdef BIRDHOUSE_HOST_TEST

#include <iostream>
#include <vector>

int main() {
    using namespace birdhouse;

    std::vector<int16_t> pcm(kTargetSamples);

    for (int i = 0; i < kTargetSamples; ++i) {
        pcm[i] = static_cast<int16_t>(
            (i * 37) % 65536 - 32768);
    }

    AudioWindowRing ring{};
    ResetAudioWindowRing(&ring);

    int16_t window[kFftSize];
    int checked = 0;

    for (int i = 0; i < kTargetSamples; ++i) {
        if (PushAudioSample(&ring, pcm[i], window)) {
            const int start = checked * kHopLength;

            for (int j = 0; j < kFftSize; ++j) {
                if (window[j] != pcm[start + j]) {
                    std::cout << "FAIL: window mismatch\n";
                    return 1;
                }
            }

            ++checked;
        }
    }

    std::cout << "Generated frames: " << checked << "\n";
    std::cout << "Expected frames: " << kExpectedFrames << "\n";
    std::cout << "Ring bytes: " << sizeof(AudioWindowRing) << "\n";

    if (checked != kExpectedFrames) {
        std::cout << "FAIL: incorrect frame count\n";
        return 1;
    }

    std::cout << "PASS: all audio windows match\n";
    return 0;
}

#endif
