# Windows 10 single-flash operator plan — TEXT ONLY, INACTIVE

2026-11-13. **BLOCKED: no new packaged P1 UF2 exists. No board operation is approved.**
The resumed focused tests, fresh clean ARC build and ELF audits passed. The
unchanged packaging sandbox could not create its required namespace; no image
or UF2 was produced. The owner confirmed Windows-only board attachment and
authorized only the existing passive Linux mount guard, which was preserved.
This is a finite future human procedure for review. The current session will not
operate Windows, contact the board, enter a mode, open a console or transfer a
file to a device. See [artifact status](FIRMWARE_UF2_VALIDATION.md) and the
[unsigned decision record](OWNER_RISK_ACCEPTANCE_RECORD.md).

## Choice of first experiment, after an artifact actually passes

| Choice | Full writes proposed | Benefit | Cost / uncertainty |
|---|---:|---|---|
| Direct new P1-mitigated Birdhouse | One | Reaches the owner's experiment with one exposure to the unqualified updater; avoids an additional full loader/metadata write | First writing outcome and Birdhouse boot behavior are encountered together; P1/P4 can prevent useful diagnostics |
| Factory rehearsal, then a separately approved Birdhouse write | Two, only if the first is reviewed and the second later approved | Successful factory programming and verified factory boot would add evidence for that exact host/transport/image case and a known application baseline | Factory rehearsal is itself potentially destructive, includes loaders and adds a full write; success proves neither damaged-loader recovery nor later Birdhouse boot |

For the owner's selected Path B objective, the conditional recommendation is
**one direct Birdhouse write** after a new artifact passes and exact-digest loss
acceptance is signed. The reason is to avoid a second full write solely for a
rehearsal that cannot close the installed-updater/recovery gaps. No failure
probability is invented and no claim of overall physical safety follows. The
earlier audit preferred factory rehearsal under its earlier decision basis;
this recommendation explicitly reflects the new one-experiment objective.
Current proposed writes for execution: **zero**, because the artifact is absent.

## Host-only preparation — before any new board contact

1. Obtain the eventual review-only UF2 and manifest directly from the ignored
   Ubuntu output using a trusted host-to-host transfer or trusted ordinary storage.
   Destination must be a normal Windows internal folder or trusted non-board
   storage, explicitly **not GROVEAI**. Do not upload firmware/vendor binaries to
   public GitHub, a cloud drive or a sharing service. Do not choose the old
   `009799e1...21600ae` UF2 or the incremental P1 ELF.
2. On Windows, show full extensions and verify the ordinary local file using
   these **read-only host-file commands**. Replace the placeholder only after a
   new manifest supplies the exact filename. Neither command targets a board:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath '<ordinary internal folder>\<exact new candidate filename>.uf2'
   (Get-Item -LiteralPath '<ordinary internal folder>\<exact new candidate filename>.uf2').Length
   ```

3. Compare the complete 64-digit digest and exact byte length with the eventual
   validated Ubuntu manifest, twice: after pre-copy and immediately before the
   separately approved transfer. A filename, shortened hash, shortcut or cloud
   placeholder is insufficient. Any mismatch means stop before board contact.
4. Keep the already verified official factory fallback on ordinary local storage:
   `grove_ai_v02-00.uf2`, 1,541,632 bytes, SHA-256
   `8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c`.
   Verify it there with the same host-file commands. Its presence authorizes no
   fallback write. It is not a backup of the installed firmware/state.

## Human preconditions and separate authorization gate

- Product must be the owner's **Grove Vision AI V1**, HX6537-A with BL702 bridge,
  not another Grove product or V2. The expected package family is `0xef32c892`.
  Installed bridge identity is owner-reported TinyUF2 `2d5b48b`, August 2022
  (the prior audit records August 23). No bridge upgrade is included.
- Record the physical board, actual target volume and any necessary mode-entry
  procedure privately in the future decision. No drive letter or COM number is
  supplied or guessed here. Volume label alone cannot establish board identity.
  A required mode entry needs its own explicit human authorization and reviewed
  steps; this kit does not perform or grant one.
- Review the intended Windows 10 host, secure data cable, documented board power
  arrangement and uninterrupted observation window. Resolve sleep/restart,
  power/cable instability or competing access before approving a write. This
  session changes no power policy, driver, service or installation.
- No simultaneous serial terminal, WebSerial/WebUSB client, Arduino/Edge Impulse
  client, camera/I2C client, driver updater, automatic copier or second transfer.
  Opening a console may change DTR/RTS/mode and is not a harmless identity query.
- Existing ten-minute GROVEAI read stability is owner-reported evidence of
  reading only. WRITE10, erase/program completion and durable verification on
  installed `2d5b48b` remain unqualified. G1/G2/G3/G4 and P4 remain OPEN.
- Before beginning, the owner must fill the record with the **new full SHA-256,
  size, filename, source, chosen one-write operation, actual target identity,
  power arrangement, observation interval, stop handling and explicit potential
  permanent-loss acceptance**. No approval field is pre-checked. Path B alone
  does not approve a not-yet-built digest. If these are incomplete, do not start.

## Exactly one future human Explorer transfer, only after that gate opens

1. Recheck the signed record and ordinary source file's full SHA-256/size. Confirm
   the agreed environment and that the intended update volume is already
   available under a separately authorized mode-entry procedure. If any identity
   or preparation is uncertain, stop before copying.
2. In Windows Explorer, select the single approved complete UF2 from the ordinary
   source folder. Perform **one manual Copy and one Paste into the verified
   target volume root**. Remain present and observe it. No script, uploader,
   edited/partial UF2, test file, multi-file batch or automatic retry is included.
3. Record copy start, elapsed observations, progress/messages and mode/board
   indications privately. A successful Explorer transfer, a disappearing update
   volume and a booting Himax application are three different observations.
   Reaching 100% or seeing CDC alone proves neither durable programming nor
   application identity. Re-reading a displayed copied file is not qualified
   physical flash readback.
4. Apply the pre-agreed finite **observation interval**, without treating its end
   as a safe power-removal/reset deadline. No universal safe timeout is known.
   If outcome remains unclear, classify it UNKNOWN and stop initiating actions.
   A stalled UI gives no evidence that erase/programming has stopped. Retain the
   agreed arrangement pending a human state-specific decision; human emergency
   physical safety control always remains with the owner.
5. End the write experiment after recording its result. No second copy, fallback,
   reset, replug or console session follows automatically, including after
   apparent success. Whole-flash readback is unqualified; even functional boot
   would provide narrower evidence than full byte verification.

## Stop and fallback decision tree

| Observation | Human disposition; no automatic next write |
|---|---|
| Source digest/size mismatch, wrong product/volume, unstable environment | Do not start. Reconcile ordinary host files and plan first. |
| Copy error, hang, unexpected disappearance or reconnect | Stop new actions; retain private timing/error evidence. Do not retry, cancel/reset/replug as a routine remedy or assume no erase occurred. |
| Host transfer appears successful but no verified application boot | State UNKNOWN, possibly partial. Review before any further contact; bridge enumeration is insufficient. |
| Drive stays present or status/error text appears | No new transfer. Reading status requires separately approved read-only scope; preserve privately. No delete/format/CHKDSK/repair. |
| App boots but identity/numerics/progress fail | Stop qualification. No repeat capture, restart loop or immediate factory copy. |
| Owner later considers factory fallback | New decision for another risky full write: same unqualified updater, exact official digest/size above, uncertain installed-state loss and recovery limits. Only a separately reviewed and approved single transfer may follow. |
| Factory write fails, loaders may be damaged, or UF2 mode is unavailable | Stop. Recovery is unproven. BL702 upgrade, WEI erase, erase_model, BLDevCube and ROM-I2C remain outside this first-flash plan. No cascade. |

Unchanged loader bytes in a package do not prove physical erase/write skipping.
Factory rollback can fail and does not guarantee restoration of settings,
calibration, model slots or the original installed app. No independent qualified
full backup/recovery route has been established.

## Initial post-boot observations and application probes

Passive indications already included in the approved observation plan may be
recorded, but must not be relabeled verified image identity. A new serial-open,
DTR/RTS/baud/mode-control contract has **not** been verified for this kit. Therefore
no AT+ command sequence is enabled or executable from this report.

Only if that contract is later evidenced and the owner separately authorizes the
exact console operation may a future reviewed plan check build/model/preprocess
identity, graded model self-test and synthetic cases. Stop at an unexpected result.
Real microphone access would require its own authorization for **exactly ONE
attempt**, with progress/timing observation and no auto-restart/repeated sampling.
P1 quarantines first-party use after stop/partial start; it does not prove DMA
quiescence or a clean initial peripheral. P4 may hang at boot or in the ISR before
the main-loop deadline or console can help. ARC MLI numerics, real microphone,
timing, cache/continuity and actual stack use remain physically unvalidated.
