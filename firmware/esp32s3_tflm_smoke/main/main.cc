#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

#include "esp_log.h"
#include "esp_system.h"

#include "firmware/inference/bird_model.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"

namespace {

constexpr const char* kTag = "birdhouse_smoke";

// Keep tensor arena 16-byte aligned for TFLite Micro.
alignas(16) uint8_t g_tensor_arena[birdhouse::kTensorArenaSizeBytes];

bool OutputMatchesReference(int8_t output_q, bool is_bird) {
  const int diff = std::abs(static_cast<int>(output_q) -
                            static_cast<int>(birdhouse::kReferenceModelOutputInt8));
  const bool decision_match = (is_bird == birdhouse::kReferenceModelOutputIsBird);

  // INT8 output is expected to be exact. We allow one quantized unit to avoid
  // unnecessary failure across different TFLite Micro kernels.
  return diff <= 1 && decision_match;
}

}  // namespace

extern "C" void app_main(void) {
  ESP_LOGI(kTag, "Birdhouse ESP32S3 TFLite Micro smoke test");
  ESP_LOGI(kTag, "Model input elements: %d", birdhouse::kModelInputElements);
  ESP_LOGI(kTag, "Tensor arena bytes: %d", birdhouse::kTensorArenaSizeBytes);
  ESP_LOGI(kTag, "Expected reference output int8: %d",
           static_cast<int>(birdhouse::kReferenceModelOutputInt8));
  ESP_LOGI(kTag, "Expected reference p_bird: %.6f",
           static_cast<double>(birdhouse::kReferenceModelOutputPBird));
  ESP_LOGI(kTag, "Expected reference is_bird: %s",
           birdhouse::kReferenceModelOutputIsBird ? "true" : "false");

  birdhouse::BirdModel model;
  if (!model.Init(g_tensor_arena, sizeof(g_tensor_arena))) {
    ESP_LOGE(kTag, "BirdModel.Init failed");
    return;
  }

  int8_t* input = model.input();
  if (input == nullptr) {
    ESP_LOGE(kTag, "Input tensor pointer is null");
    return;
  }

  std::copy(
      birdhouse::kReferenceInputInt8,
      birdhouse::kReferenceInputInt8 + birdhouse::kModelInputElements,
      input);

  if (!model.Invoke()) {
    ESP_LOGE(kTag, "BirdModel.Invoke failed");
    return;
  }

  const int8_t output_q = model.output_int8();
  const float p_bird = model.p_bird();
  const bool is_bird = model.is_bird();

  ESP_LOGI(kTag, "Output int8: %d", static_cast<int>(output_q));
  ESP_LOGI(kTag, "p_bird: %.6f", static_cast<double>(p_bird));
  ESP_LOGI(kTag, "threshold: %.6f",
           static_cast<double>(birdhouse::kModelBirdThreshold));
  ESP_LOGI(kTag, "is_bird: %s", is_bird ? "true" : "false");

  if (OutputMatchesReference(output_q, is_bird)) {
    ESP_LOGI(kTag, "SMOKE TEST PASS");
  } else {
    ESP_LOGE(kTag, "SMOKE TEST FAIL");
  }
}
