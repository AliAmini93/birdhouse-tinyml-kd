// Host inference test: the Birdhouse model on the vendor TFLite Micro sources.
//
// Built from the same TFLite Micro tree the firmware uses, with the reference
// (portable C++) kernels. It therefore validates operator coverage, the
// operator configuration, tensor contracts, arena use and numeric results of
// the reference kernels. It does NOT execute the ARC MLI kernels; those can
// only run on the ARC core or a simulator.
//
// Modes:
//   test_tflm_inference                 normal run, every check must pass
//   test_tflm_inference expect-blocked  negative control for a build that uses
//                                       the vendor operator configuration: the
//                                       model must fail to initialise or invoke
#include <sys/wait.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_model.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/tflm_vectors.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/model/student_final_int8_model_data.h"

namespace {

const size_t kArenaBytes = 256 * 1024;
const size_t kGuardBytes = 4096;
const uint8_t kGuardPattern = 0xA5;

// Arena with guard zones on both sides to detect out-of-bounds writes.
struct GuardedArena {
  std::vector<uint8_t> block;
  size_t size;
  explicit GuardedArena(size_t n) : block(n + 2 * kGuardBytes + 16, kGuardPattern), size(n) {}
  uint8_t* arena() {
    uint8_t* p = block.data() + kGuardBytes;
    const size_t mis = reinterpret_cast<uintptr_t>(p) % 16;
    return mis == 0 ? p : p + (16 - mis);
  }
  bool GuardsIntact() {
    const uint8_t* lo = block.data();
    const uint8_t* a = arena();
    for (const uint8_t* p = lo; p < a; ++p) if (*p != kGuardPattern) return false;
    for (const uint8_t* p = a + size; p < lo + block.size(); ++p) if (*p != kGuardPattern) return false;
    return true;
  }
};

const unsigned char* Model() { return birdhouse::g_student_final_int8_model_data; }
size_t ModelLen() { return birdhouse::g_student_final_int8_model_data_len; }

// Outcome of ModelInit with a given arena size, measured in a child process.
// TFLite Micro reports most out-of-memory conditions as an error, but some
// allocations are only guarded by debug assertions. This host build keeps the
// assertions enabled, so those cases abort here; the firmware is built with
// NDEBUG, where the same case would write through a null pointer instead.
enum ProbeResult { kProbeOk, kProbeCleanFailure, kProbeAssertion };

ProbeResult ProbeArena(size_t arena_bytes) {
  std::fflush(stdout);
  const pid_t pid = fork();
  if (pid == 0) {
    GuardedArena probe(kArenaBytes);
    const bh::ModelStatus s = bh::ModelInit(Model(), ModelLen(), probe.arena(), arena_bytes);
    _exit(s == bh::kModelOk ? 0 : (s == bh::kModelAllocateTensors ? 1 : 2));
  }
  int status = 0;
  waitpid(pid, &status, 0);
  if (WIFEXITED(status) && WEXITSTATUS(status) == 0) return kProbeOk;
  if (WIFEXITED(status) && WEXITSTATUS(status) == 1) return kProbeCleanFailure;
  return kProbeAssertion;
}

int RunExpectBlocked() {
  BH_CASE("negative control: vendor operator configuration must block the model");
  GuardedArena arena(kArenaBytes);
  const bh::ModelStatus init = bh::ModelInit(Model(), ModelLen(), arena.arena(), arena.size);
  std::printf("  ModelInit -> %s\n", bh::ModelStatusName(init));
  bh::ModelStatus invoke = bh::kModelNotReady;
  if (init == bh::kModelOk) {
    std::memset(bh::ModelInput(), birdhouse::kModelInputZeroPoint, birdhouse::kModelInputElements);
    invoke = bh::ModelInvoke();
    std::printf("  ModelInvoke -> %s\n", bh::ModelStatusName(invoke));
  }
  const bool blocked = (init == bh::kModelAllocateTensors) ||
                       (init == bh::kModelOk && invoke == bh::kModelInvokeFailed);
  BH_CHECK(blocked);
  std::printf("  blocked_at=%s\n", init != bh::kModelOk ? "AllocateTensors" : "Invoke");
  return bh_test::Finish("tflm_inference_expect_blocked");
}

}  // namespace

int main(int argc, char** argv) {
  if (argc > 1 && std::strcmp(argv[1], "expect-blocked") == 0) return RunExpectBlocked();

  static int8_t input[birdhouse::kFeatureElements];

  BH_CASE("argument and flatbuffer validation");
  {
    GuardedArena arena(kArenaBytes);
    BH_CHECK(!bh::ModelReady());
    BH_CHECK(bh::ModelInput() == nullptr);
    BH_CHECK(bh::ModelInvoke() == bh::kModelNotReady);
    BH_CHECK(bh::ModelInit(nullptr, ModelLen(), arena.arena(), arena.size) == bh::kModelBadArgument);
    BH_CHECK(bh::ModelInit(Model(), ModelLen(), nullptr, arena.size) == bh::kModelBadArgument);
    BH_CHECK(bh::ModelInit(Model(), ModelLen(), arena.arena(), 0) == bh::kModelBadArgument);
    BH_CHECK(bh::ModelInit(Model(), 8, arena.arena(), arena.size) == bh::kModelBadFlatbuffer);
    std::vector<unsigned char> bad(Model(), Model() + ModelLen());
    bad[5] ^= 0xFF;  // corrupt the "TFL3" identifier
    BH_CHECK(bh::ModelInit(bad.data(), bad.size(), arena.arena(), arena.size) == bh::kModelBadFlatbuffer);
    BH_CHECK(!bh::ModelReady());
    BH_CHECK(arena.GuardsIntact());
  }

  BH_CASE("initialisation and tensor contract");
  GuardedArena arena(kArenaBytes);
  const bh::ModelStatus init = bh::ModelInit(Model(), ModelLen(), arena.arena(), arena.size);
  std::printf("  ModelInit -> %s\n", bh::ModelStatusName(init));
  if (!BH_CHECK(init == bh::kModelOk)) return bh_test::Finish("tflm_inference");
  const bh::ModelInfo info = bh::ModelGetInfo();
  std::printf("  input: %zu bytes, scale=%.10g zero_point=%d\n", info.input_bytes,
              static_cast<double>(info.input_scale), info.input_zero_point);
  std::printf("  output: scale=%.10g zero_point=%d, bird threshold q>=%d\n",
              static_cast<double>(info.output_scale), info.output_zero_point,
              bh::ModelBirdThresholdQ());
  BH_CHECK(bh::ModelReady());
  BH_CHECK(info.input_bytes == static_cast<size_t>(birdhouse::kFeatureElements));
  BH_CHECK(info.input_zero_point == birdhouse::kInputZeroPoint);
  BH_CHECK(info.output_zero_point == birdhouse::kOutputZeroPoint);
  BH_CHECK(bh::ModelBirdThresholdQ() == 45);
  BH_CHECK(bh::ModelInput() != nullptr);

  BH_CASE("arena requirement (host, 64-bit, reference kernels)");
  const size_t used = info.arena_used;
  std::printf("  arena_used_bytes=%zu of %zu\n", used, kArenaBytes);
  BH_CHECK(used > 0 && used < kArenaBytes);
  BH_CHECK(ProbeArena(kArenaBytes) == kProbeOk);
  BH_CHECK(ProbeArena(16 * 1024) != kProbeOk);
  size_t lo = 16 * 1024, hi = kArenaBytes;  // lo fails, hi succeeds
  while (hi - lo > 16) {
    const size_t mid = ((lo + hi) / 2) & ~static_cast<size_t>(15);
    if (ProbeArena(mid) == kProbeOk) hi = mid; else lo = mid;
  }
  const size_t min_arena = hi;
  // Classify every failing size on a 1 KiB grid: clean error or assertion.
  size_t clean_failures = 0, assertion_failures = 0;
  size_t assertion_lo = 0, assertion_hi = 0;
  for (size_t size = 16 * 1024; size < min_arena; size += 1024) {
    const ProbeResult r = ProbeArena(size);
    BH_CHECK(r != kProbeOk);  // success must be monotonic in arena size
    if (r == kProbeCleanFailure) ++clean_failures;
    if (r == kProbeAssertion) {
      if (assertion_failures == 0) assertion_lo = size;
      assertion_hi = size;
      ++assertion_failures;
    }
  }
  // The last 4 KiB below the minimum, in 16-byte steps: this is where the
  // allocations that are only assertion-guarded run out.
  for (size_t size = min_arena - 4096; size < min_arena; size += 16) {
    if (size % 1024 == 0) continue;  // already counted on the coarse grid
    const ProbeResult r = ProbeArena(size);
    BH_CHECK(r != kProbeOk);
    if (r == kProbeCleanFailure) ++clean_failures;
    if (r == kProbeAssertion) {
      if (assertion_failures == 0 || size < assertion_lo) assertion_lo = size;
      if (size > assertion_hi) assertion_hi = size;
      ++assertion_failures;
    }
  }
  std::printf("  minimum_arena_bytes=%zu (largest failing size %zu)\n", min_arena, lo);
  std::printf("  failing sizes probed: clean_error=%zu assertion=%zu", clean_failures,
              assertion_failures);
  if (assertion_failures > 0) {
    std::printf(" (assertion window %zu..%zu bytes)", assertion_lo, assertion_hi);
  }
  std::printf("\n");
  std::printf("  margin_at_160KiB=%ld margin_at_256KiB=%ld\n",
              static_cast<long>(160 * 1024) - static_cast<long>(min_arena),
              static_cast<long>(256 * 1024) - static_cast<long>(min_arena));
  BH_CHECK(min_arena <= kArenaBytes);
  // The firmware arena must clear the requirement by a wide margin because the
  // unsafe (assertion) window sits directly below it.
  BH_CHECK(kArenaBytes >= min_arena + 64 * 1024);

  BH_CASE("clean failure for a much too small arena, then recovery");
  {
    GuardedArena small(kArenaBytes);
    BH_CHECK(bh::ModelInit(Model(), ModelLen(), small.arena(), 16 * 1024) == bh::kModelAllocateTensors);
    BH_CHECK(!bh::ModelReady());
    BH_CHECK(bh::ModelInput() == nullptr);
    BH_CHECK(bh::ModelInvoke() == bh::kModelNotReady);
    BH_CHECK(small.GuardsIntact());
  }

  BH_CASE("re-initialisation after a failed attempt");
  BH_CHECK(!bh::ModelReady());  // last probe may have failed
  BH_CHECK(bh::ModelInit(Model(), ModelLen(), arena.arena(), arena.size) == bh::kModelOk);
  BH_CHECK(bh::ModelReady());

  BH_CASE("reference vectors (expected values from TensorFlow Lite reference kernels)");
  int8_t first_pass[64] = {0};
  int mismatches = 0;
  int max_abs_diff = 0;
  for (int i = 0; i < bh_test::kReferenceVectorCount; ++i) {
    const bh_test::ReferenceVector& v = bh_test::kReferenceVectors[i];
    bh_test::FillVector(v, input);
    if (!BH_CHECK(bh_test::Fnv1a32(input, sizeof(input)) == v.input_fnv1a32)) {
      std::printf("  input hash mismatch for %s\n", v.name);
      continue;
    }
    std::memcpy(bh::ModelInput(), input, sizeof(input));
    if (!BH_CHECK(bh::ModelInvoke() == bh::kModelOk)) continue;
    const int q = bh::ModelOutputQ();
    first_pass[i] = static_cast<int8_t>(q);
    const int diff = q > v.expected_q ? q - v.expected_q : v.expected_q - q;
    if (diff != 0) ++mismatches;
    if (diff > max_abs_diff) max_abs_diff = diff;
    std::printf("  %-24s q=%4d expected=%4d p_bird=%.4f %s%s\n", v.name, q, v.expected_q,
                static_cast<double>(bh::ModelPBird()), bh::ModelIsBird() ? "BIRD" : "NON-BIRD",
                diff == 0 ? "" : "  <-- MISMATCH");
    BH_CHECK(q == v.expected_q);
    BH_CHECK(bh::ModelIsBird() == v.expected_is_bird);
  }
  std::printf("  vectors=%d mismatches=%d max_abs_diff=%d\n", bh_test::kReferenceVectorCount,
              mismatches, max_abs_diff);

  BH_CASE("tracked reference output (firmware/inference/testdata)");
  bh_test::FillVector(bh_test::kReferenceVectors[0], input);
  std::memcpy(bh::ModelInput(), input, sizeof(input));
  BH_CHECK(bh::ModelInvoke() == bh::kModelOk);
  BH_CHECK(bh::ModelOutputQ() == birdhouse::kReferenceModelOutputInt8);
  BH_CHECK(bh::ModelIsBird() == birdhouse::kReferenceModelOutputIsBird);

  BH_CASE("repeated inference is deterministic (reverse order, with a re-init in the middle)");
  for (int i = bh_test::kReferenceVectorCount - 1; i >= 0; --i) {
    if (i == bh_test::kReferenceVectorCount / 2) {
      BH_CHECK(bh::ModelInit(Model(), ModelLen(), arena.arena(), arena.size) == bh::kModelOk);
    }
    bh_test::FillVector(bh_test::kReferenceVectors[i], input);
    std::memcpy(bh::ModelInput(), input, sizeof(input));
    BH_CHECK(bh::ModelInvoke() == bh::kModelOk);
    BH_CHECK(bh::ModelOutputQ() == first_pass[i]);
  }

  BH_CASE("input tensor after Invoke (informational: is the buffer reused?)");
  bh_test::FillVector(bh_test::kReferenceVectors[0], input);
  std::memcpy(bh::ModelInput(), input, sizeof(input));
  BH_CHECK(bh::ModelInvoke() == bh::kModelOk);
  const bool preserved = std::memcmp(bh::ModelInput(), input, sizeof(input)) == 0;
  std::printf("  input_preserved_after_invoke=%s (the firmware refills the input before every Invoke)\n",
              preserved ? "true" : "false");

  BH_CASE("arena guard zones");
  BH_CHECK(arena.GuardsIntact());

  std::printf("RESULT {\"arena_used_bytes\":%zu,\"minimum_arena_bytes\":%zu,\"vectors\":%d,"
              "\"mismatches\":%d,\"max_abs_diff\":%d,\"invoke_count\":%u,\"pointer_bits\":%d,"
              "\"arena_assertion_window\":[%zu,%zu],\"arena_assertion_sizes\":%zu}\n",
              used, min_arena, bh_test::kReferenceVectorCount, mismatches, max_abs_diff,
              bh::ModelGetInfo().invoke_count, static_cast<int>(sizeof(void*) * 8),
              assertion_lo, assertion_hi, assertion_failures);
  bh::ModelDeinit();
  return bh_test::Finish("tflm_inference");
}
