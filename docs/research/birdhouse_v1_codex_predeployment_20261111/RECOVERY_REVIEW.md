# Recovery review — offline only

**Status: BLOCKED for recovery readiness; hardware write NO-GO.** No physical
board interaction was performed. This is a protocol for later owner and ChatGPT
review, not authorization to carry it out.

Two existing factory fallback copies pass SHA-256 and UF2 checks:
`8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c`.
The copies are identical and each is 1,541,632 bytes. They are factory fallbacks,
not backups of this board's installed application or configuration. See
[the local inventory summary](results/recovery_inventory.json).

The candidate is a **full Himax firmware image**, including both bootloaders.
Byte identity of their regions with the factory image proves expected contents;
it does not prove that an updater avoids erasing/writing them, that updates are
atomic, or that interrupted power leaves recovery available. Configuration lies
above the candidate payload, but the actual updater's erase range is unverified.
No application-only update is assumed safe. Model-slot updates are a different
address range and do not supply the microphone application.

No BL702 recovery binary, audited Seeed Arduino GroveAI repair-library source,
or Arduino CLI was found in the existing local tool cache. Therefore a real
repair-host build cannot be reproduced in this offline session. The prior
research's descriptions of I2C repair, BL702 ROM recovery and XMODEM are leads,
not independently established recovery procedures here. No mock repair host is
counted as recovery evidence. Nothing was downloaded or substituted.

Before proposing any hardware action:

1. The owner identifies what must be preserved and explicitly accepts or rejects
   losing the installed application/configuration. A factory fallback is not an
   exact backup; installed identity and readback availability remain unknown.
2. Supply and audit the missing recovery assets offline, record their provenance
   and hashes, and build the actual repair host using an existing compatible
   toolchain. Inspect its startup and query paths for implicit reset/write calls.
3. Review one precise transport rehearsal separately: port/power arrangement,
   automount and probing-process controls, permitted observations, timeout, and
   stop criteria. Even attaching/enumerating the board or opening serial is
   outside this session's authorization. An I2C query is also a hardware action.
4. Establish which component each recovery route repairs, required boot state,
   erase/write regions and power-loss behavior. Prove the proposed read-only
   recovery link before allowing any write. Do not update BL702 merely to test it.
5. Obtain explicit approval for one exact image hash, transport and operation.
   Never invoke the vendor auto-deploy UF2 converter or make flash/run as part of
   an offline workflow. Recheck the approved file hash immediately before a
   separately authorized transfer.

Only after an independently approved experimental write and normal boot: stop
at the first unexpected output; identify the candidate via its documented image
and new INFO fields; run INFO, graded model self-test, synthetic pipeline cases,
then one microphone capture with an external time reference. Recompute a dumped
capture on the host before any soak. A CLOSE self-test is diagnostic evidence,
not automatic numerical acceptance. CLOCK/SUSPECT means `decision=NONE` and
requires investigation. Check stack watermark since painting, arena allocation,
late callbacks and explicit stop/retry behavior. No simultaneous vendor sampling,
camera/Edge Impulse job, or I2C client belongs in the first qualification session.
