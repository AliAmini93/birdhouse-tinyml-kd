# Birdhouse Himax ARC Port

Target: Seeed Studio Grove Vision AI Module V1.

Status: Experimental offline port. NOT validated on hardware.

## Verified results

- Steps 24-25: Model assets, preprocessing and BirdModel
  compiled successfully for ARC.
- Step 26: Birdhouse components linked with the Himax SDK.
- Step 27: Model weights and Mel constants were confirmed
  in the linked ELF SYSTEM0 read-only data section.
- Step 28: All 249 PCM windows matched on the host.
- Step 29: Streaming Log-Mel matched the reference INT8
  preprocessing exactly on three synthetic host signals.
- Step 30: Actual Streaming code generation for ARC passed.
- Step 31: Simulated stereo PDM bridge passed host parity
  and compiled for ARC.
- Step 32: Bridge linked successfully into offline ELF.
- Step 33: Host audio queue tests passed; ARC compilation
  FAILED due to the lock-free atomic static assertion.

## Memory after Step 32

- ICCM1: 292342 / 327680 bytes (89.22%)
- SYSTEM0: 403668 / 1439744 bytes (28.04%)
- DCCM: 66448 / 253952 bytes (26.17%)

These are linker-reported placements, not measured runtime
memory usage.

## Important limitations

- No firmware has been flashed to the Grove Vision AI V1.
- No runtime inference on the board has been verified.
- No actual PDM capture has been verified.
- No real-time latency measurement is available.
- Step 33 requires an interrupt-safe queue implementation
  suitable for the Himax ARC target.
- The experiments contain prototypes, not production code.
- Some experiment Makefile fragments rely on separate
  SDK/toolchain files and objects in .local-tools.
- The streaming prototype duplicates FFT logic. It should
  be refactored before production integration.

## Next work

1. Investigate ARC interrupt and atomic synchronization.
2. Fix and test the producer/consumer audio queue.
3. Integrate the production streaming audio pipeline.
4. Build and audit the final offline firmware.
5. Request explicit approval before any board write,
   flash, erase, reset, or bootloader modification.
