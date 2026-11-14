# First-flash offline build and source provenance — 2026-11-13

**Fresh clean ARC build: PASS. Artifact preparation: BLOCKED at sandbox startup.**
No new image or UF2 exists. See [validation](FIRMWARE_UF2_VALIDATION.md).

## Authorization and command plan recorded before execution

The initial file-only plan required source/SDK/tool checks, preservation of old
outputs, fixed Python, static-first focused regressions, reviewed compile/link
recipes, a fresh ignored build root, postlink/operator checks, isolated packaging,
independent UF2 verification and an inactive Windows risk kit. No hardware,
uploader, OS change, installer, sudo or permission escalation is authorized.

The first attempt stopped at the existing mount-table guard under the earlier
blanket discovery prohibition. The owner's follow-up explicitly permits passive
`/proc/mounts` inspection through **the existing guard** and confirms the board
remains connected only to separate Windows 10 hardware. The old proposal to
remove the guard is superseded and was never applied. The resumed command plan
was recorded before tests/build: preserve the guard; stop if its read is
unreliable or a Grove volume is found; use a new root and unchanged verifiers.

## Source and environment

| Item | Observed result |
|---|---|
| Branch | `research/birdhouse-v1-first-flash-prep-20261113` |
| Repository HEAD | `5a94940fcce5708ff686c7aaa18ae5606ee035c6` |
| Required firmware/tool source | `3d0fb3fd4c1889d79462bbc404aee722c1811894` |
| Source Git tree object ID, not SHA-256 | `1fe29b76ed6e1dc46b47fe5ac0ea108e8fbee317` |
| HEAD delta | Three mission/launcher/README files only |
| Source comparison | All 95 tracked files under `firmware` and `tools/himax` byte-identical to `git show SOURCE:path` |
| Source inventory SHA-256 | `c6e529b1bd495d4534c38bc77d92ba193a472e2cc8d5b46761f8ff8591b54b18` |
| SDK | `9dc2370d4dc269dc4bcafcf0354b8f745d08801f`, clean before and after |
| Python | Existing owner-selected interpreter through quoted `BH_PYTHON`, always `-I -B`; 3.11.15 |
| Existing tools | g++ 13.3.0; GNU Make 4.3; bubblewrap 0.9.0; ARC GCC 10.2.0, `arc-2020.09-1-release` |
| Physical isolation | Explicit owner confirmation; no active discovery |

Inventory encoding: sort the 95 paths lexicographically; concatenate UTF-8
`path + NUL + decimal bytes + NUL + lowercase file SHA-256 + LF`; hash with
SHA-256. This is a defined source inventory, not a whole-SDK/Git-object digest.

Resumed ignored root:
`.local-tools/port-himax/first-flash-prep-20261113-OFFLINE_ONLY-3/`.
Both earlier preparation roots and all validated files were preserved. The
unnumbered root holds an earlier failed preflight-log relocation, not a build;
`-2` holds the first stopped inspection. The resumed root preserves the earlier
reports, raw commands/logs, complete provenance and failed packaging workspace.
No earlier artifact was overwritten, deleted or relabeled.

## Focused regression executed in this resumed run

The reviewed unchanged `test_pdm_safety.py` module was imported with only `WORK`
redirected to the new root's `host` directory. This avoids overwriting its old
hardcoded result file. Order: static observations, static mutations, native and
sanitizer regressions, compiled mutations. Four unittest methods passed with
zero failures/errors. No test assertion or implementation source was changed.

| Suite | Ordinary assertions | ASan/UBSan assertions |
|---|---:|---:|
| Diagnostics | 71 | 71 |
| Capture | 281 | 281 |
| PDM adapter | 95 | 95 |
| Adversarial lifecycle model | 969 | 969 |
| Runtime | 466 | 466 |
| Actual host console parser/server | 35 | 35 |
| Preprocessing reference | 21 | 21 |
| Model inference | 586 | 586 |
| Total | 2,524 | 2,524 |

**5,048 assertions across 16 variants PASS.** Seven compiled mutants compiled
successfully and failed assertions as required; four static mutants were
rejected. The 16 original binary observations and nine focused call-path/order
facts passed. Cached native link inputs stayed unchanged. No ASan/UBSan error
was reported; existing leak checking is disabled, so no leak claim is made.
These host models do not validate physical DMA, timing, microphone or ARC MLI.

## Fresh clean ARC build

Read the wrapper/overlay, relevant SDK make fragments, and precise build sections
of `run_offline_checks.py`; the broad runner was never executed. Reviewed dry-run
`all` expands only to the ELF: 286 source compiles (ten first-party, 276 SDK), one
linker-script preprocessing command, two local archives, three pinned SDK
prebuilt-library copies, seven local TCF conversions and one link. All outputs
are confined to the new ARC root. No previous ARC object, previous-build archive
or ELF is an input. Original SDK prebuilt libraries remain necessary; proprietary
library internals were not rebuilt.

The existing allowlisted `sdk_make.sh` ran against the fresh `arc` root with
`-j8`, default `all`, pinned SDK/toolchain and deterministic environment. Inherited
make injection options were cleared. Before build the root had no objects/ELF;
only reviewed empty output directories were prepared. Exit 0, about 32 seconds.
There were zero first-party and 44 vendor warning diagnostics, retained privately.
No flash/run/OTA/converter/uploader target ran.

Fresh output:
`.local-tools/port-himax/first-flash-prep-20261113-OFFLINE_ONLY-3/arc/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf`

**1,650,872 bytes**, SHA-256
`bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af`.
The complete fresh ELF equals the incremental P1 reference byte-for-byte. This
comparison occurred after the clean build; the old ELF was never its input or
substitute output. All reviewed input fingerprints, source, SDK and prior
reference bytes stayed unchanged. The fresh ELF is unexecuted and unpackaged.

A local macro dry-run reader initially stopped on a shell line continuation.
Logical-line parsing corrected that invocation review before macro preprocessing
ran; no firmware/verifier change or clean-build retry was needed. The wrapper
then produced the actual operator macro dump with one preprocess-only command.

## Fresh postlink and operator results

Unchanged `postlink_audit.py`: **28/28 PASS**, using the new ELF, new linker script
and fresh stack files. Unchanged `verify_tflm_ops.py`: **83/83 PASS**, using actual
macros, fresh kernel objects and ELF. The INT8 fully-connected overlay, MLI
workers and all three existing wraps are retained: `is_inference_running`,
`hx_drv_pdm_deinit`, and the SDK ATParser C++11 symbol. Postlink checks cover their
call sites. Independent symbol inspection found no host reset/fake audio/test or
sanitizer symbols.

| Static resource | Used / capacity |
|---|---:|
| ICCM1 | 301,306 / 327,680 bytes |
| SYSTEM0 | 849,204 / 1,439,744 bytes |
| DCCM | 76,960 / 253,952 bytes |
| Heap capacity | 176,992 bytes |
| Linker stack extent | 8,188 bytes |
| Partial known inference frames | 1,664 bytes; neither peak nor bound |

The model array and linked payload are **59,760 bytes**, SHA-256
`9e04d17723b87f9acbba3030c23e1e50b551493125e9bf7dc0aeb27f0b12db55`.
All preprocessing is byte-identical to the source commit. Selected fingerprints:

| Source | SHA-256 |
|---|---|
| `audio_preprocess.cc` | `b644a15438c3d3eb3854f92a96825b0ed76a05633ec5830bea655a2897991650` |
| `mel_filterbank.cc` | `3dcad8d090380147b8cb8d902c59a3240b6f9fb3e7cc29d146640b60aee96a44` |
| `preprocess_constants.h` | `6abf55a5bc5aea4edcd075902d8ea871c07e398a081e995f662da27d77e66bc3` |

Static fit does not establish physical stack safety or timing. P1 pending-DMA/
stop quiescence remains unproven; P4 is vendor-blocked. See
[validation](FIRMWARE_UF2_VALIDATION.md), [Windows kit](WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md),
[unsigned record](OWNER_RISK_ACCEPTANCE_RECORD.md), [decision](FINAL_ARTIFACT_DECISION.md)
and [summary](results/summary.json).
