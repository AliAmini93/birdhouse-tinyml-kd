// Host tests for the integer diagnostics helpers.
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_diag.h"
#include "firmware/himax_arc/tests/bh_test.h"

namespace {

void Collect(const char* chunk, size_t len, void* context) {
  std::string* out = static_cast<std::string*>(context);
  BH_CHECK(len <= 64);
  out->append(chunk, len);
}

std::string B64(const std::string& in) {
  std::string out;
  bh::Base64Encode(reinterpret_cast<const uint8_t*>(in.data()), in.size(), Collect, &out);
  return out;
}

}  // namespace

int main() {
  BH_CASE("CRC-32 matches the standard check value and is incremental");
  BH_CHECK(bh::Crc32("123456789", 9) == 0xCBF43926u);
  BH_CHECK(bh::Crc32("", 0) == 0u);
  BH_CHECK(bh::Crc32("6789", 4, bh::Crc32("12345", 5)) == 0xCBF43926u);

  BH_CASE("integer square root");
  BH_CHECK(bh::ISqrt64(0) == 0);
  BH_CHECK(bh::ISqrt64(1) == 1);
  BH_CHECK(bh::ISqrt64(15) == 3);
  BH_CHECK(bh::ISqrt64(16) == 4);
  BH_CHECK(bh::ISqrt64(1073741824ull) == 32768);
  BH_CHECK(bh::ISqrt64(0xFFFFFFFFFFFFFFFFull) == 0xFFFFFFFFu);

  BH_CASE("PCM statistics");
  {
    const int16_t pcm[] = {0, 0, 0, 100, -100, 32767, -32768, 0, 0, 5};
    bh::PcmStats s;
    bh::ComputePcmStats(pcm, 10, &s);
    BH_CHECK(s.min == -32768 && s.max == 32767);
    BH_CHECK(s.clipped == 2);
    BH_CHECK(s.zeros == 5);
    BH_CHECK(s.longest_zero_run == 3);
    BH_CHECK(s.mean == 0);  // sum is 4, 4/10 rounds toward zero
    BH_CHECK(s.rms == bh::ISqrt64((10000ull + 10000ull + 1073676289ull + 1073741824ull + 25ull) / 10));
    bh::ComputePcmStats(pcm, 0, &s);
    BH_CHECK(s.min == 0 && s.max == 0 && s.rms == 0);
    bh::ComputePcmStats(nullptr, 5, &s);
    BH_CHECK(s.rms == 0);
  }

  BH_CASE("base64 (RFC 4648 vectors, padding, chunking)");
  BH_CHECK(B64("") == "");
  BH_CHECK(B64("f") == "Zg==");
  BH_CHECK(B64("fo") == "Zm8=");
  BH_CHECK(B64("foo") == "Zm9v");
  BH_CHECK(B64("foob") == "Zm9vYg==");
  BH_CHECK(B64("fooba") == "Zm9vYmE=");
  BH_CHECK(B64("foobar") == "Zm9vYmFy");
  {
    std::string big(1000, '\0');
    for (size_t i = 0; i < big.size(); ++i) big[i] = static_cast<char>(i * 31 + 7);
    const std::string enc = B64(big);
    BH_CHECK(enc.size() == 4 * ((big.size() + 2) / 3));
    BH_CHECK(enc.find('\n') == std::string::npos);
  }

  BH_CASE("synthetic signals are deterministic and within range");
  std::vector<int16_t> a(bh::kTargetSamples), b(bh::kTargetSamples);
  for (int kind = 0; kind < bh::kSynthKindCount; ++kind) {
    BH_CHECK(bh::SynthFill(kind, a.data(), a.size()));
    BH_CHECK(bh::SynthFill(kind, b.data(), b.size()));
    BH_CHECK(std::memcmp(a.data(), b.data(), a.size() * sizeof(int16_t)) == 0);
    bh::PcmStats s;
    bh::ComputePcmStats(a.data(), a.size(), &s);
    BH_CHECK(s.clipped == 0);
    std::printf("  synth kind=%d name=%-12s pcm_crc=%08x min=%d max=%d rms=%u\n", kind,
                bh::SynthKindName(kind), bh::Crc32(a.data(), a.size() * sizeof(int16_t)), s.min, s.max,
                s.rms);
  }
  BH_CHECK(!bh::SynthFill(bh::kSynthKindCount, a.data(), a.size()));
  BH_CHECK(!bh::SynthFill(0, nullptr, 10));

  return bh_test::Finish("diag");
}
