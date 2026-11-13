// Host emulation of the prebuilt Himax audio library (aud_lib.h API subset).
//
// The behaviour mirrors what the disassembly of the real library showed:
//   start         resets read/write indices; block addresses are
//                 buffer + i * block_sz (bytes); more than 50 blocks is fatal
//   block done    write index +1 (wraps to 0); if it now equals the read index
//                 the library resets BOTH indices to 0 and reports nothing;
//                 the application callback runs when unread blocks >= cb_evt_blk
//   request_read  address of the block at the read index and the number of
//                 CONTIGUOUS unread blocks (up to the end of the ring only)
//   update_idx    read index += n, set to 0 when it reaches the block count
//   DMA ISR      vendor RX callback re-arms before application delivery;
//                completion acknowledgment follows the callback's return
//   stop          disable/reset does not prove absence of a pending completion
// This is a single-core behavioral model, NOT hardware validation. The unknown
// reset/pending interaction is selectable in tests; neither choice is asserted
// to describe the device. Legacy callback-only injection remains explicitly
// separate from pending DMA completion injection.
#ifndef BIRDHOUSE_HIMAX_TESTS_FAKE_AUD_LIB_H_
#define BIRDHOUSE_HIMAX_TESTS_FAKE_AUD_LIB_H_

#include <cstdint>

extern "C" {

typedef struct audio_config {
  uint32_t sample_rate;
  uint32_t* buffer_addr;
  uint32_t block_num;
  uint32_t block_sz;
  uint32_t cb_evt_blk;
} audio_config_t;

typedef enum AUDIO_ERROR_S {
  AUDIO_NO_ERROR = 0,
  AUDIO_ERROR_NOT_INIT = 1,
  AUDIO_ERROR_DRIVER = 2,
  AUDIO_ERROR_INVALID_PARAMETERS = 4,
} AUDIO_ERROR_E;

typedef enum AUDIO_SR_S { AUDIO_SR_16KHZ = 1 } AUDIO_SR_E;

typedef void (*AUD_ISR_CB)(uint32_t int_status);

AUDIO_ERROR_E hx_lib_audio_register_evt_cb(AUD_ISR_CB aud_evt_cb);
AUDIO_ERROR_E hx_lib_audio_start(audio_config_t* aud_cfg);
AUDIO_ERROR_E hx_lib_audio_stop(void);
AUDIO_ERROR_E hx_lib_audio_request_read(uint32_t* address, uint32_t* block_num);
AUDIO_ERROR_E hx_lib_audio_update_idx(uint32_t* block);

}  // extern "C"

// The real API passes 32-bit addresses; host pointers are 64-bit, so the
// emulation hands out fake addresses relative to the DMA buffer.
uint32_t fake_aud_ptr_to_addr(const void* ptr);
const int16_t* fake_aud_addr_to_ptr(uint32_t addr);

namespace fake_aud {

// Sample generator: value of `channel` (0 = left, 1 = right) at stereo frame
// `frame`, counted from the most recent start.
typedef int16_t (*SampleSource)(uint64_t frame, int channel, void* context);

struct Faults {
  bool fail_register;
  bool fail_start;
  bool fail_stop;
  bool callback_during_stop;
  bool stop_clears_pending;  // alternate hypothesis, default false (unknown on device)
  bool completion_at_start_enable;
  bool start_without_progress;  // API succeeds but no DMA is armed (P3)
  int completion_in_stop;   // 0 none; 1 before disable; 2 after disable; 3 after reset
  int fail_request_read;    // number of upcoming request_read calls that fail
  int fail_update_idx;
  int bad_address;          // number of upcoming request_read calls with a wrong address
  int suppress_callbacks;   // number of upcoming block completions without a callback
                            // (application starvation only; ISR still re-arms)
};

struct Counters {
  uint32_t starts;
  uint32_t requests;
  uint32_t stops;
  uint32_t blocks_completed;
  uint32_t callbacks;
  uint32_t ring_overflows;   // silent index resets inside the "library"
  uint32_t fatal_block_count;
  uint32_t isr_entries;
  uint32_t rearms;
  uint32_t acknowledgments;
  uint32_t irq_before_queue_publication;
  uint32_t sequence;
  uint32_t last_rearm;
  uint32_t last_callback;
  uint32_t last_ack;
};

void Reset();
void SetSource(SampleSource source, void* context);
Faults& faults();
const Counters& counters();
bool running();

// Simulated time, read by bh_port_now_us() in the host port.
uint64_t now_us();
void AdvanceTime(uint64_t us);
// Microseconds of simulated time per completed block (default 64,000).
void SetBlockPeriodUs(uint64_t us);
// The next reading of the clock is off by `delta_us` (models the vendor
// clock's one-tick error). Applies to one reading only.
void GlitchNextClockRead(int64_t delta_us);

// One DMA block completes: fill it from the source, advance the ring, maybe
// call the application callback (as the interrupt would).
void CompleteBlock();
void CompleteBlocks(uint32_t n);
// Legacy application-only callback, WITHOUT the vendor ISR/re-arm/ack path.
void DeliverLateCallback();

// Queue an old/spurious completion without fabricating newly acquired PCM.
// Delivery executes the modeled ISR even after successful vendor stop.
void QueueCompletion();
bool DispatchPending();
bool pending();
// Host IRQ port: save/restore the entire opaque prior state (bit 0 enables IRQ).
uint32_t IrqSave();
void IrqRestore(uint32_t state);
void SetIrqState(uint32_t state);
uint32_t irq_state();

}  // namespace fake_aud

#endif  // BIRDHOUSE_HIMAX_TESTS_FAKE_AUD_LIB_H_
