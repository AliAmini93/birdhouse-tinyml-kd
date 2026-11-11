// Minimal test helper: named checks, a final machine-readable summary line.
#ifndef BIRDHOUSE_HIMAX_TESTS_BH_TEST_H_
#define BIRDHOUSE_HIMAX_TESTS_BH_TEST_H_

#include <cstdio>

namespace bh_test {

struct Counters {
  int passed = 0;
  int failed = 0;
};

inline Counters& counters() {
  static Counters c;
  return c;
}

inline bool Check(bool ok, const char* what, const char* file, int line) {
  if (ok) {
    ++counters().passed;
  } else {
    ++counters().failed;
    std::printf("  CHECK FAILED %s:%d: %s\n", file, line, what);
  }
  return ok;
}

// Prints "SUMMARY {...}" and returns the process exit code.
inline int Finish(const char* suite) {
  const Counters& c = counters();
  std::printf("SUMMARY {\"suite\":\"%s\",\"checks_passed\":%d,\"checks_failed\":%d,\"status\":\"%s\"}\n",
              suite, c.passed, c.failed, c.failed == 0 ? "PASS" : "FAIL");
  return c.failed == 0 ? 0 : 1;
}

}  // namespace bh_test

#define BH_CHECK(cond) ::bh_test::Check((cond), #cond, __FILE__, __LINE__)
#define BH_CASE(name) std::printf("[case] %s\n", name)

#endif  // BIRDHOUSE_HIMAX_TESTS_BH_TEST_H_
