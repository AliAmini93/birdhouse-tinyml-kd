// Diagnostics helpers: checksums, PCM statistics, base64 output.
// Integer-only so that results are identical on the ARC target and the host.
#ifndef BIRDHOUSE_HIMAX_BH_DIAG_H_
#define BIRDHOUSE_HIMAX_BH_DIAG_H_

#include <cstddef>
#include <cstdint>

namespace bh {

// CRC-32 (IEEE 802.3, reflected, as used by zlib). Pass the previous return
// value as `crc` to continue over several buffers; start with 0.
uint32_t Crc32(const void* data, size_t len, uint32_t crc = 0);

struct PcmStats {
  int32_t min;
  int32_t max;
  int32_t mean;        // rounded toward zero
  uint32_t rms;        // integer square root of the mean square
  uint32_t clipped;    // samples equal to -32768 or 32767
  uint32_t zeros;      // samples equal to 0
  uint32_t longest_zero_run;
};
void ComputePcmStats(const int16_t* pcm, size_t count, PcmStats* out);

uint32_t ISqrt64(uint64_t v);

// Streams `len` bytes as base64 text. `sink` receives chunks of at most 64
// characters without line terminators; the caller decides how to print them.
typedef void (*TextSink)(const char* chunk, size_t len, void* context);
void Base64Encode(const uint8_t* data, size_t len, TextSink sink, void* context);

// Deterministic integer test signals for the synthetic end-to-end self-test.
// The same function runs on the host to produce the expected values.
enum SynthKind {
  kSynthSilence = 0,
  kSynthNoise = 1,       // LCG noise, about -12 dBFS peak
  kSynthTones = 2,       // two triangle waves, 1 kHz and 3.2 kHz
  kSynthChirpSteps = 3,  // square wave whose period shrinks every 0.25 s
  kSynthKindCount = 4,
};
const char* SynthKindName(int kind);
bool SynthFill(int kind, int16_t* pcm, size_t count);

}  // namespace bh

#endif  // BIRDHOUSE_HIMAX_BH_DIAG_H_
