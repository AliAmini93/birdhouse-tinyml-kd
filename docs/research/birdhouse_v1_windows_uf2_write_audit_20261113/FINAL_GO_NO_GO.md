# Final GO / NO-GO: Windows UF2 first write

2026-11-13. **NO-GO for factory or Birdhouse writes, physical recovery, active
diagnostics and BL702 update. GO: completed interactive offline research only.**
This mission ends without a physical experiment. The owner may continue to steer
the interactive session; no background/headless job or hardware workflow was started.

## What the evidence now supports

The owner's Windows 10 observation is useful: GROVEAI was visually stable for
10 minutes, INFO_UF2 was readable, and a targeted System query reported zero matching
disk/USB warnings/errors in the preceding 30 minutes. It establishes limited,
owner-reported reading evidence for installed build 2d5b48b, not reliable writing.
It does not establish a different root cause for the historical Ubuntu reset loop.

The exact factory and Birdhouse packages were independently parsed as data. Both
include the first and second Himax flash loaders. The candidate requests 628,224
payload bytes versus factory's 770,816, leaving a 142,592-byte logical factory tail
uncovered. The physical fate of that tail/configuration is unknown. The exact
candidate's stored ELF sections and compiled model were independently rechecked;
no firmware, model, architecture or configuration was changed.

The decisive unresolved questions are:

1. **Installed updater unknown.** No exact source/binary for 2d5b48b was obtained.
   Family/address enforcement, translation, buffering, erase, USB ACK timing,
   target completion, error propagation and readback verification remain unproved.
   The newer official v2.0.1 binary and current generic TinyUF2 code cannot stand
   in for it. SFUD strings do not certify direct access to Himax flash.
2. **No independent full-image Himax recovery.** Official factory UF2 uses the
   same MSC route. Neither recovery with both Himax loaders damaged nor an
   independent full-image transport has been qualified. Official I2C erase writes
   only boot config, still requires UF2, and has a newly identified last-page
   source-array overread/remainder defect. BL702 ROM repair repairs another chip.
3. **No qualified backup or installed-state rollback.** A generic official Bouffalo
   flash-read feature exists, but the reviewed documentation does not establish a
   truly non-destructive complete backup for this Grove board. Factory is not a
   backup; exact installed BL702 rollback is unavailable. Owner acceptance of
   losing installed state has not been given by authorizing this offline audit.
4. **PDM P1 and P4 remain open.** P1 concerns stop/IRQ/re-arm and pending completion
   across runs; host callback tests do not execute vendor peripheral behavior.
   P4 is unbounded ready polling on boot or ISR recovery; the main-loop deadline
   cannot recover that path. Console-based recovery cannot be assumed available.
5. **Writing itself is unqualified.** Read success does not exercise WRITE10,
   long erases/programming or durable completion. A first factory rehearsal would
   itself be a consequential write, with no atomicity or power-loss guarantee.

## Decisions by proposed action

| Action | Decision | Reason |
|---|---|---|
| This sanitized offline research/commit | GO, completed | File-only evidence and plan; no physical operation. |
| Treat existing Windows observations as write qualification | NO-GO | Read evidence has narrower scope. |
| First factory rehearsal | NO-GO | Preservation, installed write behavior, recovery and reviewed experiment gates open. |
| Birdhouse candidate deployment or capture | NO-GO | Same write/recovery gaps plus P1/P4 and physical qualification. |
| BL702 v2.0.1 update | NO-GO / explicitly unauthorized | Changes another chip, lacks exact rollback, not a diagnostic shortcut. |
| WEI erase or erase_model test | NO-GO | Consequential writes; neither is a harmless transport test or independent full recovery. |
| Repeated full firmware flashes or architecture changes | NO-GO in this mission | Trade-offs recorded; implementation untouched. |

## Required next evidence, without an experiment here

Seek exact installed BL702 source or a legally shareable matching binary with a
reliable build map; establish target-flash routing and erase/completion/verification
semantics; obtain a board-specific full-image recovery/readback contract independent
of a healthy app, including both-loader loss; settle preservation or explicit loss
acceptance; and resolve P1/P4 with authoritative hardware/driver semantics and a
reviewed qualification plan. A later owner may explicitly choose a risk-accepted
experiment, but this audit provides neither permission nor a finding of safety.

The [Windows protocol](WINDOWS10_FIRST_WRITE_DRAFT.md) is ready for future review,
not execution. No dummy file, partial UF2, read-only mount, device query, flash
utility help command, driver change, reset or replug was used to shortcut the gates.

## Deliverables and verification boundary

- [Evidence matrix and source provenance](EVIDENCE_MATRIX.md).
- [UF2 mechanism, exact image contents and conditional sector effects](UF2_WRITE_MECHANISM_AUDIT.md).
- [Windows 10 first-write/recovery draft](WINDOWS10_FIRST_WRITE_DRAFT.md).
- [Recovery, rollback, backup gates and architecture trade-offs](RECOVERY_AND_ROLLBACK_GATES.md).
- [Machine-readable results](RESULTS_SUMMARY.json).

Verification covers file identities, all 5,540 UF2 blocks, ELF/SBS reconstruction,
loader comparison, tail/padding/sector arithmetic, WEI loop bounds, report links,
privacy, JSON consistency and change scope. Prior hardware observations and PDM
binary analysis were critically reviewed but not physically reproduced. No vendor
generator, firmware, recovery utility or sketch was executed; no code tests were
needed or rerun for this reports-only change.

Only these six sanitized text reports are eligible for the commit. Commit SHA,
actual push result, remote-head comparison and final worktree status are reported
at delivery after Git operations; this report does not predict their success or
embed a self-referential commit hash. A blocked push must be reported unsynced,
without escalation, branch switching, force push or merge into main.
