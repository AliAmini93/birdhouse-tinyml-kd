# Birdhouse V1 PDM P1/P4 offline remediation and validation
OWNER-AUTHORIZED INTERACTIVE OFFLINE PDM SAFETY MISSION — 2026-11-13

Run in a LIVE INTERACTIVE Codex TUI. Owner must be able to observe, steer, and interrupt the work. Work autonomously on safe offline research and approved first-party code/tests. No codex exec, headless jobs, background agents, or hardware actions. This stage is NOT a Flash authorization.

Repository: PUBLIC AliAmini93/birdhouse-tinyml-kd. Dedicated branch: research/birdhouse-v1-pdm-safety-offline-20261113. Source baseline commit: 5361a74143f909d6cc113f4cf0a9b35e8614240a. The branch is independent of the existing validated baseline; do not change previous candidate images, other branches, or main.

Device: Grove Vision AI V1, Himax HX6537-A with BL702. The only physical board remains on a separate Windows 10 PC, not the Ubuntu development host. The Windows read test demonstrated limited 10-minute visible USB MSC stability; no firmware has ever been written in this investigation. First Flash and real capture remain NO-GO.

All research/test Python MUST use "/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3", available as $BH_PYTHON, preferably with -I -B. Never create a virtualenv, use python/python3/pip/uv/conda, or install software. Offline native C++ tests may use existing g++/make. ARC cross-compile/link is allowed ONLY after static audit of the exact command and dependencies; no device/flash/OTA/UF2 utility execution, even to request help.

## Baseline and real constraints (READ FIRST)
- docs/research/birdhouse_v1_deployment_barriers_20261111/ASSESSMENT.md and results/barrier_audit.json
- docs/research/birdhouse_v1_windows_uf2_write_audit_20261113/FINAL_GO_NO_GO.md, RECOVERY_AND_ROLLBACK_GATES.md, UF2_WRITE_MECHANISM_AUDIT.md
- docs/research/birdhouse_v1_codex_predeployment_20261111/HANDOFF_REPORT.md and validated results
- docs/research/birdhouse_v1_implementation_20261111/OFFLINE_VALIDATION_REPORT.md
- First-party firmware: firmware/himax_arc/birdhouse/bh_pdm_port.cc, bh_capture.cc/h, bh_port.h, bh_runtime.cc, bh_arc_glue.cc, bh_config.h
- Test harness: firmware/himax_arc/tests/fake_aud_lib.cc/h, test_pdm_port.cc, test_capture.cc, test_runtime.cc, host_port.cc, Makefile
- Previous deployment audit tools: tools/himax/audit_deployment_barriers.py and tools/himax/tests/test_deployment_barriers.py.
- Cached vendor SDK in ignored .local-tools/source, if present. Read-only, no proprietary copying or publishing. Inspect only source/disassembly as inert data.

Established P1 evidence: vendor PDM ISR calls vendor RX callback BEFORE completion IRQ clear, and vendor RX callback RE-ARMS DMA BEFORE invoking application callback. The first-party stop function detaches Capture under IRQ protection but restores interrupts BEFORE calling vendor stop. Vendor stop disables/resets DMA; the reset's effect on pending interrupt is unknown. A pending old completion could re-arm DMA after stop or contaminate the next run. Startup interrupt masking is intentional because vendor enables DMA before publishing queue count; do not casually remove it.

P2 limit: current fake_aud_lib simulates application callbacks, not true vendor ISR re-arm/IRQ acknowledgment or pending-completion semantics. Host test PASS cannot claim physical stop quiescence.
P3 limit: hx_lib_audio_start ignores a lower driver transfer result; API success does not prove DMA progress.
P4: vendor io_pdm_rx_open ready-bit poll lacks a timeout. Boot init and FIFO-error ISR recovery may enter it. Main-loop 8s capture timeout cannot unblock boot or ISR.

## Goal and research gates
The goal is a smallest defensible P1/P4 mitigation, tests with negative controls, and a clear remaining physical gate. DO NOT force a patch or fabricate a PASS. Read older evidence critically and explore independently at least two feasible approaches, including fail-closed behavior when actual quiescence cannot be proven. Bound the investigation: prioritize actionable implementation or a clear vendor-level BLOCKED finding, not repeated broad audits.

R0: Freeze baseline code hashes, source-linked evidence, acceptance criteria and exact test commands. Produce R0_BASELINE_AND_CONTRACT.md BEFORE changing code. Inspect all offline build/test commands for any device access or side effects, especially old scripts that check USB and vendor packagers.

R1 (P1): Reason precisely about IRQ masking, vendor callback and DMA re-arm, pending IRQ acknowledgment, stop failure, partial start and next-run contamination. If vendor semantics support a safe change, implement the smallest first-party change with bounded critical sections and correct IRQ restore, preserving other channels and the capture owner lifetime. If stop quiescence cannot be established, prefer explicit fail-closed capture lifecycle to unsupported hardware writes. No guessed register writes, no blanket IRQ disable, no assumption that channel reset clears pending completion. Strengthen fake driver/ISR model, as a model, with ordering of rearm before callback and completion clear after; pending completion before/during/after stop; stale IRQ across stop/restart; failure and ring-wrap cases. Include adversarial/negative tests that FAIL a deliberately broken implementation, plus existing regression tests. Never label a model-only test as hardware validation.

R2 (P4): Trace boot and ISR error paths to io_pdm_rx_open. Determine whether a documented bounded low-level API or first-party interception can genuinely prevent unbounded waiting. A main-loop timer, fake return value, thread timeout, watchdog reboot, polling of a fake driver, or access to a system clock from another context does NOT prove a blocked boot/ISR returns. If P4 requires vendor source or unsupported driver changes, mark VENDOR_LEVEL_BLOCKED and specify exact missing vendor evidence/patch prerequisites. Do not edit prebuilt/vendor binary or proprietary SDK, replace internal register logic, or claim P4 closed without a complete call-path argument.

R3: Run focused host tests, ASan/UBSan where available and compile checks. Recheck model/preprocess regression if the change could affect them; avoid pointless full rebuilds of untouched components. If an existing safe reviewed ARC link recipe is feasible, use a DIFFERENT ignored output directory, label artifact OFFLINE_ONLY / NOT_FOR_FLASH and audit symbols and memory. Do not package UF2, run vendor image generators, make flash, talk to the board or regenerate known-good artifacts. Independently challenge your final diff against the real ISR evidence. A test fake that assumes what the patch needs to prove is not evidence. If a patch cannot be justified, undo only experimental source edits with ordinary edits (never git reset --hard) and document the negative result.

## Safety and publication
Absolutely NO hardware enumeration or I/O, /dev, /sys, lsusb, udevadm, serial, mass storage, I2C, GPIO, USB, BOOT, reset, Flash, erase, recovery execution, vendor deploy tools, OS power/service/driver changes, sudo, privileged commands or sandbox bypass. The agent cannot access the other Windows PC. Never ask the owner to bypass protections. If hardware work is needed, STOP.
Only first-party code/test edits under firmware/himax_arc/birdhouse and firmware/himax_arc/tests, and narrowly scoped first-party tools/himax/tests analyzers when required. Do not edit model weights, preprocessing constants, signing assets, SDK, vendor files, existing validated candidate, or current bootloader. No changes to launchers or project automation.
Public repo confidentiality: never publish proprietary source or compiled binaries, .elf/.uf2, private/raw audio, serials or their hashes, unique device identities, personal paths, credentials or raw USB logs. Do not commit private test outputs. Reports must be sanitized.
Write the following NEW reports under docs/research/birdhouse_v1_pdm_safety_20261113:
1. R0_BASELINE_AND_CONTRACT.md
2. P1_ISR_STOP_RACE_REMEDIATION.md
3. P4_BOOT_ISR_POLLING_DECISION.md
4. OFFLINE_TEST_AND_BUILD_MATRIX.md
5. FINAL_GO_NO_GO.md
6. results/summary.json
If genuine code changes are unsafe, still report and test the constraints rather than invent a fix.

At each completed logical phase, privacy-check, commit safely and try a normal push to the same dedicated branch. Compare git rev-parse HEAD and git ls-remote plus a clean worktree. No force push, git reset, git clean, rebase, branch switching or main merge. If restricted Codex sandbox DNS blocks GitHub, STOP network retries without changing sandbox/host configuration, keep local commits, report NETWORK_BLOCKED and give owner safe ordinary-terminal fast-forward push and verification commands. An unsynced local commit is not SYNC_OK.

Finish with a concise PERSIAN summary identifying P1 status, P4 status, tests, remaining unknown hardware behavior, file paths, local and remote SHAs, and what must happen before a human-approved Windows 10 Flash. This mission NEVER authorizes physical deployment.
