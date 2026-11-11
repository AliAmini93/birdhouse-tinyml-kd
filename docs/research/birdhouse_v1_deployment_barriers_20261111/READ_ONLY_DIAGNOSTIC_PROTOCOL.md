# Proposed observer-only Grove V1 session

**Not executed. Not authorized by this document. Current admission: NO-GO.**
This is the next hardware-access boundary for owner and independent ChatGPT
review. Purpose: assess whether the already connected bridge remains stable
without application commands or storage/serial clients. It cannot identify the
Himax application, prove recovery, test the microphone or qualify an update.

## Preconditions for a separate approval

Each item must have concrete evidence and a named reviewer; a checked box or a
passing offline checker is insufficient by itself.

1. Owner approves this exact observer phase, duration, permitted host commands,
   private log destination and stop rule. No implied permission for later phases.
2. The board is already powered/connected in a known state. No insertion,
   replug, power transition, BOOT-button press, reset or cable change is needed.
   Current state was not queried in this offline session. If attachment is
   required, stop and review attachment/host-isolation as a separate operation.
3. A reviewed host setup prevents MSC activity. Disabling desktop automount or
   using a read-only mount is insufficient: the kernel storage driver can probe
   before a filesystem is mounted. A prepared isolated host with reviewed
   per-interface binding policy is preferable to ad hoc module changes on a
   shared workstation. Do not unload storage modules or alter binding live here.
   If the already connected board's existing binding cannot be made safe within
   the approved scope, this phase cannot begin; revise the scope before action.
4. ModemManager, GVFS/udisks, vendor daemons, Edge Impulse tools, browser WebUSB/
   WebSerial sessions, IDE monitors and automatic reconnect jobs cannot access
   this target. No mounted Grove filesystem, open tty/block client or other host
   process can create transactions. The exact verification commands and any host
   configuration changes must be reviewed first; none were executed here.
5. Target identity/path is mapped using existing host kernel/udev metadata and
   owner knowledge, with competing devices excluded. VID/PID alone identifies
   bridge mode, not unique board identity or the Himax application. Do not guess
   `/dev/ttyACM0`, a block node or a USB bus address. Keep serial strings private.
6. Reviewer confirms that proposed identity reads use **cached** kernel/udev
   fields, without USB control requests, attribute stores or device-node opens.
   Do not substitute `lsusb -v`, `udevadm trigger`, an I2C scan or a vendor tool.
7. Stop handling is agreed in advance. On failure, stop agent activity and
   preserve host evidence. Unplugging, reset and recovery remain separate
   consequential actions; no automatic response is authorized.

[OBSERVER_PLAN.json](OBSERVER_PLAN.json) currently marks every prerequisite false
because it is **unestablished**. `observer_admission()` only checks supplied
claims and permits two action names. `REVIEW_READY` would mean a complete manual
checklist, not verified host isolation, permission or device safety.

## Exact proposed observations

After separate approval and satisfaction of all prerequisites:

1. Record approved host policy, known bridge state, cached target path and a
   monotonic start time in a private session manifest. Preserve earlier logs;
   do not truncate or clear the kernel journal. Do not poll the board for state.
2. Start one **host-kernel-journal** observer for **120 seconds**, from the start
   of the approved quiet window. This spans roughly four historical 31-second
   reset periods. Existing log entries must be distinguished from new events.
   The proposed Linux observer is:

   ```sh
   timeout --signal=TERM 120s journalctl --kernel --follow --lines=0 --output=short-monotonic
   ```

   This reads the host journal only. Expected timeout termination is the end of
   observation, not a failed device test. A reviewer/operator watches throughout
   and interrupts at the first stop condition; the timeout alone is not a monitor
   or automatic safety mechanism. If journal permissions are unavailable, stop
   and review host log access; do not escalate into device access.
3. At the start and end, compare the already identified target's cached identity
   and host interface-binding metadata. Exact target path and read commands must
   be added to the approved manifest before execution. A kernel/udev database
   snapshot is acceptable only after verifying its read path cannot cause a USB
   transfer. This document intentionally supplies no executable target-discovery
   or sysfs walk. Do not read descriptor binary attributes or mounted `INFO_UF2`
   as a substitute. If the target path is not already known, stop here.
4. Record new reset/disconnect counts, SCSI/I/O/USB errors, mode/identity changes,
   policy violations and whether the full 120-second window completed. Keep raw
   logs private; publish only redacted event counts and relevant intervals. No
   application input/output or recordings are collected.

Stop immediately at the first reset, disconnect, new identity/mode, SCSI timeout,
I/O error, filesystem activity, unexpected client/probe or uncertain target.
Preserve host evidence and return for independent review. No retry loop, serial
fallback, reset, unmount/remount, driver rebind or factory repair follows.

Acceptance is narrow: 120 seconds completed, zero stop events and unchanged
reviewed host controls. This supports quiet-host transport stability only.
It does not prove the bridge's updater is safe, the Himax app is alive, a pending
DMA IRQ is cleared, or any recovery method works. Failure is NO-GO for expanding
access; an empty journal alone without isolation evidence is inconclusive.

## Actions explicitly outside this phase

- No tty open, `cat` of a tty, baud setting, line control, CDC query, `AT+INFO`,
  `BIRDINFO`, reset escape or serial monitor. Receive-only intent is not enough:
  open/close and termios/DTR/RTS can send control traffic, and 1200 baud is used
  by the cached converter to request bootloader mode.
- No I2C transaction or scan, USB descriptor query, vendor OTA tool, UF2
  converter, block read, filesystem mount, `CURRENT.UF2`/`INFO_UF2` read or write.
- No usbmon capture in this phase. A later targeted, passive host trace may help
  isolate a stall, but bus scope, permissions, private-data handling and whether
  it changes host behavior require a separate reviewed proposal.
- No attachment/power/mode transition, firmware transfer, erase, recovery test,
  bootloader update, JTAG attach or use of physical debug equipment.

## Gates for a later active diagnostic proposal

A stable observer phase permits a new proposal only. Before CDC access, establish
the exact installed BL702 behavior for open/close, baud and line-state requests,
and the currently running application's query protocol. Alternatively, review a
verified electrically receive-only external UART observation path, including
pins, voltage, grounding and proof that transmitter/reset/boot signals cannot
be driven. Either choice is hardware interaction and needs explicit approval.
Do not send guessed Birdhouse commands to an unidentified installed image.

Before any experimental firmware write: settle preservation requirements;
obtain/audit compatible bridge and Himax recovery assets; identify a board-specific
recovery path independent of a healthy candidate app; establish readback and
erase ranges; and separately approve how recovery will be qualified. Do not
update BL702 as a diagnostic shortcut. Match a proposed transfer to one exact
image SHA and inspect its actual transport, power-loss and completion semantics.
XMODEM receipt and a loader completion message are insufficient flash validation.

After a separately approved deployment, qualification must still measure PDM
startup/progress and single-stop behavior before any restart, inspect pending
IRQ/re-arm state using a reviewed method, test actual MLI numerics and measure
stack/arena/timing. FIFO-error recovery cannot rely on the main-loop timeout.
Those are future physical gates; no command for them is authorized here.
