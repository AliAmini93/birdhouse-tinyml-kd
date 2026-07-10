#ifndef BIRDHOUSE_AUDIO_PREPROCESS_H_
#define BIRDHOUSE_AUDIO_PREPROCESS_H_

#include <cstddef>
#include <cstdint>

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

// Initializes the FFT backend. Safe to call more than once.
// On ESP32S3 this initializes ESP-DSP. On desktop tests it initializes the
// portable radix-2 fallback.
bool InitializeAudioPreprocessor();

// Returns a short backend identifier for logs and reports.
const char* AudioPreprocessBackendName();

// Scratch memory owned by the preprocessing implementation. This excludes the
// caller-owned PCM buffer and output feature tensor.
size_t AudioPreprocessScratchBytes();

// Memory-safe preprocessing path:
// int16/float PCM -> 512-point FFT -> power spectrum -> log-mel
// -> normalization -> INT8 model input.
//
// The implementation processes one frame at a time and does not create a full
// 80,000-sample float copy. These functions are not re-entrant because they
// reuse a single static FFT workspace.
bool PreprocessInt16PcmToInt8ModelInput(
    const int16_t* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len);

bool PreprocessFloatPcmToInt8ModelInput(
    const float* pcm,
    size_t num_samples,
    int8_t* output,
    size_t output_len);

float DequantizeBirdProbability(int8_t output_value);
bool IsBirdFromQuantizedOutput(int8_t output_value);

}  // namespace birdhouse

#endif  // BIRDHOUSE_AUDIO_PREPROCESS_H_
