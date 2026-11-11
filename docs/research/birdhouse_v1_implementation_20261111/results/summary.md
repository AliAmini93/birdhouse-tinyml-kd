# Offline check results

Generated 2026-11-11T10:40:33Z at commit `9fd8368604a8` (tree may contain later edits).

Overall: **PASS**

| Step | Status | Check | Kind |
|---|---|---|---|
| `m1_01` | PASS | model manifest is reproducible from the tracked model array | positive |
| `m1_02` | PASS | ARC compiler sees the operator overlay: configuration audit passes | positive |
| `m1_03` | PASS | vendor operator configuration is rejected by the audit | negative control |
| `m1_04` | PASS | stage50 build is rejected: disabled gate and stub kernel detected | negative control |
| `m2_01` | PASS | reference vectors are reproducible with the TensorFlow Lite interpreter | positive |
| `m2_02` | PASS | host kernels are built with the same operator gates as the firmware | positive |
| `m2_03` | PASS | host inference on vendor TFLite Micro sources: init, arena, 26 vectors, repeat, errors | positive |
| `m2_04` | PASS | host inference with the vendor operator configuration is blocked | negative control |
| `m3_01` | PASS | diagnostics helpers (CRC-32, statistics, base64, synthetic signals) | positive |
| `m3_02` | PASS | capture core: 80,000 samples, settling, boundaries, errors, timing verdicts, reuse | positive |
| `m3_03` | PASS | PDM adapter against the emulated audio library (ring wrap, faults, overrun, late callback) | positive |
| `m3_04` | PASS | end to end on host: audio emulation -> capture -> log-mel -> model -> report | positive |
| `m4_01` | PASS | vendor-only firmware builds from the pristine SDK (comparison baseline) | positive |
| `m4_02` | PASS | candidate firmware builds and links; no compiler warnings in Birdhouse sources | positive |
| `m4_03` | PASS | operator audit of the candidate: configuration, kernel objects, registrations in the ELF | positive |
| `m4_04` | PASS | post-link audit: memory, buffers, model bytes, hooks at call sites, stack chain, heap | positive |
| `m4_05` | PASS | vendor SDK working tree is unmodified after all builds | positive |

Reproduce with `python3 tools/himax/run_offline_checks.py` using the project interpreter.
