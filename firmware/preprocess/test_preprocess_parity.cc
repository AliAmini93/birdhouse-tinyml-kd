#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "firmware/preprocess/audio_preprocess.h"
#include "firmware/preprocess/preprocess_constants.h"

namespace {

template <typename T>
bool ReadBinaryFile(const std::string& path, std::vector<T>* out) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) {
    std::cerr << "ERROR: could not open " << path << "\n";
    return false;
  }

  const std::streamsize bytes = file.tellg();
  if (bytes < 0 ||
      bytes % static_cast<std::streamsize>(sizeof(T)) != 0) {
    std::cerr << "ERROR: invalid binary size for " << path << "\n";
    return false;
  }

  file.seekg(0, std::ios::beg);
  out->resize(static_cast<size_t>(bytes) / sizeof(T));
  if (!file.read(reinterpret_cast<char*>(out->data()), bytes)) {
    std::cerr << "ERROR: could not read " << path << "\n";
    return false;
  }

  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "Usage:\n"
              << "  " << argv[0]
              << " <reference_pcm_float32.bin> "
                 "<reference_input_int8.bin>\n";
    return 2;
  }

  const std::string pcm_path = argv[1];
  const std::string ref_path = argv[2];

  std::vector<float> pcm;
  std::vector<int8_t> reference;
  if (!ReadBinaryFile<float>(pcm_path, &pcm)) return 2;
  if (!ReadBinaryFile<int8_t>(ref_path, &reference)) return 2;

  if (pcm.size() != static_cast<size_t>(birdhouse::kTargetSamples)) {
    std::cerr << "ERROR: PCM sample count mismatch. got=" << pcm.size()
              << " expected=" << birdhouse::kTargetSamples << "\n";
    return 2;
  }

  if (reference.size() !=
      static_cast<size_t>(birdhouse::kFeatureElements)) {
    std::cerr << "ERROR: reference feature count mismatch. got="
              << reference.size()
              << " expected=" << birdhouse::kFeatureElements << "\n";
    return 2;
  }

  std::vector<int8_t> output(birdhouse::kFeatureElements);

  const auto t0 = std::chrono::steady_clock::now();
  const bool ok = birdhouse::PreprocessFloatPcmToInt8ModelInput(
      pcm.data(), pcm.size(), output.data(), output.size());
  const auto t1 = std::chrono::steady_clock::now();

  if (!ok) {
    std::cerr
        << "ERROR: PreprocessFloatPcmToInt8ModelInput failed\n";
    return 2;
  }

  const double elapsed_ms =
      std::chrono::duration<double, std::milli>(t1 - t0).count();

  int exact = 0;
  int within1 = 0;
  int within2 = 0;
  int within4 = 0;
  int max_abs = 0;
  size_t max_index = 0;
  long long sum_abs = 0;
  double sum_sq = 0.0;

  for (size_t i = 0; i < reference.size(); ++i) {
    const int diff =
        static_cast<int>(output[i]) -
        static_cast<int>(reference[i]);
    const int ad = std::abs(diff);
    if (ad == 0) ++exact;
    if (ad <= 1) ++within1;
    if (ad <= 2) ++within2;
    if (ad <= 4) ++within4;
    if (ad > max_abs) {
      max_abs = ad;
      max_index = i;
    }
    sum_abs += ad;
    sum_sq +=
        static_cast<double>(diff) * static_cast<double>(diff);
  }

  const double n = static_cast<double>(reference.size());
  const double exact_pct = 100.0 * exact / n;
  const double within1_pct = 100.0 * within1 / n;
  const double within2_pct = 100.0 * within2 / n;
  const double within4_pct = 100.0 * within4 / n;
  const double mean_abs = static_cast<double>(sum_abs) / n;
  const double rmse = std::sqrt(sum_sq / n);
  const double realtime_factor =
      elapsed_ms / (birdhouse::kDurationSeconds * 1000.0);

  const int max_mel =
      static_cast<int>(max_index / birdhouse::kExpectedFrames);
  const int max_frame =
      static_cast<int>(max_index % birdhouse::kExpectedFrames);

  const bool pass_initial =
      (mean_abs <= 2.0) && (within2_pct >= 95.0);

  std::cout
      << "======================================================================\n";
  std::cout << "OPTIMIZED PREPROCESS PARITY TEST\n";
  std::cout
      << "======================================================================\n";
  std::cout << "Backend: "
            << birdhouse::AudioPreprocessBackendName() << "\n";
  std::cout << "Scratch bytes: "
            << birdhouse::AudioPreprocessScratchBytes() << "\n";
  std::cout << "PCM samples: " << pcm.size() << "\n";
  std::cout << "Feature elements: " << reference.size() << "\n";
  std::cout << "Layout: [mel][frame]\n";
  std::cout << "Expected shape: " << birdhouse::kNumMels
            << " x " << birdhouse::kExpectedFrames << "\n";
  std::cout << "elapsed_ms_host: " << elapsed_ms << "\n";
  std::cout << "realtime_factor_host: " << realtime_factor << "\n";
  std::cout
      << "----------------------------------------------------------------------\n";
  std::cout << "exact_match_pct: " << exact_pct << "\n";
  std::cout << "within_1_pct: " << within1_pct << "\n";
  std::cout << "within_2_pct: " << within2_pct << "\n";
  std::cout << "within_4_pct: " << within4_pct << "\n";
  std::cout << "mean_abs_diff_int8: " << mean_abs << "\n";
  std::cout << "rmse_int8: " << rmse << "\n";
  std::cout << "max_abs_diff_int8: " << max_abs << "\n";
  std::cout << "max_diff_index: " << max_index << "\n";
  std::cout << "max_diff_mel: " << max_mel << "\n";
  std::cout << "max_diff_frame: " << max_frame << "\n";
  std::cout << "cpp_value_at_max: "
            << static_cast<int>(output[max_index]) << "\n";
  std::cout << "python_value_at_max: "
            << static_cast<int>(reference[max_index]) << "\n";
  std::cout
      << "----------------------------------------------------------------------\n";
  std::cout
      << "acceptance_rule: mean_abs_diff_int8 <= 2 and "
         "within_2_pct >= 95\n";
  std::cout << "status: "
            << (pass_initial ? "PASS" : "WARN") << "\n";
  std::cout
      << "======================================================================\n";

  // Keep report generation possible even for WARN.
  return 0;
}
