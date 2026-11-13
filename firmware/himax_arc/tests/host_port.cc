#include "firmware/himax_arc/tests/host_port.h"

#include <cstdarg>
#include <cstdio>

#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"

namespace {
std::string g_output;
bool g_echo = false;
}  // namespace

namespace host_port {
const std::string& Output() { return g_output; }
void Clear() { g_output.clear(); }
void SetEcho(bool echo) { g_echo = echo; }
}  // namespace host_port

uint64_t bh_port_now_us() { return fake_aud::now_us(); }
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
