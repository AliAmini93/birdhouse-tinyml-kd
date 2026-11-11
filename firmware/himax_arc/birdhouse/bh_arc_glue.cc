// Himax-only glue: hooks the Birdhouse runtime into the unmodified vendor
// application and exposes it as AT commands on the existing serial console.
//
// No vendor source file is edited or copied. Two functions are interposed at
// link time with the GNU linker's --wrap option (see build/birdhouse_overlay.mk):
//
//   is_inference_running()  called by the vendor main loop on every iteration.
//                           The wrapper runs bh::RuntimePoll() first and then
//                           returns the vendor's own answer unchanged.
//   hx_drv_pdm_deinit()     called by the audio library only when it recovers
//                           from a PDM FIFO overflow. The wrapper records the
//                           event and then calls the real function.
//
// Commands (all prefixed AT+ on the vendor console):
//   BIRDINFO?            version, model checksum, arena, configuration
//   BIRDRUN              one capture + classification
//   BIRDRUN=<n>          n runs back to back (gaps between runs)
//   BIRDSTOP             abort the active capture, drop queued runs
//   BIRDLAST?            print the last result again
//   BIRDSELFTEST         model on embedded reference features, 8 graded steps
//   BIRDSELFTEST=<k>     one step (1..8)
//   BIRDSYNTH=<kind>     full pipeline on a built-in integer signal (0..3)
//   BIRDPCM=<off>,<n>    base64 dump of captured PCM samples
//   BIRDFEAT=<off>,<n>   base64 dump of the feature tensor
#if !defined(BIRDHOUSE_HOST_BUILD)

#include <cstdarg>
#include <cstdint>
#include <cstdlib>

#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_runtime.h"

#include "firmware-sdk/at-server/ei_at_server.h"

extern "C" {
#include "hx_drv_pdm_rx.h"
#include "xprintf.h"
uint64_t board_get_cur_us(void);
bool __real_is_inference_running(void);
bool __wrap_is_inference_running(void);
PDM_ERROR_E __real_hx_drv_pdm_deinit(PDM_DEV_INFO* pdm_dev_info);
PDM_ERROR_E __wrap_hx_drv_pdm_deinit(PDM_DEV_INFO* pdm_dev_info);
// Linker script symbols: the stack occupies [_e_heap, _e_stack]; the startup
// code sets sp = _e_stack and the heap ends at _e_heap.
extern char _e_heap[];
extern char _e_stack[];
extern char _f_heap[];
}

uint64_t bh_port_now_us() { return board_get_cur_us(); }

void bh_port_printf(const char* format, ...) {
  va_list args;
  va_start(args, format);
  xvprintf(format, args);  // the same formatter the vendor's ei_printf uses
  va_end(args);
}

namespace {

// Stack high-water mark. The unused part of the stack is painted once from the
// main loop; later the first overwritten word marks the deepest use. Painting
// is skipped unless the current stack pointer is inside the expected region.
const uint32_t kStackPaint = 0xB1D5A11Cu;
bool g_stack_painted = false;

void PaintStackOnce() {
  if (g_stack_painted) return;
  const uintptr_t low = reinterpret_cast<uintptr_t>(_e_heap);
  const uintptr_t high = reinterpret_cast<uintptr_t>(_e_stack);
  const uintptr_t sp = reinterpret_cast<uintptr_t>(__builtin_frame_address(0));
  if (high <= low || sp <= low + 512 || sp > high) return;
  for (uint32_t* p = reinterpret_cast<uint32_t*>(low);
       reinterpret_cast<uintptr_t>(p) + 256 < sp; ++p) {
    *p = kStackPaint;
  }
  g_stack_painted = true;
}

uint32_t StackPeakBytes() {
  if (!g_stack_painted) return 0;
  const uintptr_t low = reinterpret_cast<uintptr_t>(_e_heap);
  const uintptr_t high = reinterpret_cast<uintptr_t>(_e_stack);
  const uint32_t* p = reinterpret_cast<const uint32_t*>(low);
  while (reinterpret_cast<uintptr_t>(p) < high && *p == kStackPaint) ++p;
  return static_cast<uint32_t>(high - reinterpret_cast<uintptr_t>(p));
}

uint32_t ParseU32(const char* text, bool* ok) {
  char* end = nullptr;
  const unsigned long v = std::strtoul(text, &end, 10);
  *ok = (end != text && *end == '\0');
  return static_cast<uint32_t>(v);
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
  const uint32_t n = argc >= 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || n == 0 || n > 1000) {
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

bool AtSelfTest() {
  bh::RuntimeSelfTestModelAll();
  return true;
}

bool AtSelfTestStep(const char** argv, const int argc) {
  bool ok = false;
  const uint32_t step = argc >= 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || bh::RuntimeSelfTestModel(static_cast<int>(step)) < 0) {
    bh_port_printf("BIRDHOUSE ERROR self-test step must be 1..8 and no capture active\n");
  }
  return true;
}

bool AtSynth(const char** argv, const int argc) {
  bool ok = false;
  const uint32_t kind = argc >= 1 ? ParseU32(argv[0], &ok) : 0;
  if (!ok || kind >= static_cast<uint32_t>(bh::kSynthKindCount)) {
    bh_port_printf("BIRDHOUSE ERROR bad synth kind\n");
    return true;
  }
  bh::RuntimeRunSynthetic(static_cast<int>(kind));
  return true;
}

bool AtDump(const char** argv, const int argc, bool pcm) {
  bool ok_a = false, ok_b = false;
  const uint32_t offset = argc >= 2 ? ParseU32(argv[0], &ok_a) : 0;
  const uint32_t count = argc >= 2 ? ParseU32(argv[1], &ok_b) : 0;
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
  at->register_command("BIRDINFO", "Birdhouse: version, model and configuration", nullptr, AtInfo, nullptr, nullptr);
  at->register_command("BIRDRUN", "Birdhouse: capture 5 s and classify (=N to repeat)", AtRunOnce, nullptr, AtRunMany, "COUNT");
  at->register_command("BIRDSTOP", "Birdhouse: abort capture and queued runs", AtStop, nullptr, nullptr, nullptr);
  at->register_command("BIRDLAST", "Birdhouse: print the last result", nullptr, AtLast, nullptr, nullptr);
  at->register_command("BIRDSELFTEST", "Birdhouse: model self-test on reference features (=STEP for one)", AtSelfTest, nullptr, AtSelfTestStep, "STEP");
  at->register_command("BIRDSYNTH", "Birdhouse: pipeline self-test on a built-in signal", nullptr, nullptr, AtSynth, "KIND");
  at->register_command("BIRDPCM", "Birdhouse: base64 dump of captured PCM", nullptr, nullptr, AtDumpPcm, "OFFSET,COUNT");
  at->register_command("BIRDFEAT", "Birdhouse: base64 dump of features", nullptr, nullptr, AtDumpFeatures, "OFFSET,COUNT");
}

}  // namespace

void bh_port_print_platform_info() {
  const unsigned long stack_size = static_cast<unsigned long>(
      reinterpret_cast<uintptr_t>(_e_stack) - reinterpret_cast<uintptr_t>(_e_heap));
  const unsigned long heap_size = static_cast<unsigned long>(
      reinterpret_cast<uintptr_t>(_e_heap) - reinterpret_cast<uintptr_t>(_f_heap));
  bh_port_printf("BIRDHOUSE INFO platform=himax stack_size=%lu stack_painted=%d stack_peak=%lu heap_size=%lu\n",
                 stack_size, g_stack_painted ? 1 : 0, static_cast<unsigned long>(StackPeakBytes()),
                 heap_size);
}

extern "C" bool __wrap_is_inference_running(void) {
  // First call happens in the vendor main loop, after the vendor has created
  // its AT server and initialised the microphone.
  PaintStackOnce();
  RegisterCommandsOnce();
  bh::RuntimePoll();
  return __real_is_inference_running();
}

extern "C" PDM_ERROR_E __wrap_hx_drv_pdm_deinit(PDM_DEV_INFO* pdm_dev_info) {
  bh_port_on_pdm_reinit();
  return __real_hx_drv_pdm_deinit(pdm_dev_info);
}

#endif  // !BIRDHOUSE_HOST_BUILD
