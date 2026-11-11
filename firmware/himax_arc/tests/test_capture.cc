// Host tests for the capture core (bh_capture), called the way the audio
// interrupt would call it.
#include <cstdio>
#include <cstring>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/tests/bh_test.h"

namespace {

const bh::CaptureConfig kConfig = {bh::kTargetSamples, bh::kFramesPerBlock, bh::kSettleBlocks,
                                   bh::kCallbackIntervalUs, bh::kIntervalToleranceUs, bh::kClockTickUs, bh::kDmaCallbackBlocks};

int16_t Left(uint64_t frame) { return static_cast<int16_t>((frame * 13 + 5) % 30011 - 15005); }
int16_t Right(uint64_t frame) { return static_cast<int16_t>(-(static_cast<int>(frame % 1000)) - 7); }

// Feeds blocks with a known pattern and tracks time and frame position.
struct Feeder {
  uint64_t frame = 0;
  uint64_t now = 5000000;
  uint32_t frames_per_block = bh::kFramesPerBlock;
  std::vector<int16_t> scratch;

  void Callback(bh::Capture* c, uint32_t blocks, uint64_t advance_us) {
    now += advance_us;
    scratch.resize(static_cast<size_t>(blocks) * frames_per_block * 2);
    for (size_t i = 0; i < static_cast<size_t>(blocks) * frames_per_block; ++i) {
      scratch[2 * i] = Left(frame + i);
      scratch[2 * i + 1] = Right(frame + i);
    }
    frame += static_cast<uint64_t>(blocks) * frames_per_block;
    c->OnBlocks(scratch.data(), blocks, now);
  }
};

// PCM buffer with guard words on both sides.
struct GuardedPcm {
  static const int kGuard = 64;
  std::vector<int16_t> block;
  explicit GuardedPcm(size_t n) : block(n + 2 * kGuard, static_cast<int16_t>(0x5A5A)) {}
  int16_t* data() { return block.data() + kGuard; }
  bool GuardsIntact(size_t n) {
    for (int i = 0; i < kGuard; ++i) {
      if (block[i] != static_cast<int16_t>(0x5A5A)) return false;
      if (block[kGuard + n + i] != static_cast<int16_t>(0x5A5A)) return false;
    }
    return true;
  }
};

bool PatternMatches(const int16_t* pcm, uint32_t count, uint64_t first_frame) {
  for (uint32_t i = 0; i < count; ++i) {
    if (pcm[i] != Left(first_frame + i)) return false;
  }
  return true;
}

void RunToCompletion(bh::Capture* c, Feeder* f, uint32_t blocks_per_callback, int max_callbacks = 200) {
  for (int i = 0; i < max_callbacks && !c->complete() && c->error() == bh::kCapNone; ++i) {
    f->Callback(c, blocks_per_callback, static_cast<uint64_t>(blocks_per_callback) * 64000);
  }
}

}  // namespace

int main() {
  BH_CASE("normal capture: exactly 80,000 mono samples, settle blocks dropped");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(!c.running());
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(c.running() && !c.complete() && c.error() == bh::kCapNone);
    RunToCompletion(&c, &f, 2);
    BH_CHECK(c.complete());
    BH_CHECK(c.samples() == 80000);
    c.Finish();
    const bh::CaptureStats& s = c.stats();
    BH_CHECK(s.samples == 80000);
    BH_CHECK(s.callbacks == 41);             // (2 settle + 80 data) blocks / 2
    BH_CHECK(s.blocks_seen == 82);
    BH_CHECK(s.blocks_settle_dropped == 2);
    BH_CHECK(s.blocks_used == 79);           // 78 full blocks + 128 samples of the 79th
    BH_CHECK(s.blocks_after_complete == 1);  // second block of the completing pair
    BH_CHECK(s.min_blocks_per_callback == 2 && s.max_blocks_per_callback == 2);
    BH_CHECK(s.intervals == 40);
    BH_CHECK(s.interval_min_us == 128000 && s.interval_max_us == 128000);
    BH_CHECK(s.interval_anomalies == 0 && s.clock_steps == 0 && s.fifo_events == 0);
    BH_CHECK(s.complete_us - s.first_callback_us == 5120000);
    BH_CHECK(bh::NominalSpanUs(s, kConfig) == 5120000);
    BH_CHECK(bh::JudgeCapture(s, kConfig) == bh::kQualityClean);
    bh::CaptureStats wrong_batch = s;
    wrong_batch.min_blocks_per_callback = wrong_batch.max_blocks_per_callback = 3;
    BH_CHECK(bh::JudgeCapture(wrong_batch, kConfig) == bh::kQualitySuspect);
    BH_CHECK(PatternMatches(pcm.data(), 80000, 2 * bh::kFramesPerBlock));
    BH_CHECK(pcm.GuardsIntact(bh::kTargetSamples));
    uint64_t abs_l = 0, abs_r = 0;
    for (uint32_t i = 0; i < 80000; ++i) {
      const int l = Left(2048 + i), r = Right(2048 + i);
      abs_l += static_cast<uint64_t>(l < 0 ? -l : l);
      abs_r += static_cast<uint64_t>(r < 0 ? -r : r);
    }
    BH_CHECK(s.sum_abs_left == abs_l && s.sum_abs_right == abs_r);
  }

  BH_CASE("blocks after completion and after Finish never touch the buffer");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    RunToCompletion(&c, &f, 2);
    std::vector<int16_t> snapshot(pcm.data(), pcm.data() + bh::kTargetSamples);
    for (int i = 0; i < 5; ++i) f.Callback(&c, 2, 128000);  // audio still running
    BH_CHECK(c.stats().blocks_after_complete == 11);
    BH_CHECK(c.stats().callbacks == 41);  // statistics frozen at completion
    c.Finish();
    for (int i = 0; i < 3; ++i) f.Callback(&c, 2, 128000);  // late callbacks after stop
    BH_CHECK(c.stats().callbacks_inactive == 0);
    BH_CHECK(std::memcmp(snapshot.data(), pcm.data(), bh::kTargetSamples * sizeof(int16_t)) == 0);
    BH_CHECK(pcm.GuardsIntact(bh::kTargetSamples));
  }

  BH_CASE("block boundaries: 1, 3 and mixed blocks per callback; targets on and off a boundary");
  {
    const uint32_t targets[] = {1, 1023, 1024, 1025, 4096, 5000, 80000};
    const uint32_t patterns[][4] = {{1, 1, 1, 1}, {3, 3, 3, 3}, {1, 2, 3, 1}, {2, 1, 1, 3}};
    for (uint32_t target : targets) {
      for (const auto& pattern : patterns) {
        bh::CaptureConfig cfg = kConfig;
        cfg.target_samples = target;
        GuardedPcm pcm(target);
        bh::Capture c;
        Feeder f;
        BH_CHECK(c.Begin(pcm.data(), target, cfg));
        for (int i = 0; i < 400 && !c.complete(); ++i) f.Callback(&c, pattern[i % 4], 128000);
        BH_CHECK(c.complete());
        c.Finish();
        BH_CHECK(c.stats().samples == target);
        BH_CHECK(c.stats().blocks_used == (target + 1023) / 1024);
        BH_CHECK(PatternMatches(pcm.data(), target, 2048));
        BH_CHECK(pcm.GuardsIntact(target));
      }
    }
  }

  BH_CASE("settle count is configurable, including zero");
  {
    for (uint32_t settle = 0; settle <= 5; ++settle) {
      bh::CaptureConfig cfg = kConfig;
      cfg.settle_blocks = settle;
      cfg.target_samples = 3000;
      GuardedPcm pcm(3000);
      bh::Capture c;
      Feeder f;
      BH_CHECK(c.Begin(pcm.data(), 3000, cfg));
      RunToCompletion(&c, &f, 2);
      c.Finish();
      BH_CHECK(c.stats().blocks_settle_dropped == settle);
      BH_CHECK(PatternMatches(pcm.data(), 3000, static_cast<uint64_t>(settle) * 1024));
    }
  }

  BH_CASE("invalid Begin arguments are rejected and nothing is written");
  {
    GuardedPcm pcm(100);
    bh::Capture c;
    Feeder f;
    BH_CHECK(!c.Begin(nullptr, bh::kTargetSamples, kConfig));
    BH_CHECK(c.error() == bh::kCapBadArgument && !c.running());
    BH_CHECK(!c.Begin(pcm.data(), 100, kConfig));  // too small for 80,000
    BH_CHECK(c.error() == bh::kCapBadArgument && !c.running());
    f.Callback(&c, 2, 128000);
    BH_CHECK(c.stats().callbacks_inactive == 0);
    BH_CHECK(pcm.GuardsIntact(100));
    bh::CaptureConfig zero = kConfig;
    zero.frames_per_block = 0;
    BH_CHECK(!c.Begin(pcm.data(), bh::kTargetSamples, zero));
  }

  BH_CASE("incomplete recording: audio stops early");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 10; ++i) f.Callback(&c, 2, 128000);
    BH_CHECK(!c.complete());
    BH_CHECK(c.samples() == 18 * 1024);
    c.Fail(bh::kCapTimeout);
    c.Finish();
    BH_CHECK(c.error() == bh::kCapTimeout);
    BH_CHECK(c.stats().samples == 18 * 1024);
    BH_CHECK(PatternMatches(pcm.data(), 18 * 1024, 2048));
  }

  BH_CASE("PDM re-initialisation (FIFO overflow) is an error before completion only");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 5; ++i) f.Callback(&c, 2, 128000);
    c.OnFifoEvent();
    BH_CHECK(c.error() == bh::kCapFifoOverflow);
    c.Finish();
    BH_CHECK(c.stats().fifo_events == 1);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualitySuspect);

    bh::Capture d;
    Feeder g;
    BH_CHECK(d.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    RunToCompletion(&d, &g, 2);
    d.OnFifoEvent();  // after the last sample was stored
    BH_CHECK(d.error() == bh::kCapNone);
    BH_CHECK(d.complete());
    d.Finish();
    d.OnFifoEvent();  // outside a capture: ignored
    BH_CHECK(d.stats().fifo_events == 1);
  }

  BH_CASE("the first error is kept");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    c.Fail(bh::kCapLibraryError);
    c.Fail(bh::kCapTimeout);
    BH_CHECK(c.error() == bh::kCapLibraryError);
    c.OnBlocks(nullptr, 2, 1);
    BH_CHECK(c.error() == bh::kCapLibraryError);
  }

  BH_CASE("null block pointer or zero blocks is flagged");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    c.OnBlocks(nullptr, 2, 1);
    BH_CHECK(c.error() == bh::kCapBadBlock);
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    f.scratch.assign(4096, 0);
    c.OnBlocks(f.scratch.data(), 0, 1);
    BH_CHECK(c.error() == bh::kCapBadBlock);
  }

  BH_CASE("a stalled callback (lost block) makes the capture SUSPECT");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 100 && !c.complete(); ++i) {
      f.Callback(&c, 2, i == 20 ? 128000 + 64000 : 128000);
    }
    c.Finish();
    BH_CHECK(c.stats().interval_anomalies == 1);
    BH_CHECK(c.stats().interval_max_us == 192000);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualitySuspect);
  }

  BH_CASE("a uniformly wrong time base is reported as CLOCK, not as lost audio");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    Feeder f;
    BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 100 && !c.complete(); ++i) f.Callback(&c, 2, 64000);  // clock runs at half speed
    c.Finish();
    BH_CHECK(c.stats().interval_anomalies == 40);
    BH_CHECK(c.stats().interval_min_us == 64000 && c.stats().interval_max_us == 64000);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualityClock);

    bh::Capture d;
    Feeder g;
    BH_CHECK(d.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 100 && !d.complete(); ++i) g.Callback(&d, 2, 130000);  // +1.6 %: within tolerance per interval
    d.Finish();
    BH_CHECK(d.stats().interval_anomalies == 0);
    BH_CHECK(bh::JudgeCapture(d.stats(), kConfig) == bh::kQualityClock);
  }

  BH_CASE("one-tick clock errors are counted and do not make a capture SUSPECT");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture d;
    Feeder g;
    BH_CHECK(d.Begin(pcm.data(), bh::kTargetSamples, kConfig));
    for (int i = 0; i < 100 && !d.complete(); ++i) {
      if (i == 10) {
        g.Callback(&d, 2, 128000 + 1000000);  // reads one tick late
      } else if (i == 11) {
        g.now -= 1000000;                      // back to true time: one tick early
        g.Callback(&d, 2, 128000);
      } else if (i == 25) {
        g.now -= 1000000;                      // reads one tick early
        g.Callback(&d, 2, 128000);
      } else if (i == 26) {
        g.Callback(&d, 2, 128000 + 1000000);  // back to true time
      } else {
        g.Callback(&d, 2, 128000);
      }
    }
    d.Finish();
    BH_CHECK(d.complete());
    BH_CHECK(d.stats().clock_steps == 4);
    BH_CHECK(d.stats().interval_anomalies == 0);
    BH_CHECK(d.stats().interval_min_us == 128000 && d.stats().interval_max_us == 128000);
    BH_CHECK(bh::JudgeCapture(d.stats(), kConfig) == bh::kQualityClock);
  }

  BH_CASE("repeated use: a second Begin starts from a clean state");
  {
    GuardedPcm pcm(bh::kTargetSamples);
    bh::Capture c;
    for (int round = 0; round < 3; ++round) {
      Feeder f;
      f.frame = static_cast<uint64_t>(round) * 100000;
      const uint64_t first = f.frame + 2048;
      BH_CHECK(c.Begin(pcm.data(), bh::kTargetSamples, kConfig));
      if (round == 1) c.OnFifoEvent();  // spoil the middle round
      RunToCompletion(&c, &f, 2);
      c.Finish();
      if (round == 1) {
        BH_CHECK(c.error() == bh::kCapFifoOverflow);
      } else {
        BH_CHECK(c.error() == bh::kCapNone && c.complete());
        BH_CHECK(c.stats().callbacks == 41 && c.stats().fifo_events == 0);
        BH_CHECK(PatternMatches(pcm.data(), 80000, first));
      }
    }
  }

  BH_CASE("names for every error and quality value");
  for (int e = bh::kCapNone; e <= bh::kCapCancelled; ++e) {
    BH_CHECK(std::strcmp(bh::CaptureErrorName(static_cast<bh::CaptureError>(e)), "UNKNOWN") != 0);
  }
  for (int q = bh::kQualityClean; q <= bh::kQualitySuspect; ++q) {
    BH_CHECK(std::strcmp(bh::CaptureQualityName(static_cast<bh::CaptureQuality>(q)), "UNKNOWN") != 0);
  }

  return bh_test::Finish("capture");
}
