// Host implementations of the clock and print services in bh_port.h.
#ifndef BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_
#define BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_

#include <string>
#include <cstdint>

// Emulate a fresh process between independent test cases only. No production
// reset exists; fake_aud::Reset() alone must not reset the adapter lifecycle.
void bh_port_pdm_test_reset();

namespace host_port {

// Everything printed through bh_port_printf since the last Clear().
const std::string& Output();
void Clear();
// Echo printed text to stdout as it is produced (default off).
void SetEcho(bool echo);
// Diagnostic-only fake I/O control; zero step preserves ordinary fake clock.
void DiagConfigure(uint64_t clock_step_us, uint32_t valid = 15);
void DiagReadHook(void (*hook)(uint32_t read_number));
uint32_t DiagReads();

}  // namespace host_port

#endif  // BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_
