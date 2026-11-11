// Capture core: turns the audio library's stereo blocks into exactly N mono
// samples in a caller-owned linear buffer, and records everything needed to
// judge whether the recording is continuous.
//
// Concurrency contract
// --------------------
// The prebuilt audio library calls the application from inside the DMA-complete
// interrupt. OnBlocks() and OnFifoEvent() therefore run in interrupt context.
//
//   * Between Begin() and Finish() the interrupt side owns the PCM buffer and
//     all statistics. The main loop may only call running(), complete(),
//     error() and samples(): each reads one machine word.
//   * Begin() must be called while detached from audio. Finish() must be called
//     after port detachment; from then on the main loop owns the buffer
//     and may read stats().
//   * The port detaches the ISR pointer under brief IRQ exclusion before stop.
//     Late callbacks cannot touch this object. No masking during PCM copies.
#ifndef BIRDHOUSE_HIMAX_BH_CAPTURE_H_
#define BIRDHOUSE_HIMAX_BH_CAPTURE_H_

#include <cstddef>
#include <cstdint>

namespace bh {

enum CaptureError {
  kCapNone = 0,
  kCapBadArgument = 1,    // Begin() with a null or too small buffer
  kCapLibraryError = 2,   // audio library call returned an error
  kCapBadBlock = 3,       // block address/count outside the DMA ring
  kCapFifoOverflow = 4,   // PDM front end was re-initialised mid-capture
  kCapTimeout = 5,        // deadline expired in the main loop
  kCapStartFailed = 6,
  kCapStopFailed = 7,
  kCapCancelled = 8,      // aborted on request
};

const char* CaptureErrorName(CaptureError e);

struct CaptureConfig {
  uint32_t target_samples;
  uint32_t frames_per_block;
  uint32_t settle_blocks;
  uint32_t nominal_interval_us;
  uint32_t interval_tolerance_us;
  uint32_t clock_tick_us;
};

struct CaptureStats {
  uint32_t callbacks;              // while capturing, up to and including completion
  uint32_t blocks_seen;
  uint32_t blocks_settle_dropped;
  uint32_t blocks_used;
  uint32_t blocks_after_complete;  // delivered after the last sample was taken
  uint32_t callbacks_inactive;     // reserved, always zero; port counts detached callbacks
  uint32_t min_blocks_per_callback;
  uint32_t max_blocks_per_callback;
  uint32_t samples;
  uint32_t intervals;              // callback-to-callback intervals measured
  uint32_t interval_min_us;        // clock-tick steps excluded
  uint32_t interval_max_us;
  uint32_t interval_anomalies;     // outside nominal +/- tolerance, not a clock step
  uint32_t clock_steps;            // off by one clock tick +/- tolerance
  uint32_t fifo_events;
  uint64_t first_callback_us;
  uint64_t complete_us;
  uint64_t sum_abs_left;           // over the samples that were kept
  uint64_t sum_abs_right;
};

class Capture {
 public:
  Capture();

  // Main context, audio stopped. Returns false (and latches kCapBadArgument)
  // if the buffer cannot hold the target.
  bool Begin(int16_t* pcm, uint32_t capacity_samples, const CaptureConfig& config);

  // Interrupt context. `stereo` points at `blocks` contiguous blocks of
  // interleaved left/right int16 frames.
  void OnBlocks(const int16_t* stereo, uint32_t blocks, uint64_t now_us);
  // Interrupt context. The PDM driver was torn down and restarted.
  void OnFifoEvent();
  // ISR while attached, or main context AFTER port detachment. First error kept.
  void Fail(CaptureError e);

  // Main context, after the port has detached this object under IRQ exclusion.
  void Finish();

  // Safe from the main loop at any time.
  bool running() const { return active_ != 0; }
  bool complete() const { return complete_ != 0; }
  CaptureError error() const { return static_cast<CaptureError>(error_); }
  uint32_t samples() const { return samples_; }

  // Main context, only when not running().
  const CaptureStats& stats() const { return stats_; }

 private:
  int16_t* pcm_;
  CaptureConfig config_;
  CaptureStats stats_;
  uint64_t previous_callback_us_;
  bool have_previous_;
  volatile uint32_t active_;
  volatile uint32_t complete_;
  volatile uint32_t error_;
  volatile uint32_t samples_;
};

// Continuity verdict derived from the statistics.
enum CaptureQuality {
  kQualityClean = 0,    // regular callbacks and the span matches the nominal duration
  kQualityClock = 1,    // timing is unverified: scale/sample rate or tick-sized gaps
  kQualitySuspect = 2,  // irregular callbacks: a stall or a lost block is likely
};
const char* CaptureQualityName(CaptureQuality q);
CaptureQuality JudgeCapture(const CaptureStats& stats, const CaptureConfig& config);
// Nominal time between the first callback and the completing callback.
uint64_t NominalSpanUs(const CaptureStats& stats, const CaptureConfig& config);

}  // namespace bh

#endif  // BIRDHOUSE_HIMAX_BH_CAPTURE_H_
