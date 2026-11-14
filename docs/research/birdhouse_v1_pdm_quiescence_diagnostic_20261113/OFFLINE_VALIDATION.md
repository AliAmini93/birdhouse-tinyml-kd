# Offline validation and artifact disposition

2026-11-13. **Host/model tests and clean ARC build PASS; UF2 packaging BLOCKED.**
No hardware execution, active device probe, flash, reset, recovery or Windows
operation occurred. All Python used the owner's existing interpreter through
quoted `BH_PYTHON` with `-I -B`; no environment/install/system change occurred.

## Preservation and source identity

Before source edits, all six previous uncommitted reports and both staged and
unstaged patches were preserved in a new ignored root:
`.local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/`.
Their working bytes and the pinned factory/old candidate/reference files were
checked unchanged afterward. No earlier report or artifact was repurposed.

The source is the P1 baseline `3d0fb3fd4c1889d79462bbc404aee722c1811894` plus the
uncommitted diagnostic source/test patch. Repository HEAD is still
`5a94940fcce5708ff686c7aaa18ae5606ee035c6`; it does not include the new source.
SDK `9dc2370d4dc269dc4bcafcf0354b8f745d08801f` stayed clean.

Build-time source inventory: **98 files**, SHA-256
`796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e`.
Encoding: tracked plus nonignored new files under `firmware` and `tools/himax`,
sorted path, UTF-8 `path + NUL + decimal bytes + NUL + lowercase file SHA-256 + LF`.
All bytes stayed unchanged after the build. This is a working-source inventory,
not a claim of a new committed revision. Model/preprocessing files were unchanged.
Raw commands, inventories, source/ELF comparison evidence and logs remain ignored.

## Tests and negative controls

The existing PDM suite was run static-first with only `WORK` redirected into a
new directory. Eight retained native suites passed ordinary and ASan/UBSan runs:
2,529 assertions each, including 40 console assertions. Original lifecycle,
startup masking, detachment, exact IRQ restore, permanent quarantine and failed
start/stop behavior all remain covered. Seven compiled lifecycle mutants and
four static mutants were rejected.

The final observer fixture passed **266 assertions per native variant**, ordinary
and ASan/UBSan. Final combined total: **5,590 assertions in 18 variants**. After
independent-witness fixtures were strengthened, the observer variants were rerun;
this total uses their final counts, without double counting earlier fixtures.
No ASan/UBSan error; leak checks disabled as in the original suite. No physical
DMA/cache/latency or concurrency-exhaustiveness claim follows.

[Observer tests](../../../firmware/himax_arc/tests/test_pdm_diag.cc) check:

- Unarmed Stop performs no diagnostic status reads, wait or print.
- Armed observations preserve PCM guards, capture statistics, ring-request
  counts, start/stop count and IRQ state across stop failure/interleaving cases.
- Pending IRQ, enable attempt, callback-only delivery and changed buffer words
  independently produce failure witnesses; unknown reads never become zero-PASS.
- Frozen/discontinuous clocks terminate with INCONCLUSIVE, not a false deadline PASS.
- Other channels and disable calls are ignored; partial-start cleanup observes
  only once and cannot publish a failed owner or reopen quarantine.
- The actual host console parser arms without queuing a capture and refuses
  rearming after quarantine.

[Additional offline tests](../../../tools/himax/tests/test_pdm_quiescence.py)
verify SDK mappings/read getters, byte-identical original OnAudio/start/runtime
source, detachment-before-stop, forwarding arguments and no observer ISR print
or masking. Six additional compiled mutants each built and then failed assertions:
ignore unknown validity, changed words, enable latch, IRQ request, late callback,
or quarantine at arm. Combined compiled mutants rejected: **13**.

An initial new test compile caught a wrong test-summary helper name; it was
corrected before final validation. No firmware failure was hidden or treated as
an expected negative control.

## Clean ARC build and ELF audits

The SDK compile/link closure was reviewed before execution using a dry run.
Existing `sdk_make.sh` built in an empty new `arc` tree with `-j8`: 286 source
compiles (ten first-party, 276 SDK), linker-script preprocessing, seven local TCF
conversions, two new archives, three original SDK library copies and one link.
No old ARC build object/ELF was used. Prebuilt vendor-library internals remain
opaque and were not rebuilt. No flash/run/OTA/uploader target ran.

Fresh ELF: `.local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf`

Bytes: **1,667,964**. SHA-256:
`3e350b171ed79ae9cdc96d635475b9f6de921288adbc29aab34905d96db41eee`.
This differs from the prior P1 ELF because it includes the diagnostic. The ELF
is unexecuted and **not** a flashable UF2. No source/verifier modification occurred
after this clean build. First-party warning count: zero; vendor warnings remain
in private logs.

| Check | Result |
|---|---|
| Existing postlink memory/model/hooks/stack policy | 28/28 PASS |
| Actual macro/kernel/MLI/operator audit | 83/83 PASS |
| Additional diagnostic ELF conditions | 14/14 PASS |
| New status helper | Exactly three AUX loads; no AUX store, ack, selector write, call or mask |
| Buffer helper | Cache-bypassing `ld.di`, no write |
| Enable wrapper | Both ABI arguments saved/restored; observer then real function |
| Actual PDM read/stop linkage | Both call the forwarding wrapper |
| Vendor stop | Disable still precedes reset; no new clear operation |
| Host reset/fake/test/sanitizer symbols | Absent |
| P4 poll | Still present and unbounded |

| Static resource | Used / capacity |
|---|---:|
| ICCM1 | 302,466 / 327,680 bytes |
| SYSTEM0 | 849,812 / 1,439,744 bytes |
| DCCM | 94,880 / 253,952 bytes |
| Heap capacity | 159,072 bytes |
| Linker stack extent | 8,188 bytes |
| Stop frame / added enable-wrapper frame | 72 / 12 bytes |
| Partial known inference frame sum | 1,664 bytes; neither peak nor bound |

The 16 KiB shadow plus metadata adds static memory; the policy margin still
passes. This is not a measured stack/interrupt-nesting or timing guarantee.
Model bytes in ELF: 59,760, SHA-256
`9e04d17723b87f9acbba3030c23e1e50b551493125e9bf7dc0aeb27f0b12db55`.

## Packaging attempt and exact remaining blocker

Existing `package_offline.py`, guard and bubblewrap flags were preserved. The
previously authorized passive guard read was reliable and found no Grove volume;
no active discovery occurred. Existing/outside/symlink-escaping output roots were
rejected in focused tests before any generation. The new diagnostic ELF then
entered the original packaging workflow in the fresh ignored `package` root.

The first sandbox launch failed: **`bwrap: No permissions to create new namespace`**.
Packager exit: **1**. The vendor generator was not launched. No first generated
image, second determinism run, ELF/SBS reconstruction or new-UF2 validation exists.
The precise kernel/security-policy cause was not probed. No modified flags,
host generator fallback, permission escalation, retry or OS change occurred.
The failed workspace and invocation status remain private and preserved.

New UF2 path/hash/bytes/blocks: **NONE**. The owner cannot yet approve an exact
candidate UF2. The old verified UF2 and factory still have their original hashes;
neither is substituted for this diagnostic. [Final decision](FINAL_DECISION.md)
records the publication boundary and next human decision.
