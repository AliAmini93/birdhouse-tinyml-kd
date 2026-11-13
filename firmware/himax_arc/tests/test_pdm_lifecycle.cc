// Adversarial single-core model tests, never a claim about physical DMA stop.
#include <cstdio>
#include <cstring>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"
#include "firmware/himax_arc/tests/host_port.h"

namespace {
const bh::CaptureConfig kConfig = {32, bh::kFramesPerBlock, 0,
    bh::kCallbackIntervalUs, bh::kIntervalToleranceUs, bh::kClockTickUs, bh::kDmaCallbackBlocks};
const int16_t kGuard = 1234;
void Fresh() {
  bh_port_pdm_test_reset();  // independent process only, not a restart proof
  fake_aud::Reset();
}
void Probe(uint32_t) {
  const fake_aud::Counters& c = fake_aud::counters();
  BH_CHECK(fake_aud::running());  // re-arm must already have happened
  BH_CHECK(fake_aud::pending());  // acknowledgment must not have happened yet
  BH_CHECK(c.last_rearm < c.last_callback);
  BH_CHECK(c.last_ack < c.last_callback);
}
void AssertBlocked(bh::Capture* next) {
  const uint32_t starts = fake_aud::counters().starts;
  BH_CHECK(bh_port_pdm_faulted());
  BH_CHECK(bh_port_pdm_start(next) == -1);
  BH_CHECK(fake_aud::counters().starts == starts);
}
}  // namespace

int main() {
  BH_CASE("model independently exposes re-arm before callback and ack after return");
  {
    Fresh();
    uint32_t ring[32] = {};
    audio_config_t cfg = {AUDIO_SR_16KHZ, ring, 4, 32, 1};
    BH_CHECK(hx_lib_audio_register_evt_cb(Probe) == AUDIO_NO_ERROR);
    BH_CHECK(hx_lib_audio_start(&cfg) == AUDIO_NO_ERROR);
    fake_aud::CompleteBlocks(12);  // deliberately wraps/overruns without consumption
    BH_CHECK(fake_aud::counters().ring_overflows == 3);
    BH_CHECK(fake_aud::counters().rearms == 12);
    BH_CHECK(fake_aud::counters().acknowledgments == 12);
    BH_CHECK(fake_aud::counters().last_callback < fake_aud::counters().last_ack);
    BH_CHECK(!fake_aud::pending());
    BH_CHECK(hx_lib_audio_stop() == AUDIO_NO_ERROR);
    fake_aud::Reset();  // drop stack-backed raw ring before leaving its scope
  }

  BH_CASE("startup publication mask and exact IRQ restore, including caller already masked");
  for (uint32_t state : {0xA5u, 0xA4u}) {
    Fresh();
    fake_aud::SetIrqState(state);
    fake_aud::faults().completion_at_start_enable = true;
    std::vector<int16_t> pcm(48, kGuard);
    bh::Capture c;
    BH_CHECK(c.Begin(pcm.data(), 32, kConfig));
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    BH_CHECK(fake_aud::irq_state() == state);
    BH_CHECK(fake_aud::counters().irq_before_queue_publication == 0);
    BH_CHECK(fake_aud::counters().isr_entries == (state & 1u));
    BH_CHECK(bh_port_pdm_stop() == 0);
    BH_CHECK(fake_aud::irq_state() == state);
    c.Finish();
    AssertBlocked(&c);
    fake_aud::IrqRestore(0xA5u);
    AssertBlocked(&c);
    BH_CHECK(pcm[32] == kGuard);
  }

  BH_CASE("old pending before/during/after stop, both reset hypotheses and prior IRQ states");
  for (bool clears : {false, true}) {
    for (uint32_t state : {0xA5u, 0xA4u}) {
      for (int stage = 0; stage <= 3; ++stage) {
        for (bool pending_before : {false, true}) {
          Fresh();
          std::vector<int16_t> pcm(48, kGuard);
          bh::Capture c;
          BH_CHECK(c.Begin(pcm.data(), 32, kConfig));
          BH_CHECK(bh_port_pdm_start(&c) == 0);
          fake_aud::CompleteBlocks(3);  // leave one unread block at stop
          fake_aud::faults().stop_clears_pending = clears;
          fake_aud::faults().completion_in_stop = stage;
          fake_aud::SetIrqState(state);
          if (pending_before) fake_aud::QueueCompletion();
          const uint32_t requests = fake_aud::counters().requests;
          const std::vector<int16_t> frozen = pcm;
          const bh::CaptureStats stats = c.stats();  // no concurrent host ISR here
          BH_CHECK(bh_port_pdm_stop() == 0);
          BH_CHECK(fake_aud::irq_state() == state);
          c.Finish();
          AssertBlocked(&c);
          fake_aud::IrqRestore(0xA5u);
          // A completion arriving after reset defeats either reset hypothesis.
          fake_aud::QueueCompletion();
          BH_CHECK(fake_aud::DispatchPending());
          fake_aud::QueueCompletion();
          BH_CHECK(fake_aud::DispatchPending());
          BH_CHECK(fake_aud::running());  // concrete model counterexample to quiescence
          BH_CHECK(fake_aud::counters().rearms > 3);
          BH_CHECK(fake_aud::counters().requests == requests);
          BH_CHECK(frozen == pcm);
          BH_CHECK(std::memcmp(&stats, &c.stats(), sizeof(stats)) == 0);
          AssertBlocked(&c);
          fake_aud::faults().completion_in_stop = 0;
          BH_CHECK(bh_port_pdm_stop() == 0);  // retry does not reopen anything
          AssertBlocked(&c);
          // Resetting just the model must not silently reset production state.
          fake_aud::Reset();
          AssertBlocked(&c);
        }
      }
    }
  }

  BH_CASE("partial starts, stop errors, retries and IRQ restoration cannot publish a new owner");
  for (bool start_fails : {false, true}) {
    for (bool stop_fails : {false, true}) {
      for (uint32_t state : {0xA5u, 0xA4u}) {
        Fresh();
        std::vector<int16_t> pcm(48, kGuard);
        bh::Capture c;
        BH_CHECK(c.Begin(pcm.data(), 32, kConfig));
        fake_aud::SetIrqState(state);
        fake_aud::faults().fail_start = start_fails;
        fake_aud::faults().fail_stop = stop_fails;
        BH_CHECK(bh_port_pdm_start(&c) == (start_fails ? -3 : 0));
        BH_CHECK(fake_aud::irq_state() == state);
        if (!start_fails) BH_CHECK(bh_port_pdm_stop() == (stop_fails ? -2 : 0));
        c.Finish();
        AssertBlocked(&c);
        const uint32_t requests = fake_aud::counters().requests;
        fake_aud::IrqRestore(0xA5u);
        fake_aud::QueueCompletion(); fake_aud::DispatchPending();
        fake_aud::QueueCompletion(); fake_aud::DispatchPending();
        BH_CHECK(fake_aud::counters().requests == requests);
        BH_CHECK(pcm == std::vector<int16_t>(48, kGuard));
        fake_aud::faults().fail_stop = false;
        BH_CHECK(bh_port_pdm_stop() == 0);
        AssertBlocked(&c);
      }
    }
  }

  BH_CASE("registration failure precedes transfer attempt and remains retryable");
  {
    Fresh();
    int16_t pcm[32] = {};
    bh::Capture c;
    BH_CHECK(bh_port_pdm_start(nullptr) == -4);
    BH_CHECK(bh_port_pdm_stop() == -1);
    BH_CHECK(c.Begin(pcm, 32, kConfig));
    fake_aud::faults().fail_register = true;
    BH_CHECK(bh_port_pdm_start(&c) == -2);
    BH_CHECK(fake_aud::counters().starts == 0 && fake_aud::counters().stops == 0);
    BH_CHECK(!bh_port_pdm_faulted());
    fake_aud::faults().fail_register = false;
    BH_CHECK(bh_port_pdm_start(&c) == 0);
    BH_CHECK(bh_port_pdm_stop() == 0);
    c.Finish();
    AssertBlocked(&c);
  }

  // Mutation controls stop on assertion failures before injecting destroyed-owner IRQs.
  if (bh_test::counters().failed != 0) return bh_test::Finish("pdm_lifecycle_model_only");

  BH_CASE("destroyed capture lifetime survives full stale ISR with re-arm");
  {
    Fresh();
    {
      std::vector<int16_t> pcm(32);
      bh::Capture c;
      BH_CHECK(c.Begin(pcm.data(), 32, kConfig));
      BH_CHECK(bh_port_pdm_start(&c) == 0);
      BH_CHECK(bh_port_pdm_stop() == 0);
      c.Finish();
    }
    const uint32_t requests = fake_aud::counters().requests;
    fake_aud::QueueCompletion(); fake_aud::DispatchPending();
    fake_aud::QueueCompletion(); fake_aud::DispatchPending();
    BH_CHECK(fake_aud::running());
    BH_CHECK(fake_aud::counters().requests == requests);
  }

  BH_CASE("negative witness: raw vendor-style stop/start permits stale completion without any new PCM");
  {
    Fresh();
    uint32_t ring[32] = {};
    audio_config_t cfg = {AUDIO_SR_16KHZ, ring, 4, 32, 1};
    BH_CHECK(hx_lib_audio_register_evt_cb(Probe) == AUDIO_NO_ERROR);
    BH_CHECK(hx_lib_audio_start(&cfg) == AUDIO_NO_ERROR);
    fake_aud::SetIrqState(0xA4u);
    fake_aud::QueueCompletion();
    BH_CHECK(hx_lib_audio_stop() == AUDIO_NO_ERROR);
    BH_CHECK(!fake_aud::running() && fake_aud::pending());
    BH_CHECK(hx_lib_audio_start(&cfg) == AUDIO_NO_ERROR);
    fake_aud::IrqRestore(0xA5u);
    uint32_t addr = 0, blocks = 0;
    BH_CHECK(hx_lib_audio_request_read(&addr, &blocks) == AUDIO_NO_ERROR);
    BH_CHECK(blocks == 1);  // old completion credited to a new run
    BH_CHECK(fake_aud::counters().blocks_completed == 0);  // no new PCM acquired
    BH_CHECK(fake_aud::counters().callbacks == 1);
    fake_aud::Reset();
  }
  return bh_test::Finish("pdm_lifecycle_model_only");
}
