#ifndef BIRDHOUSE_MEL_FILTERBANK_H_
#define BIRDHOUSE_MEL_FILTERBANK_H_

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

extern const float kMelFilterbank[kNumMels * kFftBins];
extern const float kPaddedHannWindow[kFftSize];

}  // namespace birdhouse

#endif  // BIRDHOUSE_MEL_FILTERBANK_H_
