# Birdhouse on Grove Vision AI V1 — independent deployment assessment

Date: 2026-11-11. Author: Claude (independent review). Scope of this document: research only.
Nothing was built, flashed, reset, or sent to the board while producing it.

Status tags used throughout:

- **VERIFIED** — I checked the artefact myself (source, object code, binary, log).
- **PLAUSIBLE** — consistent evidence, not proven.
- **UNVERIFIED** — no evidence yet.
- **NOT SUPPORTED** — evidence against.

Local paths are repository-relative. `.local-tools/` is not published; it holds the vendor SDK,
toolchain, build outputs and saved diagnostics.

## 1. Independent verdict

1. **The existing stage50 ELF cannot run the model and must not be flashed.** VERIFIED.
   The vendor TFLite Micro build disables kernels per data type to suit its bundled camera model.
   INT8 `FULLY_CONNECTED` is on the disabled list. In the compiled object the kernel's `Eval` is a
   46-byte stub that returns an error, and `Prepare` returns an error for the MLI-applicable case.
   The model's final Dense layer is MLI-applicable, so `AllocateTensors` would fail at start.
   The firmware links cleanly; no host test of preprocessing or queues could have caught this.
2. **No prebuilt firmware can run this pipeline.** VERIFIED. Stock Seeed firmware has no audio path.
   Stock Edge Impulse firmware caps audio at about 4 s (ingestion) and 2.05 s (inference).
   One Himax firmware write is unavoidable for on-chip inference.
3. **The streaming queue design is unnecessary on this chip.** About 840 KB of RAM is free.
   Copying samples in the audio callback into a linear buffer and processing afterwards is the
   vendor's own pattern, and it reuses the batch preprocessing that already matched Python on the host.
4. **The prebuilt audio library behaves differently from what the code assumed.** VERIFIED by
   disassembly: the callback runs in interrupt context, blocks are re-armed in software, and
   overruns and FIFO overflows are handled silently.
5. **Hardware-only unknowns remain:** PDM continuity, real CPU clock, inference latency, transport
   behaviour on the development PC, and which application is installed on the board today.

## 2. System as established

```
 Linux PC ──USB── BL702 (own flash, mask-ROM recovery)
                   │  bootloader mode 2886:0060: TinyUF2 (CDC + mass storage)
                   │  normal mode     2886:8060: CDC bridge to the Himax UART
                   │
                   ├─UART ── XMODEM ──► Himax first-stage bootloader ─► burns Himax flash   [link PLAUSIBLE]
                   ├─I2C, HX_RST, two GPIO sync lines
                   └─SPI through an analog switch ──► external P25Q32SH, 4 MB           [VERIFIED]
                                                       model slots at 0x30000000 + n·1 MB
                                                       default side of the switch: Himax (XIP read)
 Himax HX6537-A (ARC EM9D, hardware single-precision FPU, application runs from RAM)
   flash image, 2 MB: 2nd bootloader @0x0 · bootloader @0x10000 · layout @0x20000
                      loader config @0x21000 · application @0x22000
   RAM regions: ICCM1 320 KB code · BOOT 130 KB · SYSTEM0 1406 KB · DCCM 248 KB + 8 KB stack
                X/Y CCM 32 KB each
   PDM microphone MSM261D3526H1CPM ── prebuilt audio library (no source)
   Grove I2C ── Himax I2C slave ◄── Arduino-compatible host for the documented repair   [untested]
 JTAG: no pin evidence. Boot-ROM I2C boot: only if the flash bootloader is missing or invalid,
 image ≤128 KB, verified.
```

## 3. Evidence table

| Claim | Status | Evidence |
|---|---|---|
| INT8 FULLY_CONNECTED disabled in stage50 | VERIFIED | `ei-model/tflite-model/trained_model_ops_define.h`; ARC section of `kernels/fully_connected.cc`; `nm`/`objdump` of the built `fully_connected.o` (`Eval` is 0x2e bytes and returns 1) |
| CONV_2D, DEPTHWISE_CONV_2D, MEAN, LOGISTIC are real | VERIFIED | object symbols `EvalMliQuantizedPerChannel`, `EvalMeanHelper`, `LogisticEval` |
| Conv and depthwise use the ARC MLI path | VERIFIED (source) | `IsMliApplicable` in `conv.cc`, `depthwise_conv.cc` |
| Audio callback runs inside the DMA-complete interrupt | VERIFIED | disassembly: `pdm_rx0_rx_ISR` → `hx_lib_audio_rx_callback` → tail call to the application callback |
| Each block is re-armed in software from that interrupt | VERIFIED | `hx_lib_audio_rx_callback` calls `hx_drv_pdm_init_transfer` |
| Ring overrun and FIFO overflow are silent to the application | VERIFIED | overrun: console print, both indices reset; FIFO error: console print, PDM de-init/re-init, block restarted |
| `block_sz` is bytes, blocks are contiguous, more than 50 blocks halts the CPU | VERIFIED | `hx_lib_audio_start` disassembly and its assert string |
| `request_read` returns only the contiguous run; `update_idx` wraps to 0 | VERIFIED | disassembly |
| Default PDM clock source is the 24 MHz crystal | VERIFIED | initial data of the library's clock-source variable |
| Vendor microsecond clock is 64-bit, built on a 1 s tick assuming 400 MHz; can jump by 1 s transiently | VERIFIED (code) | `board_get_cur_us`, `sys_timer_isr` |
| Stack is 8 KB, heap about 148 KB | VERIFIED | application linker script; heap symbols |
| 160 KiB tensor arena was never validated | VERIFIED (absence) | `docs/16_tflite_micro_model_asset_plan.md` calls it a starting value |
| Bootloader regions are byte-identical in the factory image, the Edge Impulse image and the SDK | VERIFIED | SHA comparison of UF2 payloads against SDK bootloader binaries |
| Model UF2 is written by the BL702 over SPI to a separate chip | VERIFIED (strings, schematic) | bootloader binary strings; "SPI FLASH SWITCH" schematic sheet |
| BL702 bootloader v2.0.1 checks UF2 magic and family and references both base addresses | VERIFIED for v2.0.1 | constants in the release binary; bounds checks UNVERIFIED; the installed 2022 build was not inspected |
| No `CURRENT.UF2` readback | VERIFIED for v2.0.1 | FAT directory entries in the binary |
| Probe-phase hangs on the Linux PC; USB serial string is uninitialised memory | VERIFIED (log) | saved kernel log; cause PLAUSIBLE |
| Seeed's repair: I2C procedure from an Arduino-compatible board | VERIFIED (doc, source), untested | `Seeed_Arduino_GroveAI` library and FAQ |
| Himax serial flashing: 115200, key within 0.3 s of reset, option 1, XMODEM | VERIFIED for the WE-I Plus EVB | Himax user guide; UNVERIFIED on this board |

## 4. Option matrix

| Option | On-chip inference | Flash needed | Status | Main obstacle |
|---|---|---|---|---|
| Stock Seeed firmware + model-only UF2 | no | model slot | NOT SUPPORTED | no audio front end |
| Edge Impulse prebuilt + host inference | no | maybe none | rejected for the goal | off-chip; ≤4 s capture |
| Edge Impulse-native impulse | yes | firmware | NOT SUPPORTED for this model | needs a ≤2 s window |
| Stage50 as built | — | — | NOT SUPPORTED | kernel stub |
| Vendor application intact + Birdhouse module | yes | 1 firmware | recommended | runtime behaviour untested |
| Trimmed vendor fork with AT console | yes | 1 firmware | viable, deferred | vendor handler edits, no functional gain for the first run |
| Minimal dedicated application | yes | 1 firmware | viable fallback | loses vendor console and capture path |
| Seeed example framework + audio example | yes | 1 firmware + slot | more unknowns | second codebase |
| RAM execution / JTAG | — | — | NOT SUPPORTED | no pins, no probe |
| Other hardware | not on V1 | — | out of goal | — |

## 5. Ranked designs

1. **Vendor Edge Impulse application left intact, plus an isolated Birdhouse module** reached by a
   console command. Capture-then-process; model compiled in; INT8 kernels enabled; larger arena;
   application-level dropout detection; diagnostics that let the host recompute the result from the
   captured audio.
2. **Trimmed vendor fork** keeping the AT console. Saves about 261 KB of data and an estimated
   20–30 KB of code, at the price of edits in vendor handlers.
3. **Minimal dedicated application** on the same SDK. Smallest image; all glue is new.

Rejected: stage50 as built, model-only on stock firmware, Edge Impulse-native impulse for this
model, host-side inference, RAM execution, other hardware.

## 6. Adversarial audit of the stage50 code

- **Operator stub (critical).** See section 1.
- **Arena.** 160 KiB never exercised; peak activations alone are about 140 KB by calculation.
- **Adapter versus real library semantics.** The modulo wrap handling and the
  "available > block count" check are unreachable, because `request_read` only returns contiguous runs.
  The adapter relies on the library to report dropouts; it never does.
  Error paths that return before `update_idx` lead to a silent index reset in the library.
- **Stop and re-arm.** If `stop` fails, the "started" flag stays set and every later start fails.
  A late callback after stop would push into a queue that is only reset at the next start.
- **Real-time model.** The 20 ms hop is not the constraint. Interrupt latency at each block
  boundary is, because the next block is armed from the interrupt.
- **Timeout.** Uses a vendor clock that can jump by one second; harmless for a 15 s timeout,
  harmful for timing measurements.
- **Numerics.** Host parity used the host maths library. The ARC build uses newlib `logf`,
  `sinf`, `cosf` and a software divide; ±1 differences in INT8 features are possible.
- **Packaging.** The image generation and signing step was never run for stage50.
- **What offline tests cannot show:** PDM continuity, gain and DC settling, actual sample rate,
  interrupt behaviour during inference, inference latency, stack depth, MLI numeric parity.

## 7. Minimum-risk evidence gathering (read-only)

Offline, reproducible today:

```
# kernel stub
arc-elf32-nm -S -C <stage50 build>/.../kernels/fully_connected.o
arc-elf32-objdump -d -r -C <same object>
# audio library semantics
arc-elf32-objdump -d --start-address=0x100225d4 --stop-address=0x1002293a <stage50 ELF>
# factory image integrity
sha256sum grove_ai_v02-00.uf2    # 8854e093…5b3c
```

On the PC with the board attached, observing only (each needs the owner's approval, and note that
merely attaching the board lets the OS probe it):

- `/sys/bus/usb/devices/*/idProduct` — `8060` means normal mode, `0060` bootloader.
- `udevadm info` on the serial node — check whether ModemManager will probe it.
- kernel log during a bootloader attach — count 30 s resets.
- a passive `usbmon` capture of that attach — identify the hanging SCSI command.

Decision tree: clean attach with automount off and ModemManager ignoring the device → mass-storage
transport is usable; hangs tied to MODE SENSE → retry with the usb-storage quirk; still unstable →
evaluate direct XMODEM; bootloader update only if nothing else works.

## 8. GO/NO-GO gates for any hardware write

- **G1** installed application identified; owner has decided what must be preservable.
- **G2** offline checks pass: operator audit, host inference on the same TFLM sources, packaging,
  bootloader regions equal to the factory image, UF2 addresses within 0x10000000–0x101FFFFF.
- **G3** one transport has passed a no-write rehearsal.
- **G4** recovery kit prepared: factory image hash verified; I2C repair host built and its link
  proven read-only; BL702 bootloader binary available but unused.
- **G5** direct USB port, stable power, no other process holding the serial port.
- **G6** explicit owner approval.

Factory and Edge Impulse images are fallbacks, not backups of this board.

## 9. Claims for independent challenge

1. The stage50 `fully_connected.o` has an `Eval` of 46 bytes that returns 1.
2. In `hx_lib_audio_start`, a block count above 50 halts the CPU, and block addresses are spaced by `block_sz` bytes.
3. The application audio callback executes inside `pdm_rx0_rx_ISR`, before the DMA interrupt is cleared.
4. On ring overrun the library resets both indices and reports nothing to the application.
5. Flash 0x0–0x20000 is byte-identical in `grove_ai_v02-00.uf2`, the Edge Impulse `firmware.uf2`, and the SDK bootloader binaries for `HX6537-A09TDIG-1111V`.
6. Stock Edge Impulse firmware cannot be built for an 80,000-sample audio window without source changes.
7. `grove_ai_v02-00.uf2` contains no audio, PDM or microphone code path.
8. The v2.0.1 BL702 bootloader exposes no `CURRENT.UF2`.
9. Peak activation memory of the model is 140,000 bytes, assuming SAME padding.
10. A double-buffer capture design gives gapless 5 s windows without streaming DSP, provided processing takes under 5 s.

## Limitations

- The firmware-write path from the BL702 to the Himax is inferred from both ends, not read from source.
- The BL702 analysis used the v2.0.1 release binary, not the build installed on the board.
- All timing figures are estimates.
- Recovery routes are documented by the vendors but untested here.

## Sources

- Seeed Grove Vision AI V1 wiki: https://wiki.seeedstudio.com/Grove-Vision-AI-Module/
- V1 schematic: https://files.seeedstudio.com/wiki/Grove_AI_Module/Grove_Vision_AI_NORF_v1.1.pdf
- Seeed_Arduino_GroveAI (Protocol.md, FAQs.md, library source, releases): https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI
- Seeed example firmware: https://github.com/Seeed-Studio/sscma-example-vision-ai
- Edge Impulse firmware and board documentation: https://github.com/edgeimpulse/firmware-seeed-grove-vision-ai
- Himax WE-I Plus user guide: https://github.com/HimaxWiseEyePlus/bsp_tflu/tree/master/HIMAX_WE1_EVB_user_guide
