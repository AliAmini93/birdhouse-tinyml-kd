// First-party AT handlers shared by ARC firmware and host integration tests.
#include "firmware/himax_arc/birdhouse/bh_console.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_runtime.h"
#include "firmware/himax_arc/birdhouse/bh_pdm_diag.h"
#include "firmware-sdk/at-server/ei_at_server.h"
#include <utility>

// The SDK parser calls substr(npos) for an all-whitespace line. Interpose its
// external call from ATServer, keeping vendor code unchanged. The mangled name
// is shared by the pinned ARC and host C++11 SDK builds; link/audit fails if the
// SDK ABI changes. Empty input follows the SDK's own AT_UNKNOWN path.
extern "C" const ATParseResult_t& BhRealAtParse(ATParser*, std::string)
    asm("__real__ZN8ATParser5parseENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
extern "C" const ATParseResult_t& BhWrapAtParse(ATParser*, std::string)
    asm("__wrap__ZN8ATParser5parseENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
extern "C" const ATParseResult_t& BhWrapAtParse(ATParser* parser, std::string input) {
  if (input.find_first_not_of(" \t") == std::string::npos) input.clear();
  return BhRealAtParse(parser, std::move(input));
}

// Existing SDK handlers; their implementations remain in the vendor tree.
bool at_sample_start(const char**, int);
bool at_run_impulse();
bool at_run_impulse_debug(const char**, int);
bool at_run_impulse_cont();
bool at_take_snapshot(const char**, int);
bool at_get_snapshot();
bool at_snapshot_stream(const char**, int);

namespace {
bool OwnsResources() {
  return bh::RuntimeState() == bh::kRunCapturing || bh::RuntimePendingRuns() != 0 || bh_port_pdm_faulted();
}
bool VendorBlocked() {
  bh_port_printf("BIRDHOUSE ERROR busy: vendor sampling/camera command refused\n");
  return true;
}
bool GuardSample(const char** a, int n) { return OwnsResources() ? VendorBlocked() : at_sample_start(a, n); }
bool GuardRun() { return OwnsResources() ? VendorBlocked() : at_run_impulse(); }
bool GuardDebug(const char** a, int n) { return OwnsResources() ? VendorBlocked() : at_run_impulse_debug(a, n); }
bool GuardContinuous() { return OwnsResources() ? VendorBlocked() : at_run_impulse_cont(); }
bool GuardSnapshot(const char** a, int n) { return OwnsResources() ? VendorBlocked() : at_take_snapshot(a, n); }
bool GuardStream(const char** a, int n) { return OwnsResources() ? VendorBlocked() : at_snapshot_stream(a, n); }
uint32_t ParseU32(const char* text, bool* ok) {
  *ok = false;
  if (text == nullptr || *text == '\0') return 0;
  uint32_t v = 0;
  for (; *text != '\0'; ++text) {
    if (*text < '0' || *text > '9') return 0;
    const uint32_t digit = static_cast<uint32_t>(*text - '0');
    if (v > (0xFFFFFFFFu - digit) / 10) return 0;
    v = v * 10 + digit;
  }
  *ok = true;
  return v;
}

bool Busy() {
  if (bh::RuntimeState() != bh::kRunCapturing && bh::RuntimePendingRuns() == 0 &&
      !bh_port_pdm_faulted() && !bh_port_vendor_busy()) return false;
  bh_port_printf("BIRDHOUSE ERROR busy\n");
  return true;
}

bool AtInfo() {
  bh::RuntimePrintInfo();
  return true;
}

bool AtRunOnce() {
  const int rc = bh::RuntimeRequestRuns(1);
  bh_port_printf("BIRDHOUSE RUN queued=%d rc=%d\n", rc == 0 ? 1 : 0, rc);
  return true;
}

bool AtRunMany(const char** argv, const int argc) {
  bool ok = false;
  const uint32_t n = argc == 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || n != 1) {
    bh_port_printf("BIRDHOUSE ERROR bad run count\n");
    return true;
  }
  const int rc = bh::RuntimeRequestRuns(n);
  bh_port_printf("BIRDHOUSE RUN queued=%lu rc=%d\n", static_cast<unsigned long>(rc == 0 ? n : 0), rc);
  return true;
}

bool AtStop() {
  bh::RuntimeCancel();
  bh_port_printf("BIRDHOUSE STOP state=%s\n", bh::RunStateName(bh::RuntimeState()));
  return true;
}

bool AtLast() {
  bh::RuntimePrintResult(bh::RuntimeLastResult());
  return true;
}

bool AtDmaQuery() {
  if (bh::RuntimeState() == bh::kRunCapturing || bh::RuntimePendingRuns() != 0) return true;
  bh_port_pdm_diag_print();
  return true;
}
bool AtDmaArm(const char** argv, const int argc) {
  bool ok = false;
  const uint32_t one = argc == 1 ? ParseU32(argv[0], &ok) : 0;
  if (Busy()) return true;
  const int rc = ok && one == 1 ? bh_port_pdm_diag_arm() : -2;
  bh_port_printf("BIRDHOUSE DMA arm_rc=%d capture_queued=0\n", rc);
  return true;
}

bool AtSelfTest() {
  if (Busy()) return true;
  bh::RuntimeSelfTestModelAll();
  return true;
}

bool AtSelfTestStep(const char** argv, const int argc) {
  bool ok = false;
  if (Busy()) return true;
  const uint32_t step = argc == 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || bh::RuntimeSelfTestModel(static_cast<int>(step)) < 0) {
    bh_port_printf("BIRDHOUSE ERROR self-test step must be 1..8 and no capture active\n");
  }
  return true;
}

bool AtSynth(const char** argv, const int argc) {
  bool ok = false;
  const uint32_t kind = argc == 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || kind >= static_cast<uint32_t>(bh::kSynthKindCount)) {
    bh_port_printf("BIRDHOUSE ERROR bad synth kind\n");
    return true;
  }
  if (Busy()) return true;
  if (bh::RuntimeRunSynthetic(static_cast<int>(kind)) != 0)
    bh_port_printf("BIRDHOUSE ERROR synthetic run failed\n");
  return true;
}

bool AtDump(const char** argv, const int argc, bool pcm) {
  bool ok_a = false, ok_b = false;
  const uint32_t offset = argc == 2 ? ParseU32(argv[0], &ok_a) : 0;
  const uint32_t count = argc == 2 ? ParseU32(argv[1], &ok_b) : 0;
  const bool done = ok_a && ok_b &&
                    (pcm ? bh::RuntimeDumpPcm(offset, count) : bh::RuntimeDumpFeatures(offset, count));
  if (!done) bh_port_printf("BIRDHOUSE ERROR bad dump range or capture active\n");
  return true;
}

bool AtDumpPcm(const char** argv, const int argc) { return AtDump(argv, argc, true); }
bool AtDumpFeatures(const char** argv, const int argc) { return AtDump(argv, argc, false); }

void RegisterCommandsOnce() {
  static bool registered = false;
  if (registered) return;
  registered = true;
  ATServer* at = ATServer::get_instance();
  // Preserve idle behavior, prevent resource theft while capturing or queued.
  at->register_handlers("SAMPLESTART", nullptr, nullptr, GuardSample, nullptr);
  at->register_handlers("RUNIMPULSE", GuardRun, nullptr, nullptr, nullptr);
  at->register_handlers("RUNIMPULSEDEBUG", nullptr, nullptr, GuardDebug, nullptr);
  at->register_handlers("RUNIMPULSECONT", GuardContinuous, nullptr, nullptr, nullptr);
  at->register_handlers("SNAPSHOT", nullptr, at_get_snapshot, GuardSnapshot, nullptr);
  at->register_handlers("SNAPSHOTSTREAM", nullptr, nullptr, GuardStream, nullptr);
  at->register_command("BIRDINFO", "Birdhouse: version, model and configuration", nullptr, AtInfo, nullptr, nullptr);
  at->register_command("BIRDRUN", "Birdhouse: one capture attempt; stop quarantines PDM (=1 only)", AtRunOnce, nullptr, AtRunMany, "COUNT");
  at->register_command("BIRDSTOP", "Birdhouse: abort capture and queued runs", AtStop, nullptr, nullptr, nullptr);
  at->register_command("BIRDLAST", "Birdhouse: print the last result", nullptr, AtLast, nullptr, nullptr);
  at->register_command("BIRDDMA", "Birdhouse: arm one shutdown observation (=1); query stored records", nullptr, AtDmaQuery, AtDmaArm, "ONE");
  at->register_command("BIRDSELFTEST", "Birdhouse: model self-test on reference features (=STEP for one)", AtSelfTest, nullptr, AtSelfTestStep, "STEP");
  at->register_command("BIRDSYNTH", "Birdhouse: pipeline self-test on a built-in signal", nullptr, nullptr, AtSynth, "KIND");
  at->register_command("BIRDPCM", "Birdhouse: base64 dump of captured PCM", nullptr, nullptr, AtDumpPcm, "OFFSET,COUNT");
  at->register_command("BIRDFEAT", "Birdhouse: base64 dump of features", nullptr, nullptr, AtDumpFeatures, "OFFSET,COUNT");
}

}  // namespace
namespace bh {
void ConsoleRegisterCommands() { RegisterCommandsOnce(); }
}  // namespace bh
