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
constexpr uint32_t kBlockCount = 4;
constexpr uint32_t kFramesPerBlock = 1024;

static_assert(
    kBlockBytes == kFramesPerBlock * 2 * sizeof(int16_t),
    "Unexpected PCM block layout"
);

alignas(32) static uint32_t g_dma_buffer[
    kBlockCount * kBlockBytes / sizeof(uint32_t)
];

static audio_config_t g_config = {};

static volatile uint32_t g_error = 0;
static volatile uint32_t g_blocks_received = 0;
static bool g_started = false;

void OnAudioBlock(uint32_t status) {
    (void)status;

    uint32_t first_address = 0;
    uint32_t available = 0;

    if (hx_lib_audio_request_read(
            &first_address, &available) != AUDIO_NO_ERROR) {
        g_error = 1;
        return;
    }

    if (available == 0) return;

    if (available > kBlockCount) {
        g_error = 2;
        return;
    }

    const uintptr_t base =
        reinterpret_cast<uintptr_t>(g_dma_buffer);

    const uintptr_t first =
        static_cast<uintptr_t>(first_address);

    const uintptr_t bytes = sizeof(g_dma_buffer);

    if (first < base ||
        first >= base + bytes ||
        (first - base) % kBlockBytes != 0) {
        g_error = 3;
        return;
    }

    const uint32_t first_index =
        static_cast<uint32_t>(
            (first - base) / kBlockBytes);

    for (uint32_t block = 0;
         block < available;
         ++block) {

        const uint32_t index =
            (first_index + block) % kBlockCount;

        const int16_t* stereo =
            reinterpret_cast<const int16_t*>(
                &g_dma_buffer[
                    index *
                    (kBlockBytes / sizeof(uint32_t))
                ]
            );

        if (g_error == 0) {
            if (!birdhouse_queue_push_v2(
                    stereo, kFramesPerBlock)) {
                g_error = 4;
            }
        }

        ++g_blocks_received;
    }

    // Same request/update pattern as reference SDK.
    uint32_t consumed = available;

    if (hx_lib_audio_update_idx(
            &consumed) != AUDIO_NO_ERROR) {
        g_error = 5;
    }
}

}  // namespace

// Requires prior ei_microphone_init() from SDK.
// Do not run simultaneously with EI audio inference.
extern "C" int birdhouse_pdm_hw_start() {
    if (g_started) return -1;

    birdhouse_queue_reset_v2();

    g_error = 0;
    g_blocks_received = 0;

    g_config.sample_rate = AUDIO_SR_16KHZ;
    g_config.buffer_addr = g_dma_buffer;
    g_config.block_sz = kBlockBytes;
    g_config.block_num = kBlockCount;
    g_config.cb_evt_blk = 2;

    if (hx_lib_audio_register_evt_cb(
            OnAudioBlock) != AUDIO_NO_ERROR) {
        return -2;
    }

    if (hx_lib_audio_start(
            &g_config) != AUDIO_NO_ERROR) {
        return -3;
    }

    g_started = true;
    return 0;
}

extern "C" int birdhouse_pdm_hw_stop() {
    if (!g_started) return -1;

    if (hx_lib_audio_stop() != AUDIO_NO_ERROR) {
        return -2;
    }

    g_started = false;
    return 0;
}

extern "C" uint32_t birdhouse_pdm_hw_error() {
    if (g_error != 0) return g_error;

    return birdhouse_queue_overflowed_v2()
        ? 6u
        : 0u;
}

extern "C" uint32_t birdhouse_pdm_hw_blocks() {
    return g_blocks_received;
}
