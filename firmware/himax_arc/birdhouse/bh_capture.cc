#include "firmware/himax_arc/birdhouse/bh_capture.h"

namespace bh {
namespace {

inline uint32_t AbsI16(int16_t v) {
  const int32_t x = v;
  return static_cast<uint32_t>(x < 0 ? -x : x);
}

inline uint64_t AbsDiff(uint64_t a, uint64_t b) { return a > b ? a - b : b - a; }

}  // namespace

const char* CaptureErrorName(CaptureError e) {
  switch (e) {
    case kCapNone: return "NONE";
    case kCapBadArgument: return "BAD_ARGUMENT";
    case kCapLibraryError: return "LIBRARY_ERROR";
    case kCapBadBlock: return "BAD_BLOCK";
    case kCapFifoOverflow: return "FIFO_OVERFLOW";
    case kCapTimeout: return "TIMEOUT";
    case kCapStartFailed: return "START_FAILED";
    case kCapStopFailed: return "STOP_FAILED";
    case kCapCancelled: return "CANCELLED";
  }
  return "UNKNOWN";
}

const char* CaptureQualityName(CaptureQuality q) {
  switch (q) {
    case kQualityClean: return "CLEAN";
    case kQualityClock: return "CLOCK";
    case kQualitySuspect: return "SUSPECT";
  }
  return "UNKNOWN";
}

Capture::Capture()
    : pcm_(nullptr), config_(), stats_(), previous_callback_us_(0), have_previous_(false),
      active_(0), complete_(0), error_(kCapNone), samples_(0) {}

bool Capture::Begin(int16_t* pcm, uint32_t capacity_samples, const CaptureConfig& config) {
  active_ = 0;
  pcm_ = pcm;
  config_ = config;
  stats_ = CaptureStats();
  stats_.min_blocks_per_callback = 0xFFFFFFFFu;
  stats_.interval_min_us = 0xFFFFFFFFu;
  previous_callback_us_ = 0;
  have_previous_ = false;
  complete_ = 0;
  samples_ = 0;
  error_ = kCapNone;
  if (pcm == nullptr || config.target_samples == 0 || config.frames_per_block == 0 ||
      capacity_samples < config.target_samples) {
    error_ = kCapBadArgument;
    return false;
  }
  active_ = 1;
  return true;
}

void Capture::Fail(CaptureError e) {
  if (error_ == kCapNone) error_ = static_cast<uint32_t>(e);
}

void Capture::OnFifoEvent() {
  if (active_ == 0) return;
  ++stats_.fifo_events;
  // After completion the kept samples are already in the buffer; a restart of
  // the front end no longer affects them.
  if (complete_ == 0) Fail(kCapFifoOverflow);
}

void Capture::OnBlocks(const int16_t* stereo, uint32_t blocks, uint64_t now_us) {
  if (active_ == 0) {
    return;
  }
  if (stereo == nullptr || blocks == 0) {
    Fail(kCapBadBlock);
    return;
  }

  if (complete_ == 0) {
    ++stats_.callbacks;
    if (blocks < stats_.min_blocks_per_callback) stats_.min_blocks_per_callback = blocks;
    if (blocks > stats_.max_blocks_per_callback) stats_.max_blocks_per_callback = blocks;

    if (!have_previous_) {
      have_previous_ = true;
      stats_.first_callback_us = now_us;
    } else {
      // Unsigned difference of two 64-bit readings; a backward step shows up as
      // a huge value and is classified below like any other anomaly.
      const uint64_t delta = now_us - previous_callback_us_;
      const uint64_t nominal = config_.nominal_interval_us;
      const uint64_t tol = config_.interval_tolerance_us;
      const uint64_t tick = config_.clock_tick_us;
      ++stats_.intervals;
      const bool regular = AbsDiff(delta, nominal) <= tol;
      // One clock tick late, or one tick early (delta wraps negative).
      const bool step_late = tick != 0 && AbsDiff(delta, nominal + tick) <= tol;
      const bool step_early = tick != 0 && tick > nominal &&
                              AbsDiff(previous_callback_us_ - now_us, tick - nominal) <= tol;
      if (!regular && (step_late || step_early)) {
        ++stats_.clock_steps;
      } else {
        if (!regular) ++stats_.interval_anomalies;
        const uint32_t d32 = delta > 0xFFFFFFFFull ? 0xFFFFFFFFu : static_cast<uint32_t>(delta);
        if (d32 < stats_.interval_min_us) stats_.interval_min_us = d32;
        if (d32 > stats_.interval_max_us) stats_.interval_max_us = d32;
      }
    }
    previous_callback_us_ = now_us;
  }

  const uint32_t frames = config_.frames_per_block;
  for (uint32_t b = 0; b < blocks; ++b) {
    ++stats_.blocks_seen;
    if (complete_ != 0) {
      ++stats_.blocks_after_complete;
      continue;
    }
    if (stats_.blocks_settle_dropped < config_.settle_blocks) {
      ++stats_.blocks_settle_dropped;
      continue;
    }
    const int16_t* src = stereo + static_cast<size_t>(b) * frames * 2;
    const uint32_t have = samples_;
    const uint32_t want = config_.target_samples - have;
    const uint32_t n = want < frames ? want : frames;
    int16_t* dst = pcm_ + have;
    uint64_t abs_l = 0, abs_r = 0;
    for (uint32_t i = 0; i < n; ++i) {
      const int16_t left = src[2 * i];
      dst[i] = left;
      abs_l += AbsI16(left);
      abs_r += AbsI16(src[2 * i + 1]);
    }
    stats_.sum_abs_left += abs_l;
    stats_.sum_abs_right += abs_r;
    ++stats_.blocks_used;
    stats_.samples = have + n;
    samples_ = have + n;
    if (have + n == config_.target_samples) {
      stats_.complete_us = now_us;
      complete_ = 1;  // published last: the buffer is fully written
    }
  }
}

void Capture::Finish() { active_ = 0; }

uint64_t NominalSpanUs(const CaptureStats& stats, const CaptureConfig& config) {
  return static_cast<uint64_t>(stats.intervals) * config.nominal_interval_us;
}

CaptureQuality JudgeCapture(const CaptureStats& stats, const CaptureConfig& config) {
  if (stats.fifo_events != 0) return kQualitySuspect;
  if (stats.samples != config.target_samples) return kQualitySuspect;
  if (stats.intervals == 0) return kQualitySuspect;
  const uint32_t measured = stats.intervals - stats.clock_steps;
  if (measured == 0) return kQualitySuspect;
  // A tick-sized gap could also hide lost audio. Counting it is useful, but
  // the host cannot prove that it was just the clock. Withhold valid decisions.
  // Irregular spacing means audio was lost or delayed, whatever the time base.
  if (stats.interval_max_us - stats.interval_min_us > config.interval_tolerance_us) {
    return kQualitySuspect;
  }
  if (stats.clock_steps != 0) return kQualityClock;
  // Regular spacing that disagrees with nominal needs an external timebase:
  // it could be a clock-scale problem OR a wrong sample rate / systematic loss.
  if (stats.interval_anomalies != 0) return kQualityClock;
  const uint64_t nominal = config.nominal_interval_us;
  const uint64_t mid = (static_cast<uint64_t>(stats.interval_min_us) + stats.interval_max_us) / 2;
  if (AbsDiff(mid, nominal) * 100 > nominal) return kQualityClock;
  return kQualityClean;
}

}  // namespace bh
