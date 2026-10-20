#include "streaming_logmel_step29.cc"

namespace {
birdhouse::StreamingLogMel g_stream;
}

extern "C" void birdhouse_streaming_reset() {
    g_stream.Reset();
}

extern "C" int birdhouse_streaming_push(
    int16_t sample,
    int8_t* output,
    size_t output_len) {

    return g_stream.Push(
        sample, output, output_len) ? 1 : 0;
}

extern "C" int birdhouse_streaming_frames() {
    return g_stream.FrameCount();
}

extern "C" size_t birdhouse_streaming_workspace() {
    return sizeof(g_stream);
}
