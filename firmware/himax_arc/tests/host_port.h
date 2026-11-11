// Host implementations of the clock and print services in bh_port.h.
#ifndef BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_
#define BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_

#include <string>

namespace host_port {

// Everything printed through bh_port_printf since the last Clear().
const std::string& Output();
void Clear();
// Echo printed text to stdout as it is produced (default off).
void SetEcho(bool echo);

}  // namespace host_port

#endif  // BIRDHOUSE_HIMAX_TESTS_HOST_PORT_H_
