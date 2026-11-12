# A1 offline recovery-asset acquisition and audit

2026-11-12, acquired 16:48–16:49 UTC. **Status: A1 COMPLETE (offline).**

- Nothing was executed, compiled, imported or flashed. That includes downloaded binaries, firmware,
  installers, vendor tools and Arduino code.
- No board, USB device, serial port, I2C bus, block device or host setting was touched.
- Files were fetched over HTTPS into a new git-ignored directory
  (`.local-tools/recovery-assets/seeed-official-20261112/`). Each final redirect was checked against
  an allow-list of official hosts.
- Analysis used the mandated existing HCI Python in isolated mode, reading files as bytes only.
- Machine-readable summary: [results/asset_audit.json](results/asset_audit.json).

## 1. Provenance

The source is `Seeed-Studio/Seeed_Arduino_GroveAI`:
- A Seeed-Studio organisation repository, not a fork, MIT licence.
- It is the download location linked from Seeed's "Grove - Vision AI Module" wiki.
- Tags: `v2.0.0` → `49664aa8d5d63dfaaefe319b54455fb320791cbc`, `v1.1.0` → `cb0a4426801e…`,
  `v1.0.0` → `4bb63f7c9820…`. The default branch was at `b4ef904dea4bcaf9ac55672a2138388169dce65a`
  when fetched.
- **GitHub publishes no digest for any of these assets** (`digest: null`). The hashes below were
  computed locally.

| File | Release (id) / asset id | Uploaded (UTC) | Bytes | SHA-256 |
|---|---|---|---:|---|
| `tinyuf2-grove_vision_ai_v2.0.1.bin` | v2.0.0 (114739495) / 130945222 | 2023-10-17 | 93,500 | `5b0773315e923ce65b5c033b8b269d7ad396a088940a50f9cfe13ac3972d1d9c` |
| `tinyuf2-grove_vision_ai_v2.0.1.bin` | v1.1.0 (96435427) / 102196405 | 2023-04-04 | 93,500 | identical to the above |
| `grove_ai_v02-00.uf2` | v2.0.0 / 121727367 | 2023-08-16 | 1,541,632 | `8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c` |
| `erase_model.uf2` | v2.0.0 / 121851617 | 2023-08-17 | 38,400 | `1668c816a1d0de5e7fe498495330f055af8c77098adfce1e7551ea2e68b29ad9` |
| Library source, tag v2.0.0 (codeload tarball) | — | — | 1,127,306 | `fb097a50e3d71137a01f782a763fbf6a6c1fe009a89c286d33da34c1f67eb86b` |
| Library source, commit `b4ef904d…` (codeload tarball) | — | — | 1,130,891 | `13ec7b56032de354cfd426cb38046d845ade461cc5c0755c54f246218ab967b6` |

Release URLs have the form
`https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI/releases/download/<tag>/<file>` and
redirected to `release-assets.githubusercontent.com`.

**Documentation (official, saved locally):**

| File | Bytes | SHA-256 |
|---|---:|---|
| Seeed wiki "Grove - Vision AI Module" (`wiki.seeedstudio.com/Grove-Vision-AI-Module/`) | 166,229 | `be349441…` |
| Bouffalo Lab `bouffalo_sdk` `docs/zh/get_started/flash_cube.rst` | 5,856 | `48751b81…` |
| Bouffalo Lab *Flash Cube* user guide v1.6 (2025), PDF | 2,065,694 | `51136477…` |

Full hashes are in the JSON.

**Not downloaded:** the BLDevCube installer archive, which is a tool and outside A1. Seeed's wiki is
the only official BLDevCube *procedure* for this board found. Bouffalo's current official
documentation covers its successor, Flash Cube.

## 2. Factory UF2 compared with the existing local fallback

The downloaded `grove_ai_v02-00.uf2` is **byte-for-byte identical** to both existing local fallback
copies. All 1,541,632 bytes compare equal and there is no first differing offset. The local fallback
is therefore exactly Seeed's published v2.0.0 factory image, not merely a file of the same size. It
is still **not a backup** of this board's installed application or configuration.

## 3. UF2 structure

| Image | Blocks | Payload/block | Flags | Family | Address range | Payload bytes |
|---|---:|---:|---|---|---|---:|
| Official factory `grove_ai_v02-00.uf2` | 3,011 | 256 | `0x2000` family present | `0xef32c892` | `0x10000000`–`0x100BC300` | 770,816 |
| Official `erase_model.uf2` | 75 | 256 | `0x2000` | `0xef32c892` | `0x00000000`–`0x00004B00` | 19,200 |
| Local Birdhouse candidate (`009799e1…`) | 2,454 | 256 | `0x2000` | `0xef32c892` | `0x10000000`–`0x10099600` | 628,224 |

All three files pass the same checks:
- Every block has valid magics and a complete `blockNo` sequence, with a single `numBlocks` value.
- None has duplicate or overlapping addresses.
- Each is one contiguous range.
- None uses the MD5, file-container or extension flags.

**Overlaps and contents:**
- Factory and candidate overlap over the whole candidate range (628,224 bytes), of which 157,278
  bytes are identical.
- The factory extends 142,592 bytes beyond the candidate's end, `0x10099600`–`0x100BC300`.
- `erase_model.uf2` uses a separate address space (`0x0`–`0x4B00`) and overlaps neither image. Its
  payload is not a uniform fill. How the bootloader maps those addresses is not documented.
- **Himax loaders are inside both full images:**
  - The SDK file `sign_formal_PA8530_EM9D_2nd_Bootloader.bin` sits exactly at `0x10000000`.
  - `sign_formal_PA8530_EM9D_Bootloader.bin` sits exactly at `0x10010000`.
  - Writing either the factory or the candidate image therefore rewrites both Himax loaders.
  - The SDK ROM-I2C bootstrap image is not present in either, as expected for a RAM-loaded image.
- `BLp`-tagged regions start at offsets `0x0`, `0x10000`, `0x20000`, `0x21000`, `0x22000`, then
  every `0x10000`.
- The 4 KiB record at `0x21000` is **identical in factory and candidate**. Section 3 of the Himax
  assessment explains its role in the official I2C "erase".

## 4. BL702 bootloader v2.0.1 (bytes only)

- **Not a raw flash dump with a boot header.** The image starts with a RISC-V `auipc` instruction
  and has no `BFNP` boot header. That matches Seeed's procedure, in which BLDevCube's MCU mode
  creates the header at programming time.
- **One image, both USB personalities.** It contains two USB device descriptors:
  - `2886:8060`: bcdUSB 2.10, class EF/02/01, bcdDevice 01.00.
  - `2886:0060`: bcdUSB 2.00, same class and bcdDevice.

  The `8060` fields match the cached metadata of the board now connected.
- **UF2 family check:** a `lui`/`addi` pair at image offset `0x982` builds the constant
  `0xef32c892`, the family ID of all three UF2 files.
- **Identity strings:** "TinyUF2 Bootloader v2.0.1 - bouffalolab/bl_mcu_sdk (V1.4.3-8-g8742503a)",
  Model "Seeed Studio Grove Vision AI", Board-ID "Grove Vision AI", built "Apr 4 2023".
- **Installed bootloader** (cached `INFO_UF2.TXT`): build `2d5b48b`, same SDK tag, Model "Seeed
  Studio Grove AI", Board-ID "Grove AI", dated Aug 23 2022.
- **Other features in the strings:**
  - An SFUD SPI-flash driver (SFDP probing; 4 KiB, block and chip erase).
  - An XMODEM transmit state machine.
  - A WebUSB landing page and Microsoft OS 2.0 WinUSB GUID, matching the driverless vendor interface
    `1.2` seen in C3.
  - Vendor build-host paths are present and deliberately not reproduced.

## 5. Official library source (text read only)

The `v2.0.0` tag and default-branch `b4ef904d` trees differ only in examples, docs, CI files and
pin-macro guards. The `WEI` recovery code and `examples/erase/erase.ino` are functionally identical.
Their behaviour is audited in [HIMAX_RECOVERY_ASSESSMENT.md](HIMAX_RECOVERY_ASSESSMENT.md).

## 6. Limits

- No publisher signature or digest exists. Provenance rests on HTTPS from the official organisation
  and the two independently uploaded, identical bootloader copies.
- Strings and descriptors show capability, not runtime behaviour.
- The Linux fix claimed by Seeed is not explained by any changelog or source in the downloads.
- The A1 scripts and private outputs are kept with the ignored assets and are not published.
