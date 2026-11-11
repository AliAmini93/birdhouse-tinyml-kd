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
volatile uint32_t g_started = 0;

// Interrupt context.
void OnAudio(uint32_t /*status*/) {
  bh::Capture* capture = g_capture;
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

  g_capture = capture;
  g_config.sample_rate = AUDIO_SR_16KHZ;
  g_config.buffer_addr = g_dma_buffer;
  g_config.block_sz = bh::kDmaBlockBytes;
  g_config.block_num = bh::kDmaBlockCount;
  g_config.cb_evt_blk = bh::kDmaCallbackBlocks;

  if (hx_lib_audio_register_evt_cb(OnAudio) != AUDIO_NO_ERROR) {
    g_capture = nullptr;
    return -2;
  }
  if (hx_lib_audio_start(&g_config) != AUDIO_NO_ERROR) {
    g_capture = nullptr;
    return -3;
  }
  g_started = 1;
  return 0;
}

int bh_port_pdm_stop() {
  if (g_started == 0) return -1;
  const bool ok = hx_lib_audio_stop() == AUDIO_NO_ERROR;
  // Cleared even if the library reports an error, so that a later start is
  // not refused forever. g_capture stays set: a callback that was already
  // pending is then delivered to a capture object that ignores it.
  g_started = 0;
  return ok ? 0 : -2;
}

void bh_port_on_pdm_reinit() {
  bh::Capture* capture = g_capture;
  if (g_started != 0 && capture != nullptr) capture->OnFifoEvent();
}
