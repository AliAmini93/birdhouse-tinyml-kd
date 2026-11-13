# Windows UF2 safety audit: evidence matrix

2026-11-13. Owner-authorized interactive, file-only research. Baseline repository commit:
9ab87fea1bde6419478480249e9dd518acff6bfd, branch
research/birdhouse-v1-predeployment-codex-20261111. The target board is not on the
execution host; the owner's board is on a different Windows 10 host.
No device access, vendor-code execution, package installation, host configuration
change, firmware change, or physical experiment was performed. The six reports are
the only new filesystem outputs of this audit. Public sources were read through
connectors/browser research; no downloaded code was executed or imported.

**Decision: GO for this completed offline audit; NO-GO for first write, deployment,
recovery execution, or BL702 update.** See [the decision](FINAL_GO_NO_GO.md).

## Evidence classes

- MEASURED: independently calculated from local files as inert bytes.
- SOURCE: directly read source text at an identified revision; applicability is stated separately.
- CARRIED: prior sanitized evidence, critically reviewed but not independently reproduced here.
- OWNER: owner's limited observation, without raw Windows evidence inspected in this audit.
- INFERENCE: engineering interpretation; neither code identity nor physical behavior is established.
- UNKNOWN/BLOCKED: evidence needed to close the question is unavailable within this mission.

## Claim matrix

| ID | Claim and evidence | Class / confidence | Limit or consequence |
|---|---|---|---|
| E01 | INFO_UF2 identifies installed TinyUF2 build 2d5b48b, Aug 23 2022, SDK V1.4.3-8-g8742503a; owner reports the same build on Windows. | CARRIED + OWNER / moderate | Not a dump, full commit identity, or proof of the code implementing writes. |
| E02 | Windows GROVEAI visually remained present for 10 minutes without reconnect, INFO_UF2 was readable, and a targeted System query found zero matching disk/USB warnings/errors over 30 minutes. | OWNER / limited | Exact query coverage, USB transaction continuity and WRITE10 behavior were not independently inspected. No write qualification. |
| E03 | Historical Ubuntu: 27 PID 0060 MSC sessions, all with resets, 59 resets total; PID 8060 sessions had no resets in the reviewed history. | CARRIED / bounded historical evidence | The SCSI-timeout explanation is a motivated hypothesis. Windows reading does not prove or refute that root cause. Earlier 22-reset counts used a smaller log scope. |
| E04 | Installed BL702 source/binary is absent from inspected caches; 2d5b48b lookup failed in upstream adafruit/tinyuf2 and in the release uploader's LynnL4/tinyuf2 fork. Global short-hash search returned unrelated commits. | SOURCE search / strong scoped negative | Absence from these searches is not proof the source never existed. Exact installed acceptance, buffering, erases, ACK and verification remain BLOCKED. |
| E05 | Official v2.0.1 binary SHA-256 5b0773315e923ce65b5c033b8b269d7ad396a088940a50f9cfe13ac3972d1d9c; two release copies match per A1. Family-constant instruction bytes at offset 0x982 independently rechecked. | MEASURED + CARRIED | Newer image, not installed firmware. Strings/constant construction do not establish complete write or recovery behavior. |
| E06 | Generic TinyUF2 core in August 2022 invokes board_flash_write before block accounting; write/flush APIs return void. Current upstream propagates write failures and has an optional flash-status hook. | SOURCE / high for those files | Neither revision is the Grove BL702 port or the installed build. No backport assumption. |
| E07 | Factory, exact pinned Birdhouse candidate and erase_model UF2 pass independent block parsing: 5,540 total blocks; valid magics, family, flags, numbering, contiguous addresses, payload size, zero unused block bytes. | MEASURED / high | File integrity and compatibility of packaging, not flash integrity or boot-ROM acceptance. |
| E08 | Both full images include exact SDK second loader at offset 0, first loader at 0x10000; entire loader slots and 0x21000 record match between images. | MEASURED / high | Full-image requests cover loader regions. Actual skip/erase/program behavior remains unknown. Identical bytes do not protect against erase interruption. |
| E09 | Candidate coverage ends at 0x10099600; factory ends at 0x100BC300; uncovered difference 142,592 bytes. Candidate unpadded image is 628,016 bytes, followed by 208 zero payload bytes. | MEASURED / high | No claim that uncovered physical flash survives; see sector scenarios in [mechanism audit](UF2_WRITE_MECHANISM_AUDIT.md). |
| E10 | Candidate's seven stored ELF sections reconstruct exactly from SBS descriptors; validated model is present in reconstructed read-only data. | MEASURED / high | Model bytes span packaging chunks; searching only for one contiguous flat-image blob is insufficient. This validates packaging, not execution. |
| E11 | SFUD and XMODEM strings occur in newer official BL702 binary; A1 reports descriptors for both USB personalities. | CARRIED / moderate | SFUD could serve staging or another flash; direct programming of Himax flash is unproved. UART/XMODEM dependency is also not established for installed UF2. |
| E12 | SDK first-loader analysis places EOT ACK before caller erase/program, with no checked program result before the completion message. | CARRIED / specific binary only | Not an observed USB ACK or installed bridge path. It cannot establish installed UF2 timing. |
| E13 | Official WEI erase writes a configuration record at 0x21000, then reset; the official workflow still uses factory UF2. | SOURCE + MEASURED / high | Not bulk erase, not full-image restoration, not independent of MSC. |
| E14 | WEI load_config loop copies 128 bytes at offset 640 from a 764-byte array, then sends a separate 124-byte remainder. | SOURCE + MEASURED / high static finding | Four-byte out-of-bounds source read; runtime effects/receiver handling unknown. Prior A1 omitted this defect. Do not execute the sketch. |
| E15 | Bouffalo Flash Cube guide sections 6.1/6.3 document BL702 selection and generic flash-content reading. | Official documentation / high for feature | Does not prove a nonintrusive Grove backup; boot entry, helper execution, read protection, full range and side effects are unverified. |
| E16 | No reviewed official Grove V1 procedure provides a qualified, truly non-destructive full backup of existing BL702 and Himax firmware/configuration. | Scoped source review / moderate | Not proof readback is technically impossible. CURRENT.UF2 in generic upstream is not evidence it exists or covers the right chip here. |
| E17 | Application-independent and MSC-independent full Himax recovery have not been demonstrated; both-loader-loss recovery through installed UF2 is unproved. | UNKNOWN / consequential | Factory fallback is an asset, not a recovery guarantee or installed-state backup. |
| E18 | PDM P1 stop/IRQ/re-arm race and P4 unbounded boot/ISR polling remain open in the exact candidate. | CARRIED static evidence / high within scope | Windows storage stability does not close either hazard. No capture or retry authorized. |

## Source registry and provenance

Local authoritative inputs, all read before new conclusions:

- [Stage A/C report](../birdhouse_v1_usb_stage_ac_20261112/REPORT.md).
- A1 [asset audit](../birdhouse_v1_recovery_assets_20261112/OFFLINE_ASSET_AUDIT.md),
  [BL702 assessment](../birdhouse_v1_recovery_assets_20261112/BL702_RECOVERY_ASSESSMENT.md),
  [Himax assessment](../birdhouse_v1_recovery_assets_20261112/HIMAX_RECOVERY_ASSESSMENT.md),
  [gates](../birdhouse_v1_recovery_assets_20261112/NEXT_GO_NO_GO.md), and
  [asset JSON](../birdhouse_v1_recovery_assets_20261112/results/asset_audit.json).
- Deployment-barrier [assessment](../birdhouse_v1_deployment_barriers_20261111/ASSESSMENT.md)
  and [observer protocol](../birdhouse_v1_deployment_barriers_20261111/READ_ONLY_DIAGNOSTIC_PROTOCOL.md).
- [Recovery review](../birdhouse_v1_codex_predeployment_20261111/RECOVERY_REVIEW.md),
  [packaging manifest](../birdhouse_v1_codex_predeployment_20261111/results/validated/package_candidate.json),
  and [expected device values](../birdhouse_v1_codex_predeployment_20261111/results/validated/expected_device_values.json).

External primary sources inspected on 2026-11-13:

| Source | Revision / exact location | Provenance boundary |
|---|---|---|
| [Seeed V1 wiki](https://wiki.seeedstudio.com/Grove-Vision-AI-Module/) | Replacement of new models; Exception Processing parts 1–3 | Official workflow; live page, not a specification of installed internals. Cached A1 page SHA-256 be3494412532cf568ecf3191231439f7937b73b327c7e029845a6f1e3d483bb8. |
| [Seeed v2.0.0 release](https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI/releases/tag/v2.0.0) | Factory asset 121727367; BL702 asset 130945222; erase_model asset 121851617 | Official organization; A1 HTTPS acquisition, no publisher digest/signature supplied in that manifest. |
| [WEI source](https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI/blob/49664aa8d5d63dfaaefe319b54455fb320791cbc/Seeed_Arduino_GroveAI.cpp#L546-L713) | Seeed_Arduino_GroveAI.cpp lines 546–713; .h line 41; commit 49664aa8d5d63dfaaefe319b54455fb320791cbc (tag v2.0.0) | Public official source; local archived source read as text, never compiled/imported. |
| [Historical TinyUF2 core](https://github.com/adafruit/tinyuf2/tree/e91e98cbabf9139b9c84e21a4304a504be8e4345/src) | Commit e91e98cbabf9139b9c84e21a4304a504be8e4345, 2022-08-17; src/ghostfat.c, msc.c, board_api.h | Official upstream, contemporaneous comparison ONLY. It is not build 2d5b48b. |
| [Current TinyUF2 core](https://github.com/adafruit/tinyuf2/tree/d4a85300160ae1ad9069a4e450e067949fca35fd/src) | Commit d4a85300160ae1ad9069a4e450e067949fca35fd, 2026-11-12; same three files | Official upstream, newer comparison ONLY; inspected ports directory has no BL702/Grove port. |
| [Release uploader's fork](https://github.com/LynnL4/tinyuf2) | Master 119763803d3c91706f224ae771d67d2bae1d5fb4; listed branches also checked for BL702/Grove paths | Discovery lead, NOT an official Seeed release source or installed-code attribution. No full source downloaded. |
| [UF2 specification](https://github.com/microsoft/uf2#file-format) | README: format and family flag | Format authority; not a board safety guarantee. |
| [Bouffalo Flash Cube guide](https://github.com/bouffalolab/bouffalo_sdk/blob/master/tools/bflb_tools/bouffalo_flash_cube/docs/FlashCube_User_Guide.pdf) | Cached official PDF, printed pp. 29–30, sections 6.1–6.3, version 1.6 / 2025; SHA-256 51136477c2a90d11b1865b766555dea3313eeeea78f5a34b8a5aed71e6ae293d | Text extracted locally with Poppler, no vendor execution. URL is mutable; cached digest identifies the inspected bytes. |
| [Windows FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers) | API description, Remarks | Host buffering behavior, not proof of remote firmware verification. |
| [SDK source](https://github.com/edgeimpulse/firmware-seeed-grove-vision-ai/tree/9dc2370d4dc269dc4bcafcf0354b8f745d08801f) | Synopsys_PA8535_EM9D_DFSS_SDK_3.3; configs/grove_ai_config.h in app/scenario_app/edge_impulse_visionai | Local revision independently confirmed. Proprietary binary/source contents are not reproduced. |

Connector limits: repository-fork listing and generic repository-search URL forms were
unsupported; binary PDF fetch through the GitHub connector was unsupported. These are
API capability limits, not evidence about the board. Existing cached official data and
supported read APIs sufficed; no sandbox bypass was requested. No exact installed code
was found. The seven-character build label is not promoted to an invented full SHA.

## Independent verification and corrections

All Python calculations used the owner's existing BH_PYTHON with -I and standard
library only. Small inline analyzers read files as bytes/text; no project or vendor
module was imported. UF2 parsing, ELF section reconstruction, loader identity, padding,
tail arithmetic and WEI loop bounds were independently checked. Existing packaging,
driver tests and vendor generators were not rerun.

Corrections to prior reports: (1) full images REQUEST writes to both loader regions,
but actual physical rewrite/skip policy is unknown; (2) an uncovered UF2 tail is not
known to retain its previous physical contents; (3) SFUD strings do not establish
direct BL702-to-Himax SPI recovery; (4) generic official BL702 flash-read tooling
exists, but a qualified non-destructive board backup route does not follow; (5) WEI's
last-page loop has a newly identified static bounds defect. Earlier reports remain
historical evidence with these qualifications.

Privacy: no raw logs, serials, unique hardware identifiers, private host paths,
credentials, audio or proprietary code/binary payloads are included. Published hashes
identify firmware/model research artifacts, not private device identity.
