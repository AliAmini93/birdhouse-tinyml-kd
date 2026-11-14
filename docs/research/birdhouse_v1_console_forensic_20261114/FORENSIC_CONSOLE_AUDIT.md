# Exact diagnostic firmware: console forensic audit

2026-11-14. **OFFLINE_AUDIT_PASS; ARTIFACT_READY_FOR_OWNER_RISK_DECISION.**
The expected UF2 contains the expected diagnostic ELF. The compiled Himax console
requests **UART1 / 921600 baud / 8N1 / hardware flow control OFF**. Birdhouse
registers `AT+BIRDINFO?` on reaching its normal main-loop polling path. No
demonstrable incompatibility with the owner's 2022 BL702 build was established.
End-to-end console operation remains a physical experiment, with specific
unresolved bridge assumptions below. This verdict authorizes no device operation.

This was a read-only firmware investigation: file hashing, ELF disassembly,
existing map/log/config inspection and independent container parsing. There was
no rebuild, compiler/preprocessor invocation, image generation, hardware access,
mount/device discovery, Windows automation, reset or flash. Only new audit
records were written. Earlier reports and pending source changes were preserved.

## Exact artifact and provenance

Private relative path abbreviations used in this report:

- `B` = `.local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY`
- `O` = `B/arc/obj_socket_24/gnu_arcem9d_wei_r16`
- `P` = `B/package-native-terminal-01`
- `S` = `.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3`
- `A` = `.local-tools/port-himax/console-forensic-20261114-OFFLINE_ONLY`

| Actual file | Bytes | SHA-256 |
|---|---:|---|
| `P/out/birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2` | 1,260,032 | `0eb316e68ba5b88c407d9f2f907891bab722820077e40de8d93f167d746f9cf8` |
| `P/out/birdhouse_candidate_output.img` | 629,808 | `abb9a98da36447c9632d14d8b913a21480aedd8c9afbc594ffc8b91d1159fe1b` |
| `O/WEI_FW_gnu_arcem9d_wei_r16.elf` | 1,667,964 | `3e350b171ed79ae9cdc96d635475b9f6de921288adbc29aab34905d96db41eee` |
| `O/WEI_FW_gnu_arcem9d_wei_r16.map` | 8,152,787 | `be4e9f3c98562522e306ac0072642dd918e5d62d63540aeec94f34417bd15206` |

The actual ELF copies in both `P/run1/image_gen/input/` and
`P/run2/image_gen/input/` have the same expected ELF digest. Both generated
`image_gen/output/output.img` files equal the packaged image byte for byte.
`B/package-native-terminal-01.json` records PASS for all 41 checks, deterministic
two-run generation with image generator 2.5.3 and the existing sandbox workflow.
Both corresponding `image_gen.log` files finish with successful image generation.
This audit did not rerun that workflow or independently observe its execution.

The independent full UF2 parser checked every block's magic, family, flags,
payload size, numbering, total, address progression and zero padding:
**2,461 blocks**, 512 bytes/block, 256 payload bytes/block, family `0xef32c892`,
flags `0x2000`, address range `[0x10000000, 0x10099d00)`. Its 630,016 payload bytes
are exactly the image followed by 208 zero bytes. The SBS descriptor/section
reconstruction also matches **all 480,290 stored ELF bytes**, including the IVT
marker, at the expected destinations. Thus the console findings belong to this
UF2, rather than an earlier candidate. Package parity does not verify signature
acceptance, durable programming or application boot on the actual board.

The source is P1 commit `3d0fb3fd4c1889d79462bbc404aee722c1811894` **plus the
existing uncommitted diagnostic patch**. It must not be described as that commit
alone. All 98 files in `B/source-before-build.json` still match their recorded
digests; recorded source-inventory SHA-256 is
`796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e`.
Repository HEAD is `5a94940fcce5708ff686c7aaa18ae5606ee035c6`; SDK HEAD is clean at
`9dc2370d4dc269dc4bcafcf0354b8f745d08801f`.

Inspected build evidence is `B/arc-clean-build.log`, `arc-dryrun.log`,
`arc-reviewed-plan.json`, `arc-build-status.json`, the real linker map,
`O/linker_gnu.ldf`, relevant `.o.d` dependencies, `libembarc.a`,
`libboard_open_socket.a`, and `B/arc/birdhouse/tflm_config.macros`.
The archived clean build records exit 0, a new output root, no old object reuse,
and 32.71 seconds. Archived postlink, operator and diagnostic checks respectively
record **28/28, 83/83 and 14/14 PASS**. These are inspected prior results, not
newly executed tests. The actual link command contains all four wraps:
`is_inference_running`, `hx_drv_pdm_deinit`, `_dma_chan_enable`, and the exact
C++ `ATParser::parse(std::string)` symbol.

The small `.map` files in `P/run*/image_gen/input/` are vendor packaging templates,
**not** the real linker map above. The earlier `B/package-invocation.log` describes
the failed sandbox attempt; it is not evidence against the later native-terminal
package. Earlier dated BLOCKED reports remain historical records; this audit
supersedes their claim that this exact diagnostic UF2 does not yet exist.

## Compiled console configuration

| Parameter | Finding | Evidence and classification |
|---|---|---|
| UART instance | DFSS UART1, ID 1 | **VERIFIED:** final `xprintf_setup` at `0x1002e89c` passes 1 to `hx_drv_uart_get_dev`; the application obtains ID 1 again at `0x10013628`. |
| Requested baud | 921600 | **VERIFIED:** `0xe1 << 12` immediately before indirect `uart_open` at `0x1002e8be`; not a header-only conclusion. |
| Data/parity/stop | 8 bits, no parity, one stop bit | **VERIFIED:** linked `ss_uart_open` at `0x1002c274` stores `{8,0,0}` and calls `set_dps`; `set_dps` selects LCR value 3. SDK enum/header semantics agree. |
| Hardware flow | Disabled | **VERIFIED:** `ss_uart_open` passes zero to `IO_UART_SET_FLOW_CONTROL` (`0x26`). This does not establish USB control-line behavior in BL702. |
| Clock/divisor | Descriptor clock 400 MHz; divisor 27 for this requested baud | **VERIFIED** ELF data and divisor algorithm. **INFERRED** wire rate at nominal clock: about 925926 baud (+0.469%). Actual clock and wire timing are unmeasured. |
| Descriptor default | 115200 before open | **VERIFIED:** `dfss_uart_1_install` initializes 115200; the later console open supplies 921600. The descriptor default is not the effective console request. |
| Application baud reporting | Device-specific getter returns 921600 | **VERIFIED:** `EiDeviceVisionAI::get_data_output_baudrate` at `0x10011ed4`. The generic base getter returns 115200 and its default/max setters are empty; none overrides the observed console open. |
| Logical pins | UART1_RX / UART1_TX | **VERIFIED** peripheral selection; QFN72 schematic labels RX pin 36 and TX pin 37. Active pin-mux state and the owner's board revision/routing are **UNKNOWN**. |

Actual logged compiler commands for `app/main.c`,
`app/scenario_app/edge_impulse_visionai/edge_impulse_visionai.cc` and
`library/common/console_io.c` force-include
`board/socket/configs/24/core_config.h`. They define `BOARD_SOCKET`,
`BOARD_HIMAXEM9D`, `HW_VERSION=24`, `IC_PACKAGE_QFN72`, `EDGE_IMPULSE_VISIONAI`,
`GROVE_VISION_AI`, `LIB_COMMON`, `LIB_AUDIO`, `__GNU__`, `DBG_LESS`, `DEBUG` and
`NDEBUG`; C commands additionally define `__Xdmac`. All command-line definitions
are recorded, deduplicated, in the [machine-readable evidence](results/summary.json).

There is no command-line `UART_PROTOCOL`, `ENABLE_UART_BLOCKING_TASK`,
`BOARD_CONSOLE_UART_BAUD` override or `-U` option in these commands. Dependency
files select the board/24 header: its QFN72/non-`UART_PROTOCOL` branch selects
UART1 and its console baud is 921600. The conditional 9600 override in
`console_io.h` did not take effect, as the final immediate proves. The TFLM macro
probe is operator evidence, not a complete console preprocessor dump; no new
preprocessing was performed.

The Grove configuration enables `USE_I2C_SLAVE` and leaves `USE_WEBUSB` commented
out. The observed `webusb_init` sideband call is nevertheless compiled; neither
that name nor its presence establishes a Himax USB CDC endpoint.

`grove_vision_ai_config.h` defines `DEBUGGER_ATTACH_PIN=IOMUX_PGPIO1`, active 1,
and `WEBUSB_SYNC_PIN=IOMUX_PGPIO8`, active 1. The final `debugger_init` configures
PGPIO1 as input; `webusb_init` configures PGPIO8 as output and drives it low.
These are board sideband signals. They must not be assumed to be USB DTR or RTS
without bridge/routing evidence. The SDK permits alternate UART1 mux routes;
`hx_drv_iomux_init` in this ELF initializes GPIO interrupt handling, not a proven
UART pad-route selection. No physical mux state was read.

## Actual startup and registration path

| Step | Final ELF evidence |
|---|---|
| ARC entry | ELF entry `0x10000004`, `_arc_start`/`_arc_reset` in `.ivt`: cache setup, stack/global pointer, BSS clear; exception initialization and C++ constructors/init arrays precede `board_main`. |
| Board support | `board_main` `0x1002c9e0` calls `board_init` `0x1002e5d8`, then `xprintf_setup`, then infrastructure events, then `main` `0x10000800`. `board_init` installs both UART drivers before console open. |
| Vendor application | `main` calls `edge_impulse_visionai` `0x10013600`: device/camera objects, timer, debugger, WebUSB-sideband initialization, external flash, microphone, accelerometer, console UART lookup, banner, I2C server, AT initialization, prompt, loop. |
| AT Server | `ei_at_init` `0x10011924` gets the singleton and registers vendor handlers. Prompt is printed before the first Birdhouse polling hook. A prompt alone is not proof that Birdhouse registration already ran. |
| Birdhouse hook | Actual loop calls `__wrap_is_inference_running` `0x10002c58`, which calls `bh::ConsoleRegisterCommands` `0x10000c20` at `0x10002ca2`, then `RuntimePoll`, then the original vendor predicate. It runs on idle iterations and before handling an available character. |
| BIRDINFO registration | At `0x10000ce8`, the registration call uses ELF string `BIRDINFO` at `0x20020a44` and read-handler `AtInfo` at `0x100008bc`; run/write handlers are null. `AtInfo` calls `RuntimePrintInfo` `0x10001dcc`. The once guard prevents duplicate registrations. |
| Request/response | UART1 `uart_read_nonblock` feeds `ATServer::handle`; CR executes the buffer, LF is ignored. Read commands dispatch to the read handler. Both vendor `ei_printf` and Birdhouse `bh_port_printf` call `xvprintf`, whose output callback is `console_putchar` and UART1 write. |

The map attributes startup and `board_main`/`board_init` to `libembarc.a`
members `arc_startup.o`, `board.o`, `socket_init.o`, and console setup to
`libboard_open_socket.a(console_io.o)`. Prebuilt BSP members are treated as binary
evidence; the available vendor source alone is not proof of their build options.

**Conditional registration is established:** with normal initialization and
allocation success, reaching the intended polling loop registers `AT+BIRDINFO?`,
including before the first received character is parsed. The known P4 path
`ei_microphone_init -> hx_lib_audio_init -> hx_drv_pdm_init -> io_pdm_rx_open`
occurs before AT initialization and may hang in the vendor ready poll. Earlier
startup failures, allocation failures or that hang can therefore prevent commands
without implying a UART/BL702 incompatibility.

## Compatibility matrix and bridge limits

VERIFIED means established from these files or explicitly attributed documentation;
INFERRED means supported interpretation; UNKNOWN means absent evidence for the
installed physical system. None means physically verified in this session.

| Question | Status | Conclusion |
|---|---|---|
| Exact UF2 has the audited UART and command code | **VERIFIED** | ELF/image/UF2 correspondence passes. |
| Himax AT input or BIRDINFO output waits for DTR/RTS | **VERIFIED: no such gate in traced paths** | The compiled path uses UART read/write, not a CDC endpoint or a debugger-attach check. This conclusion is scoped to Himax. |
| Himax consumes USB CDC line coding | **VERIFIED: absent from traced console path** | Baud is opened locally at 921600. Windows CDC requests terminate at the separate bridge. |
| BL702 provides computer-to-Himax connectivity | **VERIFIED documentation; INFERRED intended console transport** | Seeed's V1 documentation describes the connection, but does not specify this installed build's UART/control-line implementation. |
| 2022 `2d5b48b` accepts/applies 921600 CDC coding | **UNKNOWN** | Owner-reported installed identity, no exact installed binary/source in existing evidence. It may apply, ignore or constrain line coding. |
| DTR/RTS open/close affects bridge gating, reset, boot or flash routing | **UNKNOWN** | No exact-build mapping or execution evidence. Himax flow-control-off does not settle it. The schematic also contains a `DEBUG_DTR` net; it does not establish the installed USB control-line mapping. |
| BL702-side configuration/update is required | **UNKNOWN requirement; none demonstrated** | No evidence justifies a prerequisite bridge upgrade or baud patch. |
| 115200 in generic V1 wiki proves incompatibility | **Not established** | It is a general rate/example, not an exclusive bridge capability or this ELF's configuration. |
| Newer BL702 release notes prove a Windows 10 console defect in 2022 | **Not established** | Notes about Mac/Linux recognition do not establish this specific UART incompatibility. A newer cached binary cannot substitute for the installed image. |
| Reliable UART1 routing, Windows terminal opening, application boot | **UNKNOWN physically** | Requires a bounded owner experiment, not more static proof. |

Primary external evidence, consulted 2026-11-14:
[Seeed Grove Vision AI V1 wiki](https://wiki.seeedstudio.com/Grove-Vision-AI-Module/)
(generic rate, product/BL702 role and release-note scope), and its linked
[V1.1 QFN72 circuit diagram](https://files.seeedstudio.com/wiki/Grove_AI_Module/Grove_Vision_AI_NORF_v1.1.pdf)
(pin labels and sideband net labels). Only searchable PDF labels were available
for this audit; visual connectivity could not be independently resolved through
the available reader. No BL702 pin assignment or net-to-USB semantics is claimed.
V2 documentation was not used as V1 compatibility evidence.

## Practical deployment decision

**Proceed to an explicit owner risk decision on this existing exact candidate;
no console-related rebuild or BL702 upgrade is justified by the available
evidence.** Unknown physical behavior is an accepted-or-declined experiment risk,
not a demand for impossible read-only proof. The owner may still decline because
this is the sole board without qualified independent recovery.

If accepted later, prefer **one direct diagnostic UF2 write** over a factory
rehearsal plus diagnostic write: the rehearsal adds a second risky full write and
does not establish the diagnostic console's behavior. Neither route has a
quantified failure probability. A successful host transfer does not prove Himax
programming or boot. Exact-hash approval and the reviewed manual Windows write
steps remain separate from this audit; there is no write command here.

The minimum later console check is one owner-authorized manual Windows terminal
open at **921600, 8N1, no flow control**, using the owner's identified existing
port, followed by **one `AT+BIRDINFO?` with CR termination**. Record the terminal's
actual DTR/RTS-on-open policy beforehand; avoid deliberate line toggling,
auto-reconnect and concurrent clients. This proposes no known universally safe
DTR level. The owner must explicitly accept the unknown bridge effects of that
one open, or defer it. No device/console action occurred during this audit.

- Recognizable Birdhouse information: PASS for that observed end-to-end console
  exchange; not proof of DMA shutdown or all startup interleavings.
- Readable AT prompt/vendor text but unknown BIRDINFO: distinguish registration,
  parser and actual running-image identity before concluding bridge failure.
- Silence, garbling, disconnection or a hang: INCONCLUSIVE for the cause. Preserve
  the observation and stop; no automatic baud sweep, re-open/reset/replug,
  second flash, factory fallback or bridge upgrade follows.

Microphone capture requires its own subsequent scope and remains at most one
armed attempt under permanent P1 quarantine. The
[single-capture protocol](../birdhouse_v1_pdm_quiescence_diagnostic_20261113/WINDOWS10_SINGLE_CAPTURE_PROTOCOL.md)
retains its measurement limits; its historical requirement for a proven console
contract can instead be resolved by the owner's explicit acceptance of the
specific residual console risks identified here. P4, real ARC MLI/timing/stack,
pending-DMA identity and complete stop quiescence remain unresolved. One quiet
physical capture cannot prove shutdown race-free for every interrupt interleaving.

See the [full inspected-file hash manifest and parameters](results/summary.json)
and [publication record](PUBLICATION.md). No binary, map, vendor source dump or raw
machine log is eligible for publication.
