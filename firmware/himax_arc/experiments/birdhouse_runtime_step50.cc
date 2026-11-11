#include <cstddef>
#include <cstdint>

#include "firmware/inference/bird_model.h"
#include "streaming_logmel_step29.cc"
#include "edge-impulse-sdk/porting/ei_classifier_porting.h"

extern "C" int birdhouse_pdm_hw_start();
extern "C" int birdhouse_pdm_hw_stop();
extern "C" uint32_t birdhouse_pdm_hw_error();
extern "C" uint32_t birdhouse_pdm_hw_blocks();
extern "C" int birdhouse_queue_pop_v2(int16_t* sample);

namespace {

constexpr size_t kArenaBytes = 160 * 1024;

// Place the experimental model arena in SYSTEM0,
// not in the limited DCCM region.
alignas(16) static uint8_t g_arena[kArenaBytes]
    __attribute__((section(".tensor_arena")));

birdhouse::BirdModel g_model;
birdhouse::StreamingLogMel g_stream;

enum RuntimeState {
    IDLE,
    RECORDING,
    COMPLETED,
    FAILED
};

RuntimeState g_state = IDLE;
bool g_model_initialized = false;
uint32_t g_samples = 0;
uint64_t g_started_ms = 0;

void Fail(const char* message) {
    if (g_state == RECORDING) {
        birdhouse_pdm_hw_stop();
    }

    g_state = FAILED;
    ei_printf("BIRDHOUSE ERROR: %s\n", message);
}

}  // namespace

extern "C" int birdhouse_runtime_start() {
    if (g_state == RECORDING) {
        return -1;
    }

    // Allow a new recording after completion or failure.
    if (g_state == COMPLETED || g_state == FAILED) {
        g_state = IDLE;
    }

    ei_printf("BIRDHOUSE: initializing model\n");

    if (!g_model_initialized) {
        if (!g_model.Init(g_arena, sizeof(g_arena))) {
            Fail("Model Init or AllocateTensors failed");
            return -2;
        }
        g_model_initialized = true;
    }

    if (!g_model.input() ||
        g_model.input_size() <
            static_cast<size_t>(birdhouse::kFeatureElements)) {
        Fail("Invalid model input");
        return -3;
    }

    g_stream.Reset();
    g_samples = 0;

    if (birdhouse_pdm_hw_start() != 0) {
        Fail("PDM start failed");
        return -4;
    }

    g_started_ms = ei_read_timer_ms();
    g_state = RECORDING;

    ei_printf("BIRDHOUSE: recording 5 seconds\n");

    return 0;
}

extern "C" void birdhouse_runtime_poll() {
    if (g_state != RECORDING) {
        return;
    }

    if (birdhouse_pdm_hw_error() != 0) {
        Fail("PDM or audio queue overflow");
        return;
    }

    int16_t pcm = 0;

    // Bounded work per main-loop iteration.
    for (int i = 0; i < 1024; ++i) {
        if (!birdhouse_queue_pop_v2(&pcm)) {
            break;
        }

        g_stream.Push(
            pcm,
            g_model.input(),
            g_model.input_size());

        ++g_samples;

        if (g_samples == birdhouse::kTargetSamples) {
            if (birdhouse_pdm_hw_stop() != 0) {
                Fail("PDM stop failed");
                return;
            }

            if (birdhouse_pdm_hw_error() != 0) {
                Fail("Audio capture error");
                return;
            }

            if (g_stream.FrameCount() !=
                birdhouse::kExpectedFrames) {
                Fail("Incorrect Mel frame count");
                return;
            }

            ei_printf("BIRDHOUSE: running inference\n");

            if (!g_model.Invoke()) {
                Fail("TFLite Micro Invoke failed");
                return;
            }

            ei_printf("BIRDHOUSE: p_bird=");
            ei_printf_float(g_model.p_bird());
            ei_printf("\n");

            ei_printf(
                g_model.is_bird()
                    ? "BIRDHOUSE RESULT: BIRD\n"
                    : "BIRDHOUSE RESULT: NON-BIRD\n");

            g_state = COMPLETED;
            return;
        }
    }

    if (ei_read_timer_ms() - g_started_ms > 15000) {
        Fail("Audio capture timeout");
    }
}

extern "C" uint32_t birdhouse_runtime_samples() {
    return g_samples;
}

extern "C" int birdhouse_runtime_state() {
    return static_cast<int>(g_state);
}

extern "C" size_t birdhouse_runtime_arena_size() {
    return sizeof(g_arena);
}
