# Himax HX6537 recovery assessment (offline)

**Verdict: no independent Himax recovery route is qualified. Himax writes are NO-GO.**

## 1. Flash layout established from the images

UF2 addresses are based at `0x10000000`. Offsets below are relative to that base and assume it maps
to Himax flash offset 0; the address mapping inside the BL702 bootloader is not documented.

| Offset | Content | Factory | Candidate |
|---|---|---|---|
| `0x00000` | SDK `..._2nd_Bootloader.bin` (47,756 B), exact bytes | yes | yes |
| `0x10000` | SDK `..._Bootloader.bin` (48,428 B), exact bytes | yes | yes |
| `0x21000` | `BLp\x02` boot-configuration record (identical in both) | yes | yes |
| `0x20000`, `0x22000`, then every `0x10000` | further `BLp`-tagged sections | yes | yes |
| End | — | `0xBC300` | `0x99600` |

Consequences:
- **Both loaders are rewritten.** A full factory or candidate UF2 write rewrites both Himax loaders.
  UF2 delivery is block-by-block, not transactional, so an interrupted write can damage the loaders.
- **The candidate leaves a tail.** The candidate does not cover `0x99600`–`0xBC300`, which keeps
  prior contents. How a partially covered 4 KiB sector is erased is unknown.
- **Model space is separate.** `erase_model.uf2` targets a separate address space (`0x0`–`0x4B00`)
  that overlaps neither image. Its semantics are inferred only from its name.

## 2. Candidate routes

| Route | Depends on | Status |
|---|---|---|
| R1 UF2 copy to GROVEAI (official) | BL702 TinyUF2 healthy, stable `0060` MSC on the host used | **Blocked on this host** by the reset loop; other hosts unqualified |
| R2 Official I2C "erase", then R1 | External I2C master, Himax I2C system slave, then R1 | Restores nothing alone; still needs R1 (section 3) |
| R3 Himax ROM-I2C bootstrap / I2C OTA write of a full image | External I2C master, ROM boot entry, an image format the ROM accepts | Unofficial for Grove; SDK assets exist; unverified |
| R4 Himax 1st-loader XMODEM | BL702 `8060` bridge, UART routing, loader entry | Unverified; loader ACKs before burning and does not check the write result (ASSESSMENT) |
| R5 Debug probe | Wiring, probe, attach semantics | Not available |

## 3. Official I2C recovery source (Seeed_Arduino_GroveAI `WEI`)

The source text was audited; nothing was compiled.

- **Addresses:** `HIMAX_SYSTEM_ADDRESS 0x79` (register access) and `HIMAX_FLASH_ADDRESS 0x62`, the
  same address as the application protocol. This is new evidence that `0x62` is used as a 7-bit I2C
  address. That holds only for this library's flash protocol; it is not established for this board.
- **`ID()`** reads register `0xB00000FC` through `0x79`.
- **`enter_bootloader()`** performs undocumented register writes: `0xB0000010←0x8`,
  `0xB0000520←0x2`, `0xB0000070←0x1`, then `0xB0000020←0x80000002`, followed by a 1 s wait. Their
  meaning, presumably boot-mode selection and reset, is not documented.
- **`load_config()` (the core of "erase")** writes; it does not bulk-erase:
  - A start command `51 02 …` with words `0x12`, `0x41`, `0x21000` and `0x2FC`.
  - Then the 764-byte embedded `BLp\x02` record in 128-byte pages, each followed by a CRC-16
    (reflected polynomial `0x8408`, initial `0xFFFF`, no final XOR, i.e. CRC-16/MCRF4XX).
  - Then a done command `51 04`.
  - The blob shares its 8-byte header and 397 of 764 bytes with the factory and candidate record at
    `0x21000`.
  - Inference: the official "erase" replaces the Himax boot-configuration record so that the existing
    application is no longer booted. The record's exact meaning is unknown.
- **`reset()`** sends `50 06 00 00`.
- **`erase()`** calls `enter_bootloader()` again, so the example enters it twice.
- **No safety checks:**
  - No readback, no verification and no command error handling.
  - `sys_read` polls status **without a timeout**.
  - Some helpers use the global `Wire` instead of the configured bus.
  - A `flash_read` primitive exists, but no documented readback command uses it.
- **Recovery by this route alone is incomplete.** After "erase", Seeed's procedure restores the
  factory UF2 through GROVEAI (R1). The wiki also says to try the UF2 copy first and to erase only if
  that fails.

## 4. Requirements for an independent Himax route

A route counts as independent only if it can restore a known-good Himax image while both of the
following hold:
- (a) the Himax application or loader is broken;
- (b) the BL702 `0060` MSC path is unavailable or unstable.

Minimum requirements:
1. **Hardware:** an external 3.3 V-compatible I2C master on the module's Grove I2C pins, with the bus
   topology confirmed from a schematic. It must be established whether the BL702 shares that bus.
   Power arrangement follows Seeed's FAQ connection order and overheating warning.
2. **Documented entry:** documentary proof that the `0x79` register path and the boot entry work
   without valid flash contents (ROM or hardware level). The local WE-I manual section 3.3.1
   conditions are the starting point.
3. **Full-image protocol:** a documented full-image write and **readback/verify** protocol over that
   path, with page size, addressing, CRC and status semantics. The 764-byte config write is not
   enough.
4. **Image acceptance:** the factory image (`8854e093…`) is acceptable to that path, including any
   signature checks on `BLp` sections.
5. **Rehearsal:** with only one board, the first rehearsal is itself an irreversible write. It
   therefore needs the owner's preservation decision first; no backup or readback of the installed
   application exists.
6. **Tooling:** an audited, reproducible repair-host build using an existing toolchain, plus the MCU
   board. The Arduino toolchain and MCU host remain **missing**.

Until 1–6 are met, the only plausible Himax recovery is R1 on a host where `0060` MSC is proven
stable. That makes the qualification of such a host the critical next gate.
