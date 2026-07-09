#include <algorithm>
#include <cmath>
#include <cstdint>

#include "esp_log.h"

#include "firmware/inference/bird_model.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/preprocess/audio_preprocess.h"
#include "firmware/preprocess/preprocess_constants.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"
#include "firmware/preprocess/testdata/reference_pcm_float32.h"

namespace {

constexpr const char* kTag = "birdhouse_pipe";

alignas(16) uint8_t g_tensor_arena[birdhouse::kTensorArenaSizeBytes];
int8_t g_generated_input[birdhouse::kFeatureElements];

struct ParityStats {
  int exact = 0;
  int within_1 = 0;
  int within_2 = 0;
  int max_abs = 0;
  int max_index = 0;
  long long sum_abs = 0;
};

ParityStats CompareGeneratedInput() {
  ParityStats stats;

  for (int i = 0; i < birdhouse::kFeatureElements; ++i) {
    const int diff = static_cast<int>(g_generated_input[i]) -
                     static_cast<int>(birdhouse::kReferenceInputInt8[i]);
    const int ad = std::abs(diff);
    if (ad == 0) ++stats.exact;
    if (ad <= 1) ++stats.within_1;
    if (ad <= 2) ++stats.within_2;
    if (ad > stats.max_abs) {
      stats.max_abs = ad;
      stats.max_index = i;
    }
    stats.sum_abs += ad;
  }

  return stats;
}

bool InputParityPass(const ParityStats& stats) {
  const float n = static_cast<float>(birdhouse::kFeatureElements);
  const float within_2_pct = 100.0f * static_cast<float>(stats.within_2) / n;
  const float mean_abs = static_cast<float>(stats.sum_abs) / n;
  return mean_abs <= 2.0f && within_2_pct >= 95.0f;
}

bool OutputMatchesReference(int8_t output_q, bool is_bird) {
  const int diff = std::abs(static_cast<int>(output_q) -
                            static_cast<int>(birdhouse::kReferenceModelOutputInt8));
  const bool decision_match = (is_bird == birdhouse::kReferenceModelOutputIsBird);
  return diff <= 1 && decision_match;
}

}  // namespace

extern "C" void app_main(void) {
  ESP_LOGI(kTag, "Birdhouse ESP32S3 preprocessing-to-inference integration test");
  ESP_LOGI(kTag, "Reference PCM samples: %u",
           static_cast<unsigned>(birdhouse::kReferencePcmFloat32Length));
  ESP_LOGI(kTag, "Feature elements: %d", birdhouse::kFeatureElements);
  ESP_LOGI(kTag, "Tensor arena bytes: %d", birdhouse::kTensorArenaSizeBytes);

  ESP_LOGI(kTag, "Running embedded preprocessing reference path...");
  const bool preprocess_ok = birdhouse::PreprocessFloatPcmToInt8ModelInput(
      birdhouse::kReferencePcmFloat32,
      birdhouse::kReferencePcmFloat32Length,
      g_generated_input,
      birdhouse::kFeatureElements);

  if (!preprocess_ok) {
    ESP_LOGE(kTag, "Preprocessing failed");
    return;
  }

  const ParityStats stats = CompareGeneratedInput();
  const float n = static_cast<float>(birdhouse::kFeatureElements);
  const float exact_pct = 100.0f * static_cast<float>(stats.exact) / n;
  const float within_1_pct = 100.0f * static_cast<float>(stats.within_1) / n;
  const float within_2_pct = 100.0f * static_cast<float>(stats.within_2) / n;
  const float mean_abs = static_cast<float>(stats.sum_abs) / n;

  ESP_LOGI(kTag, "Input parity exact_match_pct: %.4f", static_cast<double>(exact_pct));
  ESP_LOGI(kTag, "Input parity within_1_pct: %.4f", static_cast<double>(within_1_pct));
  ESP_LOGI(kTag, "Input parity within_2_pct: %.4f", static_cast<double>(within_2_pct));
  ESP_LOGI(kTag, "Input parity mean_abs_diff_int8: %.6f", static_cast<double>(mean_abs));
  ESP_LOGI(kTag, "Input parity max_abs_diff_int8: %d", stats.max_abs);
  ESP_LOGI(kTag, "Input parity max_diff_index: %d", stats.max_index);

  if (!InputParityPass(stats)) {
    ESP_LOGE(kTag, "INPUT PARITY FAIL");
    return;
  }

  ESP_LOGI(kTag, "INPUT PARITY PASS");

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

  std::copy(g_generated_input, g_generated_input + birdhouse::kFeatureElements, input);

  if (!model.Invoke()) {
    ESP_LOGE(kTag, "BirdModel.Invoke failed");
    return;
  }

  const int8_t output_q = model.output_int8();
  const float p_bird = model.p_bird();
  const bool is_bird = model.is_bird();

  ESP_LOGI(kTag, "Output int8: %d", static_cast<int>(output_q));
  ESP_LOGI(kTag, "p_bird: %.6f", static_cast<double>(p_bird));
  ESP_LOGI(kTag, "threshold: %.6f", static_cast<double>(birdhouse::kModelBirdThreshold));
  ESP_LOGI(kTag, "is_bird: %s", is_bird ? "true" : "false");

  ESP_LOGI(kTag, "Reference output int8: %d",
           static_cast<int>(birdhouse::kReferenceModelOutputInt8));
  ESP_LOGI(kTag, "Reference p_bird: %.6f",
           static_cast<double>(birdhouse::kReferenceModelOutputPBird));
  ESP_LOGI(kTag, "Reference is_bird: %s",
           birdhouse::kReferenceModelOutputIsBird ? "true" : "false");

  if (OutputMatchesReference(output_q, is_bird)) {
    ESP_LOGI(kTag, "PREPROCESSING-INFERENCE TEST PASS");
  } else {
    ESP_LOGE(kTag, "PREPROCESSING-INFERENCE TEST FAIL");
  }
}
