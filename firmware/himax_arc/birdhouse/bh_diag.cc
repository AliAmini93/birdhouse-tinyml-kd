#include "firmware/himax_arc/birdhouse/bh_diag.h"

namespace bh {

uint32_t Crc32(const void* data, size_t len, uint32_t crc) {
  // Nibble-wise table: 64 bytes of constants instead of 1 KiB.
  static const uint32_t kTable[16] = {
      0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu, 0x76DC4190u, 0x6B6B51F4u,
      0x4DB26158u, 0x5005713Cu, 0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu,
      0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu};
  const uint8_t* p = static_cast<const uint8_t*>(data);
  crc = ~crc;
  for (size_t i = 0; i < len; ++i) {
    crc ^= p[i];
    crc = kTable[crc & 0x0Fu] ^ (crc >> 4);
    crc = kTable[crc & 0x0Fu] ^ (crc >> 4);
  }
  return ~crc;
}

uint32_t ISqrt64(uint64_t v) {
  uint64_t result = 0;
  uint64_t bit = static_cast<uint64_t>(1) << 62;
  while (bit > v) bit >>= 2;
  while (bit != 0) {
    if (v >= result + bit) {
      v -= result + bit;
      result = (result >> 1) + bit;
    } else {
      result >>= 1;
    }
    bit >>= 2;
  }
  return static_cast<uint32_t>(result);
}

void ComputePcmStats(const int16_t* pcm, size_t count, PcmStats* out) {
  PcmStats s = PcmStats();
  if (pcm == nullptr || count == 0) {
    *out = s;
    return;
  }
  int32_t lo = 32767, hi = -32768;
  int64_t sum = 0;
  uint64_t sum_sq = 0;
  uint32_t run = 0;
  for (size_t i = 0; i < count; ++i) {
    const int32_t v = pcm[i];
    if (v < lo) lo = v;
    if (v > hi) hi = v;
    sum += v;
    sum_sq += static_cast<uint64_t>(static_cast<int64_t>(v) * v);
    if (v == -32768 || v == 32767) ++s.clipped;
    if (v == 0) {
      ++s.zeros;
      ++run;
      if (run > s.longest_zero_run) s.longest_zero_run = run;
    } else {
      run = 0;
    }
  }
  s.min = lo;
  s.max = hi;
  s.mean = static_cast<int32_t>(sum / static_cast<int64_t>(count));
  s.rms = ISqrt64(sum_sq / count);
  *out = s;
}

void Base64Encode(const uint8_t* data, size_t len, TextSink sink, void* context) {
  static const char kAlphabet[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  char chunk[64];
  size_t used = 0;
  size_t i = 0;
  while (i < len) {
    const size_t remain = len - i;
    const uint32_t b0 = data[i];
    const uint32_t b1 = remain > 1 ? data[i + 1] : 0;
    const uint32_t b2 = remain > 2 ? data[i + 2] : 0;
    const uint32_t triple = (b0 << 16) | (b1 << 8) | b2;
    chunk[used++] = kAlphabet[(triple >> 18) & 0x3F];
    chunk[used++] = kAlphabet[(triple >> 12) & 0x3F];
    chunk[used++] = remain > 1 ? kAlphabet[(triple >> 6) & 0x3F] : '=';
    chunk[used++] = remain > 2 ? kAlphabet[triple & 0x3F] : '=';
    i += remain > 3 ? 3 : remain;
    if (used == sizeof(chunk)) {
      sink(chunk, used, context);
      used = 0;
    }
  }
  if (used != 0) sink(chunk, used, context);
}

const char* SynthKindName(int kind) {
  switch (kind) {
    case kSynthSilence: return "SILENCE";
    case kSynthNoise: return "NOISE";
    case kSynthTones: return "TONES";
    case kSynthChirpSteps: return "CHIRP_STEPS";
  }
  return "UNKNOWN";
}

bool SynthFill(int kind, int16_t* pcm, size_t count) {
  if (pcm == nullptr) return false;
  switch (kind) {
    case kSynthSilence:
      for (size_t i = 0; i < count; ++i) pcm[i] = 0;
      return true;
    case kSynthNoise: {
      uint32_t state = 0x1234ABCDu;
      for (size_t i = 0; i < count; ++i) {
        state = state * 1664525u + 1013904223u;
        pcm[i] = static_cast<int16_t>(static_cast<int32_t>(state >> 19) - 4096);  // [-4096, 4095]
      }
      return true;
    }
    case kSynthTones:
      for (size_t i = 0; i < count; ++i) {
        // Triangle, period 16 samples (1 kHz), amplitude 8000.
        const int32_t a = static_cast<int32_t>(i % 16);
        const int32_t tri_a = (a < 8 ? a : 16 - a) * 2000 - 8000;
        // Triangle, period 5 samples (3.2 kHz), amplitude 3000.
        const int32_t b = static_cast<int32_t>(i % 5);
        const int32_t tri_b = (b < 3 ? b : 5 - b) * 3000 - 3000;
        pcm[i] = static_cast<int16_t>(tri_a + tri_b);
      }
      return true;
    case kSynthChirpSteps:
      for (size_t i = 0; i < count; ++i) {
        // Square wave; the half-period drops from 40 samples (200 Hz) by 2
        // samples every 4000 samples (0.25 s) down to 2 samples (4 kHz).
        const uint32_t step = static_cast<uint32_t>(i / 4000);
        const uint32_t half = step >= 19 ? 2u : 40u - 2u * step;
        pcm[i] = ((i / half) % 2 == 0) ? 6000 : -6000;
      }
      return true;
  }
  return false;
}

}  // namespace bh
