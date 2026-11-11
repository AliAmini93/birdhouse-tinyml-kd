#include "firmware/himax_arc/tests/fake_aud_lib.h"

#include <cstring>

namespace {

const uint32_t kFakeBase = 0x80000000u;
const uint32_t kMaxBlocks = 50;

struct State {
  AUD_ISR_CB callback;
  audio_config_t config;
  bool running;
  uint32_t read_idx;
  uint32_t write_idx;
  uint64_t frame;  // stereo frames produced since start
  fake_aud::SampleSource source;
  void* source_context;
  fake_aud::Faults faults;
  fake_aud::Counters counters;
  uint64_t now_us;
  uint64_t block_period_us;
  int64_t clock_glitch_us;
  bool clock_glitch_armed;
};

State g;

uint32_t Unread() {
  return g.write_idx >= g.read_idx ? g.write_idx - g.read_idx
                                   : g.write_idx + g.config.block_num - g.read_idx;
}

int16_t DefaultSource(uint64_t frame, int channel, void*) {
  return static_cast<int16_t>(channel == 0 ? (frame * 7 + 1) % 20011 - 10005 : -4321);
}

}  // namespace

uint32_t fake_aud_ptr_to_addr(const void* ptr) {
  const uint8_t* base = reinterpret_cast<const uint8_t*>(g.config.buffer_addr);
  if (base == nullptr) return kFakeBase;
  return kFakeBase + static_cast<uint32_t>(static_cast<const uint8_t*>(ptr) - base);
}

const int16_t* fake_aud_addr_to_ptr(uint32_t addr) {
  const uint8_t* base = reinterpret_cast<const uint8_t*>(g.config.buffer_addr);
  return reinterpret_cast<const int16_t*>(base + (addr - kFakeBase));
}

extern "C" AUDIO_ERROR_E hx_lib_audio_register_evt_cb(AUD_ISR_CB cb) {
  if (g.faults.fail_register) return AUDIO_ERROR_DRIVER;
  if (cb != nullptr) g.callback = cb;  // the real library ignores a null pointer
  return AUDIO_NO_ERROR;
}

extern "C" AUDIO_ERROR_E hx_lib_audio_start(audio_config_t* cfg) {
  if (cfg->block_num > kMaxBlocks) {
    ++g.counters.fatal_block_count;  // the real library halts the CPU here
    return AUDIO_ERROR_INVALID_PARAMETERS;
  }
  g.config = *cfg;
  g.read_idx = 0;
  g.write_idx = 0;
  g.frame = 0;
  g.running = true;
  ++g.counters.starts;
  return g.faults.fail_start ? AUDIO_ERROR_DRIVER : AUDIO_NO_ERROR;
}

extern "C" AUDIO_ERROR_E hx_lib_audio_stop(void) {
  ++g.counters.stops;
  if (g.faults.callback_during_stop && g.callback != nullptr) g.callback(0);
  if (!g.faults.fail_stop) g.running = false;
  return g.faults.fail_stop ? AUDIO_ERROR_NOT_INIT : AUDIO_NO_ERROR;
}

extern "C" AUDIO_ERROR_E hx_lib_audio_request_read(uint32_t* address, uint32_t* block_num) {
  ++g.counters.requests;
  if (g.faults.fail_request_read > 0) {
    --g.faults.fail_request_read;
    return AUDIO_ERROR_DRIVER;
  }
  const uint32_t contiguous = g.write_idx >= g.read_idx ? g.write_idx - g.read_idx
                                                        : g.config.block_num - g.read_idx;
  *block_num = contiguous;
  *address = kFakeBase + g.read_idx * g.config.block_sz;
  if (g.faults.bad_address > 0) {
    --g.faults.bad_address;
    *address += 2;  // not on a block boundary
  }
  return AUDIO_NO_ERROR;
}

extern "C" AUDIO_ERROR_E hx_lib_audio_update_idx(uint32_t* block) {
  if (g.faults.fail_update_idx > 0) {
    --g.faults.fail_update_idx;
    return AUDIO_ERROR_DRIVER;
  }
  g.read_idx += *block;
  if (g.read_idx >= g.config.block_num) g.read_idx = 0;
  return AUDIO_NO_ERROR;
}

namespace fake_aud {

void Reset() {
  std::memset(&g, 0, sizeof(g));
  g.source = DefaultSource;
  g.block_period_us = 64000;
  g.now_us = 1000000;  // arbitrary non-zero start
}

void SetSource(SampleSource source, void* context) {
  g.source = source != nullptr ? source : DefaultSource;
  g.source_context = context;
}

Faults& faults() { return g.faults; }
const Counters& counters() { return g.counters; }
bool running() { return g.running; }

uint64_t now_us() {
  if (g.clock_glitch_armed) {
    g.clock_glitch_armed = false;
    return static_cast<uint64_t>(static_cast<int64_t>(g.now_us) + g.clock_glitch_us);
  }
  return g.now_us;
}

void AdvanceTime(uint64_t us) { g.now_us += us; }
void SetBlockPeriodUs(uint64_t us) { g.block_period_us = us; }

void GlitchNextClockRead(int64_t delta_us) {
  g.clock_glitch_us = delta_us;
  g.clock_glitch_armed = true;
}

void CompleteBlock() {
  if (!g.running) return;
  g.now_us += g.block_period_us;

  // The DMA engine has filled the block at the write index.
  const uint32_t frames = g.config.block_sz / 4;
  int16_t* dst = reinterpret_cast<int16_t*>(
      reinterpret_cast<uint8_t*>(g.config.buffer_addr) + g.write_idx * g.config.block_sz);
  for (uint32_t i = 0; i < frames; ++i) {
    dst[2 * i] = g.source(g.frame + i, 0, g.source_context);
    dst[2 * i + 1] = g.source(g.frame + i, 1, g.source_context);
  }
  g.frame += frames;
  ++g.counters.blocks_completed;

  // Interrupt handler of the real library.
  g.write_idx += 1;
  if (g.write_idx == g.config.block_num) g.write_idx = 0;
  if (g.write_idx == g.read_idx) {
    ++g.counters.ring_overflows;  // "aud_rbf_of": both indices reset, nothing reported
    g.write_idx = 0;
    g.read_idx = 0;
  }
  if (g.faults.suppress_callbacks > 0) {
    --g.faults.suppress_callbacks;
    return;
  }
  if (Unread() >= g.config.cb_evt_blk && g.callback != nullptr) {
    ++g.counters.callbacks;
    g.callback(0);
  }
}

void CompleteBlocks(uint32_t n) {
  for (uint32_t i = 0; i < n; ++i) CompleteBlock();
}

void DeliverLateCallback() {
  if (g.callback != nullptr) {
    ++g.counters.callbacks;
    g.callback(0);
  }
}

}  // namespace fake_aud
