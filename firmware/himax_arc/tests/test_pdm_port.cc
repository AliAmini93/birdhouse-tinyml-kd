// Host tests for the PDM adapter (bh_pdm_port.cc) against the emulated audio
// library. The adapter source is the same file that is linked into the firmware.
#include <cstdio>
#include <cstring>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"

namespace {

const bh::CaptureConfig kConfig = {bh::kTargetSamples, bh::kFramesPerBlock, bh::kSettleBlocks,
                                   bh::kCallbackIntervalUs, bh::kIntervalToleranceUs, bh::kClockTickUs};

int16_t Source(uint64_t frame, int channel, void*) {
  if (channel == 1) return static_cast<int16_t>(-11);
  return static_cast<int16_t>((frame * 37 + 3) % 30011 - 15005);
}

bool Matches(const int16_t* pcm, uint32_t count, uint64_t first_frame) {
  for (uint32_t i = 0; i < count; ++i) {
    if (pcm[i] != Source(first_frame + i, 0, nullptr)) return false;
  }
  return true;
}

std::vector<int16_t> g_pcm(bh::kTargetSamples + 16, 0x7B7B);

void Fresh() {
  fake_aud::Reset();
  fake_aud::SetSource(Source, nullptr);
  std::fill(g_pcm.begin(), g_pcm.end(), static_cast<int16_t>(0x7B7B));
}

bool GuardIntact() {
  for (size_t i = bh::kTargetSamples; i < g_pcm.size(); ++i) {
    if (g_pcm[i] != static_cast<int16_t>(0x7B7B)) return false;
  }
  return true;
}

}  // namespace

int main() {
  BH_CASE("normal capture through the ring, including many wraps");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    BH_CHECK(fake_aud::running());
    uint32_t blocks = 0;
    while (!c.complete() && blocks < 200) {
      fake_aud::CompleteBlock();
      ++blocks;
    }
    BH_CHECK(c.complete());
    BH_CHECK(blocks == 82);  // 2 settle + 80 data, delivered in pairs
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
    BH_CHECK(!fake_aud::running());
    BH_CHECK(c.error() == bh::kCapNone);
    BH_CHECK(c.stats().samples == 80000 && c.stats().callbacks == 41);
    BH_CHECK(c.stats().min_blocks_per_callback == 2 && c.stats().max_blocks_per_callback == 2);
    BH_CHECK(Matches(g_pcm.data(), 80000, 2048));
    BH_CHECK(GuardIntact());
    BH_CHECK(fake_aud::counters().ring_overflows == 0);
    BH_CHECK(fake_aud::counters().callbacks == 41);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualityClean);
  }

  BH_CASE("start/stop argument and state errors");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(bh_port_pdm_stop() == -1);        // not started
    BH_CHECK(bh_port_pdm_start(nullptr) == -4);
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    BH_CHECK(bh_port_pdm_start(&c) == -1);     // already started
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
  }

  BH_CASE("library refuses to register or start: nothing is left half-started");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    fake_aud::faults().fail_register = true;
    BH_CHECK(bh_port_pdm_start(&c) == -2);
    fake_aud::faults().fail_register = false;
    fake_aud::faults().fail_start = true;
    BH_CHECK(bh_port_pdm_start(&c) == -3);
    BH_CHECK(!fake_aud::running());
    fake_aud::faults().fail_start = false;
    BH_CHECK(bh_port_pdm_start(&c) == 0);      // recovers
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
  }

  BH_CASE("failed stop detaches ownership and blocks restart until explicit stop succeeds");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::faults().fail_stop = true;
    BH_CHECK(bh_port_pdm_stop() == -2);
    c.Finish();
    BH_CHECK(fake_aud::running());  // failure is not proof DMA stopped
    BH_CHECK(bh_port_pdm_start(&c) == -1);
    const bh::CaptureStats frozen = c.stats();
    std::vector<int16_t> snapshot = g_pcm;
    fake_aud::faults().bad_address = 1;
    fake_aud::CompleteBlocks(4);
    BH_CHECK(snapshot == g_pcm);
    BH_CHECK(std::memcmp(&frozen, &c.stats(), sizeof(frozen)) == 0);
    BH_CHECK(c.error() == bh::kCapNone);
    fake_aud::faults().bad_address = 0;
    fake_aud::faults().fail_stop = false;
    BH_CHECK(bh_port_pdm_stop() == 0);
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);      // stage50 would have refused forever
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
  }

  BH_CASE("library error from request_read / update_idx is latched");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(4);
    fake_aud::faults().fail_request_read = 1;
    fake_aud::CompleteBlocks(2);
    BH_CHECK(c.error() == bh::kCapLibraryError);
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();

    Fresh();
    bh::Capture d;
    BH_CHECK(d.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&d) == 0);
    fake_aud::faults().fail_update_idx = 1;
    fake_aud::CompleteBlocks(2);
    BH_CHECK(d.error() == bh::kCapLibraryError);
    BH_CHECK(bh_port_pdm_stop() == 0);
    d.Finish();
  }

  BH_CASE("a block address outside the ring layout is rejected without copying");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(2);  // settle pair
    fake_aud::faults().bad_address = 1;
    fake_aud::CompleteBlocks(2);
    BH_CHECK(c.error() == bh::kCapBadBlock);
    BH_CHECK(c.samples() == 0);
    BH_CHECK(g_pcm[0] == static_cast<int16_t>(0x7B7B));
    BH_CHECK(fake_aud::counters().ring_overflows == 0);  // blocks were still handed back
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
  }

  BH_CASE("held-off interrupts: the library silently resets its ring; capture is flagged SUSPECT");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(20);
    fake_aud::faults().suppress_callbacks = 6;  // 6 block periods without the callback running
    uint32_t guard = 0;
    while (!c.complete() && guard++ < 400) fake_aud::CompleteBlock();
    BH_CHECK(c.complete());
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
    BH_CHECK(fake_aud::counters().ring_overflows >= 1);       // audio was lost in the library
    BH_CHECK(c.error() == bh::kCapNone);                      // ... and it told nobody
    BH_CHECK(!Matches(g_pcm.data(), 80000, 2048));            // the recording is discontinuous
    BH_CHECK(c.stats().interval_anomalies >= 1);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualitySuspect);  // but it is detected
  }

  BH_CASE("PDM driver re-initialisation during capture is an error");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    bh_port_on_pdm_reinit();  // before start: ignored
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(10);
    bh_port_on_pdm_reinit();
    BH_CHECK(c.error() == bh::kCapFifoOverflow);
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
    BH_CHECK(c.stats().fifo_events == 1);
    bh_port_on_pdm_reinit();  // after stop: ignored
    BH_CHECK(c.stats().fifo_events == 1);
  }

  BH_CASE("a callback pending at stop time is ignored");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(4);
    fake_aud::faults().suppress_callbacks = 1;
    fake_aud::CompleteBlock();  // nonempty ring at stop
    fake_aud::faults().callback_during_stop = true;
    const uint32_t requests = fake_aud::counters().requests;
    const uint32_t late = bh_port_pdm_late_callbacks();
    BH_CHECK(bh_port_pdm_stop() == 0);
    BH_CHECK(fake_aud::counters().requests == requests);
    BH_CHECK(bh_port_pdm_late_callbacks() == late + 1);
    c.Finish();
    std::vector<int16_t> snapshot(g_pcm.begin(), g_pcm.end());
    const bh::CaptureStats frozen = c.stats();
    fake_aud::faults().fail_request_read = 1;
    fake_aud::DeliverLateCallback();
    BH_CHECK(fake_aud::counters().requests == requests);
    BH_CHECK(std::memcmp(&frozen, &c.stats(), sizeof(frozen)) == 0);
    BH_CHECK(snapshot == g_pcm);
    BH_CHECK(c.error() == bh::kCapNone);
  }

  BH_CASE("failed partial start plus failed cleanup cannot publish or reuse an owner");
  {
    Fresh();
    {
      bh::Capture c;
      BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
      fake_aud::faults().fail_start = true;
      fake_aud::faults().fail_stop = true;
      BH_CHECK(bh_port_pdm_start(&c) == -3);
      BH_CHECK(bh_port_pdm_faulted());
      BH_CHECK(bh_port_pdm_start(&c) == -1);
      c.Finish();
    }  // callback target has now been destroyed
    const uint32_t requests = fake_aud::counters().requests;
    fake_aud::CompleteBlocks(6);
    fake_aud::DeliverLateCallback();
    BH_CHECK(fake_aud::counters().requests == requests);
    BH_CHECK(GuardIntact());
    fake_aud::faults().fail_stop = false;
    BH_CHECK(bh_port_pdm_stop() == 0);
  }

  BH_CASE("one-tick clock error is counted and timing remains unverified");
  {
    Fresh();
    bh::Capture c;
    BH_CHECK(c.Begin(g_pcm.data(), bh::kTargetSamples, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    uint32_t blocks = 0;
    while (!c.complete() && blocks < 200) {
      if (blocks == 31) fake_aud::GlitchNextClockRead(-1000000);  // this callback reads 1 s early
      fake_aud::CompleteBlock();
      ++blocks;
    }
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
    BH_CHECK(c.stats().clock_steps == 2);  // the early reading and the return to true time
    BH_CHECK(c.stats().interval_anomalies == 0);
    BH_CHECK(bh::JudgeCapture(c.stats(), kConfig) == bh::kQualityClock);
    BH_CHECK(Matches(g_pcm.data(), 80000, 2048));
  }

  return bh_test::Finish("pdm_port");
}
