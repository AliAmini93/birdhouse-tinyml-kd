# Windows 10 first-write and recovery protocol: review draft

2026-11-13. **PLAN ONLY. Current entry decision: NO-GO. No step below is authorized
for execution by this audit.** The owner must review a concrete future operation
and explicitly authorize it after the applicable gates are closed or residual risks
are explicitly accepted. No hardware action occurred while preparing this plan.

Scope: Grove Vision AI V1, HX6537-A plus BL702 installed TinyUF2 2d5b48b (Aug 23
2022). Hardware is on the owner's different Windows 10 machine. No Linux device
access is part of this plan. BL702 update, I2C repair, vendor utilities, firmware
generators and driver/service changes are excluded from this first-write operation.

## A. Decision record before scheduling any experiment

The future record must contain the operator/reviewer, date, exact image SHA-256,
expected UF2 bytes/blocks/address interval, installed bridge version, chosen copy
method, expected mode transitions, maximum reviewed completion time, private
evidence location, preservation decision, recovery route and stop rules. Keep
host/device identifiers private. No guessed drive letter or COM port is acceptable.

1. Review [gates G0–G7](RECOVERY_AND_ROLLBACK_GATES.md). The present audit cannot
   certify both-loader recovery or the installed updater. Record those unresolved
   risks explicitly; do not silently mark the checklist passed.
2. Decide what must survive: installed BL702, Himax app, model slots, configuration
   and calibration. If preservation is required and a qualified backup is absent,
   **do not write**. If loss is acceptable, record acceptance that factory fallback
   may not reproduce installed state and that recovery itself can fail.
3. First write, if ever separately approved, should be one exact factory image to
   rehearse the official route. It is a destructive experiment, not a harmless
   transport test. Successful factory writing would support only that tested case;
   it would not prove recovery with both loaders erased or interrupted power.
4. Candidate transfer is a later separate decision after factory results, recovery
   review and PDM P1/P4 disposition. Do not chain factory and candidate copies in
   one unattended workflow. Do not switch to BL702 v2.0.1 as an automatic remedy.

## B. Host-only image preflight

Prepare files on the Windows host's ordinary local storage, not on the board,
before any device-related action. Confirm full names/extensions and avoid cloud
placeholders, shortcuts or a similarly named older candidate.

| Approved-image choice | Bytes | Required SHA-256 |
|---|---:|---|
| First factory rehearsal: grove_ai_v02-00.uf2 | 1,541,632 | 8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c |
| Later Birdhouse candidate, only under a new approval | 1,256,448 | 009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae |

For an ordinary local source file only, PowerShell's host-side check can be:

    Get-FileHash -Algorithm SHA256 -LiteralPath '<local source UF2>'
    (Get-Item -LiteralPath '<local source UF2>').Length

The placeholder must resolve to the source on ordinary host storage. This report
does not supply a write command or executable deployment script. Hash before the
session and again immediately before the separately approved transfer. Any mismatch
is a stop; never regenerate or reconvert files during the session. Factory fallback
must already be locally available and hashed even when considering a later candidate.

## C. Power, host and client preflight

The future operator must document the exact arrangement and its stability:

- Reliable host power (AC/charged battery or an appropriately supported power
  arrangement), board's documented supply, sound USB data cable and secure direct
  connection. No loose connectors, hub power uncertainty, simultaneous unreviewed
  external supplies or hot wiring. Do not change the arrangement during a transfer.
- A planned uninterrupted window with no host sleep, shutdown, restart or cable
  movement. Any needed power/OS policy changes require their own future review;
  this draft does not request or perform driver, service or power-setting changes.
- Close applications that could use CDC, WebUSB/WebSerial, Edge Impulse, Arduino,
  camera or I2C. Do not open a serial terminal merely to identify the board;
  opening/baud/DTR/RTS may alter its state. Avoid concurrent automatic copy/retry
  tools or multiple Explorer copy operations. Do not disable security software as
  an improvised remedy.
- Confirm which physical board and volume the owner intends, with identifiers
  kept private. The execution agent must not enumerate local devices. The owner
  on Windows controls any later approved physical/mode steps.

## D. Read phase, retained as a separate qualification level

On the same Windows host, build, cable, port and power arrangement intended for a
future write, review the existing owner evidence: 10 minutes visually stable
GROVEAI, readable INFO_UF2 and zero matching System warning/error events in a
targeted 30-minute query. Record exactly which evidence is owner-reported and the
query's actual filters/time coverage if later available. Do not infer unlogged
transactions were successful, or that every reset would appear under that query.

If a fresh read phase is separately authorized later, require correct installed
identity, no observed reconnects, timeouts or I/O errors and readable INFO_UF2 over
at least the reviewed 10-minute window. Stop on any uncertainty or failure.
Do not create, delete or rename even a test file on GROVEAI; file names do not
guarantee harmless updater behavior. Do not run CHKDSK, format, repair the FAT,
copy erase_model, or test with a partial UF2.

**Passing D qualifies limited reading only.** Required write evidence must cover
WRITE10/error propagation, buffering/erase/programming and durable completion on
the installed bridge. A later successful one-image rehearsal with post-boot checks
adds empirical evidence; it cannot be obtained without accepting the first-write
risk. There is no non-destructive shortcut from reading to full write qualification.

## E. Single approved transfer: future operator sequence

This section remains unavailable until the future decision record explicitly
opens it. The following sequence is for human review, not an instruction to act now.

1. Reconfirm the authorized image and source SHA/size, power, client isolation,
   operator presence, reviewed deadlines and factory fallback. Preserve prior
   private evidence; do not clear Windows logs. If completion timing and response
   to a stall are not agreed, do not start.
2. If mode entry is required, separately authorize the V1 BOOT double-click and
   confirm GROVEAI and INFO_UF2. Do not substitute BOOT-held reconnect: the official
   BL702 programming workflow uses that different entry for ROM ISP. No RESET,
   replug or cable movement is implied by the audit or by a mode name.
3. Use the one reviewed ordinary Windows file-copy method to put the complete
   approved UF2 in the volume root, once. Keep the operator watching throughout.
   No vendor converter/uploader, shell auto-retry, parallel copies, drive format,
   arbitrary block writes or attempt to preserve loaders by editing UF2 blocks.
4. Observe copy progress, actual elapsed time, messages, drive/mode transition
   and board indications. The official wiki describes fast work-LED activity
   while burning and disappearance of the drive afterwards. These are useful
   expected signs, not proof of content integrity. Never disconnect just because
   Explorer reaches 100%, or assume a copy failure happened before any erasure.
5. Treat successful host copy, expected drive disappearance and successful Himax
   boot as separate observations. Windows may buffer writes; even an explicit
   [host flush](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
   would not prove this bridge verified Himax flash. Do not add privileged volume
   flushing or eject/reset experiments. Preserve power until the reviewed
   completion/settling condition is met. No fixed safe delay is established for
   the installed build; arbitrary extra waiting cannot prove completion either.
6. No automatic second transfer follows. Record the outcome for review. If the
   board remains in UF2 or the completion window expires, follow F, not a retry.

## F. Failure handling by stage

| Observed stage / symptom | Immediate handling for the future reviewed session | Prohibited automatic response |
|---|---|---|
| Before copy: hash mismatch, identity doubt, unstable reading, power/client problem | Do not begin transfer; preserve host-only evidence and revise the plan. | Reconvert, pick another similarly named file, change firmware/driver. |
| During copy: failure dialog, unexpected disappearance, timeout/reset/reconnect | Stop initiating new actions; do not retry or deliberately interrupt power. Preserve timing/message evidence privately. Owner retains emergency control. | Looping copies, cancel/replug/reset/erase as a routine remedy. |
| After host success: expected disappearance but no confirmed boot | Classify state as unknown/possibly partial. Maintain the reviewed power arrangement and request a new state-specific review. | Treating bridge CDC enumeration as proof Himax booted; blindly opening serial. |
| Drive stays present, or an ERROR.TXT-like status appears | Under separately approved reading only, preserve status text privately and sanitize it. Unknown status semantics on installed build. | Delete the error file, format, force completion, copy again. |
| UF2 cannot be re-entered under an already approved procedure | Stop and assess which chip/path failed. | Escalate to BLDevCube, BOOT-held ROM entry, Chip Erase or I2C sketch. |
| Candidate boots but numeric/capture/IRQ/memory check fails | Stop application qualification and do not queue another capture. Review fallback as its own write. | Repeated captures or restart loops to make the failure disappear. |
| Power interrupted or board overheats/electrical hazard appears | Human follows a pre-agreed physical safety response. Treat firmware state as unknown; no software recovery follows automatically. | Repeated cycling or testing a recovery theory on the only board. |

A write cannot be made safe by promising a clean abort: after the first accepted
payload, flash may already be changed. A stalled host UI does not reveal whether
the target is still erasing/programming. No universal safe power-removal time is
known. The future reviewer must explicitly bound handling of this uncertainty.

## G. Post-copy verification and return-to-UF2 semantics

1. Check expected boot/mode indications without assuming USB personality identifies
   the Himax app. INFO_UF2 identifies BL702, not the newly written Himax image.
   GROVEAI is a virtual update interface, so reading back a filename or hashing a
   displayed copied file is not established as physical flash verification.
2. If an independently qualified readback route later exists, compare all intended
   physical bytes and affected sector boundaries, including loader and upper config
   preservation requirements. Otherwise record that whole-flash verification is
   unavailable. Functional boot is narrower evidence and must be labeled as such.
3. Returning to UF2 is a new mode-entry operation using the documented V1 BOOT
   double-click under its own approved sequence. Drive disappearance does not
   certify return availability; the installed behavior with both Himax loaders
   damaged remains unknown. Do not assume RESET or power cycling repairs a partial
   image. BOOT-held attach is BL702 ROM programming entry, not a factory rollback.
4. For a later factory fallback: reconfirm stable approved transport, accepted
   installed-state loss, exact factory hash/size and an explicit new write scope.
   Copy factory once by the reviewed method. Do not insert WEI erase as a default
   pre-step; it writes config, has an audited bounds defect and is not independent
   recovery. If factory fails, stop; do not cascade to BL702 update.

## H. Post-boot safety and application qualification

Future factory rehearsal: establish the expected factory behavior using separately
reviewed observation/query methods and firmware identity evidence. A revived bridge
alone is insufficient. Document what was and was not verified before considering
a candidate write.

Future Birdhouse candidate, only after P1/P4 review and separately authorized CDC/
capture access: use [expected device values](../birdhouse_v1_codex_predeployment_20261111/results/validated/expected_device_values.json)
and the pinned build/model identifiers. Establish a console-open/mode-control
contract before opening a port. Do not send Birdhouse commands to an unidentified
installed app. Then stage:

1. INFO/build/model/preprocess identity and memory/arena diagnostics.
2. Graded model self-test, with actual numerical acceptance thresholds reviewed;
   CLOSE is diagnostic, not automatic acceptance. Stop at an unexpected result.
3. Synthetic pipeline cases before microphone input; verify decision gating.
4. One capture only, measured against an external time reference and measured DMA
   progress. API-start success alone is insufficient. CLOCK/SUSPECT requires
   decision=NONE and investigation. Preserve any audio privately; do not publish it.
5. Check stack watermark, arena use, timing, single-stop completion and late
   callbacks/re-arm state by a previously reviewed method. No automatic retry,
   restart or soak. Host fake-callback tests cannot establish peripheral quiescence.

P1 permits stop/IRQ interleaving and old completion/re-arm uncertainty. P4 permits
unbounded boot or ISR initialization polling; an eight-second main-loop deadline
cannot rescue a blocked boot/ISR. Loss of console must therefore have a recovery
plan independent of the app. Post-boot tests cannot replace the pre-write recovery
gate, and this draft authorizes none of those tests.
