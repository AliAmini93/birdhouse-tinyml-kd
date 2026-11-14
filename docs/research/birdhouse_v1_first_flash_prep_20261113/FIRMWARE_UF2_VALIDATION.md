# Firmware and UF2 validation — sandbox startup blocked

2026-11-13. **BLOCKED: BUBBLEWRAP_NAMESPACE_CREATION_DENIED.** The fresh clean P1
ELF passed code/link audits. Existing packaging exited 1 because its required
sandbox could not start. No new application image or UF2 was produced. New UF2
path, SHA-256, bytes, blocks and section/address manifest are null in
[summary.json](results/summary.json). No old package was copied or relabeled.

## Existing guard preserved; earlier policy conflict resolved

The owner now explicitly permits the existing guard's passive mount inspection
and confirms physical Windows-only board attachment. The guard/verifier source
is unchanged: `package_offline.py`, SHA-256
`d4c60ccf89f7a63873ff579c9d53a394f54cd1f52d439c70a56103c6d7d4611d`.
The earlier guard-removal proposal is superseded and was never applied.

The guard catches `OSError` internally. A private invocation harness therefore
observes its actual execution with Python's standard tracing API and aborts on
read exceptions, malformed rows, an empty/incomplete return or a Grove hit.
It replaces neither `open`, the guard, the verifier nor any sandbox flag. The
unchanged `main()` calls the original guard and performs its original checks.
All observed guard calls completed valid nonempty reads and reported no Grove
volume. Only count/success metadata remains private; mount contents are not
published. Physical absence is owner-confirmed, not inferred from this result.

Before generation, exact main-path tests rejected existing, outside and
symlink-escaping output roots. None reached generation or created package outputs.
Actual packaging ran only after fresh postlink/operator PASS, into the new ignored
`first-flash-prep-20261113-OFFLINE_ONLY-3/package/` root. No active device probe ran.

## Specific technical blocker

The existing packager copied its local Linux tool inputs into the fresh workspace
and attempted the unchanged bubblewrap command. Its first launch failed:

> bwrap: No permissions to create new namespace

The diagnostic suggests unavailable non-privileged namespace creation. The exact
kernel/security-policy cause was not probed or changed. Installed bubblewrap
0.9.0 does not prove nested isolation can start in this session. The generator
was not launched; there is no generated `output.img`, second deterministic run,
final `out` directory or UF2. The packager returns before writing its normal
validation JSON on this failure; separate private invocation status records
exit 1 and the sandbox error. No synthetic PASS JSON was substituted.

No modified flags, retry, OS change, permission escalation, host generator run,
verifier bypass or old-UF2 fallback occurred. The failed workspace is preserved.
Further production needs a separately authorized environment supporting the same
isolation; this session does not weaken or bypass it.

## Artifact identities

| Role | Bytes | SHA-256 |
|---|---:|---|
| Fresh clean P1 ELF, unpackaged | 1,650,872 | `bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af` |
| Prior incremental P1 ELF, comparison only | 1,650,872 | `bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af` |
| Official local factory `grove_ai_v02-00.uf2` | 1,541,632 | `8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c` |
| PRE-P1 ELF, excluded | 1,650,872 | `8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f` |
| PRE-P1 image, excluded | 628,016 | `c2d7e176436433f714633bc817cec3bc232c8fabd62389567be518358b6de388` |
| PRE-P1 UF2, excluded | 1,256,448 | `009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae` |

The exact new ELF path/build proof is in [provenance](BUILD_AND_SOURCE_PROVENANCE.md).
Its whole-file equality to the incremental reference was checked after rebuilding
available sources. No first-party source or verification standard changed. All
prior reference files were rehashed before/after resumed work and stayed unchanged.
All binaries/vendor files remain ignored/private, ineligible for public GitHub.

## Independent reference parsing, never a new-package validation

Earlier in this same live mission a separate `struct` parser checked every
factory and PRE-P1 UF2 block: three magics, flags `0x2000`, family `0xef32c892`,
256-byte payloads, exact numbering/count, unique contiguous addresses, zero
unused bytes and the 2 MiB limit. `uf2_tool.py info` independently passed both;
its `verify` passed the old image/UF2 pair. No such result exists for a new UF2.

| Reference | Blocks | Payload bytes | Half-open target interval |
|---|---:|---:|---|
| Factory | 3,011 | 770,816 | `[0x10000000,0x100BC300)` |
| PRE-P1 UF2 | 2,454 | 628,224 | `[0x10000000,0x10099600)` |

Factory payload SHA-256:
`809bfedf75413355d88b97564b07eab2b526ec0c00c112e5e04edf4ad4768a40`.
Old payload SHA-256:
`b8a12eb299aaa7ce0428c05eab0c4fe1c7ed0ce21b4b15d387f03d9dacfcab2d`.
The old image's 208-byte zero padding was checked. For this PRE-P1 reference only,
loader slots `[0,0x20000)` and config `[0x21000,0x22000)` match factory; metadata
`[0x20000,0x21000)` differs. Factory supplies a further 142,592-byte tail at
`[0x99600,0xBC300)`. These dimensions cannot be assigned to the absent P1 UF2.
Matching loader bytes mean package parity, not physical erase/write skipping or
preservation of installed settings/calibration.

## Remaining gates

Regressions, clean build, ELF model, three wraps, operator/kernel linkage, static
resources and production test-symbol exclusion passed. Still required: twice-
generated deterministic image inside the unchanged sandbox; ELF/SBS reconstruction
of all bytes/destinations; exact packaged model identity; factory loader/config
and tail comparisons; two independent new-UF2 validations; review-only filename;
new UF2 digest unequal to the PRE-P1 exclusion; two reads of its final on-disk
digest/size. Cryptographic acceptance by the boot ROM and physical boot would
remain UNKNOWN after package checks. No new digest can yet be approved for writing.
