// An independent stored Python oracle closes the duplicate-pipeline test gap.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "firmware/preprocess/audio_preprocess.h"
#include "firmware/preprocess/testdata/reference_pcm_float32.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"
#include "firmware/himax_arc/tests/bh_test.h"

int main() {
  int8_t output[birdhouse::kFeatureElements + 16];
  std::memset(output, 42, sizeof(output));
  BH_CHECK(birdhouse::PreprocessFloatPcmToInt8ModelInput(
      birdhouse::kReferencePcmFloat32, birdhouse::kTargetSamples, output, birdhouse::kFeatureElements));
  int different = 0, max_abs = 0;
  for (int i = 0; i < birdhouse::kFeatureElements; ++i) {
    const int diff = static_cast<int>(output[i]) - birdhouse::kReferenceInputInt8[i];
    const int abs = diff < 0 ? -diff : diff;
    if (abs != 0) ++different;
    if (abs > max_abs) max_abs = abs;
  }
  BH_CHECK(different == 0);
  for (int i = birdhouse::kFeatureElements; i < static_cast<int>(sizeof(output)); ++i) BH_CHECK(output[i] == 42);
  BH_CHECK(!birdhouse::PreprocessFloatPcmToInt8ModelInput(nullptr, 80000, output, sizeof(output)));
  BH_CHECK(!birdhouse::PreprocessFloatPcmToInt8ModelInput(birdhouse::kReferencePcmFloat32, 80000, nullptr, 9960));
  BH_CHECK(!birdhouse::PreprocessFloatPcmToInt8ModelInput(birdhouse::kReferencePcmFloat32, 80000, output, 9959));
  std::printf("ORACLE elements=9960 mismatches=%d max_abs_diff=%d\n", different, max_abs);
  return bh_test::Finish("preprocess_reference");
}
