# Offline test and build matrix

2026-11-13. **OFFLINE_ONLY / NOT_FOR_FLASH.** Native and static checks model
software behavior; they cannot qualify physical DMA stop or a bounded boot/ISR.
This command audit was written before executing the new comprehensive suite.
Results will be appended after execution, including any failures and repairs.

## Reviewed command and dependency boundary

From the repository root:

```sh
"$BH_PYTHON" -I -B -m unittest discover -s tools/himax/tests -p test_pdm_safety.py -v
```

The exact compiler argument arrays, suite source lists, cached operands and
mutations are in [test_pdm_safety.py](../../../tools/himax/tests/test_pdm_safety.py).
Each native translation unit uses `g++ -std=c++11 -O2 -g -fno-pie`, host/static-memory
defines, repository/operator-overlay includes and the cached vendor model includes
as system headers, with `-Wall -Wextra -Werror -c SOURCE -o OBJECT`. Linking uses
`g++ -no-pie -o TEST OBJECTS [CACHED_ARCHIVE] -lm`; console additionally uses the
existing AT-parser linker wrap. Sanitized variants add
`-fsanitize=address,undefined -fno-omit-frame-pointer` on compilation and linking.
The subprocess API supplies argument lists, never shell command expansion.

Eight suites: diagnostics, capture, original PDM adapter, new lifecycle model,
runtime, actual vendor console parser/server, stored preprocessing reference,
and model inference. Runtime/console/inference link read-only validated host
`overlay` / `overlay-san` kernel archives; console also links the corresponding three
validated AT objects. The sanitizer archive's ASan/UBSan references are checked
with native `nm`, and all cached operand bytes are checked unchanged afterward.
No vendor source or binary is copied into the repository or reports. Synthetic
PCM in host tests is generated mathematically; no real/private audio is used.

The same command compiles seven deliberate mutations into temporary first-party
copies. Each must compile successfully and exit 1 with `CHECK FAILED` assertions.
It also reads the frozen candidate with ARC `objdump`/`readelf` (inert data only),
rechecks the 16 original PDM observations and nine focused call-path/order facts,
and rejects four mutated static observations. No old barrier CLI, hardware
metadata, cached USB log, packager, image generator or broad discovery is used.

All output is in new ignored storage below
`.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH`.
The JSON produced there is a private test output and will not be staged.
A sanitized aggregation belongs in this report and `results/summary.json`.
Each child subprocess has a 60-second host safety limit; it makes no assertion
that a blocked firmware boot or ISR would return. Leak detection is disabled
because it is unavailable under the sandbox tracer; no leak claim.

The two initial direct native PDM commands from R0 have passed: adapter 95
assertions; initial lifecycle model 969 assertions. The comprehensive suite
rebuilds their current sources, including the negative-control early-exit guard.

## ARC command gate

The existing SDK recipe has been read statically. No SDK make/build command has
been executed in this mission. A new ARC compile/link may proceed only after
review of its exact argument arrays and inert file operands. It must write to a
new ignored directory and must not invoke a generator, converter, device utility
or make flash/run/OTA target. Any inability to establish that boundary will be
reported as a skipped link, never as a successful firmware build.

## First run correction (before re-execution)

The initial comprehensive run rejected one link: the unsanitized cached console
parser objects were absent. All 15 other native variants passed, including the
sanitized console. This was an operand/provenance assumption in the new test
harness, not a firmware failure. The harness now explicitly compiles the three
host parser/server translation units from the read-only SDK for both variants.
Only these vendor units use `-w`, matching the existing host Makefile; first-party
warnings remain errors. The cached kernel archives remain read-only link inputs.
The earlier statement about reusing cached AT objects is superseded by this note.

For ARC, the reviewed make parse-time shell expansions are local `uname`, `pwd`
and a compiler library-path query. The selected prebuilt BSP configuration avoids
the optional SVN query. No recursive make/forced recipe is present in the scanned
SDK make fragments. A foreground `make -n all` with explicit configuration and a
new output root will only capture the expanded recipe; no target recipe will be
executed. Each selected compiler/link line will then be validated before any
cross-compile. The full vendor make recipe will not be executed.

## Exact incremental ARC recipe audit (before cross-compilation)

A first dry-run attempt stopped because the new output directory did not exist;
only that new ignored directory was created, then the dry run succeeded. No
vendor build target ran. The expanded recipe contains ten first-party compiles
and a link with 286 inert object/archive operands, all present in the old build.
No device/flash/OTA/UF2 utility was invoked, including for help.

Exact recipe expansion, from repository root, using session variables `REPO=$PWD`,
`WORK=$REPO/.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH`,
`SDK=$REPO/.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3`,
`TC=$REPO/.local-tools/toolchains/arc_gnu_ei_prebuilt_minimal_elf32_le_linux_install/bin`:

```sh
mkdir -p "$WORK/arc"
env -u MAKEFLAGS -u MFLAGS -u GNUMAKEFLAGS -u MAKEFILES PATH="$TC:$PATH" SOURCE_DATE_EPOCH=1794355200 LC_ALL=C TZ=UTC make -n -C "$SDK" -f makefile -f "$REPO/firmware/himax_arc/birdhouse/build/birdhouse_overlay.mk" APP_TYPE=edge_impulse_visionai LIB_BSP_PREBUILT=1 OUT_DIR_ROOT="$WORK/arc" BH_REPO="$REPO" BH_OBJ="$WORK/arc/birdhouse" all > "$WORK/arc-dryrun.log" 2>&1
```

The reviewed command lists are private `arc-reviewed-plan.json` in WORK, derived
with `shlex.split` from that log. They select only the ten first-party C++ lines
and single ELF link, replacing compiler names with absolute existing ARC compiler
paths. Response-file and generated-include operands point to the read-only old
validated build's `embARC_generated`; its gcc.arg contains only the nine reviewed
`-m...` core flags. The linker script is that build's unchanged linker_gnu.ldf,
with no INCLUDE/INPUT/GROUP directives. Every non-Birdhouse object/archive path is
mapped to its existing baseline-build operand (or original SDK archive); none is
copied or rebuilt. New first-party objects and dependency/stack files remain in
WORK/arc/birdhouse. The new ELF output is explicitly named
`birdhouse_pdm_quarantine_OFFLINE_ONLY_NOT_FOR_FLASH.elf`.

All 286 link operands were audited as inert data. Compiler includes/defines,
core ABI flags, standard C++11 mode and three existing linker wraps are retained.
No plugin/wrapper/specs execution option or host-build define is present. The
underlying assembler/linker and standard libraries belong to the existing ARC
compiler. Every selected source and reused input has a private pre-execution
fingerprint; output and dependency paths are constrained to the new root. The
complete command arrays are frozen before execution, not reconstructed during
it. This is an incremental relink of cached vendor objects, **not a clean SDK
rebuild**, a packaged candidate, or a physical qualification artifact.

Exact foreground replay (reviewed here before execution):

```sh
"$BH_PYTHON" -I -B - <<'PY'
from pathlib import Path
import hashlib, json, os, subprocess
work = Path('.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH')
plan = json.loads((work / 'arc-reviewed-plan.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in plan['inputs'].items())
env = dict(os.environ, SOURCE_DATE_EPOCH='1794355200', LC_ALL='C', TZ='UTC')
with (work / 'arc-compile-link.log').open('x') as log:
    for args in plan['commands']:
        Path(args[args.index('-o')+1]).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(args, cwd=plan['cwd'], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in plan['inputs'].items())
print('10 first-party ARC compiles and incremental link completed; reused inputs unchanged')
PY
```

The ten cross-compiles succeeded. The first link could not open its map output:
the incremental replay had created the ELF parent but omitted the separate map
parent. No input was changed. One existing SDK `ei_fusion` missing-config `#warning`
was emitted through the ARC glue include; no first-party warning was emitted.
Correction: create the new map-output parent, then replay only the unchanged
reviewed link command, checking input fingerprints before and afterward:

```sh
"$BH_PYTHON" -I -B - <<'PY'
from pathlib import Path
import hashlib, json, os, subprocess
work = Path('.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH')
plan = json.loads((work / 'arc-reviewed-plan.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in plan['inputs'].items())
args = plan['commands'][-1]
map_path = next(a.split('-Map=',1)[1] for a in args if '-Map=' in a)
Path(map_path).parent.mkdir(parents=True, exist_ok=True)
with (work / 'arc-link-retry.log').open('x') as log:
    result = subprocess.run(args, cwd=plan['cwd'], env=dict(os.environ, SOURCE_DATE_EPOCH='1794355200', LC_ALL='C', TZ='UTC'), stdout=log, stderr=subprocess.STDOUT, timeout=60)
assert result.returncode == 0, 'ARC link failed; inspect private log'
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in plan['inputs'].items())
print('Reviewed incremental ARC link PASS; reused inputs unchanged')
PY
```

## Final results

| Native suite | Assertions, ordinary | Assertions, ASan + UBSan | Result |
|---|---:|---:|---|
| Diagnostics | 71 | 71 | PASS |
| Capture | 281 | 281 | PASS |
| Original adapter regression | 95 | 95 | PASS |
| New adversarial lifecycle model | 969 | 969 | PASS, model only |
| Runtime/inference integration | 466 | 466 | PASS |
| Actual host console parser/server | 35 | 35 | PASS |
| Stored preprocessing reference | 21 | 21 | PASS, all 9,960 feature values covered |
| Model inference reference | 586 | 586 | PASS, 28 reference outputs |
| **Total** | **2,524** | **2,524** | **5,048 assertions** |

Four focused Python unittest methods passed after the missing-parser-operand
repair. Seven compiled implementation/model mutants exited 1 with failed
assertions; compilation failure never counted as rejection. Four static evidence
mutants were rejected. All 16 original frozen PDM observations plus nine focused
call-path/order checks passed; these include confirmation of unresolved hazards.
The final native run completed in about 49 seconds. No ASan/UBSan error was seen;
no leak, race-detector, physical latency or hardware-continuity claim is made.
A final wording-only test-case rename labels application starvation accurately;
it changes no assertion, model or implementation behavior.

ARC: ten first-party sources compiled, incremental cached-vendor link passed.
The exact existing post-link analyzer was reviewed as file-only and run as:

```sh
"$BH_PYTHON" -I -B tools/himax/postlink_audit.py --elf "$WORK/arc/birdhouse_pdm_quarantine_OFFLINE_ONLY_NOT_FOR_FLASH.elf" --ldscript "$REPO/.local-tools/port-himax/bh-codex-validated/bh-candidate/obj_socket_24/gnu_arcem9d_wei_r16/linker_gnu.ldf" --toolchain-bin "$TC" --manifest firmware/himax_arc/birdhouse/model_manifest.json --stack-usage-root "$WORK/arc/birdhouse" --stack-usage-root "$REPO/.local-tools/port-himax/bh-codex-validated/bh-candidate/obj_socket_24/gnu_arcem9d_wei_r16" --json-out "$WORK/postlink.json"
```

**28/28 post-link checks PASS.** Independent ARC nm/objdump inspection confirms
no `bh_port_pdm_test_reset` or fake-driver symbol in the ELF, and real INT8 MLI
fully-connected code is retained. Disassembly of the new stop shows exactly two
stores between IRQ save and restore: null owner and state 2. Vendor stop follows
restore, and there is no success-path store reopening state 0. Re-running the
16 original PDM observations against the *new* ELF also passes: vendor re-arm
still precedes application delivery and completion acknowledgment still follows
RX return. Stop/reset/pending and unbounded-open hazards therefore still exist.

| Resource | Used/capacity |
|---|---:|
| ICCM1 | 301,306 / 327,680 bytes |
| SYSTEM0 | 849,204 / 1,439,744 bytes |
| DCCM | 76,960 / 253,952 bytes |
| Heap capacity | 176,992 bytes |
| Linker stack extent | 8,188 bytes |
| Partial known inference frame sum | 1,664 bytes; neither peak nor bound |

New local-only ELF: 1,650,872 bytes, SHA-256
`bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af`.
It is unexecuted and unpackageable for this mission; no image/UF2 was produced.
Memory fit is static capacity, not measured free memory or stack safety. Model
bytes match the unchanged manifest. Host references do not execute ARC MLI.

The original validated ELF, image and UF2 still match the three R0/prior hashes.
The SDK working tree remains clean at `9dc2370d4dc269dc4bcafcf0354b8f745d08801f`.
All reused ARC/native inputs were verified unchanged. Model weights and
preprocessing sources/constants have no diff against the requested baseline;
reference regeneration and broad full rebuilds were unnecessary. No vendor
files, launchers, makefiles, signing assets or previous candidates were edited.
