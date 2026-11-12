# Grove Vision AI V1: cached-metadata results, PID 0060 isolation plan, recovery gates

2026-11-12. Redacted report; **pending privacy review, not committed**. Raw evidence (journal
dumps containing serial strings, script outputs) is stored privately outside the repository
(mode 700) with SHA-256 sums. Every shell command was individually approved by the owner.

**Update (A1, same day):** the offline asset audit in
[../birdhouse_v1_recovery_assets_20261112/](../birdhouse_v1_recovery_assets_20261112/OFFLINE_ASSET_AUDIT.md)
resolves several open points in section 4. Those rows are corrected below and marked "A1".

**Status:** target identity UNAMBIGUOUS; current mode is CDC-only and quiet. A target-specific
isolation method for PID `0060` has been identified. It was proposed, **not applied**. Stage B,
firmware writes and recovery remain **NO-GO**.

No host configuration, driver binding, power setting, serial/block device, mount, reset, BOOT
action, reconnection or USB request was made or caused. The only USB-related reads were cached
kernel sysfs/udev metadata, verified as described in section 2.

## 1. Inputs carried forward (H1–H8, H8b, H8c)

- Host: Ubuntu 24.04.4, kernel `7.0.0-38-generic`, systemd 255, GNOME on X11, bare metal.
- Active probers: ModemManager (all ttys tagged `ID_MM_CANDIDATE=1`, no ignore rule for VID 2886),
  udisks2 with GNOME `automount` and `automount-open`, fwupd. In-kernel disk polling is 2 s.
  `usb_storage.delay_use=1` s.
- Two journalled boots show 38 Grove sessions on kernel path `3-8`. All 59 resets occurred in PID
  `0060` sessions (MSC + CDC, GROVEAI drive). PID `8060` (CDC only) had no resets.
- In `0060` sessions:
  - usb-storage binds at +0.13 s after enumeration.
  - The first reset comes at a median of +31.46 s, then every 30.72 s.
  - The SCSI disk attached in only 5 of 27 sessions, and always after 3–4 resets.
  - Every GROVEAI auto-mount that fell inside a session came ≥93 s after its enumeration. One mount
    line fell 0.5 s *before* an enumeration and belongs to the preceding session.
  - One fwupd error per boot (≈+54 s) also came after the first reset.
- Inference: the first stalled command is issued during the kernel's own sd probe, and the host's
  30 s SCSI timeout then resets the device in a loop. The board-side reason for the stall is
  unknown.
- The 4 ModemManager lines naming path `3-8` fall outside every Grove session. C0 found 26
  enumerations on that path this boot, of which 18 were the Grove, so those lines most plausibly
  belong to another device that used the same port.

## 2. C-class results (cached metadata only)

**Non-interactivity was checked against upstream Linux v7.0 source** (Ubuntu patches not inspected):
- `drivers/usb/core/sysfs.c`: identity, speed, power-duration, string and interface attributes
  only format cached `descriptor`, `actconfig`, `cur_altsetting` and `udev` fields (some take the
  device lock). There is no `usb_control_msg`, `usb_string` or runtime-PM call.
- `drivers/base/power/sysfs.c`: `control`, `runtime_status` and `autosuspend_delay_ms` only read
  `dev->power` fields.
- `usb_uevent`, `usb_dev_uevent` and `usb_if_uevent` (read by `udevadm info`) use cached fields
  only.
- Excluded: hub-port attributes. `port/disable` calls `usb_autopm_get_interface` and
  `usb_hub_port_status`, so it is not passive.

| Check | Result |
|---|---|
| C0 presence/continuity | Path `3-8` present (xHCI root hub `usb3`). The last enumeration was device number 34, `2886:8060`, ≈43 min earlier. Since then: 0 resets, 0 disconnects, 0 MSC binds, 1 ACM bind. **PASS** |
| C1 identity | `2886:8060`, bcdDevice 01.00, USB 2.10, full-speed (12 Mb/s), bMaxPower 500 mA, config 1, 3 interfaces, IAD composite (EF/02/01), "Seeed Studio" / "Grove AI". The serial (hashed in memory, never printed) matches the open journal session and historical identity **H1**. devnum matches the journal. **UNAMBIGUOUS** |
| C2 power/topology | `power/control=on` (no autosuspend), `runtime_status=active`, `active_duration` equals `connected_duration`, so never suspended. Connected since **15:38:50 UTC**. Direct root port, no external hub. |
| C3 interfaces | `1.0` CDC-ACM 02/02/**00** → `cdc_acm`, `ttyACM0`. `1.1` CDC data 0a/00/00 → `cdc_acm`. `1.2` **vendor-specific ff/00/00, no kernel driver**. No mass-storage interface, no SCSI host. **PASS** |
| C5 udev | `ttyACM0`: `ID_MM_CANDIDATE=1`. No `ID_MM_DEVICE_IGNORE`, `ID_MM_PORT_*` or `ID_MM_DEVICE_PROCESS`. `TAGS=:systemd:` only (no `uaccess`). No `UDISKS_*`. |

**ModemManager filtering: inferred FILTERED (not probed).**
- MM ≥1.20 defaults to the strict policy, and the unit passes no filter flag.
- Strict forbids serial ports by default.
- Its CDC-ACM rule accepts only class 2 / subclass 2 / protocol 1–6, the AT command sets; this port
  reports protocol 0.
- The device has no network interface.
- No MM log line exists for this session.

MM debug output and the exact 1.23.4 filter source were not available, so this is inference.

**Residual exposure in the current mode:**
- Interface `1.2` has no driver, so any root process using libusb (e.g. fwupd) could send it
  vendor requests. Without a `uaccess` tag, browser WebUSB in the user session is unlikely to be
  able to open it. Device-node permissions were not checked.
- `cdc_acm` refcount 0 shows no tty client as of H5. This must be rechecked immediately before any
  later phase.

## 3. Target-specific isolation plan for PID 0060 (proposed, not applied)

**Recommended mechanism:** add a usb-storage quirk entry `2886:0060:i` (`US_FL_IGNORE_DEVICE`).

**How it prevents the loop (upstream v7.0 `drivers/usb/storage/usb.c`):**
1. `usb_stor_probe1` logs "USB Mass Storage device detected".
2. `get_device_info` applies the module `quirks` string through `usb_stor_adjust_quirks`, logs
   "device ignored" and returns `-ENODEV`.
3. The temporary host is released. `usb_stor_probe2` never runs, so there is no `scsi_add_host`,
   no delayed scan, no control thread and no SCSI command.

With no SCSI command, the 30 s SCSI-timeout reset loop cannot start. uas is not involved: the
journal shows usb-storage, never uas, binding the `0060` interface.

**Two ways to apply it (each a host change needing separate approval):**
- **Runtime:** a root write of `2886:0060:i` to `/sys/module/usb_storage/parameters/quirks`.
  - The parameter is a single 128-byte string with mode 0644 (currently empty), so the write
    replaces the whole list.
  - It affects only future probes of that VID:PID.
  - The other attached USB drive and the current `8060` session are unaffected.
  - Rollback: write an empty string.
- **Persistent:** `/etc/modprobe.d/` with `options usb-storage quirks=2886:0060:i`.
  - Effective at the next module load, i.e. reboot. usb-storage is loaded and in use, so do not
    reload it.
  - Rollback: delete the file.

**Companion, target-specific udev rules** (in `/etc/udev/rules.d`, applied at the next add event;
no `udevadm trigger`):
- `ID_MM_DEVICE_IGNORE=1` for `2886:0060` and `2886:8060`. The `0060` ACM protocol is unverified.
- Optionally `UDISKS_IGNORE=1` for `2886:0060`, which matters only if the quirk is later removed.
- Session-scoped fwupd suspension (e.g. stopping the D-Bus-activated daemon with masking only for
  the session) also needs its own review, because fwupd reacted to past `0060` attaches.

**Rejected alternatives:**

| Alternative | Why rejected |
|---|---|
| Disabling automount, udisks or tracker | By the section 1 inference, the stall starts in the kernel probe, before any user-space prober. |
| Read-only mount | Still issues SCSI traffic. |
| udev per-interface `authorized=0` | Races the in-kernel probe, which runs at +0.13 s. |
| Host-controller `interface_authorized_default=0`, global `authorized_default=0`, `scsi_mod.scan=manual`, blacklisting usb-storage | Bus- or host-wide; would break the attached USB drive and the internal SCSI scan. |
| Changing timeouts or `delay_use` | Only shifts the period. |
| Command-specific quirk letters (e.g. `o`, `w`, `n`, `e`, `f`, `m`) | Guesses until the stalled command is identified, which needs a separately reviewed usbmon trace. |
| A dedicated isolated host booted with `usb-storage.quirks=2886:0060:i`, MM and fwupd disabled, no desktop | Not rejected: **preferred** for any consequential session. |

**Falsification value:** with the quirk active, a `0060` enumeration should log "device ignored",
create no `scsi host`/`sd` lines, and show **no reset at ≈+31.5 s**. If resets persist, the
host-timeout hypothesis is refuted and the cause is board-side. Entering `0060` needs a BOOT
double-click and returning needs a reset or replug. Both are physical actions requiring separate
approval.

**Effect on UF2 flashing and recovery:**
- While the quirk is active, the GROVEAI drive never appears on this host: no UF2 copy, no
  `INFO_UF2.TXT` read.
- Removing it would be expected to restore the loop. Historically, in `0060` mode the disk attached
  only after 3–4 resets and kept resetting.
- UF2 writes are block-by-block, not transactional, and the factory and candidate UF2s include the
  Himax bootloader regions. A write over this transport could leave a partial image.
- Isolation is therefore a **protective and diagnostic measure, not an enabler**. Every documented
  Himax recovery (factory UF2, or I2C erase then UF2) depends on the same `0060` MSC path, so
  recovery is not independent on this host.

## 4. Official Seeed recovery assets versus local evidence

From the Seeed V1 wiki and the Seeed_Arduino_GroveAI GitHub releases API. No release asset has a
published digest, and nothing was downloaded.

| Asset (official) | Size | Purpose | Local status |
|---|---:|---|---|
| `tinyuf2-grove_vision_ai_v2.0.1.bin` (releases v1.1.0 and v2.0.0) | 93,500 | BL702 bootloader. Wiki: "has now fixed the problem of Vision AI not being able to be recognised by Mac and Linux" | **A1: acquired** (`5b077331…`; both release copies identical) |
| BouffaloLabDevCube 1.6.6 (win32 archive, files.seeedstudio.com) | — | BL702 ROM-ISP programming (hold BOOT while connecting; Chip Erase) | **Missing**; Windows-only as documented |
| `grove_ai_v02-00.uf2` (v2.0.0) | 1,541,632 | Factory Himax firmware | **A1: byte-for-byte identical** to both local fallback copies (`8854e093…`) |
| `erase_model.uf2` (v2.0.0) | 38,400 | Model-area erase via UF2 (by name) | **A1: acquired** (`1668c816…`); also depends on the MSC path |
| Older factory/capture UF2s (v01-30, capture v01-00) | 1.44–1.55 MB | Older images | Missing; not needed |
| Seeed_Arduino_GroveAI source (WEI `ID`/`enter_bootloader`/`erase`, Protocol.md) | — | I2C erase from an external MCU | **A1: acquired and audited.** "Erase" rewrites the Himax boot record at `0x21000`. Arduino toolchain and MCU host still **missing** |

**Installed BL702 bootloader:**
- The cached `INFO_UF2.TXT` reports TinyUF2 build `2d5b48b` (2022-08-23). That predates v2.0.1,
  which was built Apr 4 2023 and first uploaded on 2023-04-04 to release v1.1.0 (release published
  2023-03-22).
- The installed binary is **not** available, so a BL702 update cannot be rolled back to the exact
  installed version.
- A1: the v2.0.1 image contains both the `0060` and `8060` USB personalities, so one BL702 image
  provides both modes.

## 5. Staged recovery and firmware-update qualification plan

| Stage | Action | Approval needed | GO gate (all required) | Status |
|---|---|---|---|---|
| 0 | Host-only and cached-metadata inspection | done | — | **Complete** |
| 1 | Download listed official assets into a new empty directory over HTTPS. Record SHA-256; compare the two `tinyuf2` copies and the factory UF2 with the local fallback. Offline audit: UF2 block family/addresses/coverage, bootloader strings/VID/PID/MSC behaviour, WEI erase semantics. **No execution.** | A1: exact URL list | Provenance and hashes recorded; coverage of Himax loader regions known; whether the BL702 image includes the bridge app known | Ready for review |
| 2 | Apply isolation policy (runtime quirk, MM ignore rule; optional udisks/fwupd) | A2: each change separately, with rollback text | Read-back of parameter and rule files; C0/C1 show the current session undisturbed | NO-GO until approved |
| 3a | Stage B in `8060` (120 s journal) or simply later H8 re-aggregation | A3a | Section 6 conditions | Optional, low information value |
| 3b | `0060` isolation test: BOOT double-click, journal-only observation for ≥10 min, return by approved reset/replug | A3b: physical mode transition and return | Quirk active; probers suppressed; stop rule agreed | NO-GO |
| 4 | Qualify one write transport, read-only first: a different OS host or an isolated host for MSC, or a BL702 2.0.1 update (W2). Requirement: ≥10 min in `0060` with zero resets and I/O errors, and `INFO_UF2.TXT` readable, on the exact host to be used | A4 per host; **W2 is an irreversible BL702 write**: separate A6 | Zero-reset MSC window; for W2, ROM-ISP entry first verified read-only and the owner accepts no exact rollback | NO-GO |
| 5 | Recovery rehearsal: write the **factory** UF2 over the qualified transport, after the owner accepts loss of the installed app/config (no backup exists). Separately qualify one independent route (I2C erase + UF2, or BL702 ROM ISP for the bridge) | A5 preservation decision; A7 rehearsal write | Factory image boots and enumerates normally; route documented with erase/write ranges | NO-GO |
| 6 | Candidate write, one exact hash (`009799e1…` UF2), re-hashed immediately before transfer | A8 | G1–G5 passed; PDM risks P1/P4 resolved or explicitly accepted; abort criteria agreed | NO-GO |
| 7 | Post-write qualification (INFO, graded self-test, synthetic cases, one timed capture, stack/arena/IRQ checks) | A9 | Stop at first unexpected output | NO-GO |

**Rollback limitations:**
- No readback or backup exists of the installed Himax app/config, so any Himax write rolls back only
  to the factory image.
- The installed BL702 bootloader binary is unavailable, so BL702 updates are irreversible to the
  exact prior version.
- UF2 is not transactional, and the SDK XMODEM loader ACKs before burning and does not check the
  program result.
- No power-loss behaviour is known.
- On this host, every documented Himax recovery path shares the unstable `0060` MSC transport.
- A passing Stage B or isolation test never implies update safety.

## 6. Stage B status (8060 mode)

| Condition | Status |
|---|---|
| Identity | met (C1) |
| No MSC | met (C3) |
| No autosuspend | met (C2) |
| ModemManager | filtered (inferred, C3/C5) |
| Quiet baseline | met (≥43 min, zero target events) |
| Owner approval of exact window, log destination and stop rule | still required |
| Fresh `cdc_acm` refcount/fd check immediately before and after | still required |
| No libusb/WebUSB use of interface `1.2` (owner confirmation; fwupd suppression optional) | still required |

The existing 43-minute quiet journal window already exceeds the 120 s observation. Stage B in `8060`
cannot inform the `0060` barrier.

**Decisions:**
- Stage 1 downloads: ready for review.
- Isolation policy: ready for review, not applied.
- Stage B, `0060` tests, BL702 update, all writes and recovery: **NO-GO**.

Sources: upstream Linux v7.0 (`drivers/usb/core/{sysfs,driver,message,usb,port}.c`,
`drivers/usb/storage/usb.c`, `drivers/base/power/sysfs.c`); modemmanager.org port and device
detection; ModemManager filter patch (cdc-acm protocols 1–6, 2018); Seeed wiki "Grove - Vision AI
Module"; GitHub releases API for Seeed-Studio/Seeed_Arduino_GroveAI.
