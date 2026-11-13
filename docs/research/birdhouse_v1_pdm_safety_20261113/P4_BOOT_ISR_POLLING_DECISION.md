# P4 boot/ISR polling decision

2026-11-13. **VENDOR_LEVEL_BLOCKED. P4 is not closed.**
No firmware patch for this poll is justified by the available interface and
call graph. Main-loop capture timeout remains useful only when control returns
to that loop. No hardware action or watchdog/reboot workaround is authorized.

## Complete paths to the poll in the frozen candidate

Evidence is the original hash-pinned linked ELF and read-only cached SDK headers
and application sources, rechecked independently in
[test_pdm_safety.py](../../../tools/himax/tests/test_pdm_safety.py).
SDK-root-relative locations identify evidence without reproducing vendor code:
`app/scenario_app/edge_impulse_visionai/edge_impulse_visionai.cc:83`,
`sensors/ei_microphone.cpp:211-216`, `library/audio/aud_lib.h:142-183`,
`platform/inc/hx_drv_pdm_rx.h:55-71`, and
`platform/peripheral/pdm/pdm_rx.h:63-91` (the sensors path is relative to the app).

| Context | Reachable call sequence | Why the existing guard cannot unblock it |
|---|---|---|
| Boot | `main` -> `edge_impulse_visionai` -> `ei_microphone_init()` -> `hx_lib_audio_init` -> `hx_drv_pdm_init` -> `io_pdm_rx_open` | Initialization happens before the first-party runtime/console hook. The microphone initializer ignores audio-init status and returns true if it returns at all. |
| PDM FIFO/error IRQ | `pdm_rx0_err_ISR` -> registered error callback `hx_lib_audio_err_callback` -> `hx_lib_audio_deinit` -> wrapped driver deinit; then `hx_lib_audio_init` -> `hx_drv_pdm_init` -> `io_pdm_rx_open` | Recovery reinitializes synchronously inside the error callback. The existing first-party deinit wrapper records a FIFO event and calls the original; it does not stop subsequent reinitialization. |

The frozen `io_pdm_rx_open` is at 0x1002a0f8. Its ready-bit loop at
0x1002a1b4-0x1002a1be repeatedly reads hardware and branches back when not ready.
There is no counter decrement, deadline, error exit or call in that loop. Every
normal initialized-device return is after the loop. Other early error returns
for device selection/state do not bound the path after the device is enabled.
The error ISR's earlier DMA acknowledgment does not bound this ready wait.
The error callback also proceeds toward transfer setup after audio init; it does
not propagate an initialization failure into a safe terminal lifecycle.

## Approaches examined

1. **A documented bounded low-level open/init or abort API.** The inspected
   headers expose open/init/close/read/stop/ioctl and callback registration, but
   no deadline/cancelable-open contract or documented interrupt-independent
   timeout. Implementation is prebuilt. A timeout on a fake open does not modify
   or bound the real ready loop. No applicable bounded alternative was found in
   this pinned SDK; this is a scoped finding, not a claim about all vendor SDKs.
2. **First-party link interception around initialization/deinit.** A wrapper that
   calls the real open can hang in the same loop. Returning failure before entry
   avoids that call by disabling initialization; it does not implement bounded
   working PDM. Boot currently ignores status, and the ISR recovery callback can
   continue to transfer setup after init failure. A no-op/success wrapper would
   fabricate initialized state. A full fail-closed PDM-disabled build would need
   separate interception/coverage of all boot, error, transfer and vendor-client
   entries, safe channel state and status propagation. Existing `--wrap` hooks
   do not establish that coverage; internal/same-object references cannot be
   presumed interposable. No such stub or new link interception was installed.
3. **Main-loop deadline, another clock/thread, watchdog or reboot.** None supplies
   a return edge from the blocked boot/ISR. Reboot may reenter the same loop and
   is not quiescence or recovery evidence. These are not accepted P4 mitigations.

Permanent P1 quarantine prevents another first-party capture after stop; it
cannot prevent boot initialization or an already-running peripheral's FIFO-error
ISR from reaching this poll. It therefore makes no P4 closure claim.

## Exact prerequisites for a defensible vendor repair

- Source or an authoritative patch for this exact driver/part/version, with a
  bounded ready wait on every open/reopen path, a specified finite polling budget
  or interrupt-independent time source, and an explicit timeout return edge.
- Defined cleanup of enabled peripheral, reserved DMA channel, descriptor state,
  pending/latched completion and error interrupts on timeout, preserving unrelated
  channels and restoring the caller's interrupt state. P1 drain/ack semantics
  must be documented alongside it; reset alone is insufficient evidence.
- Error propagation through driver init, audio init and boot microphone init;
  failed initialization must prevent all dependent starts and invalid state use.
- Bounded/deferred error recovery: no automatic potentially blocking reopen in
  ISR; a latched failure must reach main context safely, and a failed recovery
  must not unconditionally re-arm transfer. Every indirect callback/internal
  reference must be covered in the final linked image.
- Offline verification of the exact patched call graph, real stuck-ready-low
  negative controls at the low-level implementation, and later separately
  approved measurement of boot/error behavior, timing and stop quiescence on the
  real part. A host fake alone cannot provide the hardware evidence.

No SDK source, prebuilt object, register implementation, bootloader or binary was
modified. Public reports contain conclusions, symbols and provenance only.
The [final decision](FINAL_GO_NO_GO.md) keeps first Flash and real capture NO-GO.
