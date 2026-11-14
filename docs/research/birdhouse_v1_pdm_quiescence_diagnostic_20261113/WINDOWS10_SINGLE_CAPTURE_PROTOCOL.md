# Windows 10 one-capture diagnostic experiment — inactive review protocol

2026-11-13. **INACTIVE: no validated diagnostic UF2 exists.** No action below was
executed or authorized by this offline mission. This protocol requires later
owner approval of an exact new candidate and a separate safe console contract.
It does not approve a flash, mode entry, console open, reset or recovery now.

## Entry gates

1. A future diagnostic UF2 must pass unchanged sandbox packaging, deterministic
   generation, ELF/SBS/model identity, pinned-factory layout comparison and two
   independent UF2 validations. Record its full SHA-256, bytes, blocks and source
   inventory. None of those UF2 identity fields is currently available.
2. Move that future file only to an ordinary internal Windows folder or trusted
   non-board storage. Check full SHA-256 with `Get-FileHash -Algorithm SHA256`
   and byte length with `(Get-Item -LiteralPath '<ordinary source file>').Length`.
   The target must not be GROVEAI. No binary goes to public GitHub/cloud.
3. A later written authorization must separately name the exact digest and
   reviewed one-time manual Windows write procedure. The earlier first-flash
   recovery/preservation risks remain open: sole-board loss and settings/
   calibration loss are possible; factory fallback is another risky full write.
4. Before *opening* a console, establish the actual BL702/Windows port-open,
   DTR/RTS/baud and mode-control contract. This mission has not established it.
   No guessed COM port, driver change, auto-open terminal or background client.
5. Confirm Grove Vision AI V1/HX6537-A, the approved exact file and known installed
   bridge identity; record actual board/port privately. Stable power/cable/host
   arrangement and sole-client access must be reviewed. No updater, camera,
   sampling client, repeated command macro, auto-reconnect or auto-retry.
6. Agree a **30-second observation-only window** from the one run command. This
   is an experimental evidence deadline, never a safe reset/replug/power-removal
   deadline. P4 may hang; loss of response means stop issuing actions and seek a
   new state-specific human decision. No automatic recovery follows.

## Minimal future experiment, after every gate and explicit owner scope

The future owner-approved console sequence is text only:

1. `AT+BIRDINFO?` once: verify expected model/configuration and candidate identity
   evidence. The generic version string alone is insufficient to identify bytes.
2. `AT+BIRDDMA=1` once: require `arm_rc=0 capture_queued=0`. This command does not
   start DMA. Optionally query `AT+BIRDDMA?` before capture to confirm ARMED and
   NOT_FINISHED; it reads stored metadata only.
3. `AT+BIRDRUN=1` **once**: require queued=1/rc=0. Record external host time. Send
   no further commands during capture/Stop/observation; do not poll the console.
   Existing runtime Stop happens automatically after the one capture. Do not
   add a manual stop or a second run to improve the result.
4. If the normal RESULT arrives within the observation window, record its capture
   samples, callbacks/blocks, errors, quality and available timing. Confirm real
   progress (not just API success). Then issue `AT+BIRDDMA?` once. It prints the
   frozen before/after/timed records, not a fresh hardware read. Use `AT+BIRDLAST?`
   only if the stored result must be printed again under the agreed read scope.
5. End the experiment. No second capture, stop retry, reboot, reset/replug or
   fallback write. P1 quarantine remains active regardless of the result.
   Keep any console evidence private and sanitize it before publication; no
   microphone audio/PCM dump is needed or authorized by this protocol.

Nominal configuration is 16 kHz stereo DMA, 1,024 frames/64 ms per block, delivered
in two-block callbacks, with 80,000 retained mono samples. These are configured
expectations, not already measured microphone/rate qualification. The 512 ms
post-stop window covers eight nominal block periods. Actual capture progress
and window timing must be observed, not presumed.

## Acceptance table — evidence for this one instrumented execution

| Result | Measurable condition | Meaning |
|---|---|---|
| FAIL: busy after return | Any valid phase-1/2 busy=1 | Not idle at that read; does not identify which transaction |
| FAIL: pending DMA request | Any valid phase-1/2 irq=1 | DMA request remains or appeared after return; CPU latch and event identity remain unknown |
| FAIL: re-arm attempt | post_enable=1 | Audited enable path attempted channel-4 enable after the post-return marker; not automatic proof of completed writes |
| FAIL: late callback | Any timed row late count differs from phase-1 count | Application callback occurred after the first post-return sample; owner detachment must still hold |
| FAIL: buffer change | Any timed changed_words>0 | A word differed from its previous uncached read; requires attribution review, not assumed DMA causality |
| FAIL: new completion status | Completion history changes 0 to 1 after phase 1 | Completion became visible after the initial post-return read |
| INCONCLUSIVE | No result/records, Stop rc!=0 without a positive failure witness, error status, incomplete window, invalid fields, clock_bad=1, budget=1, or excessive gap | No usable negative result; do not retry |
| PASS_SAMPLED_ONLY | All conditions below pass, without any positive failure witness | No specified activity detected in this covered interval; **not full quiescence** |

For PASS_SAMPLED_ONLY, require real capture progress, finished=1, window=1,
clock_bad=0, budget=0, stop_rc=0, 34 rows (phase 0, phase 1, 32 phase-2 samples),
valid=15 on post-stop rows, final elapsed>=512000 us and max gap<=32000 us.
Require no post busy/error/IRQ, changed words, late-count increase or post-enable
latch. A sticky completion=1 throughout is historical, not itself a failure.
If an independent timing observation contradicts the configured window, classify
INCONCLUSIVE even if the firmware label says PASS. Positive failures take
precedence over incomplete timing or missing other fields.

`during_enable=1` means an enable attempt occurred during the vendor call **or
the return-to-marker gap**. It cannot locate the attempt exactly before/after
return, even if later samples are quiet. Treat the stop-interleaving explanation
as INCONCLUSIVE and preserve that witness. No IRQ masking is added to force an
interleaving or manufacture a pending event in this one-capture protocol.

## What this experiment cannot establish

The output intentionally states enabled state, CPU pending latch, bus drain,
same-value writes and full quiescence are UNOBSERVABLE. If pending was never
observed before Stop, survival of an already pending request was not exercised.
Even pending=1 before and after cannot identify whether it is the same event or
a new one. A negative buffer comparison misses equal-value, reverted and
inter-scan writes. Reads are sequential; a callback or DMA transition can occur
between them. Wrapper evidence covers audited PDM calls, not every possible
writer of an AUX register. Existing vendor error paths may still print or block.

One successful physical capture does **not** establish race-free DMA shutdown
under all interrupt interleavings, authorize repeated captures, close P1/P4 or
qualify recovery. Further closure needs an authoritative channel-local
stop/drain/ack contract and separately designed qualification; it cannot be
obtained by silently expanding this one-attempt experiment.

See [design/evidence](OBSERVABILITY_AND_DESIGN.md),
[offline results](OFFLINE_VALIDATION.md) and [decision](FINAL_DECISION.md).
