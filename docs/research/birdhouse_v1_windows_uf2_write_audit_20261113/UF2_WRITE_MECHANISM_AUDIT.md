# Installed BL702 UF2 mechanism and image audit

2026-11-13. **Installed write mechanism: unresolved; deployment NO-GO.**
This is a static audit. [Evidence IDs and provenance](EVIDENCE_MATRIX.md) distinguish
installed observations, newer release bytes, generic upstream code and inference.

## 1. What code can actually be attributed

The installed identity is the short build label 2d5b48b, dated Aug 23 2022, from
cached/owner-reported INFO_UF2. Its executable and exact source were not obtained.
Lookup in adafruit/tinyuf2 and the public fork associated with the release uploader
did not resolve that commit. Therefore there is no honest installed-source path or
full commit to quote. Same SDK banner, product name or VID/PID cannot supply it.

The official replacement is a different, 93,500-byte v2.0.1 binary dated Apr 4 2023.
Its hash is 5b0773315e923ce65b5c033b8b269d7ad396a088940a50f9cfe13ac3972d1d9c.
At file offset 0x982, independently rechecked RISC-V constant-building instructions
construct 0xef32c892. No binary payload or proprietary source is reproduced here.
This supports the family constant identified by A1. A constant alone is not a
complete parser/control-flow audit. SFUD erase/program/SFDP and XMODEM strings
indicate linked capabilities; they do not identify the target flash, routing,
buffer size, execution path or old-version behavior. No new binary was executed.

## 2. Precise public-core comparison, not installed-port attribution

The following are observations of Adafruit's own TinyUF2 source. The historical
snapshot is contemporaneous with the installed build, not proven to be its ancestor.

| Function | Historical upstream e91e98cbabf9139b9c84e21a4304a504be8e4345 | Current upstream d4a85300160ae1ad9069a4e450e067949fca35fd |
|---|---|---|
| Block screening | src/ghostfat.c:226–233 tests magics, family-present and no-flash flags; no payload-length test there. | src/ghostfat.c:238–244 additionally bounds payload by the data field. |
| Family/address | src/ghostfat.c:488–503 compares BOARD_UF2_FAMILY_ID and passes targetAddr/payloadSize to board_flash_write. No address interval is enforced by this function. | src/ghostfat.c:495–511 similarly delegates address policy to board code. |
| Write error | src/board_api.h:139 declares void board_flash_write; ghostfat.c:498 cannot inspect a return. | src/board_api.h:223 returns bool; ghostfat.c:503–506 aborts on failure. |
| Completion | ghostfat.c:505–534 accounts unique block numbers and calls board_flash_flush at the advertised count; duplicate accounting happens AFTER the write call. | ghostfat.c:513–542 retains counting, then checks optional board_flash_ok after flush. This is not necessarily readback/hash verification. |
| MSC response | src/msc.c:137–154 counts a sector as processed for every nonzero uf2_write_block result, including rejected non-UF2 blocks. | src/msc.c:126–146 explicitly maps UF2_WRITE_FAILED to SCSI MEDIUM_ERROR/write error; non-UF2 sectors still succeed. |
| Finish callback | src/msc.c:157–198 calls board_dfu_complete after all counted blocks, following the WRITE10 completion callback. | src/msc.c:149–184 prevents normal completion on aborted updates. |
| Reading | ghostfat.c:454–472 synthesizes CURRENT.UF2 via board_flash_read. | ghostfat.c:462–477 also synthesizes it; port implementation still determines scope. |

Links: [historical ghostfat](https://github.com/adafruit/tinyuf2/blob/e91e98cbabf9139b9c84e21a4304a504be8e4345/src/ghostfat.c#L488-L539),
[historical MSC](https://github.com/adafruit/tinyuf2/blob/e91e98cbabf9139b9c84e21a4304a504be8e4345/src/msc.c#L137-L198),
[current ghostfat](https://github.com/adafruit/tinyuf2/blob/d4a85300160ae1ad9069a4e450e067949fca35fd/src/ghostfat.c#L495-L548),
[current MSC](https://github.com/adafruit/tinyuf2/blob/d4a85300160ae1ad9069a4e450e067949fca35fd/src/msc.c#L126-L184),
[current flash API](https://github.com/adafruit/tinyuf2/blob/d4a85300160ae1ad9069a4e450e067949fca35fd/src/board_api.h#L217-L232).

These files illustrate why copying a current implementation's safety features into
an explanation of a 2022 build would be wrong. They do not establish the Grove
buffering/erase strategy, physical address limits or transport to the Himax. The
current upstream ports directory has no BL702/Grove implementation. No public BL702
port matched to the installed or replacement image was established in this audit.

## 3. Installed mechanism: question-by-question disposition

| Question | Established | Still unknown on build 2d5b48b |
|---|---|---|
| Accepted family | Official and candidate files use 0xef32c892; newer replacement builds that constant. | Whether old firmware requires it, permits alternatives, or silently discards mismatches. |
| Accepted address intervals | Full images encode 0x10000000-based destinations; erase_model encodes low addresses. | Bounds, overflow checks, special commands and mapping to physical flash/chip; local converter's 2 MiB limit is host policy, not proof of bootloader enforcement. |
| Buffering | UF2 packets have 512 bytes with 256-byte payload in these files. | Whole image versus page/sector/chunk staging; RAM versus BL702/external flash; out-of-order/duplicate handling. |
| Erases | Both full files request payload over loader regions and metadata. | Erase unit, when erase begins, erase-before-receive versus after complete reception, skip-equal policy, chip erase, read-modify-write or tail fill. |
| ACK timing | Windows read worked by owner report. SDK Himax first-loader ACK-before-burn is prior binary-specific evidence. | USB WRITE10/CSW timing relative to buffering, erase/program, Himax ACK and durable flash completion. No timing bound established. |
| Completion | Official documentation expects the drive to disappear after copy. | Whether disappearance can precede target burn, which errors are exposed, watchdog/reset timing and maximum completion time. |
| Integrity | Files independently hash/parse correctly; no MD5/extension flags in them. | Read-after-write, byte compare, CRC/signature enforcement on the actual update route, retry/error propagation and complete-flash coverage. |

UF2 blocks are self-contained address-bearing units; the format itself supplies no
whole-image atomic commit or guaranteed readback. These files have family flags,
not a file-level cryptographic verification mechanism. This follows the
[UF2 format](https://github.com/microsoft/uf2#file-format), not a board-specific
experiment. USB receipt, UF2 block counting, XMODEM receipt and flash verification
must remain distinct. No transaction/power-loss guarantee is supported here.

## 4. Exact file-level memory contents

All intervals below are half-open [start,end). Offsets subtract UF2 base
0x10000000. This is package addressing; mapping offset zero to Himax physical flash
zero is plausible but unproved in installed BL702 code.

| File | UF2 bytes / blocks | Payload interval | Payload bytes / SHA-256 |
|---|---:|---|---|
| Official grove_ai_v02-00.uf2 | 1,541,632 / 3,011 | [0x10000000,0x100BC300) | 770,816 / 809bfedf75413355d88b97564b07eab2b526ec0c00c112e5e04edf4ad4768a40 |
| Pinned Birdhouse candidate | 1,256,448 / 2,454 | [0x10000000,0x10099600) | 628,224 / b8a12eb299aaa7ce0428c05eab0c4fe1c7ed0ce21b4b15d387f03d9dacfcab2d |
| Official erase_model.uf2 | 38,400 / 75 | [0x00000000,0x00004B00) | 19,200 / 4c1d6254f14a45e6bd607f20000cde14868912ad7eb8278a715f53ca25742c66 |

Every file has flags 0x2000, family 0xef32c892, 256-byte payloads, valid magics,
complete numbering, contiguous unique destinations and zero unused UF2 block bytes.
Container SHA-256 values are in [the summary](RESULTS_SUMMARY.json). Multiple cached
candidates have the same filename but different bytes; only hash
009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae was selected.

| Relative package interval | Exact content / comparison |
|---|---|
| [0x00000,0x0BA8C) | 47,756-byte SDK sign_formal_PA8530_EM9D_2nd_Bootloader.bin; exact in both, SHA-256 a4db778603072b8151b7fb3bbb55a7640b4d3623bc3fb1a4813a00b6b50586fe. |
| [0x0BA8C,0x10000) | 17,780 bytes of 0xFF in both. These are transmitted payload bytes, not omitted blocks. |
| [0x10000,0x1BD2C) | 48,428-byte SDK sign_formal_PA8530_EM9D_Bootloader.bin; exact in both, SHA-256 6ed391b0eea39eafacf6f5f621cdd5afda4351b651b8234e87c4b9554b98d1f0. |
| [0x1BD2C,0x20000) | 17,108 bytes of 0xFF in both, also transmitted. |
| [0x20000,0x21000) | BLp metadata slot; differs. Candidate manifest describes type 0x03 object of 1,380 bytes; remaining slot padding is part of the file. Exact internal semantics are not fully decoded. |
| [0x21000,0x22000) | Identical 4 KiB BLp boot-configuration slot; candidate manifest type 0x12 object of 1,284 bytes. Not the same blob as the WEI repair array. |
| [0x22000,0x99600) | Candidate application containers, signing/SBS descriptors and padding. Eight chunks begin at 0x22000 + n*0x10000, n=0..7. Seven are 65,536 bytes; final object at 0x92000 is 30,000 bytes. |
| [0x99530,0x99600) | Last 208 bytes are zero UF2 payload padding after the 628,016-byte candidate image. |
| [0x22000,0xBC300) in factory | Official factory application containers; starts at 0x22000 + n*0x10000, n=0..9. Factory proprietary internals are not reproduced or claimed fully decoded. |
| [0x99600,0xBC300) | 142,592 bytes supplied only by factory. Not supplied, zeroed or preserved by any candidate block. Actual retention/erasure is a separate physical question. |

Factory/candidate overlap is 628,224 bytes, with 157,278 identical bytes. Whole
loader slots [0,0x20000) and the boot-config slot match; other equal bytes do not
constitute a safe differential-update map. Neither full image embeds the SDK
ROM-I2C bootstrap by the prior exact-substring check; this check was not rerun.

Candidate image SHA-256 is c2d7e176436433f714633bc817cec3bc232c8fabd62389567be518358b6de388.
Its matched ELF is 8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f.
Independent ELF32/SBS parsing reconstructed these stored sections byte-for-byte:

| Section | Runtime destination | Original section bytes |
|---|---|---:|
| .ivt | 0x10000004 | 328 |
| .vector | 0x10000400 | 1,024 |
| .text | 0x10000800 | 298,698 |
| .read_only_data | 0x20020800 | 171,716 |
| .data | 0x200EE2C0 | 6,700 |
| .rodata_in_data | 0x200EFCEC | 16 |
| .sdata | 0x200EFCFC | 24 |

Runtime destinations are not UF2 flash destinations. The containers include a
four-byte IVT marker and alignment padding. The 59,760-byte validated model,
SHA-256 9e04d17723b87f9acbba3030c23e1e50b551493125e9bf7dc0aeb27f0b12db55,
is present in reconstructed .read_only_data. BSS/arena/stack are not serialized as
initialized model data. No image was regenerated; no generator was run.

## 5. Physical erase effects: known versus conditional

**Known:** the files' requested bytes and boundaries above. **Unknown:** actual
flash chip/geometry selected by the installed bridge, translation, erase policy,
staging region, skip-equal logic and interruption behavior. SFUD support for a
4 KiB operation in a newer binary is not proof of this board's erase policy.

If, and only if, offset-based writes use minimally rounded 4 KiB sector erases:

- Candidate touches sectors [0,0x9A000): 154 sectors. Its final sector is
  [0x99000,0x9A000); payload ends at 0x99600, leaving 0xA00 (2,560) bytes unsupplied.
  A plain erase could turn that suffix to 0xFF; read-modify-write could preserve it.
- Factory touches [0,0xBD000): 189 sectors. Its final sector suffix
  [0xBC300,0xBD000) is 0xD00 (3,328) unsupplied bytes.
- The candidate's 142,592-byte uncovered factory tail divides into 2,560 bytes
  sharing its final sector and 140,032 bytes at/above 0x9A000. Only under the
  minimal-erase assumption would the latter be outside erased sectors.
- With 64 KiB rounding, candidate coverage rounds to 0xA0000, so 27,136 bytes
  after 0x99600 could be affected. Whole-chip/staging strategies could affect more.

These are arithmetic scenarios, not measured erase results. The SDK config address
0x1FE000 is beyond both file payloads and both rounding examples, but whole-chip
erase, staging aliasing or a different translation could still affect it. No
installed configuration preservation guarantee follows. Erase_model's disjoint
logical address interval does not prove disjoint physical flash or harmlessness.

## 6. Recovery implications

The direct-SPI hypothesis would permit restoration without healthy Himax software
only if BL702 owns/accesses the correct target flash, holds Himax safely, applies
the full address map and verifies programming. SFUD strings alone prove none of
those conditions. A UART/XMODEM implementation instead needs a reachable loader
or a confirmed ROM bootstrap. Neither installed path is established.

Accordingly: app damaged with loaders intact is a plausible official factory-UF2
recovery case; both loaders damaged is **unproved**, not certified recoverable and
not proven impossible. BL702 damage requires its separate ROM recovery route.
These boundaries and the newly found WEI defect are expanded in
[recovery gates](RECOVERY_AND_ROLLBACK_GATES.md).
