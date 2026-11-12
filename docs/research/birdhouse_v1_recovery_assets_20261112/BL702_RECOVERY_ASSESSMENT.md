# BL702 recovery and bootloader v2.0.1 assessment (offline)

**Verdict: BL702 update NO-GO. A documented, ROM-based repair path exists but has not been verified
on this board or host.**

## What the BL702 is responsible for

The BL702 is the board's USB device. Evidence from A1 and the cached C1/C3 metadata shows one BL702
image provides both personalities:

| Mode | VID:PID | Function | Evidence |
|---|---|---|---|
| UF2 bootloader | `2886:0060` | Mass-storage GROVEAI drive plus CDC | Descriptor in v2.0.1 image; 27 journalled sessions, all with MSC and resets |
| Bridge / application | `2886:8060` | CDC-ACM (`ttyACM0`) plus driverless vendor/WebUSB interface | Descriptor in v2.0.1 image; current board (C1/C3) |

The image's SFUD SPI-flash driver suggests that UF2 writes are programmed into the Himax SPI flash
by the BL702 itself. If so, the UF2 route does not depend on a healthy Himax application or loader.
This is an inference from strings and has not been verified.

## Installed versus v2.0.1

| | Installed (cached `INFO_UF2.TXT`) | Official v2.0.1 |
|---|---|---|
| Build | `2d5b48b`, Aug 23 2022 | v2.0.1, Apr 4 2023 (first uploaded 2023-04-04, re-uploaded unchanged 2023-10-17) |
| SDK base | bl_mcu_sdk V1.4.3-8-g8742503a | same |
| Model / Board-ID | Seeed Studio Grove AI / Grove AI | Seeed Studio Grove Vision AI / Grove Vision AI |
| `8060` descriptor | bcdUSB 2.10, EF/02/01, bcdDevice 01.00 (live C1) | identical fields |
| UF2 family accepted | factory UF2 family `0xef32c892` (assumed) | `0xef32c892` built in code |

**Compatibility:**
- Same SDK tag, same VID/PIDs and descriptor class, and the same UF2 family as the factory and
  candidate images. That is consistent with a drop-in replacement for the same hardware.
- bcdDevice is 01.00 in both, so the running version cannot be told apart from USB metadata alone.
- Seeed's wiki states: *"The latest version of the BootLoader has now fixed the problem of Vision AI
  not being able to be recognised by Mac and Linux."* That is the symptom family observed here (the
  `0060` MSC reset loop). No changelog or source in the downloads explains the fix, so it remains a
  **vendor claim**.

## Official update path (documented only; not performed)

The Seeed wiki procedure:
1. Use Windows `BLDevCube.exe`, select BL702/704/706, View → MCU, and choose the `.bin` as the Image
   file.
2. With no other devices attached, **hold BOOT while connecting** the module and release it when the
   5 V and 3.3 V LEDs light. This is the BL702 ROM boot path. A BOOT double-click instead enters
   TinyUF2.
3. Refresh, choose the port, Open UART, set **Chip Erase = True**, then Create&Program.

What follows from that procedure:
- **No self-update path.** Seeed provides no UF2 self-updater for the bootloader, so TinyUF2 cannot
  replace itself through GROVEAI.
- **The ROM ISP device identity on this host is unknown.** Its VID:PID, driver and whether it
  presents as a serial port are not established. The ROM ISP path does not use the `0060` MSC
  interface, so the reset loop does not apply to it.
- **Chip erase removes both USB personalities** until programming completes. An interrupted
  programme leaves only ROM ISP. ROM ISP is in mask ROM, so in principle it can always be re-entered
  with BOOT held; this has not been tested here.
- **No rollback to `2d5b48b`.** The installed binary has never been obtained. Rollback is limited to
  re-programming v2.0.1.
- **Irreversible options must stay off.** Bouffalo's official Flash Cube guide documents eFuse
  programming and encryption/signature modes for BL702. These are irreversible and must not be
  enabled.
- **Tool choice.** The official tool is Windows-only. Linux use would mean Bouffalo Flash Cube
  (official, CLI/GUI) or unofficial tools (e.g. `blisp`). Each requires separate review, and none
  may be run in A1.

## BL702 recovery is not Himax recovery

- A BL702 update rewrites the BL702's own boot flash. The Himax firmware is expected to be
  untouched, since the BL702 reaches the Himax SPI flash only through its UF2 logic. This is not
  verified, and the board schematic is not available locally.
- Conversely, factory UF2 or I2C operations do not repair the BL702.
- Each component needs its own route and its own gate.

## Requirements before any BL702 action

1. **Owner approvals:** the owner accepts that there is no exact rollback and approves one image hash
   (`5b0773315e…d1d9c`).
2. **Read-only ROM ISP check:** the ROM ISP identity is verified first. That means a separately
   approved, enumeration-only observation with BOOT held, no programming, and a defined return path.
3. **Tool reviewed:** the tool, host OS and configuration are reviewed, with eFuse/encrypt/sign
   disabled and Chip Erase scope understood.
4. **Stable power and a stop rule:** power is stable, and there is a stop rule for interruption. The
   first response to any interruption is to re-enter ROM ISP, never to attempt a Himax operation.
5. **Post-update verification:** read the new `INFO_UF2.TXT` (requires a qualified MSC window).
   Before any Himax write, confirm that `0060` no longer triggers the reset loop on the chosen host.
