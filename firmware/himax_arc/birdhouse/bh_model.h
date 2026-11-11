// Birdhouse TFLite Micro wrapper for the Himax firmware.
//
// One model instance, explicit status codes for every initialisation stage, and
// accessors the diagnostics need (arena use, raw quantised output). The same
// file is compiled for the ARC target and for the host tests.
#ifndef BIRDHOUSE_HIMAX_BH_MODEL_H_
#define BIRDHOUSE_HIMAX_BH_MODEL_H_

#include <cstddef>
#include <cstdint>

namespace bh {

enum ModelStatus {
  kModelOk = 0,
  kModelBadArgument = 1,       // null model/arena or zero size
  kModelBadFlatbuffer = 2,     // missing "TFL3" identifier or too short
  kModelSchemaVersion = 3,     // schema version differs from the runtime
  kModelAllocateTensors = 4,   // arena too small, missing or disabled operator
  kModelInputTensor = 5,       // wrong type, shape or byte size
  kModelInputQuantization = 6, // scale/zero point differ from the preprocessing
  kModelOutputTensor = 7,
  kModelOutputQuantization = 8,
  kModelNotReady = 9,          // Invoke/accessor used before a successful Init
  kModelInvokeFailed = 10,
};

const char* ModelStatusName(ModelStatus status);

struct ModelInfo {
  size_t arena_size;
  size_t arena_used;      // valid after a successful ModelInit
  size_t input_bytes;
  float input_scale;
  int input_zero_point;
  float output_scale;
  int output_zero_point;
  uint32_t invoke_count;
};

// Builds the interpreter in the given arena. May be called again after a
// failure or to re-create the interpreter; the previous one is destroyed first.
ModelStatus ModelInit(const unsigned char* model_data, size_t model_len,
                      uint8_t* arena, size_t arena_size);
void ModelDeinit();
bool ModelReady();

// Input tensor storage: kFeatureElements int8 values laid out [mel][frame].
// nullptr unless ModelReady().
int8_t* ModelInput();

ModelStatus ModelInvoke();

// Raw quantised output of the last successful Invoke.
int8_t ModelOutputQ();
// (q - zero_point) * scale, in [0, 1).
float ModelPBird();
// p_bird >= kModelBirdThreshold.
bool ModelIsBird();
// Smallest raw output value that is classified as bird; for reports.
int ModelBirdThresholdQ();

const ModelInfo& ModelGetInfo();

}  // namespace bh

#endif  // BIRDHOUSE_HIMAX_BH_MODEL_H_
