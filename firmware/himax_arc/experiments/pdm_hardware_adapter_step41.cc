#include <cstddef>
#include <cstdint>

extern "C" {
#include "aud_lib.h"
}

extern "C" void birdhouse_queue_reset_v2();
extern "C" int birdhouse_queue_push_v2(
    const int16_t* stereo, uint32_t frames);
extern "C" int birdhouse_queue_overflowed_v2();

namespace {

constexpr uint32_t kBlockBytes = 4096;
constexpr uint32_t kBlocks = 4;
constexpr uint32_t kStereoFrames = 1024;

// DMA buffer: four blocks, 4096 bytes each.
alignas(32) static uint32_t g_dma_buffer[
    kBlocks * kBlockBytes / sizeof(uint32_t)
];

static audio_config_t g_config = {};
static volatile uint32_t g_error = 0;
static volatile uint32_t g_blocks_received = 0;
static bool g_started = false;

// Audio driver callback. Never run FFT or inference here.
void OnAudioBlock(uint32_t status) {
    (void)status;

    // Drain at most the four configured DMA blocks.
    for (uint32_t i = 0; i < kBlocks; ++i) {
        uint32_t address = 0;
        uint32_t available = 0;

        if (hx_lib_audio_request_read(
                &address, &available) != AUDIO_NO_ERROR) {
            g_error = 1;
            break;
        }

        if (available == 0) break;

        if (address == 0) {
            g_error = 2;
            break;
        }

        // Request the next block separately, so a
        // DMA ring-buffer wrap does not require guessing
        // the address of the following block.
        const int16_t* stereo =
            reinterpret_cast<const int16_t*>(
                static_cast<uintptr_t>(address));

        if (!birdhouse_queue_push_v2(
                stereo, kStereoFrames)) {
            g_error = 3;
        }

        uint32_t consumed = 1;

        if (hx_lib_audio_update_idx(
                &consumed) != AUDIO_NO_ERROR) {
            g_error = 4;
            break;
        }

        ++g_blocks_received;
    }
}

}  // namespace

// Must be called from the main program after
// the SDK has initialized the audio peripheral.
// Must not overlap an Edge Impulse audio capture.
extern "C" int birdhouse_pdm_hw_start() {
    if (g_started) return -1;

    birdhouse_queue_reset_v2();
    g_error = 0;
    g_blocks_received = 0;

    g_config.sample_rate = AUDIO_SR_16KHZ;
    g_config.buffer_addr = g_dma_buffer;
    g_config.block_sz = kBlockBytes;
    g_config.block_num = kBlocks;
    g_config.cb_evt_blk = 2;

    if (hx_lib_audio_register_evt_cb(
            OnAudioBlock) != AUDIO_NO_ERROR) {
        return -2;
    }

    if (hx_lib_audio_start(&g_config) != AUDIO_NO_ERROR) {
        return -3;
    }

    g_started = true;
    return 0;
}

// Main program context only; never call from ISR.
extern "C" int birdhouse_pdm_hw_stop() {
    if (!g_started) return -1;

    const AUDIO_ERROR_E result = hx_lib_audio_stop();
    if (result != AUDIO_NO_ERROR) return -2;

    g_started = false;
    return 0;
}

extern "C" uint32_t birdhouse_pdm_hw_error() {
    if (g_error != 0) return g_error;
    return birdhouse_queue_overflowed_v2() ? 5u : 0u;
}

extern "C" uint32_t birdhouse_pdm_hw_blocks() {
    return g_blocks_received;
}
