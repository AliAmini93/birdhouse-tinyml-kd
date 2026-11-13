# Recovery, backup and rollback gates

2026-11-13. **NO-GO for any recovery execution or firmware write.** This report is
file-only engineering research. The owner's Windows observations narrow the host
problem but do not qualify programming or certify recovery with damaged loaders.
See [evidence](EVIDENCE_MATRIX.md) and [mechanism details](UF2_WRITE_MECHANISM_AUDIT.md).

## 1. Independence has two different meanings

Application-independent recovery must work when Birdhouse cannot boot or answer.
Loader-independent recovery must additionally work when both Himax flash loaders
are invalid. Transport-independent recovery must work when BL702's 0060 MSC path is
unavailable. A route may satisfy one property without satisfying the others.

| Failure state / route | Evidence | Gate still open |
|---|---|---|
| Himax application broken, BL702 and Himax loaders healthy; factory UF2 | Official Seeed workflow recommends direct factory copy before I2C erase. | Installed bridge path, mode entry, host writing and factory boot have not been demonstrated on this board. Plausible, not qualified. |
| One Himax loader damaged; installed UF2 | Full factory file contains both loaders. | File inclusion does not establish that a remaining loader or BL702 can restore the other. Entry/dependencies unknown. |
| Both Himax loaders damaged; installed UF2 | Newer BL702 image has SFUD and XMODEM markers. | No source/trace proves direct Himax SPI access or ROM-assisted restoration. BLOCKED for a claim of recovery. |
| Healthy BL702, unusable MSC; WEI I2C erase then UF2 | Official config rewrite and factory-copy procedure. | Still requires MSC; not a full-image transport-independent route. Source defect described below. |
| Himax ROM-I2C bootstrap | Exact-part SDK RAM bootstrap and manual already reviewed in prior barrier assessment. | Grove wiring/straps, ROM entry with broken flash, host tool, format acceptance and full restore/verify are unqualified. Upload executes code, so is not read-only. |
| Himax loader UART/XMODEM | Prior static SDK receive/burn analysis. | Requires working reachable loader; installed routing/entry unverified. ACK precedes burn in inspected SDK receiver. |
| BL702 firmware damaged; BL702 ROM ISP | Official BOOT-held entry and programming workflow. | Not tested here; exact installed backup unavailable, tool/driver/power prerequisites unqualified. Repairs BL702, not Himax. |
| Both chips' firmware damaged | In principle, separate BL702 repair then a Himax route. | No demonstrated complete chain. Do not count two unqualified routes as one qualified recovery. |
| Debug probe / direct flash programmer | Generic technical possibilities only. | No verified board wiring, electrical isolation, attach/reset behavior or nondestructive backup/recovery procedure. |

No statement above certifies that both-loader damage permanently bricks Himax.
The supported conclusion is that recovery from that state is unproved, and no
independent full-image Himax recovery is ready for use on this board.

## 2. Critical review of official WEI erase

At Seeed_Arduino_GroveAI commit 49664aa8d5d63dfaaefe319b54455fb320791cbc:

- Seeed_Arduino_GroveAI.cpp:647–665 writes system registers to request loader entry.
  Dependence of this register path on valid flash/ROM state is not documented here.
- load_config:668–697 sends a start command with target 0x21000 and length 0x2FC
  (764), page commands and done. erase:707–713 enters loader, calls it, then resets.
  It is a configuration write, not a complete Himax flash restore.
- flash_read:560–571 only requests bytes from an I2C address; it provides no
  documented addressed full-flash readback transaction. A name is not a backup API.
- sys_read has an unbounded wait; return/status handling in the repair flow does
  not independently verify the programmed record. Some helpers use global Wire.

**New static bounds finding:** loader_config is 764 bytes, independently parsed
from the source array, SHA-256
94173481259fd4bdead3ca10379839063c89f79acde578b2163a64d15df30019.
WEI_FALSH_PAGE_SIZE is 128 (.h:41). The loop at .cpp:676–680 uses i < sizeof(array),
then copies 128 bytes at every iteration. Its six offsets are 0,128,256,384,512,640.
The final copy reads [640,768), four bytes beyond the array. The later remainder
branch (.cpp:682–693) separately sends the last 124 bytes again. This is a C++
out-of-bounds source read; no deterministic runtime payload, flash effect or
compiler behavior can be inferred. Intended bytes offered by the source-level
loop/remainder total 768 + 124, while the start command declares 764. Receiver
rejection/truncation semantics remain unknown.

This finding strengthens the gate against using the erase sketch as a diagnostic
or automatic retry. No source was patched, built or executed. The official wiki's
completion text does not replace readback verification. Its subsequent factory UF2
step still depends on the same USB path. [Official source](https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI/blob/49664aa8d5d63dfaaefe319b54455fb320791cbc/Seeed_Arduino_GroveAI.cpp#L668-L713).

## 3. Backup/readback: documented features versus safe board routes

| Candidate backup route | What is officially documented or present | Why it is not a qualified non-destructive backup here |
|---|---|---|
| GROVEAI INFO_UF2 | Official bridge-identification text file. | Contains build metadata, not BL702/Himax firmware or configuration. |
| CURRENT.UF2 | Generic official Adafruit upstream synthesizes bytes through board_flash_read, including in the inspected 2022 core. | Installed Grove fork may omit it or map another chip/staging area; newer v2.0.1 binary contains no literal CURRENT string in the inspected bytes. Absence of that string alone is not proof that readback is impossible. No installed full-flash read path/range or side effects established. |
| Bouffalo Flash Cube Read Flash | Official 2025 guide, sections 6.1/6.3, printed pp. 29–30, lists BL702 and reading a selected flash range to flash.bin. | Generic capability is real; Grove ROM entry/reset, helper execution, exact flash extent, protection and absence of implicit changes are unreviewed. Tool was not run. No guarantee of a truly nonintrusive backup of this installed board. Does not read Himax through that documentation. |
| BLDevCube update workflow | Seeed documents Chip Erase=True and Create&Program. | A destructive update procedure, not a backup. Do not run it to find out whether readback works. |
| WEI flash_read | Public I2C receive primitive. | No full addressed dump command, completeness contract, safe entry or verified read-only transaction sequence. |
| Himax loader dump markers / ROM bootstrap / debugger | SDK binary markers/manual and generic possibilities. | Markers do not define a reachable safe command; bootstrap/debug attach can execute/reset/change state. No officially qualified Grove full backup route identified. |

Source for the generic BL702 read feature:
[official Flash Cube guide](https://github.com/bouffalolab/bouffalo_sdk/blob/master/tools/bflb_tools/bouffalo_flash_cube/docs/FlashCube_User_Guide.pdf),
cached digest in [E15/source registry](EVIDENCE_MATRIX.md). This is a scoped negative
finding: **no truly non-destructive full backup route is established by the reviewed
official Grove materials**, not a claim that no read command exists anywhere.

No installed BL702 backup, Himax application backup or configuration backup exists
in the evidence used here. The identical factory fallback copies are recovery
assets, never backups of the installed state. Reflashing factory cannot promise
restoration of the current app, settings, model slots, calibration or entire flash.
Never publish any future full dump without privacy/security review.

## 4. Rollback limits

1. A factory fallback is another nontransactional full write through the same
   unqualified installed updater. It can also fail and requests loader-region data.
2. Matching loader bytes do not prove the updater skips their sectors. No atomic
   bank swap, power-fail safe journal or protected-loader guarantee is established.
3. Candidate and factory omit upper flash/configuration ranges; physical erase
   effects outside payload are unknown. Shorter-image tail cleanup is not assured.
4. BL702 v2.0.1 is available but the exact installed 2d5b48b image is not. Updating
   the bridge would lose exact rollback and remains explicitly unauthorized.
5. A future first factory write is itself the first consequential experiment. It
   cannot be prequalified as safe by read-only observation alone. Its risk requires
   an explicit owner loss decision and independently reviewed experimental scope.

## 5. Full firmware versus separate models/configuration

| Choice | Engineering advantages | Engineering costs / unresolved hazards |
|---|---|---|
| Repeated full Birdhouse image | One pinned artifact binds microphone code, preprocessing, operator resolver, model, quantization and diagnostics; reproducible package identity. | Repeatedly exposes loader/metadata regions, transfers more bytes, increases interruption opportunities and potentially erase wear. No endurance or failure probability is quantified. Each flash can lose existing state. |
| Separate model slot | With a compatible resident app and verified mapping, can reduce transferred/erased scope and avoid loader updates. Seeed's V1 tutorials describe multiple vision-model slots. | Same UF2 transport remains; slot addressing, erase boundaries, integrity and resident-app compatibility must be established. A vision model UF2 does not install Birdhouse PDM/preprocessing/runtime. |
| Separate persistent config | Small bounded updates could avoid firmware changes; runtime settings can sometimes avoid flash writes entirely. | Requires schema/version compatibility, validation, erase-unit isolation, wear strategy and power-failure behavior. A tiny record may still erase a whole sector. No safe config updater is established for this candidate. |
| Future app-only image | Could avoid loader ranges if supported by an audited updater and boot manifest. | Removing blocks from a full image is not proof of a valid bootable package or preserved sectors. Requires its own format, dependency and recovery audit. |

The current Birdhouse runtime explicitly passes the linked student model array to
ModelInit (firmware/himax_arc/birdhouse/bh_runtime.cc:210–211). bh_model.cc checks
shape/type/quantization and uses a fixed five-operator resolver; bh_config.h fixes
capture parameters. The validated 59,760-byte model is compiled into the application,
not automatically interchangeable with Seeed's external vision-model slots.
Separate model/config updates would be an architecture change needing design and
qualification. **No architecture, model, configuration or updater was changed.**

Minimizing unnecessary full flashes is a reasonable engineering objective, but
neither a smaller file nor model-only transfer closes the current transport and
recovery gaps. Do not use a dummy file or erase_model as a harmless write test.

## 6. Gates and present state

| Gate | Evidence needed | Present state |
|---|---|---|
| G0 identity/provenance | Exact image hashes, version map and correct V1 target | File provenance PASS; installed full code identity unresolved. |
| G1 preservation | Qualified complete backup, or explicit acceptance of unrecoverable installed-state loss | OPEN. Owner's audit authorization is not loss acceptance. |
| G2 installed updater | Source/binary-correlated address mapping, buffering, erase/ACK/completion/error/verify semantics | BLOCKED by missing installed code. |
| G3 write transport | Evidence on exact Windows host/cable/power/build covering WRITE10 and programming, with errors/completion checked | OPEN. Read-only owner observations are useful but insufficient. |
| G4 full Himax recovery | Route proven independent of candidate health; for highest-risk loader writes, both-loader-loss restoration and an independent transport route | OPEN/BLOCKED. No qualified full-image route independent of MSC. |
| G5 application safety | P1 stop/re-arm/IRQ quiescence and P4 unbounded boot/ISR polling resolved with authoritative semantics and validation | OPEN. Existing host tests do not close peripheral behavior. |
| G6 experimental first write | Reviewed staged plan, power/timeout/failure handling, exact image and new owner authorization | DRAFT ONLY; [protocol](WINDOWS10_FIRST_WRITE_DRAFT.md). |
| G7 post-boot qualification | Identified image, numerics, timing/progress, stack/arena, single-stop and no late re-arm | NOT RUN; hardware actions excluded. |

No gate is waived by Windows read stability. An owner could later choose a
separately reviewed destructive experiment with explicit residual-risk acceptance;
that would be a changed decision basis, not a finding of safety in this audit.
