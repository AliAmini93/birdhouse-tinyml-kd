# Offline deployment-barrier assessment evidence

Starting HEAD: `1095349f459d974975e606d243c84d26635f67bf`; correct research
branch and clean worktree confirmed before work. No firmware or vendor inputs
were edited. No physical device access or internet research was performed.

## Milestone: independent barrier assessment

- **PASS:** exact candidate disassembly and switch-table decoding; 16 PDM static
  observations, including open stop/re-arm and unbounded-ready-poll hazards.
- **PASS:** six cached recovery-asset checks and eight pinned first-loader
  call-order checks. This is documentation/static evidence only.
- **PASS:** ten targeted offline tests. Negative controls cover inserted global
  IRQ enable, unknown calls, wrong switch tables, altered loader receive/ACK/
  erase/error-branch sites, malformed checklists and forbidden actions.
- **BLOCKED:** demonstrated Grove-specific recovery, installed image readback,
  host-isolation prerequisites and all physical timing/IRQ/numerical evidence.
- **NO-GO:** firmware writes and active hardware diagnostics. Observer-only
  session is proposed for independent review; its checklist remains NO-GO.

Executed from the repository root using only the mandated existing HCI
interpreter (represented here by `BH_PYTHON`, with private machine paths omitted):

```sh
"$BH_PYTHON" -m unittest discover -s tools/himax/tests -p test_deployment_barriers.py -v
"$BH_PYTHON" tools/himax/audit_deployment_barriers.py --observer-plan docs/research/birdhouse_v1_deployment_barriers_20261111/OBSERVER_PLAN.json --out /tmp/bh_barrier_audit_reviewed.json
```

The second command returned static PASS and hardware NO-GO. Its public-safe JSON
was copied to [results/barrier_audit.json](results/barrier_audit.json). Temporary
analysis wrappers/disassembly are local-only; vendor code is not included.
Reproduction must use a fresh output filename. The test command is repeated only
after changes to the new analyzer/tests; prior completed validation suites are
not repeated.

The analyzer invokes the existing ARC `objdump` on the exact candidate ELF. It
also uses existing `objcopy` to wrap the pinned first-loader payload for
disassembly in a temporary directory. Neither ELF is executed. DOCX content is
read as local ZIP/XML; embedded diagrams were inspected locally. Vendor tools,
including `ota.exe` and `uf2conv.py`, were read as files only, never run/imported.

SDK checkout: `9dc2370d4dc269dc4bcafcf0354b8f745d08801f`, clean. Hash and source
scope checks confirm the previously validated candidate is unchanged; no build
or packaging was necessary. The previous implementation report remains evidence
for that candidate, subject to the sharper limits in this assessment.

Publication is restricted to the new first-party analyzer/test, assessment,
protocol, manual checklist and redacted JSON summaries. No vendor files, images,
SDK/toolchain copies, raw logs, device identifiers, credentials, audio or datasets
are staged. Branch/whitelist, full staged diff and whitespace checks are reviewed
before commit. Publication synchronization is verified with `git ls-remote`
after push; local commit alone never means synchronized.
