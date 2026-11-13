# P1 ISR/stop race: fail-closed containment

2026-11-13. **P1: PARTIALLY_MITIGATED_FAIL_CLOSED. Physical quiescence: OPEN.**
The patch prevents a second first-party capture owner from being published after
any transfer attempt ends. It does not prevent vendor DMA re-arm after stop,
clear pending interrupts, prove the first capture starts clean, or authorize use
on hardware. [R0](R0_BASELINE_AND_CONTRACT.md) fixes the original evidence/contract.

## Alternatives examined against the actual ISR

| Approach | Evidence needed / finding | Decision |
|---|---|---|
| Mask stop, disable/reset, acknowledge the channel, then restart | Requires authoritative reset/completion semantics, channel-local drain/ack ordering, no surviving in-flight completion and a way to prevent vendor re-arm during teardown. Existing headers provide no stop-and-drain contract. Distinct reset/clear operations do not establish their interaction. Masking stop alone leaves an old IRQ deliverable immediately on restore or against the next run. | Rejected as unproved; no guessed register/API calls or extended mask. |
| Application generation/late-callback filter | Vendor RX callback re-arms before application dispatch; callback has no transfer generation token. Reset ring indices can make an old completion look current. Dropping an application callback cannot stop the preceding re-arm. | Insufficient for either quiescence or safe restart. |
| Permanent first-party lifecycle quarantine | Requires no new hardware semantics. Never publish another owner once a transfer has been attempted and detached, regardless of stop API status. Keep the static DMA buffer alive. | Implemented; software containment only. |

The frozen ELF's DMA branch increments its completion count and dispatches RX
without a queue-empty guard, then clears completion after RX returns. RX advances
its audio ring, re-arms the driver, and only then delivers the application event
when its unread threshold is met. The non-DMA/polled branch has different checks;
its queue guard cannot be assumed to protect the DMA branch. The new static tests
check the actual pinned DMA order independently of the fake. No proprietary
instructions or source are reproduced here.

## Production change and ownership argument

[bh_pdm_port.cc](../../../firmware/himax_arc/birdhouse/bh_pdm_port.cc) retains the
existing three machine-word states, now meaning unused / active-or-starting /
permanently quarantined. Stop saves IRQ state, nulls the Capture pointer, latches
quarantine, restores the exact prior state, and calls the existing vendor stop.
Only detachment and the state store were added to that existing brief exclusion;
there is no vendor call or PCM copy inside the stop critical section. No register
access or new channel/DMA API was introduced. Other channels and interrupt masks
are not explicitly changed by this patch; the existing global save/restore pair
is retained only for the short ownership publication/detachment boundary.

Stop still returns the vendor API's success/failure as 0/-2. `faulted()` remains
true even on success. A retry can attempt cleanup but never changes quarantine.
There is no production transition back to unused. A null argument or callback
registration failure occurs before a transfer attempt and remains retryable.
Partial-start failure performs the existing cleanup and permanently quarantines,
even when cleanup reports success. It never publishes the failed Capture.

Startup masking is preserved: the vendor enables DMA before publishing the queue
count. Owner publication happens only after successful high-level start, before
restoring interrupts. This avoids that initialization race; it does **not** prove
progress (P3) or reject a completion left by an earlier vendor client. Clean boot
and initial peripheral state remain physical/vendor prerequisites. The traced
normal start helpers have bounded software setup; elapsed time and bus stalls
are not bounded by these host tests.

The single-core main loop cannot run inside an in-progress ISR. After detachment
under IRQ exclusion, later callbacks read null and return before ring access or
Capture dereference. The caller may Finish/destroy Capture; the vendor's DMA
buffer itself stays static. Re-arm can continue into that static buffer and the
vendor may still overflow/recover/print or block in P4. This is why containment
is not a claim of a stopped or generally safe peripheral.

[Runtime](../../../firmware/himax_arc/birdhouse/bh_runtime.cc) and
[console](../../../firmware/himax_arc/birdhouse/bh_console.cc) accept only count 1,
reject further captures after quarantine, and discard pending work on a latched
fault. Existing resource guards then also refuse vendor sampling/camera starts
and synthetic/model self-tests. This intentionally conservative behavior does
not cover independent vendor I2C clients or every other SDK entry point. The
console help/API comments reflect the changed contract. Existing clean first-run
inference remains a host diagnostic; CLEAN is not continuity proof.

## Model, adversaries and regression boundary

[fake_aud_lib](../../../firmware/himax_arc/tests/fake_aud_lib.cc) now models DMA
armed state, a pending completion, IRQ exclusion, re-arm before application
callback, and acknowledgment after return. A completion can execute even while
DMA was stopped; it can re-arm again. Reset clearing pending is a selectable
hypothesis, not a discovered fact. Completion injection is exercised before,
at three stages during, and after stop, with both reset hypotheses and both
caller IRQ states. The 32 stop scenarios also inject post-reset completions.
Eight failure/IRQ combinations cover partial start and stop success/failure.
A raw stop/start witness credits one old block to a new ring with **zero newly
acquired PCM**, directly challenging the old index-reset safety comment.

The fake's queue-publication sentinel catches removing startup masking. An
independent application probe observes DMA already re-armed and completion still
pending during callback. Suppressed application callbacks model starvation, not
masked hardware IRQs; explicit pending/IRQ APIs test masking. Legacy direct
callback injection remains clearly labeled and is not the source of ISR evidence.
The model omits DMA buses, cache, electrical timing, nested interrupt priorities,
real queue implementation and FIFO recovery; it cannot close P2 or P4.

[test_pdm_lifecycle.cc](../../../firmware/himax_arc/tests/test_pdm_lifecycle.cc)
passes 969 assertions in each native variant. It checks frozen stats/PCM, no ring
reads while detached, destroyed-owner lifetime, exact opaque IRQ-state restore,
startup publication, quarantine after successful retries and independence of
fake-driver reset from adapter state. Test-only reset emulates a fresh process;
it is compiled only with `BIRDHOUSE_HOST_BUILD` and is excluded from ARC objects.
It is not a procedure for restarting/resetting hardware.

Seven compiled mutants must fail assertions: reopening after stop, bypassing the
start guard, missing detach, removed startup mask, enabling an already-masked
caller, premature modeled acknowledgment, and delayed modeled re-arm. Four
additional static evidence mutations must be rejected. All were rejected. The
old multi-run/stop-retry expectations were replaced by explicit quarantine
checks. Forty independent native process fixtures retain numerical/content
coverage; they are no longer described as a same-device restart soak.

See the [matrix](OFFLINE_TEST_AND_BUILD_MATRIX.md) for native/sanitizer/build
results and limitations. No test changes the unknown hardware contract into an
assumption of safe reset. No experimental register patch was attempted or needs
rollback. A production-capable repeated-capture fix remains vendor-dependent.
