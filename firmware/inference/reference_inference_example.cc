#include <algorithm>
#include <cstdint>
#include <iostream>

#include "firmware/inference/bird_model.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"

// This example requires TensorFlow Lite Micro include/library paths.
// It is a firmware/desktop integration example, not a plain g++ test.

int main() {
  static uint8_t tensor_arena[birdhouse::kTensorArenaSizeBytes];

  birdhouse::BirdModel model;
  if (!model.Init(tensor_arena, sizeof(tensor_arena))) {
    std::cerr << "BirdModel init failed\n";
    return 1;
  }

  int8_t* input = model.input();
  if (input == nullptr) {
    std::cerr << "Input tensor is null\n";
    return 1;
  }

  std::copy(
      birdhouse::kReferenceInputInt8,
      birdhouse::kReferenceInputInt8 + birdhouse::kModelInputElements,
      input);

  if (!model.Invoke()) {
    std::cerr << "Invoke failed\n";
    return 1;
  }

  std::cout << "output_int8 = " << static_cast<int>(model.output_int8()) << "\n";
  std::cout << "p_bird = " << model.p_bird() << "\n";
  std::cout << "is_bird = " << (model.is_bird() ? "true" : "false") << "\n";

  std::cout << "reference_output_int8 = "
            << static_cast<int>(birdhouse::kReferenceModelOutputInt8) << "\n";
  std::cout << "reference_p_bird = " << birdhouse::kReferenceModelOutputPBird << "\n";
  std::cout << "reference_is_bird = "
            << (birdhouse::kReferenceModelOutputIsBird ? "true" : "false")
            << "\n";

  return 0;
}
