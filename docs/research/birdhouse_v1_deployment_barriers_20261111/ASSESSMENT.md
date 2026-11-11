# Grove Vision AI V1: remaining deployment barriers

2026-11-11. Starting commit: `1095349f459d974975e606d243c84d26635f67bf`.
Branch: `research/birdhouse-v1-predeployment-codex-20261111`.

**Deployment: NO-GO. Recovery readiness: BLOCKED. Offline investigation: PASS.**
The next proposed step is a separately reviewed, observer-only host session under
[this exact protocol](READ_ONLY_DIAGNOSTIC_PROTOCOL.md). Its prerequisites remain
unestablished, so execution is also NO-GO today. No board access, device discovery,
serial/I2C communication, reset, image transfer or bootloader update occurred.

The firmware, SDK and validated artifacts remain unchanged. The prior
[implementation milestone](../birdhouse_v1_codex_predeployment_20261111/HANDOFF_REPORT.md)
is retained; its inference, sanitizer, build and packaging suites were not rerun.
This assessment adds file-only binary analysis, cached-log analysis, a manual
admission checklist and ten focused tests. Static checks confirm observations,
including hazards; their PASS status does not close hardware gates.

## PDM startup and interrupts

Evidence is from the **actual linked ARC candidate**, not a replacement driver.
[Machine-readable results](results/barrier_audit.json) pin its SHA-256 and record
function addresses. Jump tables are decoded from ELF bytes rather than treating
them as instructions. The first-party adapter and its existing tests were also
read directly.

| Question | Finding | Disposition |
|---|---|---|
| Does masking interrupts around startup wait for an ISR? | On the initialized PDM/16 kHz path, the rate selector reaches a register-write leaf; transfer setup programs DMA descriptors and enables the channel. No software ISR-completion wait or internal global IRQ re-enable was found in the traced normal helpers. Ring setup is bounded by the configured block count. | Suspected software deadlock narrowed substantially. This is conditional static evidence, not elapsed-time or bus-stall proof. |
| Is the mask unnecessary? | `io_pdm_rx_read` enables DMA before updating its queued-transfer counter. The adapter masks interrupts until initialization and capture-owner publication are complete. | Retain the startup mask; removing it without another synchronization mechanism would expose an initialization race. |
| Does successful stop establish quiescence? | The adapter detaches the application target under IRQ protection, then restores IRQ state **before** vendor stop. Vendor stop disables/resets the channel and resets counters, without an explicit completion-IRQ clear. The ISR invokes the vendor RX callback before its completion clear; that callback re-arms DMA before the application callback. | **OPEN P1:** an interrupt can interleave with stop. A pending old completion may also survive stop or be delivered against the next run. Reset's implicit IRQ effects are unknown. |
| Do late-callback tests close P1? | `fake_aud_lib.cc` invokes the application callback directly. It does not execute vendor re-arm, channel reset, pending status or IRQ acknowledgment. | **VERIFIED LIMIT P2:** the tests establish detached PCM-owner safety, not a stopped peripheral or a clean next-run boundary. |
| Does start success prove acquisition started? | `hx_lib_audio_start` discards `hx_drv_pdm_init_transfer`'s result. The underlying read is void and can silently return on queue-full. Vendor `ei_microphone_init()` also ignores initialization status and returns true. | **VERIFIED LIMIT P3:** wait for measured progress; never treat API success as proof of active DMA. |
| Can the eight-second capture timeout recover every failure? | `io_pdm_rx_open` has a ready-bit polling loop without a deadline. Boot initialization reaches it; FIFO-error recovery calls audio deinit/init in interrupt context and can reach it again. | **OPEN P4:** a blocked boot path or ISR cannot be preempted by the main-loop timeout. Console availability and recovery cannot be assumed. |

Relevant addresses in this exact candidate:

- Adapter start/stop: `0x10002664` / `0x10002620`.
- Audio start: `0x10024200`; 16 kHz case: `0x1001d29a`; rate-ioctl leaf: `0x1002a5e0`.
- DMA read: `0x1002a348`; stop: `0x1002a460`.
- Vendor RX callback: `0x10024024`; PDM ISR: `0x1002a018`.
- DMA reset: `0x10023844`, writes auxiliary register `0x68a`;
  completion clear: `0x10023838`, writes `0x688`.
- Error callback: `0x100241a4`; peripheral open: `0x1002a0f8`.

Distinct register writes and separate SDK APIs do **not** prove reset leaves a
pending IRQ intact. That uncertainty prevents a justified low-level patch today.
No global DMA clear, guessed register write or blanket interrupt disable was
added. The normal first-party detachment remains valuable even if the peripheral
can still re-arm.

The preferred next offline input is authoritative documentation for the exact
ARC DMA reset/completion/interrupt semantics, plus the applicable PDM driver
source if available. A narrow stop protocol would need to prevent re-arm during
teardown, stop/drain the channel, handle pending completion and preserve the
previous interrupt state without affecting other channels. A software model
would test that proposed contract, but could not establish the hardware contract.
Until that is known, repeated stop/restart is an explicit physical qualification
gate. The later single-capture test must stop on unexpected late callbacks or
progress and must not automatically queue another run.

## Recovery: available assets versus demonstrated capability

Only existing cached material was inspected. The SDK checkout is clean at
`9dc2370d4dc269dc4bcafcf0354b8f745d08801f`. Paths below are relative to its
`Synopsys_PA8535_EM9D_DFSS_SDK_3.3/` directory. No vendor executable was run.

| Route | What the cache establishes | Grove-specific gap |
|---|---|---|
| BL702 USB MSC/UF2 forwarding | Cached `INFO_UF2.TXT` identifies historical TinyUF2 build `2d5b48b`, dated 2022-08-23. The Grove README documents a BOOT-button/UF2 flow and recommends a BL702 update on first use. | Current installed identity, forwarding protocol, update erase ranges and stability are unverified. The installed bridge's exact source/binary is absent from inspected caches. A README recommendation is not permission or evidence that an update is safe. |
| Himax first-loader UART/XMODEM | Exact-part SDK binary contains the receive/burn path. New disassembly analysis establishes RAM reception and the call order described below. | Installed loader identity, Grove UART routing through BL702, entry method and bridge segmentation are unverified. No recovery or power-loss experiment. |
| Himax second-loader OTA / flash dump | Normal SDK second loader has UART/I2C OTA, dump and erase markers. The local WE-I manual documents loaders and host version matching. | Markers do not establish reachable commands, a safe readback path, board wiring or an executable Grove repair-host build. |
| Himax ROM I2C bootstrap | **Additional existing asset found:** exact-part-labelled, 47,500-byte bootstrap under `tools/OTA_Tool/BootUpFromI2C/HX6537-A09TDIG-1111V_QFN72/`. Local manual section 3.3.1 describes conditional ROM boot. | ROM entry requires failed/no valid flash loader or boot option `011`; Grove strap access, compatible wiring/host and acceptance of this image are unverified. Sending it executes RAM code and is outside read-only diagnostics. This is not BL702 recovery. |
| BL702 ROM recovery | Earlier research describes a bridge-repair route. The SDK README links an external update asset, which was not fetched. | Compatible local BL702 image/source, entry wiring and a verified repair procedure are absent. Repairing the bridge would not itself restore Himax flash. |
| Factory fallback UF2 / backup | Prior milestone verified two identical factory fallback files. | They are not backups of the installed application/configuration. Installed flash readback remains unverified, not proven impossible. Later TinyUF2 backup features cannot be assumed present in this 2022 build. |
| Debug probe / generic ARC tooling | ARC tools are available for offline build/disassembly. | No independently verified Grove debug wiring, compatible probe or nonintrusive attach semantics. Not a ready recovery route. |

Important local fingerprints (all binaries remain unpublished):

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `tools/image_gen_cstm/input/BLp/QFN72/HX6537-A09TDIG-1111V/sign_formal_PA8530_EM9D_Bootloader.bin` | 48,428 | `6ed391b0eea39eafacf6f5f621cdd5afda4351b651b8234e87c4b9554b98d1f0` |
| Normal second loader in the same directory | 47,756 | `a4db778603072b8151b7fb3bbb55a7640b4d3623bc3fb1a4813a00b6b50586fe` |
| ROM-I2C bootstrap described above | 47,500 | `d223adc96db68a64059e78b6b783d8db044b4ddc72b01c4c3e2203c0cb089400` |
| `tools/OTA_Tool/doc/WE-I OTA_v2.1.0 usage guide for cstm.docx` | 203,192 | `c4e7bf12089118318354dae72aaa5738d677402216646fa8fc4bec10881c76dd` |

The manual's ROM procedure uses 400 kHz I2C, an image below 128 KiB, a staging
address of `0x20020800` and execution at `0x20000000`. These describe generic
WE-I prerequisites, not a tested Grove V1 procedure. The `0x62` transfer marker
must not be guessed to be a slave address. Its figures do not establish this
board's connector, electrical levels or strap accessibility.

### What the first-loader binary adds

The audit strips the pinned file's `0x28c`-byte envelope and wraps its remaining
bytes for **disassembly only** at `0x20000000`. No loader code is executed or
modified. Its startup/data mapping and receive/burn menu were inspected locally.
The temporary analysis ELF is not firmware and is never a deployable artifact.

- The caller supplies a RAM buffer at `0x20050000` and calls the receiver at
  `0x200015ae`. On a negative return it skips the erase/program path.
- The receiver's EOT branch sends ACK (`0x06`) at `0x20009c82`, then returns the
  received count. The caller's erase and program calls occur later at
  `0x200016b2` and `0x200016cc`. SPI command construction supports their
  interpretation as sector erase and page program.
- The caller does not inspect the program return before printing its completion
  message. Neither an XMODEM ACK nor that message establishes independently
  verified flash contents.

**Inference:** for this SDK receiver, transfer receipt precedes burning. It does
not establish transactional update safety. The installed loader and BL702
forwarding may differ or split a file into multiple transfers. UART byte I/O
uses driver function pointers, so this is not an exhaustive proof that no helper
can write flash. No interrupted-transfer behavior is claimed.

The candidate includes both Himax bootloaders. Identical loader bytes do not
exclude sector erasure, bootloader damage during interrupted writes, or a bridge
that writes as it receives. A full-image update remains consequential. Before
any write, the owner must choose preservation requirements, and a recovery route
must be qualified for the exact board/component independently of the candidate
application being healthy.

Do not use the vendor tools as diagnostics: `tools/ufconv/uf2conv.py` enumerates
ports, can select 1200 baud to request bootloader entry, and writes `NEW.UF2`;
`tools/OTA_Tool/readme.txt` says no-argument `ota.exe` force-upgrades. Neither was
imported or executed. No `--help` safety assumption is made.

## Transport evidence and next boundary

The historical kernel log contains **22 resets**, including **16 adjacent
intervals between 30.714 and 31.836 seconds**, twelve Mode Sense log entries and
one explicit failed SCSI Read(10). It records two USB product IDs and two distinct
serial strings; device identifiers and raw logs remain private. This establishes
historical instability under storage traffic. It does not identify the exact
stalled command, competing process, power problem or root cause. A kernel
"device firmware changed" message is descriptor-comparison evidence, not proof
of a persistent firmware write. The earlier empty 20-second observation was
shorter than one typical reset interval and cannot qualify stability.

Disabling automount alone does not prevent kernel MSC probing. A read-only mount
still generates device transactions; the saved FAT errors even mention an
attempt to mark the filesystem dirty. Opening a tty can emit CDC line-coding and
DTR/RTS changes. The vendor's 1200-baud transition confirms that serial setup can
change boot mode. No serial program, mount, I2C scan or USB descriptor utility
belongs in the proposed first observation.

[The proposed protocol](READ_ONLY_DIAGNOSTIC_PROTOCOL.md) allows only cached
host metadata and kernel-journal observation for 120 seconds on an already
powered/connected board, after reviewed host isolation. Any required attach,
power change, tty open or I2C transaction needs a separate phase and review.
The [manual checklist](OBSERVER_PLAN.json) deliberately records every prerequisite
as unestablished. Its offline evaluation is **NO-GO**; it neither inspects host
state nor grants approval. There is no executable hardware diagnostic in this
milestone.

## Evidence, reproduction and decision

New verification: **16 PDM static checks, six recovery-asset checks, eight loader
call-order checks PASS; ten targeted tests PASS.** Mutation controls reject an
inserted interrupt enable, unknown helper, wrong jump table, and missing critical
receive/ACK/erase/error-branch instructions. Manual admission fails closed for
missing prerequisites, malformed action lists and active hardware actions. These
tests validate the analyzer against the real local binaries and cached log;
they do not execute ARC code or simulate successful hardware recovery.

From the repository root, set `BH_PYTHON` to the mandatory existing HCI Python
executable. Use a new output filename for each run:

```sh
"$BH_PYTHON" -m unittest discover -s tools/himax/tests -p test_deployment_barriers.py -v
"$BH_PYTHON" tools/himax/audit_deployment_barriers.py --observer-plan docs/research/birdhouse_v1_deployment_barriers_20261111/OBSERVER_PLAN.json --out /tmp/bh_barrier_recheck.json
```

Exact command evidence and publication scope are in [PROGRESS.md](PROGRESS.md).
No new image was produced. The inspected candidate ELF remains SHA-256
`8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f`;
the prior packaged image remains
`c2d7e176436433f714633bc817cec3bc232c8fabd62389567be518358b6de388` and UF2
`009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae`.

The decision remains **NO-GO for firmware deployment and active diagnostics**.
Normal-start software waiting is no longer the leading PDM concern. Stop/IRQ
quiescence, unbounded initialization/error recovery, unstable historical USB
transport and unqualified recovery remain consequential barriers. Actual MLI
numerics, microphone timing, memory/stack use and electrical behavior retain
their previous physical gates. Independent review may authorize only the narrow
observer phase once its host prerequisites are established; it must not imply
approval for the next phase or for a write.
