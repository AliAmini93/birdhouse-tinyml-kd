# Owner decision record — unsigned, inactive

2026-11-13. **BLOCKED: no newly validated UF2 exists. Do not sign a digest-specific
write approval until the offline artifact gates pass.** Complete the actual
identity/host details privately; do not commit device IDs or personal signatures
to the public repository. Selection of Path B is not approval for an unknown hash.
Resumed host/build/ELF checks passed; namespace creation prevented packaging.
The unpackaged ELF is not an approvable UF2. Physical Windows-only attachment
was confirmed; no hardware operation was authorized or performed.

| Required field | Owner entry (blank unless stated as known context) |
|---|---|
| Operator / reviewer / decision date | ____________________ |
| Physical product and privately verified target volume | ____________________ |
| Firmware source (known context) | `3d0fb3fd4c1889d79462bbc404aee722c1811894` |
| Chosen new UF2 filename | ____________________ (currently unavailable) |
| Chosen full 64-digit SHA-256 | ____________________ (currently unavailable) |
| Chosen exact bytes / blocks / address interval | ____________________ |
| Ubuntu and Windows independent hash/size checks | ____________________ |
| Choice: direct Birdhouse one write, or factory rehearsal only | ____________________ |
| Exact one-time manual Explorer operation, actual source and target | ____________________ |
| Any required mode-entry operation, separately approved steps | ____________________ |
| Windows host / cable / documented power arrangement | ____________________ |
| Finite observation interval and state-specific stall handling | ____________________ |
| Private observation/evidence location | ____________________ |

All acknowledgments remain unchecked:

- [ ] I accept possible permanent loss of this **sole board**, even if the host
  transfer appears successful, and understand that hardware replacement may be needed.
- [ ] I accept possible unrecoverable loss of installed app, settings, model slots
  and calibration. There is no qualified independent full backup/recovery, and
  the official factory image is not my installed-state backup.
- [ ] I understand installed BL702 `2d5b48b` write/erase/completion/readback behavior
  is unresolved; Windows read stability does not qualify WRITE10 or durable flash.
- [ ] I understand P1 is permanent first-party one-attempt quarantine, not proven
  DMA stop/quiescence, and P4 remains `VENDOR_LEVEL_BLOCKED` with possible boot/ISR hang.
- [ ] I understand real ARC MLI, microphone, timing and stack are unvalidated;
  offline packaging success would leave actual boot UNKNOWN.
- [ ] I choose the stated write count knowingly. A factory rehearsal adds a risky
  full write and does not guarantee recovery from damaged loaders or interruption.
- [ ] I approve only the exact digest and numbered human operation written above.
  No automatic retry, factory fallback, reset/replug, BL702 update, WEI erase,
  BLDevCube, ROM-I2C or console/capture access is included.
- [ ] I understand G1/G2/G3/G4 and P4 remain OPEN; my loss acceptance is a changed
  experimental decision basis, not evidence that these technical uncertainties closed.

Official fallback context only: `grove_ai_v02-00.uf2`, **1,541,632 bytes**, SHA-256
`8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c`.
Using it requires another explicitly approved full-write decision; success is not
guaranteed. No fallback approval is recorded here.

Owner decision (approve / decline / defer): ____________________

Owner explicit authorization text / date: ____________________

Reviewer confirmation of exact artifact and procedure: ____________________

No signature, check mark or approval has been supplied by Codex. The
[operator plan](WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md) remains inactive.
