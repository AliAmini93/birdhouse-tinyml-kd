# PDM shutdown observability and diagnostic design

2026-11-13. **P1 remains OPEN.** This mission implements a bounded, opt-in
observation, not a synchronized stop repair. No hardware operation occurred.
The six earlier uncommitted reports and index/worktree patches were saved before
source edits in ignored storage; their working bytes remain unchanged.

## Evidence boundary

SDK: `9dc2370d4dc269dc4bcafcf0354b8f745d08801f`, clean. Baseline P1 source:
`3d0fb3fd4c1889d79462bbc404aee722c1811894`. Private static inspection used the
previous fresh ELF, SHA-256
`bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af`.
No vendor source/binary/disassembly is reproduced in this public report.

The [Himax-authored HX6537-A datasheet V05, section 5.13, printed p.48](https://w3.icshop.com.tw/pd/368030502027/datasheet.pdf#page=48)
(distributor mirror) describes the EM9D peripheral micro-DMA and transfer setup.
It does not define channel stop/drain, pending-interrupt reset effects, or a
readback-enabled-state contract. Its memory-mapped accelerator DMA is not a
substitute for the peripheral micro-DMA. No PDF was redistributed. The general
ARC manual could not be retrieved; no uninspected register semantics were taken
from a search snippet or another DMA architecture.

Pinned SDK evidence, paths relative to the SDK root:

| Evidence | Supported conclusion |
|---|---|
| `board/socket/configs/24/io_config.h:83-86` | PDM RX0 channel 4; peripheral RX/error/clip vectors 69/70/71 |
| Linked `pdm_rx_devs` +7 and `io_pdm_rx_stop` descriptor load/shift | Actual linked DMA channel is 4, mask `0x10`, not just a build-time guess |
| `core_config.h:133-138,258-262`; `dmac_init` disassembly | 16-channel, multiple-internal configuration; DMA completion vector 20+4=24 and error 36+4=40 |
| `inc/arc/arc.h:412-414` | SDK status-register names/addresses: `AUX_DMACSTAT0` (0x686), `AUX_DMACSTAT1` (0x687), `AUX_DMACIRQ` (0x688) |
| `arc/arc_udma.c:199-217,234-251` | Separate read getters for DMA IRQ, busy, completion; polling interprets channel bit 4 and error bit 20 |
| `arc/arc_dmac.c:76-84`, separate clear functions | Status helpers issue reads; acknowledgment/error clear are distinct writes |
| `inc/arc/arc_builtin.h:229-240` | Cache-bypassing aligned word-read helper; new ELF confirms `ld.di` |
| Linked PDM read/ISR/stop and audio RX paths | Re-arm precedes app callback; acknowledgment follows RX return; stop disables/resets without an explicit DMA IRQ clear |

These are SDK-supported read contracts and static implementation evidence, not
independent silicon qualification. Peripheral IRQ 69 must not be confused with
DMA completion IRQ 24. The observer never selects, masks or acknowledges either.

## Observable and deliberately unobservable states

| Quantity | Diagnostic treatment |
|---|---|
| Busy | Channel-4 bit from SDK `AUX_DMACSTAT0` read; instantaneous only |
| Completion/error history | Channel-4 low/high bit from `AUX_DMACSTAT1`; sticky history is not current write activity |
| DMA interrupt request | Channel-4 `AUX_DMACIRQ` read; separate from the CPU interrupt-controller latch |
| Enabled state | **UNOBSERVABLE**: no established safe, interpreted enabled-state read; do not read enable/disable command registers speculatively |
| CPU pending/active latch | **UNOBSERVABLE**: banked selector access would alter shared state without a justified concurrency contract |
| Identity of a pending event across reset | **UNOBSERVABLE**: no generation tag; a post-stop request may be surviving or newly generated |
| Buffer changes | Exact word comparisons through uncached reads of our own lifetime-static 16 KiB DMA buffer |
| Every physical buffer write / bus drain | **UNOBSERVABLE**: same-value writes, reverted changes and inter-scan activity can escape observation |
| Re-arm attempt | Forwarded `_dma_chan_enable(mask, enable)` call with channel-4 mask and enable=1; not proof of successful bus progress or coverage of every possible direct AUX writer |

No ring/descriptor getter is used: the descriptor-memory getter could dereference
mutable state. No guessed address, sentinel write, cache flush, FIFO read, IRQ
acknowledgment or low-level stop/reset change was added.

## Minimal instrumentation and its cost

[bh_pdm_diag.h](../../../firmware/himax_arc/birdhouse/bh_pdm_diag.h) defines the
one-attempt observer. [bh_pdm_port.cc](../../../firmware/himax_arc/birdhouse/bh_pdm_port.cc)
retains the original OnAudio/start bodies and quarantine. A separate forwarding
wrapper in [ARC glue](../../../firmware/himax_arc/birdhouse/bh_arc_glue.cc) records
only word counters/idempotent latches, then calls the real enable function with
the exact original arguments. It does not print, mask interrupts, copy audio or
suppress/issue a DMA operation. Fresh linkage checks prove the PDM read/stop
call sites reach it. Aggregate enable counts can undercount nested increments;
the post-enable witness uses an idempotent latch instead of relying on counts.

`AT+BIRDDMA=1` arms once while idle; it queues no capture and reads no hardware.
The owner would separately issue `AT+BIRDRUN=1`. At the first Stop:

1. Original saved-IRQ detachment/quarantine/restore occurs unchanged.
2. Row phase 0 reads the documented status fields before the vendor Stop call.
3. Original `hx_lib_audio_stop()` runs once, unchanged. The existing normalized
   0/-2 return value is retained.
4. Row phase 1 is the earliest sequential post-return status sample, before the
   first buffer scan. The original caller can be preempted between return and
   the post-phase marker: that small boundary is **UNOBSERVABLE**. A
   `during_enable` latch therefore covers the call plus this return gap.
5. Main context observes 32 further samples at target 16 ms spacing for 512 ms,
   with a maximum 1,000,000 clock reads. The buffer shadow is main-owned; the DMA
   buffer is never written by the diagnostic. No PCM owner is dereferenced.
6. Records freeze before returning from Stop to the existing Finish/process
   path. `AT+BIRDDMA?` prints stored metadata only, outside capture/ISR.

Rows are not atomic snapshots. Timed row timestamps precede their buffer scan;
IRQ callbacks can run between reads. A scan is not a coherent whole-buffer
snapshot. Clock reversal, a >32 ms discontinuity or uncovered sampling gap,
invalid fields, failed Stop or exhausted budget prevents a sampled PASS. The
existing BSP clock can jump one second, so clock checks are diagnostic limits,
not a new trusted timing contract. P4 can block the ISR/main context forever;
the operation-count budget cannot rescue it or impose a hardware wall-clock bound.

The opt-in observation delays post-capture processing, uses a 16 KiB shadow plus
records and adds wrapper timing/12 bytes of wrapper stack. Even unarmed, the
wrapper has instruction/memory-layout overhead. Tests establish functional
behavior/order/ownership, not cycle-identical uninstrumented behavior. The
instrumentation can shift the race it measures; it never demonstrates all
interleavings or permits a second capture.

A `PASS_SAMPLED_ONLY` result means no specified activity was seen in that covered
interval. The printed `full_quiescence=UNOBSERVABLE` is intentional. See the
[precise interpretation and owner protocol](WINDOWS10_SINGLE_CAPTURE_PROTOCOL.md),
[offline validation](OFFLINE_VALIDATION.md) and [final decision](FINAL_DECISION.md).
