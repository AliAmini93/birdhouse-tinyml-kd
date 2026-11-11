# Codex independent predeployment audit — 2026-11-11

Reviewed starting point: `120a72831db4d36904848a2b92e5a366d3ae5451`.
Branch: `research/birdhouse-v1-predeployment-codex-20261111`.
All work is offline. Hardware deployment remains **NO-GO**.

## M1 — capture ownership and output validity: PASS

Found and fixed: late callbacks could mutate completed statistics or latch an
error after ownership returned to main; callback target survived stop indefinitely;
failed stop allowed an unconfirmed DMA engine to restart; failed start did not
clean up a partially enabled driver. Publication/reset and detachment now use IRQ
exclusion with compiler barriers. No masking during PCM copies. Stop failure
quarantines new starts until an explicit successful `BIRDSTOP` retry. Detached
callbacks never call the audio library or dereference the previous capture.

The old late-callback test had an empty ring and the stop fake always disabled
DMA even on failure. Tests now inject a nonempty ring, callback inside stop,
request errors, DMA continuing after failed stop, partial start failure, and a
destroyed callback target. These are adversarial API interleavings, not proof of
physical interrupt behavior.

A backward BSP clock read no longer underflows the capture deadline. CLOCK and
SUSPECT runs retain diagnostic raw inference but print `decision=NONE` and stop
queued runs. A tick-sized timing gap cannot be proven harmless. Dumps now expose
only data produced by the current sequence, including only the captured prefix
of an aborted recording; self-test cannot relabel an old PCM buffer.

Reproduce (existing toolchain/SDK only):

```sh
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 make -C firmware/himax_arc/tests -j8 run-unit SAN=1
make -C firmware/himax_arc/tests -j8 run-tflm
tools/himax/sdk_make.sh .local-tools/port-himax/bh-codex-m1 -j8
```

Suite totals: `results/m1.json`. Host inference 28/28 bit exact, 586 assertions;
ARC build succeeds without first-party warnings; SDK working tree stays pristine.
LeakSanitizer is unavailable under this sandbox's tracing environment. Address and
undefined-behavior checks remain enabled. The existing Makefile did not instrument
vendor TFLM objects; that coverage gap is addressed in the later tooling milestone.

## M2 — real vendor serial command integration: PASS

Moved the existing first-party AT handlers into `bh_console.cc`, compiled on
both host and ARC. Host tests send bytes through unmodified vendor ATServer,
ATParser, line buffer/history and singleton sources, not a fake registry. Only
printing/transport and hardware handler endpoints are stubbed.

The new adversarial test failed 11 assertions before fixes: signed and oversized
numbers wrapped/truncated to run counts; extra arguments were accepted; synthetic
requests while capturing were silently ignored and could overwrite queued work.
Strict decimal uint32 parsing and exact argument counts now agree across ILP32
and LP64. Busy operations emit explicit errors. Vendor sampling/camera AT handlers
are guarded while Birdhouse captures or has queued work; idle handlers still
forward to the SDK. Birdhouse refuses requests while vendor inference/streaming
is active or the PDM stop fault remains latched.

Reproduce M1 commands plus the integrated `test_console` suite in `run-unit`.
`results/m2.json` records the regression and post-fix results. ARC builds using
the same new handlers. Vendor header warnings from the camera API are visible;
M3 strengthens warning attribution rather than treating a successful link as proof.

M1 synchronization: local and remote were both
`30e713139ea6a8d3eff18c222839020f3543f774` immediately after its successful push.

## M3 — independent validation, packaging and recovery review: PASS / BLOCKED

**Offline validation PASS: 22/22**, recorded in `results/validated/summary.json`.
Six fully instrumented capture/runtime/console/preprocessing suites pass 796
assertions; host model inference passes 586 assertions with 28/28 raw outputs
bit-exact. Real vendor kernel and AT object instrumentation is checked separately.
The stored Python preprocessing oracle matches all 9,960 output elements.

Further repaired issues: the legacy preprocessing parity program returned zero
on WARN; it now fails its process status. The SDK AT parser threw on whitespace;
a small link interposition uses its own empty-input path, with real-dispatcher
regression coverage and an ARC post-link call-site check. Unexpected callback
batch size now invalidates capture timing even when timestamps appear regular.

Tooling now instruments vendor TFLM as well as first-party objects, tracks vendor
header dependencies, regenerates all three reference files outside tracked
sources, rejects unsafe make arguments/inherited make options, preserves old
build/results trees and marks skipped checks NOT_RUN/PARTIAL. Backend value 2 is
rejected (the SDK selects ARC only with ==1); the final ELF must contain the real
INT8 MLI workers. First-party ARC warnings are fatal; system-header warnings are
attributed to their actual diagnostic filename, including parallel make output.

Packaging supplies the ARC tools explicitly (the old implementation relied on
ambient PATH), runs in a namespace hiding devices, USB metadata, host sockets,
mounted media and network, and checks every ELF payload byte and destination in
binary loader descriptors. Deliberate payload/descriptor corruptions are rejected.
The packager/converter preserve prior outputs and never enumerate USB or deploy.
SOURCE_DATE_EPOCH pins the SDK build stamp. Two clean builds yield the same ELF;
two packaging runs yield the same image. All generated binaries remain local.

Initial failed runs are preserved locally. The first exposed vendor-header
warnings after enabling Werror; the second exposed misattribution of an
interleaved vendor warning. Both are fixed with focused regressions. The final
22-step report is a fresh run and inherits no earlier PASS records.

Stack safety is explicitly UNPROVEN: the frame sum omits nested/prebuilt/library
and interrupt paths. Heap capacity is a linker figure, not current free heap.
Recovery readiness remains BLOCKED on missing local assets and all physical
checks remain untested. `RECOVERY_REVIEW.md` defines the review gates.

M2 synchronization: local and remote were both
`bf19a7ad12e82976575ad557995faba9eed696c8` immediately after its successful push.
