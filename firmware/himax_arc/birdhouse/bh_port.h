// Platform services the Birdhouse runtime needs. Implemented by
// bh_pdm_port.cc + bh_arc_glue.cc on the Himax, and by fakes in the host tests.
#ifndef BIRDHOUSE_HIMAX_BH_PORT_H_
#define BIRDHOUSE_HIMAX_BH_PORT_H_

#include <cstdint>

namespace bh {
class Capture;
}

// Starts PDM capture; audio blocks are delivered to `capture` from interrupt
// context until bh_port_pdm_stop(). Returns 0 on success.
int bh_port_pdm_start(bh::Capture* capture);
// Stops PDM capture. Returns 0 on success. A later start is always allowed.
int bh_port_pdm_stop();
// Called when the PDM driver is torn down and restarted by the audio library's
// own error handling (FIFO overflow). Interrupt context.
void bh_port_on_pdm_reinit();

// Monotonic microseconds. On the Himax this may be off by one second for a
// single reading (see bh_config.h).
uint64_t bh_port_now_us();

// printf subset: %s %c %d %u %ld %lu %lx, with width and zero padding.
// No floating point, no 64-bit integers.
void bh_port_printf(const char* format, ...);

// Prints platform facts as "BIRDHOUSE INFO ..." lines (stack use on the Himax).
void bh_port_print_platform_info();

#endif  // BIRDHOUSE_HIMAX_BH_PORT_H_
