#include "firmware/himax_arc/tests/host_port.h"

#include <cstdarg>
#include <cstdio>

#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_pdm_diag.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"

namespace {
std::string g_output;
bool g_echo = false;
uint64_t g_diag_clock_step = 0;
uint32_t g_diag_valid = kBhPdmDiagValid;
uint32_t g_diag_reads = 0;
void (*g_diag_hook)(uint32_t) = nullptr;
}  // namespace

namespace host_port {
const std::string& Output() { return g_output; }
void Clear() { g_output.clear(); }
void SetEcho(bool echo) { g_echo = echo; }
void DiagConfigure(uint64_t step, uint32_t valid) {
  g_diag_clock_step = step; g_diag_valid = valid; g_diag_reads = 0; g_diag_hook = nullptr;
}
void DiagReadHook(void (*hook)(uint32_t)) { g_diag_hook = hook; }
uint32_t DiagReads() { return g_diag_reads; }
}  // namespace host_port

uint64_t bh_port_now_us() {
  if (g_diag_clock_step) fake_aud::AdvanceTime(g_diag_clock_step);
  return fake_aud::now_us();
}
BhPdmDmaStatus bh_port_pdm_diag_read_status() {
  ++g_diag_reads;
  if (g_diag_hook) g_diag_hook(g_diag_reads);
  const BhPdmDmaStatus s = {g_diag_valid, fake_aud::running() ? 1u : 0u,
      fake_aud::counters().blocks_completed ? 1u : 0u, 0u, fake_aud::pending() ? 1u : 0u};
  return s;  // hypotheses for tests, never evidence about hardware semantics
}
uint32_t bh_port_pdm_diag_read_word(const uint32_t* word) { return *word; }
bool bh_port_vendor_busy() { return false; }
uint32_t bh_port_irq_save() { return fake_aud::IrqSave(); }
void bh_port_irq_restore(uint32_t state) { fake_aud::IrqRestore(state); }

void bh_port_printf(const char* format, ...) {
  char buffer[512];
  va_list args;
  va_start(args, format);
  std::vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);
  g_output += buffer;
  if (g_echo) std::fputs(buffer, stdout);
}

void bh_port_print_platform_info() { bh_port_printf("BIRDHOUSE INFO platform=host\n"); }
