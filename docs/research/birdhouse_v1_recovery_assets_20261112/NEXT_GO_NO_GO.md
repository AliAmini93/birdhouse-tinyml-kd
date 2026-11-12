# Next GO / NO-GO after A1

2026-11-12. Inputs:
- [Stage A/C report](../birdhouse_v1_usb_stage_ac_20261112/REPORT.md)
- [offline asset audit](OFFLINE_ASSET_AUDIT.md)
- [BL702 assessment](BL702_RECOVERY_ASSESSMENT.md)
- [Himax assessment](HIMAX_RECOVERY_ASSESSMENT.md)

## What A1 changed

- **Factory image confirmed.** The local factory fallback is byte-identical to Seeed's official
  `grove_ai_v02-00.uf2` (v2.0.0). It is still not a backup of the installed application.
- **Official BL702 bootloader v2.0.1 is in hand** (`5b077331…`) and has been audited. It carries both
  the `0060` and `8060` personalities and checks the factory UF2 family. Seeed states it fixes Linux
  and Mac recognition, which is unverified.
- **The official I2C "erase" is a write.** It rewrites the Himax boot-configuration record at
  `0x21000` and then depends on the UF2 route. It is not an independent recovery.
- **Full images rewrite both Himax loaders** non-atomically.

## Decisions

| Item | Decision | Gate to reach GO |
|---|---|---|
| A1 offline acquisition/audit | **GO, complete** | — |
| A2 host isolation (usb-storage quirk `2886:0060:i`, ModemManager ignore rule) | **Ready for review, not applied** | Owner approves each change and its rollback text |
| A3b `0060` isolation test on this host | NO-GO | A2 applied; approved BOOT double-click and return path; journal-only stop rule |
| **H-Q: read-only `0060` MSC qualification on another OS** (Windows, for which Seeed documents the workflow) with the *installed* bootloader | **Recommended next physical gate; NO-GO until approved** | Owner-approved host; no copy or write; observe enumeration, ≥10 min with no reset or I/O error, read `INFO_UF2.TXT` only |
| BL702 v2.0.1 update | NO-GO | BL702 assessment requirements 1–5; read-only ROM-ISP identity check first; owner accepts no rollback to `2d5b48b` |
| Official I2C erase (`WEI`) | NO-GO | MCU host, toolchain, wiring and schematic missing; it is a write; not independent |
| Himax factory rehearsal write (R1) | NO-GO | Qualified MSC host (H-Q or post-update); owner preservation decision; stop rule |
| Birdhouse candidate write (`009799e1…`) | NO-GO | Every gate above, plus PDM P1/P4 resolved or accepted; one exact hash; post-write plan |
| Stage B (`8060`, 120 s) | Optional, low value | Conditions in Stage A/C report section 6 |

## Recommended order

1. A2 review, then A3b. This tests whether hiding the drive from usb-storage stops the reset loop,
   confirming or refuting the host-timeout hypothesis.
2. H-Q on a Windows host with the installed bootloader. If `0060` MSC is stable there, a recovery
   transport exists without touching the BL702.
3. Decide on the BL702 update only after steps 1 and 2:
   - If H-Q passes, it is optional.
   - If H-Q fails, it is the vendor-documented remedy, with ROM ISP as the documented re-entry path.
4. Rehearse the factory image only after a qualified transport exists and the owner accepts losing
   the installed application.

**Approvals still required:** A2, each A2 change, A3b, H-Q, BL702 update, any I2C operation, the
factory rehearsal and the candidate write. Each is separate, and none is implied by A1.
