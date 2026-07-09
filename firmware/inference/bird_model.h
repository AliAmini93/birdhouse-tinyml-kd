#ifndef BIRDHOUSE_BIRD_MODEL_H_
#define BIRDHOUSE_BIRD_MODEL_H_

#include <cstddef>
#include <cstdint>

#include "firmware/model/model_constants.h"

namespace tflite {
class MicroInterpreter;
}  // namespace tflite

namespace birdhouse {

class BirdModel {
 public:
  BirdModel();

  bool Init(uint8_t* tensor_arena, size_t tensor_arena_size);

  int8_t* input();
  size_t input_size() const;

  bool Invoke();

  int8_t output_int8() const;
  float p_bird() const;
  bool is_bird() const;

 private:
  bool initialized_;
  tflite::MicroInterpreter* interpreter_;
  void* model_;
};

}  // namespace birdhouse

#endif  // BIRDHOUSE_BIRD_MODEL_H_
