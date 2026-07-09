#ifndef BIRDHOUSE_AUDIO_PREPROCESS_H_
#define BIRDHOUSE_AUDIO_PREPROCESS_H_

#include <cstddef>
#include <cstdint>

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

// Reference preprocessing path:
// int16/float PCM -> log-mel -> normalize -> INT8 model input.
// This contains a naive DFT for parity testing. Replace the DFT with an
// optimized FFT backend for real ESP32S3 deployment.
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

