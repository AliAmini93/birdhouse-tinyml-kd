// Adapter between the prebuilt Himax audio library and bh::Capture.
//
// Library behaviour this code relies on (established by disassembly of the
// library in the linked firmware; see docs/research/.../CLAUDE_RESEARCH_REPORT.md):
//   * The registered callback runs inside the DMA-complete interrupt, after the
//     library has already re-armed the next block.
//   * request_read returns the address of the oldest unread block and the
//     number of *contiguous* unread blocks (never across the ring end).
//   * update_idx advances the read index and wraps it to 0.
//   * block_sz is in bytes; blocks are laid out contiguously in the buffer.
//   * If the application does not consume, the library silently resets both
//     ring indices. If the PDM FIFO overflows, it silently re-initialises the
//     driver. Neither is reported; see bh_port_on_pdm_reinit and the interval
//     statistics in bh_capture.
//
// The same file is compiled for the host tests against an emulation of the
// library (firmware/himax_arc/tests/fake_aud_lib.*).
#include <cstddef>
#include <cstdint>

#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_pdm_diag.h"

#if defined(BIRDHOUSE_HOST_BUILD)
#include "firmware/himax_arc/tests/fake_aud_lib.h"
#define BH_DMA_ADDR(ptr) fake_aud_ptr_to_addr(ptr)
#define BH_DMA_PTR(addr) fake_aud_addr_to_ptr(addr)
#else
extern "C" {
#include "aud_lib.h"
}
#define BH_DMA_ADDR(ptr) static_cast<uint32_t>(reinterpret_cast<uintptr_t>(ptr))
#define BH_DMA_PTR(addr) reinterpret_cast<const int16_t*>(static_cast<uintptr_t>(addr))
#endif

namespace {

static_assert(bh::kDmaBlockCount <= 50, "the audio library halts the CPU above 50 blocks");
static_assert(bh::kDmaBlockBytes % 4 == 0 && bh::kDmaBlockBytes <= 8192,
              "block size must be whole stereo frames and at most 8 KiB");
static_assert(bh::kDmaCallbackBlocks >= 1 && bh::kDmaCallbackBlocks < bh::kDmaBlockCount,
              "callback threshold must leave room in the ring");

// Written by the DMA engine; read by OnAudio() in interrupt context.
alignas(32) uint32_t g_dma_buffer[bh::kDmaBlockCount * bh::kDmaBlockBytes / sizeof(uint32_t)];
audio_config_t g_config;

bh::Capture* volatile g_capture = nullptr;
// 0 = no transfer attempted, 1 = active/starting, 2 = permanently quarantined.
// Vendor stop/reset has no established pending-IRQ contract. There is no
// production transition from quarantine to unused, even after a stop retry.
volatile uint32_t g_started = 0;
volatile uint32_t g_late_callbacks = 0;

BhPdmDiagReport g_diag = {};
// Main-only shadow; never written to DMA memory or exposed as audio.
uint32_t g_diag_shadow[bh::kDmaBlockCount * bh::kDmaBlockBytes / sizeof(uint32_t)];
volatile uint32_t g_diag_phase = 0;  // 0 off, 1 armed, 2 stop call, 3 after return
volatile uint32_t g_diag_enables = 0;
volatile uint32_t g_diag_post_enable = 0;
volatile uint32_t g_diag_during_enable = 0;

void DiagRow(uint32_t phase, uint32_t elapsed, uint32_t changes) {
  BhPdmDiagRow& r = g_diag.row[g_diag.rows++];
  r.phase = phase;
  r.elapsed_us = elapsed;
  r.dma = bh_port_pdm_diag_read_status();
  r.late_callbacks = g_late_callbacks;
  r.enable_attempts = g_diag_enables;
  r.changed_words = changes;
}

void DiagObserve(int rc) {
  // Owner was already detached, P1 latched and vendor stop returned. No new
  // IRQ exclusion, vendor call, retry, DMA write, print or dynamic allocation.
  g_diag_phase = 3;
  g_diag.stop_rc = rc;
  const uint64_t start = bh_port_now_us();
  DiagRow(1, 0, 0);  // hardware reads precede the first buffer scan
  for (uint32_t i = 0; i < sizeof(g_diag_shadow) / sizeof(uint32_t); ++i)
    g_diag_shadow[i] = bh_port_pdm_diag_read_word(&g_dma_buffer[i]);
  uint64_t previous = start;
  uint32_t previous_sample = 0;
  uint32_t samples = 0;
  for (uint32_t polls = 0; polls < kBhPdmDiagPollBudget; ++polls) {
    const uint64_t now = bh_port_now_us();
    // Existing BSP clock can jump by one second. Never use that to pass early.
    if (now < previous || now - previous > 2 * kBhPdmDiagStepUs) {
      g_diag.clock_invalid = true;
      break;
    }
    previous = now;
    const uint64_t elapsed = now - start;
    if (elapsed < (samples + 1) * kBhPdmDiagStepUs) continue;
    uint32_t changes = 0;
    for (uint32_t i = 0; i < sizeof(g_diag_shadow) / sizeof(uint32_t); ++i) {
      const uint32_t word = bh_port_pdm_diag_read_word(&g_dma_buffer[i]);
      if (word != g_diag_shadow[i]) ++changes;
      g_diag_shadow[i] = word;
    }
    const uint32_t us = static_cast<uint32_t>(elapsed);
    const uint32_t gap = us - previous_sample;
    if (gap > g_diag.max_gap_us) g_diag.max_gap_us = gap;
    previous_sample = us;
    DiagRow(2, us, changes);
    if (++samples == kBhPdmDiagSamples) {
      g_diag.window_complete = true;
      break;
    }
  }
  g_diag.budget_exhausted = !g_diag.window_complete && !g_diag.clock_invalid;
  g_diag.post_enable_attempt = g_diag_post_enable;
  g_diag.during_stop_enable_attempt = g_diag_during_enable;
  bool observable = rc == 0 && g_diag.window_complete && !g_diag.clock_invalid &&
                    g_diag.max_gap_us <= 2 * kBhPdmDiagStepUs;
  bool activity = g_diag_post_enable != 0;
  const BhPdmDiagRow& first = g_diag.row[1];
  for (uint32_t i = 1; i < g_diag.rows; ++i) {
    const BhPdmDiagRow& r = g_diag.row[i];
    observable = observable && r.dma.valid == kBhPdmDiagValid && !r.dma.error;
    activity = activity || ((r.dma.valid & 1u) && r.dma.busy) ||
               ((r.dma.valid & 8u) && r.dma.irq) || r.changed_words != 0 ||
               r.late_callbacks != first.late_callbacks ||
               ((r.dma.valid & first.dma.valid & 2u) &&
                !first.dma.complete && r.dma.complete);
  }
  g_diag.verdict = activity ? kBhDmaObservedFail :
      observable ? kBhDmaObservedPass : kBhDmaInconclusive;
  g_diag.finished = true;
}

// Interrupt context.
void OnAudio(uint32_t /*status*/) {
  bh::Capture* capture = g_capture;
  // Detachment precedes stop(), including a failing stop. Do not even access
  // the library ring after detachment: it may belong to a different client.
  if (capture == nullptr) {
    if (g_late_callbacks != 0xFFFFFFFFu) ++g_late_callbacks;
    return;
  }
  uint32_t address = 0;
  uint32_t blocks = 0;
  if (hx_lib_audio_request_read(&address, &blocks) != AUDIO_NO_ERROR) {
    if (capture != nullptr) capture->Fail(bh::kCapLibraryError);
    return;
  }
  if (blocks == 0) return;

  const uint32_t base = BH_DMA_ADDR(g_dma_buffer);
  const uint32_t offset = address - base;
  const bool valid = address >= base && blocks <= bh::kDmaBlockCount &&
                     offset % bh::kDmaBlockBytes == 0 &&
                     offset / bh::kDmaBlockBytes + blocks <= bh::kDmaBlockCount;
  if (capture != nullptr) {
    if (valid) {
      capture->OnBlocks(BH_DMA_PTR(address), blocks, bh_port_now_us());
    } else {
      capture->Fail(bh::kCapBadBlock);
    }
  }
  // Always hand the blocks back, even on error, so the library's ring stays
  // consistent and it does not start printing overflow messages.
  uint32_t consumed = blocks <= bh::kDmaBlockCount ? blocks : bh::kDmaBlockCount;
  if (hx_lib_audio_update_idx(&consumed) != AUDIO_NO_ERROR && capture != nullptr) {
    capture->Fail(bh::kCapLibraryError);
  }
}

}  // namespace

// Requires the vendor's ei_microphone_init() (PDM interface selected and the
// audio library initialised), which the vendor application calls at boot.
int bh_port_pdm_start(bh::Capture* capture) {
  if (capture == nullptr) return -4;
  if (g_started != 0) return -1;

  g_config.sample_rate = AUDIO_SR_16KHZ;
  g_config.buffer_addr = g_dma_buffer;
  g_config.block_sz = bh::kDmaBlockBytes;
  g_config.block_num = bh::kDmaBlockCount;
  g_config.cb_evt_blk = bh::kDmaCallbackBlocks;

  if (hx_lib_audio_register_evt_cb(OnAudio) != AUDIO_NO_ERROR) {
    return -2;
  }
  const uint32_t irq = bh_port_irq_save();
  g_started = 1;
  // Keep IRQs masked: vendor DMA enable precedes its queue-count publication.
  // Resetting indices does NOT establish a clean boundary for an old IRQ.
  // A subsequent run is forbidden, including after partial-start cleanup.
  const bool ok = hx_lib_audio_start(&g_config) == AUDIO_NO_ERROR;
  if (ok) g_capture = capture;
  bh_port_irq_restore(irq);
  if (!ok) {
    // A failed start can have enabled part of the driver. Stop explicitly;
    // permanently quarantine, regardless of the cleanup API's return value.
    bh_port_pdm_stop();
    return -3;
  }
  return 0;
}

int bh_port_pdm_stop() {
  if (g_started == 0) return -1;
  const uint32_t irq = bh_port_irq_save();
  g_capture = nullptr;
  g_started = 2;
  bh_port_irq_restore(irq);
  const bool observe = g_diag.armed && !g_diag.finished;
  if (observe) {
    DiagRow(0, 0, 0);
    g_diag_phase = 2;
  }
  const bool ok = hx_lib_audio_stop() == AUDIO_NO_ERROR;
  if (observe) DiagObserve(ok ? 0 : -2);
  // The return value describes the API only. A pending completion can still
  // re-arm DMA; neither success nor a retry proves physical quiescence.
  return ok ? 0 : -2;
}

uint32_t bh_port_pdm_late_callbacks() { return g_late_callbacks; }
bool bh_port_pdm_faulted() { return g_started == 2; }

int bh_port_pdm_diag_arm() {
  if (g_started != 0 || g_diag.armed) return -1;
  g_diag.armed = true;
  g_diag_phase = 1;
  return 0;
}

const BhPdmDiagReport& bh_port_pdm_diag_report() { return g_diag; }

void bh_port_pdm_diag_enable_event(uint32_t mask, int enable) {
  if (g_diag_phase == 0 || !(mask & kBhPdmDmaMask) || enable != 1) return;
  if (g_diag_enables != 0xFFFFFFFFu) ++g_diag_enables;
  // Idempotent latches cannot lose evidence under a nested enable attempt.
  if (g_diag_phase == 2) g_diag_during_enable = 1;
  if (g_diag_phase == 3) g_diag_post_enable = 1;
}

void bh_port_pdm_diag_print() {
  const char* result = !g_diag.finished ? "NOT_FINISHED" :
      g_diag.verdict == kBhDmaObservedFail ? "FAIL" :
      g_diag.verdict == kBhDmaObservedPass ? "PASS_SAMPLED_ONLY" : "INCONCLUSIVE";
  bh_port_printf("BIRDHOUSE DMA armed=%u finished=%u result=%s window=%u clock_bad=%u budget=%u gap_us=%lu stop_rc=%d post_enable=%lu during_enable=%lu\n",
      g_diag.armed ? 1u : 0u, g_diag.finished ? 1u : 0u, result,
      g_diag.window_complete ? 1u : 0u, g_diag.clock_invalid ? 1u : 0u,
      g_diag.budget_exhausted ? 1u : 0u, static_cast<unsigned long>(g_diag.max_gap_us),
      g_diag.stop_rc, static_cast<unsigned long>(g_diag.post_enable_attempt),
      static_cast<unsigned long>(g_diag.during_stop_enable_attempt));
  bh_port_printf("BIRDHOUSE DMA enabled=UNOBSERVABLE cpu_irq_pending=UNOBSERVABLE bus_drain=UNOBSERVABLE same_value_writes=UNOBSERVABLE full_quiescence=UNOBSERVABLE\n");
  for (uint32_t i = 0; i < g_diag.rows; ++i) {
    const BhPdmDiagRow& r = g_diag.row[i];
    bh_port_printf("BIRDHOUSE DMA row=%lu phase=%lu us=%lu valid=%lu busy=%lu complete=%lu error=%lu irq=%lu late=%lu enables=%lu changed_words=%lu\n",
        static_cast<unsigned long>(i), static_cast<unsigned long>(r.phase),
        static_cast<unsigned long>(r.elapsed_us), static_cast<unsigned long>(r.dma.valid),
        static_cast<unsigned long>(r.dma.busy), static_cast<unsigned long>(r.dma.complete),
        static_cast<unsigned long>(r.dma.error), static_cast<unsigned long>(r.dma.irq),
        static_cast<unsigned long>(r.late_callbacks), static_cast<unsigned long>(r.enable_attempts),
        static_cast<unsigned long>(r.changed_words));
  }
}

void bh_port_on_pdm_reinit() {
  bh::Capture* capture = g_capture;
  if (g_started != 0 && capture != nullptr) capture->OnFifoEvent();
}

#if defined(BIRDHOUSE_HOST_BUILD)
// Test process isolation only. Never linked into production firmware. The fake
// driver reset is deliberately separate, so it cannot silently reopen starts.
void bh_port_pdm_test_reset() {
  g_capture = nullptr;
  g_started = 0;
  g_late_callbacks = 0;
  g_diag = BhPdmDiagReport();
  g_diag_phase = g_diag_enables = g_diag_post_enable = g_diag_during_enable = 0;
}
#endif
