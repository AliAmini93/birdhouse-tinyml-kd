#include <cstddef>
#include <cstdint>

#include "firmware/inference/bird_model.h"
#include "firmware/preprocess/audio_preprocess.h"

extern "C" int birdhouse_link_probe(
    const int16_t* pcm,
    uint8_t* arena,
    size_t arena_size,
    int8_t* features) {

    if (!birdhouse::PreprocessInt16PcmToInt8ModelInput(
            pcm, birdhouse::kTargetSamples,
            features, birdhouse::kFeatureElements)) {
        return -1;
    }

    birdhouse::BirdModel model;

    if (!model.Init(arena, arena_size)) {
        return -2;
    }

    int8_t* input = model.input();
    if (!input) return -3;

    for (size_t i = 0; i < model.input_size(); ++i) {
        input[i] = features[i];
    }

    if (!model.Invoke()) return -4;

    return model.is_bird() ? 1 : 0;
}
