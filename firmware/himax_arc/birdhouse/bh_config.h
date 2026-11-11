// Fixed parameters of the Birdhouse capture/inference module on the Himax.
#ifndef BIRDHOUSE_HIMAX_BH_CONFIG_H_
#define BIRDHOUSE_HIMAX_BH_CONFIG_H_

#include <cstddef>
#include <cstdint>

#include "firmware/preprocess/preprocess_constants.h"

namespace bh {

constexpr uint32_t kSampleRateHz = 16000;
constexpr uint32_t kTargetSamples = static_cast<uint32_t>(birdhouse::kTargetSamples);  // 80,000

// PDM/DMA ring. These are the values the vendor firmware itself uses for
// microphone ingestion, so the prebuilt audio library is exercised in a
// configuration that is known to work.
//   block size is in BYTES; one stereo frame is 2 x int16 = 4 bytes
//   the library halts the CPU if the block count exceeds 50
constexpr uint32_t kDmaBlockBytes = 4096;
constexpr uint32_t kDmaBlockCount = 4;
constexpr uint32_t kDmaCallbackBlocks = 2;
constexpr uint32_t kFramesPerBlock = kDmaBlockBytes / 4;  // 1024

// The PDM front end runs a DC-removal filter; the vendor code discards the
// first two blocks (2048 frames, 128 ms) after every start. Same here.
constexpr uint32_t kSettleBlocks = 2;

// Time between two audio callbacks when nothing is lost.
constexpr uint32_t kCallbackIntervalUs =
    static_cast<uint32_t>(static_cast<uint64_t>(kDmaCallbackBlocks) * kFramesPerBlock * 1000000u / kSampleRateHz);  // 128,000
// A lost or repeated block shifts an interval by at least half the nominal value.
constexpr uint32_t kIntervalToleranceUs = 16000;
// The vendor microsecond clock is built on a 1 s tick and can be off by exactly
// one tick for a single reading. Such steps are counted, not treated as loss.
constexpr uint32_t kClockTickUs = 1000000;

// Hard deadline for one capture, measured in the main loop. Nominal duration is
// (2 settle + 80 data) blocks = 5.25 s.
constexpr uint32_t kCaptureDeadlineUs = 8000000;

// Host measurement: 148,800 bytes with the reference kernels. See PROGRESS.md.
constexpr size_t kArenaBytes = 256 * 1024;

}  // namespace bh

// Large buffers go to the 1.4 MB SYSTEM0 region through the vendor linker
// script's ".tensor_arena" output section; ordinary .bss lands in the 248 KB
// DCCM region that also holds the heap.
#if defined(BIRDHOUSE_HOST_BUILD)
#define BH_BIG_RAM
#else
#define BH_BIG_RAM __attribute__((section(".tensor_arena")))
#endif

#endif  // BIRDHOUSE_HIMAX_BH_CONFIG_H_
