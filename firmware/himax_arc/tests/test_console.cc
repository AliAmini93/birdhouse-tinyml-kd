// Bytes go through the vendor's actual ATServer::handle and ATParser.
#include <cstdarg>
#include <cstdio>
#include <string>
#include "firmware-sdk/at-server/ei_at_server.h"
#include "firmware/himax_arc/birdhouse/bh_console.h"
#include "firmware/himax_arc/birdhouse/bh_runtime.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/host_port.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"

// Console transport only: the parser, command registry and dispatcher are real.
void ei_printf(const char* format, ...) {
  char line[512];
  va_list args;
  va_start(args, format);
  std::vsnprintf(line, sizeof(line), format, args);
  va_end(args);
  bh_port_printf("%s", line);
}
void ei_putchar(char c) { bh_port_printf("%c", c); }
bool at_info() { return true; }  // unused vendor default INFO handler
static int vendor_calls = 0;
bool at_sample_start(const char**, int) { ++vendor_calls; return true; }
bool at_run_impulse() { ++vendor_calls; return true; }
bool at_run_impulse_debug(const char**, int) { ++vendor_calls; return true; }
bool at_run_impulse_cont() { ++vendor_calls; return true; }
bool at_take_snapshot(const char**, int) { ++vendor_calls; return true; }
bool at_get_snapshot() { return true; }
bool at_snapshot_stream(const char**, int) { ++vendor_calls; return true; }

static void Send(const char* command) {
  host_port::Clear();
  for (const char* c = command; *c != '\0'; ++c) ATServer::get_instance()->handle(*c);
}
static bool Has(const char* text) { return host_port::Output().find(text) != std::string::npos; }

int main() {
  fake_aud::Reset();
  bh::RuntimeTestReset();
  ATServer::get_instance()->register_command("SAMPLESTART", "", nullptr, nullptr, at_sample_start, "SENSOR");
  ATServer::get_instance()->register_command("RUNIMPULSE", "", at_run_impulse, nullptr, nullptr, nullptr);
  bh::ConsoleRegisterCommands();
  bh::ConsoleRegisterCommands();
  BH_CASE("numeric inputs are strict decimal uint32 across host and MCU");
  const char* bad[] = {"AT+BIRDRUN=4294967297\r", "AT+BIRDRUN=-4294967295\r",
                       "AT+BIRDRUN=18446744073709551617\r", "AT+BIRDRUN=+1\r",
                       "AT+BIRDRUN=1,2\r", "AT+BIRDRUN=\r", "AT+BIRDRUN=1x\r"};
  for (const char* cmd : bad) {
    Send(cmd);
    BH_CHECK(Has("BIRDHOUSE ERROR bad run count"));
    BH_CHECK(bh::RuntimePendingRuns() == 0);
    bh::RuntimeCancel();
  }
  BH_CASE("actual dispatcher routes read, run, write and CRLF");
  Send("AT+BIRDINFO?\r\n");
  BH_CHECK(Has("BIRDHOUSE INFO version="));
  Send("AT+BIRDSYNTH=0\r");
  BH_CHECK(Has("source=SYNTH state=DONE decision="));
  Send("AT+BIRDPCM=0,1,2\r");
  BH_CHECK(Has("BIRDHOUSE ERROR"));
  Send("AT+BIRDRUN=2\r");
  BH_CHECK(bh::RuntimePendingRuns() == 2);
  Send("AT+SAMPLESTART=Microphone\r");
  BH_CHECK(Has("vendor sampling/camera command refused") && vendor_calls == 0);
  Send("AT+RUNIMPULSE\r");
  BH_CHECK(Has("vendor sampling/camera command refused") && vendor_calls == 0);
  Send("AT+BIRDSYNTH=1\r");
  BH_CHECK(Has("BIRDHOUSE ERROR busy"));
  bh::RuntimePoll();
  Send("AT+BIRDSYNTH=1\r");
  BH_CHECK(Has("BIRDHOUSE ERROR busy"));
  Send("AT+BIRDSTOP\r");
  BH_CHECK(Has("BIRDHOUSE STOP state=FAILED"));
  BH_CHECK(bh::RuntimePendingRuns() == 0 && !fake_aud::running());
  Send("AT+RUNIMPULSE\r");
  BH_CHECK(vendor_calls == 1);
  Send("AT+BIRDSELFTEST=4\r");
  BH_CHECK(Has("step=4 out_q=12 expected_q=12 abs_diff=0"));
  Send("AT+BIRDPCM=0,1\r");
  BH_CHECK(Has("BIRDHOUSE ERROR"));
  Send("AT+BIRDFEAT=0,10\r");
  BH_CHECK(Has("BIRDHOUSE DUMP BEGIN what=features_s8"));
  return bh_test::Finish("console");
}
