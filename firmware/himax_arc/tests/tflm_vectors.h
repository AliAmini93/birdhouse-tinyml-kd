// Input generation rules shared with tools/himax/gen_tflm_reference.py.
// Each rule uses only integer arithmetic so that Python and C++ build
// byte-identical inputs; the FNV-1a hash stored with every vector proves it.
#ifndef BIRDHOUSE_HIMAX_TESTS_TFLM_VECTORS_H_
#define BIRDHOUSE_HIMAX_TESTS_TFLM_VECTORS_H_

#include <cstddef>
#include <cstdint>

#include "firmware/himax_arc/tests/testdata/tflm_reference_vectors.h"
#include "firmware/preprocess/preprocess_constants.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"

namespace bh_test {

inline uint32_t Fnv1a32(const int8_t* data, size_t len) {
  uint32_t h = 0x811C9DC5u;
  for (size_t i = 0; i < len; ++i) {
    h ^= static_cast<uint8_t>(data[i]);
    h *= 0x01000193u;
  }
  return h;
}

inline int8_t ClampInt8(int v) {
  return static_cast<int8_t>(v < -128 ? -128 : (v > 127 ? 127 : v));
}

// Fills `out` (kFeatureElements values, layout [mel][frame]) for one vector.
inline void FillVector(const ReferenceVector& v, int8_t* out) {
  const int mels = birdhouse::kNumMels;
  const int frames = birdhouse::kExpectedFrames;
  const int n = birdhouse::kFeatureElements;
  const int8_t* ref = birdhouse::kReferenceInputInt8;
  const int zp = birdhouse::kInputZeroPoint;
  uint32_t state = v.param;
  switch (v.kind) {
    case kVectorReference:
      for (int i = 0; i < n; ++i) out[i] = ref[i];
      break;
    case kVectorConstant:
      for (int i = 0; i < n; ++i) out[i] = static_cast<int8_t>(static_cast<int32_t>(v.param));
      break;
    case kVectorRampMel:
      for (int m = 0; m < mels; ++m)
        for (int f = 0; f < frames; ++f) out[m * frames + f] = static_cast<int8_t>(-128 + m * 6);
      break;
    case kVectorRampFrame:
      for (int m = 0; m < mels; ++m)
        for (int f = 0; f < frames; ++f) out[m * frames + f] = static_cast<int8_t>(-128 + f);
      break;
    case kVectorChecker:
      for (int m = 0; m < mels; ++m)
        for (int f = 0; f < frames; ++f) out[m * frames + f] = ((m + f) % 2) ? 100 : -100;
      break;
    case kVectorLcgFull:
      for (int i = 0; i < n; ++i) {
        state = state * 1664525u + 1013904223u;
        out[i] = static_cast<int8_t>(static_cast<int>(state >> 24) - 128);
      }
      break;
    case kVectorLcgNarrow:
      for (int i = 0; i < n; ++i) {
        state = state * 1664525u + 1013904223u;
        out[i] = static_cast<int8_t>(zp + static_cast<int>((state >> 24) % 41u) - 20);
      }
      break;
    case kVectorRefScaled:
      for (int i = 0; i < n; ++i) {
        const int d = (static_cast<int>(ref[i]) - zp) * static_cast<int>(v.param);
        out[i] = static_cast<int8_t>(zp + d / 8);  // truncates toward zero
      }
      break;
    case kVectorRefNoise:
      for (int i = 0; i < n; ++i) {
        state = state * 1664525u + 1013904223u;
        out[i] = ClampInt8(static_cast<int>(ref[i]) + static_cast<int>((state >> 24) % 25u) - 12);
      }
      break;
    case kVectorRefShift:
      for (int m = 0; m < mels; ++m)
        for (int f = 0; f < frames; ++f)
          out[m * frames + f] = ref[m * frames + (f + static_cast<int>(v.param)) % frames];
      break;
    case kVectorRefReversed:
      for (int m = 0; m < mels; ++m)
        for (int f = 0; f < frames; ++f) out[m * frames + f] = ref[m * frames + (frames - 1 - f)];
      break;
  }
}

}  // namespace bh_test

#endif  // BIRDHOUSE_HIMAX_TESTS_TFLM_VECTORS_H_
