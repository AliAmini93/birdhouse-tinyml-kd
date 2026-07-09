#include "firmware/inference/bird_model.h"

#include "firmware/model/model_constants.h"
#include "firmware/model/student_final_int8_model_data.h"

#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace birdhouse {
namespace {

constexpr int kOpResolverSize = 12;

tflite::MicroMutableOpResolver<kOpResolverSize>* CreateResolver() {
  static tflite::MicroMutableOpResolver<kOpResolverSize> resolver;

  static bool initialized = false;
  if (!initialized) {
    resolver.AddConv2D();
    resolver.AddDepthwiseConv2D();
    resolver.AddFullyConnected();
    resolver.AddMean();
    resolver.AddLogistic();
    resolver.AddReshape();
    resolver.AddQuantize();
    resolver.AddDequantize();
    resolver.AddAveragePool2D();
    resolver.AddMaxPool2D();
    resolver.AddAdd();
    resolver.AddMul();
    initialized = true;
  }

  return &resolver;
}

}  // namespace

BirdModel::BirdModel()
    : initialized_(false), interpreter_(nullptr), model_(nullptr) {}

bool BirdModel::Init(uint8_t* tensor_arena, size_t tensor_arena_size) {
  if (tensor_arena == nullptr || tensor_arena_size == 0) {
    return false;
  }

  const tflite::Model* model =
      tflite::GetModel(g_student_final_int8_model_data);
  if (model == nullptr) {
    return false;
  }

  model_ = const_cast<tflite::Model*>(model);

  static tflite::MicroInterpreter static_interpreter(
      model,
      *CreateResolver(),
      tensor_arena,
      tensor_arena_size);

  interpreter_ = &static_interpreter;

  if (interpreter_->AllocateTensors() != kTfLiteOk) {
    initialized_ = false;
    return false;
  }

  TfLiteTensor* in = interpreter_->input(0);
  if (in == nullptr || in->type != kTfLiteInt8) {
    initialized_ = false;
    return false;
  }

  if (in->bytes < static_cast<size_t>(kModelInputElements)) {
    initialized_ = false;
    return false;
  }

  TfLiteTensor* out = interpreter_->output(0);
  if (out == nullptr || out->type != kTfLiteInt8) {
    initialized_ = false;
    return false;
  }

  initialized_ = true;
  return true;
}

int8_t* BirdModel::input() {
  if (!initialized_ || interpreter_ == nullptr) {
    return nullptr;
  }
  TfLiteTensor* in = interpreter_->input(0);
  return in == nullptr ? nullptr : in->data.int8;
}

size_t BirdModel::input_size() const {
  return static_cast<size_t>(kModelInputElements);
}

bool BirdModel::Invoke() {
  if (!initialized_ || interpreter_ == nullptr) {
    return false;
  }
  return interpreter_->Invoke() == kTfLiteOk;
}

int8_t BirdModel::output_int8() const {
  if (!initialized_ || interpreter_ == nullptr) {
    return 0;
  }
  const TfLiteTensor* out = interpreter_->output(0);
  if (out == nullptr || out->data.int8 == nullptr) {
    return 0;
  }
  return out->data.int8[0];
}

float BirdModel::p_bird() const {
  return (static_cast<int>(output_int8()) - kModelOutputZeroPoint) *
         kModelOutputScale;
}

bool BirdModel::is_bird() const {
  return p_bird() >= kModelBirdThreshold;
}

}  // namespace birdhouse
