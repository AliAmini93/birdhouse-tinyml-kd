#include "firmware/himax_arc/birdhouse/bh_model.h"

#include <cmath>
#include <cstring>
#include <new>

#include "firmware/model/model_constants.h"

#include "edge-impulse-sdk/tensorflow/lite/c/common.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_interpreter.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "edge-impulse-sdk/tensorflow/lite/schema/schema_generated.h"

namespace bh {
namespace {

// Operators used by the model; must match model_manifest.json.
// tools/himax/verify_tflm_ops.py checks the kernels behind these registrations.
constexpr int kOpCount = 5;

typedef tflite::MicroMutableOpResolver<kOpCount> Resolver;

Resolver* GetResolver() {
  static Resolver resolver;
  static bool populated = false;
  if (!populated) {
    resolver.AddConv2D();
    resolver.AddDepthwiseConv2D();
    resolver.AddMean();
    resolver.AddFullyConnected();
    resolver.AddLogistic();
    populated = true;
  }
  return &resolver;
}

// The interpreter is built in place so that ModelInit can be repeated without
// a heap and without relying on static-initialisation order.
alignas(alignof(tflite::MicroInterpreter))
    unsigned char g_interpreter_storage[sizeof(tflite::MicroInterpreter)];
tflite::MicroInterpreter* g_interpreter = nullptr;
bool g_ready = false;
int8_t g_last_output = 0;
ModelInfo g_info = {};

bool NearlyEqual(float a, float b) {
  const float diff = std::fabs(a - b);
  const float scale = std::fabs(b) > 1e-12f ? std::fabs(b) : 1e-12f;
  return diff <= scale * 1e-5f;
}

void DestroyInterpreter() {
  if (g_interpreter != nullptr) {
    g_interpreter->~MicroInterpreter();
    g_interpreter = nullptr;
  }
  g_ready = false;
}

}  // namespace

const char* ModelStatusName(ModelStatus status) {
  switch (status) {
    case kModelOk: return "OK";
    case kModelBadArgument: return "BAD_ARGUMENT";
    case kModelBadFlatbuffer: return "BAD_FLATBUFFER";
    case kModelSchemaVersion: return "SCHEMA_VERSION";
    case kModelAllocateTensors: return "ALLOCATE_TENSORS";
    case kModelInputTensor: return "INPUT_TENSOR";
    case kModelInputQuantization: return "INPUT_QUANTIZATION";
    case kModelOutputTensor: return "OUTPUT_TENSOR";
    case kModelOutputQuantization: return "OUTPUT_QUANTIZATION";
    case kModelNotReady: return "NOT_READY";
    case kModelInvokeFailed: return "INVOKE_FAILED";
  }
  return "UNKNOWN";
}

ModelStatus ModelInit(const unsigned char* model_data, size_t model_len,
                      uint8_t* arena, size_t arena_size) {
  DestroyInterpreter();
  g_info = ModelInfo();
  g_info.arena_size = arena_size;
  g_last_output = 0;

  if (model_data == nullptr || arena == nullptr || arena_size == 0) {
    return kModelBadArgument;
  }
  // A TFLite flatbuffer carries the file identifier "TFL3" at offset 4.
  if (model_len < 16 || std::memcmp(model_data + 4, "TFL3", 4) != 0) {
    return kModelBadFlatbuffer;
  }

  const tflite::Model* model = tflite::GetModel(model_data);
  if (model == nullptr || model->version() != TFLITE_SCHEMA_VERSION) {
    return kModelSchemaVersion;
  }

  g_interpreter = new (g_interpreter_storage)
      tflite::MicroInterpreter(model, *GetResolver(), arena, arena_size);

  // "true": keep preparing after a failing node so every problem is logged.
  if (g_interpreter->AllocateTensors(true) != kTfLiteOk) {
    DestroyInterpreter();
    return kModelAllocateTensors;
  }

  const TfLiteTensor* in = g_interpreter->input(0);
  if (in == nullptr || in->type != kTfLiteInt8 || in->dims == nullptr ||
      in->dims->size != 4 || in->dims->data[0] != birdhouse::kModelInputBatch ||
      in->dims->data[1] != birdhouse::kModelInputMels ||
      in->dims->data[2] != birdhouse::kModelInputFrames ||
      in->dims->data[3] != birdhouse::kModelInputChannels ||
      in->bytes != static_cast<size_t>(birdhouse::kModelInputElements)) {
    DestroyInterpreter();
    return kModelInputTensor;
  }
  if (!NearlyEqual(in->params.scale, birdhouse::kModelInputScale) ||
      in->params.zero_point != birdhouse::kModelInputZeroPoint) {
    DestroyInterpreter();
    return kModelInputQuantization;
  }

  const TfLiteTensor* out = g_interpreter->output(0);
  if (out == nullptr || out->type != kTfLiteInt8 ||
      out->bytes != static_cast<size_t>(birdhouse::kModelOutputElements)) {
    DestroyInterpreter();
    return kModelOutputTensor;
  }
  if (!NearlyEqual(out->params.scale, birdhouse::kModelOutputScale) ||
      out->params.zero_point != birdhouse::kModelOutputZeroPoint) {
    DestroyInterpreter();
    return kModelOutputQuantization;
  }

  g_info.arena_used = g_interpreter->arena_used_bytes();
  g_info.input_bytes = in->bytes;
  g_info.input_scale = in->params.scale;
  g_info.input_zero_point = in->params.zero_point;
  g_info.output_scale = out->params.scale;
  g_info.output_zero_point = out->params.zero_point;
  g_ready = true;
  return kModelOk;
}

void ModelDeinit() { DestroyInterpreter(); }

bool ModelReady() { return g_ready && g_interpreter != nullptr; }

int8_t* ModelInput() {
  if (!ModelReady()) return nullptr;
  TfLiteTensor* in = g_interpreter->input(0);
  return in == nullptr ? nullptr : in->data.int8;
}

ModelStatus ModelInvoke() {
  if (!ModelReady()) return kModelNotReady;
  if (g_interpreter->Invoke() != kTfLiteOk) return kModelInvokeFailed;
  const TfLiteTensor* out = g_interpreter->output(0);
  if (out == nullptr || out->data.int8 == nullptr) return kModelInvokeFailed;
  g_last_output = out->data.int8[0];
  ++g_info.invoke_count;
  return kModelOk;
}

int8_t ModelOutputQ() { return g_last_output; }

float ModelPBird() {
  return static_cast<float>(static_cast<int>(g_last_output) -
                            birdhouse::kModelOutputZeroPoint) *
         birdhouse::kModelOutputScale;
}

bool ModelIsBird() { return ModelPBird() >= birdhouse::kModelBirdThreshold; }

int ModelBirdThresholdQ() {
  for (int q = -128; q <= 127; ++q) {
    const float p = static_cast<float>(q - birdhouse::kModelOutputZeroPoint) *
                    birdhouse::kModelOutputScale;
    if (p >= birdhouse::kModelBirdThreshold) return q;
  }
  return 128;  // no representable output reaches the threshold
}

const ModelInfo& ModelGetInfo() { return g_info; }

}  // namespace bh
