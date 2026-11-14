// Diagnostic model checks: no claim about real DMA or cache behavior.
#include <cstdio>
#include <cstring>
#include <vector>
#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_pdm_diag.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"
#include "firmware/himax_arc/tests/host_port.h"

namespace {
const bh::CaptureConfig kConfig = {32, bh::kFramesPerBlock, 0,
    bh::kCallbackIntervalUs, bh::kIntervalToleranceUs, bh::kClockTickUs, bh::kDmaCallbackBlocks};
void Fresh(uint64_t step = 1000, uint32_t valid = 15) {
  bh_port_pdm_test_reset(); fake_aud::Reset();
  host_port::DiagConfigure(step, valid); host_port::Clear();
}
void Pending(uint32_t n) { if (n == 3) fake_aud::QueueCompletion(); }
void Late(uint32_t n) {
  if (n == 3) { fake_aud::QueueCompletion(); fake_aud::DispatchPending(); }
}
void OnlyLate(uint32_t n) { if (n == 3) fake_aud::DeliverLateCallback(); }
void Write(uint32_t n) { if (n == 3) fake_aud::ChangeDmaWordForTest(0); }
void Rearm(uint32_t n) {
  if (n == 3) bh_port_pdm_diag_enable_event(kBhPdmDmaMask, 1);
}
void OtherChannel(uint32_t n) {
  if (n == 3) {
    bh_port_pdm_diag_enable_event(1u, 1);
    bh_port_pdm_diag_enable_event(kBhPdmDmaMask, 0);
  }
}
void ClockJump(uint32_t n) { if (n == 2) fake_aud::AdvanceTime(1000000); }
void CheckOwner(const bh::Capture& c, const std::vector<int16_t>& pcm,
                const bh::CaptureStats& stats, const std::vector<int16_t>& saved) {
  BH_CHECK(std::memcmp(&c.stats(), &stats, sizeof(stats)) == 0);
  BH_CHECK(pcm == saved);
  BH_CHECK(bh_port_pdm_faulted());
  BH_CHECK(fake_aud::irq_state() == 0xA5u);
  BH_CHECK(host_port::Output().empty());  // no prints from stop or callbacks
}
}  // namespace

int main() {
  BH_CASE("unarmed path has zero diagnostic reads, waits or prints");
  {
    Fresh(0); std::vector<int16_t> pcm(48, 1234); bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig)); BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(2); const uint64_t time = fake_aud::now_us();
    BH_CHECK(bh_port_pdm_stop() == 0); c.Finish();
    BH_CHECK(fake_aud::now_us() == time); BH_CHECK(host_port::DiagReads() == 0);
    BH_CHECK(!bh_port_pdm_diag_report().armed); BH_CHECK(host_port::Output().empty());
  }
  BH_CASE("armed observation preserves capture/PCM, stop sequence and quarantine");
  for (bool fail : {false, true}) {
    for (int stage = 0; stage <= 3; ++stage) {
      Fresh(); BH_CHECK(bh_port_pdm_diag_arm() == 0); BH_CHECK(bh_port_pdm_diag_arm() == -1);
      std::vector<int16_t> pcm(48, 1234); bh::Capture c;
      BH_CHECK(c.Begin(pcm.data(), 32, kConfig)); BH_CHECK(bh_port_pdm_start(&c) == 0);
      fake_aud::CompleteBlocks(3);
      fake_aud::faults().fail_stop = fail; fake_aud::faults().completion_in_stop = stage;
      const auto saved = pcm; const auto stats = c.stats(); const auto requests = fake_aud::counters().requests;
      BH_CHECK(bh_port_pdm_stop() == (fail ? -2 : 0)); c.Finish();
      const auto& r = bh_port_pdm_diag_report();
      BH_CHECK(r.finished && r.window_complete && r.rows == kBhPdmDiagSamples + 2);
      BH_CHECK(r.row[0].phase == 0 && r.row[1].phase == 1 && r.row[2].phase == 2);
      BH_CHECK(r.row[r.rows - 1].elapsed_us >= kBhPdmDiagWindowUs);
      BH_CHECK(r.max_gap_us <= 2 * kBhPdmDiagStepUs);
      BH_CHECK(r.verdict == ((fail || stage == 3) ? kBhDmaObservedFail : kBhDmaObservedPass));
      BH_CHECK(fake_aud::counters().stops == 1 && fake_aud::counters().starts == 1);
      BH_CHECK(fake_aud::counters().requests == requests); CheckOwner(c, pcm, stats, saved);
      BH_CHECK(bh_port_pdm_start(&c) == -1 && bh_port_pdm_diag_arm() == -1);
      const uint32_t reads = host_port::DiagReads(); fake_aud::faults().fail_stop = false;
      BH_CHECK(bh_port_pdm_stop() == 0); BH_CHECK(host_port::DiagReads() == reads);
      BH_CHECK(bh_port_pdm_faulted());
    }
  }
  BH_CASE("pending, late callback and rearm attempt are positive witnesses");
  for (auto hook : {Pending, Late, OnlyLate, Rearm, Write}) {
    Fresh(); BH_CHECK(bh_port_pdm_diag_arm() == 0);
    std::vector<int16_t> pcm(48, 1234); bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig)); BH_CHECK(bh_port_pdm_start(&c) == 0);
    fake_aud::CompleteBlocks(3); const auto saved = pcm; const auto stats = c.stats();
    // Independent word-write and callback-only fixtures isolate each witness;
    // neither is presented as a faithful real DMA transition.
    host_port::DiagReadHook(hook); BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish(); const auto& r = bh_port_pdm_diag_report();
    BH_CHECK(r.verdict == kBhDmaObservedFail);
    if (hook == Rearm || hook == Late) BH_CHECK(r.post_enable_attempt == 1);
    if (hook == Write) {
      bool changed = false;
      for (uint32_t i = 2; i < r.rows; ++i) changed = changed || r.row[i].changed_words != 0;
      BH_CHECK(changed);
    }
    if (hook == Late) {
      BH_CHECK(fake_aud::counters().last_rearm < fake_aud::counters().last_callback);
      BH_CHECK(fake_aud::counters().last_callback < fake_aud::counters().last_ack);
    }
    CheckOwner(c, pcm, stats, saved);
  }
  BH_CASE("unknown reads, frozen clock and clock discontinuity never pass");
  for (int mode = 0; mode < 3; ++mode) {
    Fresh(mode == 1 ? 0 : 1000, mode == 0 ? 0 : 15);
    BH_CHECK(bh_port_pdm_diag_arm() == 0); std::vector<int16_t> pcm(48); bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig)); BH_CHECK(bh_port_pdm_start(&c) == 0);
    if (mode == 2) host_port::DiagReadHook(ClockJump);
    BH_CHECK(bh_port_pdm_stop() == 0); c.Finish();
    const auto& r = bh_port_pdm_diag_report(); BH_CHECK(r.verdict == kBhDmaInconclusive);
    if (mode == 1) BH_CHECK(r.budget_exhausted && !r.window_complete);
    if (mode == 2) BH_CHECK(r.clock_invalid && !r.window_complete);
    bh_port_pdm_diag_print();
    BH_CHECK(host_port::Output().find("full_quiescence=UNOBSERVABLE") != std::string::npos);
    BH_CHECK(host_port::Output().find("INCONCLUSIVE") != std::string::npos);
  }
  BH_CASE("other channels and disable operations are neither changed nor counted as rearm");
  {
    Fresh(); BH_CHECK(bh_port_pdm_diag_arm() == 0);
    std::vector<int16_t> pcm(48); bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig)); BH_CHECK(bh_port_pdm_start(&c) == 0);
    host_port::DiagReadHook(OtherChannel); BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish(); const auto& r = bh_port_pdm_diag_report();
    BH_CHECK(r.verdict == kBhDmaObservedPass && r.post_enable_attempt == 0);
    BH_CHECK(r.row[r.rows - 1].enable_attempts == 1);
  }
  BH_CASE("partial-start cleanup observes once without publishing a capture owner");
  {
    Fresh(); BH_CHECK(bh_port_pdm_diag_arm() == 0);
    std::vector<int16_t> pcm(48, 1234); bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig));
    fake_aud::faults().fail_start = true;
    BH_CHECK(bh_port_pdm_start(&c) == -3);
    BH_CHECK(bh_port_pdm_diag_report().finished && bh_port_pdm_faulted());
    fake_aud::QueueCompletion(); fake_aud::DispatchPending();
    BH_CHECK(fake_aud::counters().requests == 0 && c.samples() == 0);
    BH_CHECK(pcm[0] == 1234 && pcm[32] == 1234);
    BH_CHECK(bh_port_pdm_start(&c) == -1 && bh_port_pdm_diag_arm() == -1);
    c.Finish();
  }
  host_port::DiagConfigure(0);
  return bh_test::Finish("pdm_diag_observer_model_only");
}
