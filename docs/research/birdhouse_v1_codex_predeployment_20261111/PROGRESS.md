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
