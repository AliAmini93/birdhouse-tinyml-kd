# Offline check results

Generated 2026-11-11T10:19:28Z at commit `8a4d8dfbe69c` (tree may contain later edits).

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

Reproduce with `python3 tools/himax/run_offline_checks.py` using the project interpreter.
