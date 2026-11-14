# Final AT / BL702 deployment decision

2026-11-14. **ARTIFACT_READY_FOR_OWNER_RISK_DECISION; no hardware action authorized.**
Recommend option A: retain the current BL702 and, only after separate exact-file
owner approval, perform one direct diagnostic Birdhouse write. Do not add a
BL702 update or factory rehearsal on the strength of factory AT silence alone.

## Evidence and its limits

| Finding | Evidence class | Practical consequence |
|---|---|---|
| Exact Birdhouse console is UART1, requested 921600, 8N1, hardware flow off | VERIFIED offline ELF/image/UF2 correspondence in the [forensic audit](../birdhouse_v1_console_forensic_20261114/FORENSIC_CONSOLE_AUDIT.md) | Use that configuration for a separately approved future Birdhouse console check; generic factory baud examples do not override it. |
| COM6 is the BL702 USB interface on the owner's Windows system | OWNER-SUPPLIED Windows diagnostic finding; not remeasured in Ubuntu | A COM port establishes bridge enumeration, not Himax startup, UART routing or an AT Server. COM numbers can change. |
| Installed factory application may lack a compatible AT Server | INFERRED possibility; installed application identity is unknown | An absent AT reply is not a demonstrated BL702 fault. No repeat baud testing is proposed. |
| Seeed's 2023 firmware release introduced AT Server support | VERIFIED official [v2.0.0 release notes](https://github.com/Seeed-Studio/Seeed_Arduino_GroveAI/releases/tag/v2.0.0), published 2023-08-02 in existing asset metadata | AT support is application/version dependent. This does not prove which application is installed or require a factory update before Birdhouse. |
| Seeed documented BL702 compatibility fixes | VERIFIED [V1 documentation](https://wiki.seeedstudio.com/Grove-Vision-AI-Module/) describes recognition fixes for Mac/Linux | It does not prove an installed-bridge incompatibility with this Windows 10 / Birdhouse console combination. |
| Current bridge is owner-reported 2022 TinyUF2 build `2d5b48b` | Existing audit plus owner context; exact installed binary/source unavailable | CDC line-coding application, DTR/RTS effects and mode/flash routing remain UNKNOWN. No specific incompatibility or required update has been established. |

The supplied Windows findings are carried as owner evidence. This session did
not reopen COM6, inspect devices, test baud rates or acquire new Windows logs.
No private device identifiers or raw serial evidence is reproduced here.

The exact existing diagnostic artifact is private:
`.local-tools/port-himax/pdm-quiescence-diagnostic-20261113-OFFLINE_ONLY/package-native-terminal-01/out/birdhouse_candidate_OFFLINE_ONLY_do_not_deploy.uf2`

SHA-256: `0eb316e68ba5b88c407d9f2f907891bab722820077e40de8d93f167d746f9cf8`.
Size: **1,260,032 bytes**, **2,461 blocks**, family **0xef32c892**.
Its ELF is **1,667,964 bytes**, SHA-256
`3e350b171ed79ae9cdc96d635475b9f6de921288adbc29aab34905d96db41eee`.
The source is baseline `3d0fb3fd4c1889d79462bbc404aee722c1811894` plus the
reviewed diagnostic patch. All 98 build-time source identities match inventory
SHA-256 `796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e`;
SDK `9dc2370d4dc269dc4bcafcf0354b8f745d08801f` remains clean. No firmware was
rebuilt or modified for publication. The [publication manifest](PUBLICATION_MANIFEST.json)
records source and publication-file identities; the final Git commit identifies
the committed version of this previously pending patch.

## Decision matrix

| Option | What is known | Unresolved risk | What can actually be learned | Extra write justified? |
|---|---|---|---|---|
| **A. Direct Birdhouse, retain current BL702** | The exact package passes offline checks; its AT Server and conditional BIRDINFO registration are linked. No bridge-specific defect has been proved. | Unqualified physical update/boot; bridge line coding and DTR/RTS behavior; P4 may prevent AT initialization; sole-board loss and no qualified independent recovery. | Successful Birdhouse information exchange would establish the observed application/bridge/Windows path. A later separately authorized single capture can provide sampled DMA evidence. Silence does not isolate the cause. | **Recommended conditional choice:** one intended Himax UF2 write; zero preliminary bridge/factory writes. It directly tests the owner's experiment with fewer write operations, without claiming lower quantified failure probability. |
| **B. Update BL702 first** | Official newer bridge firmware exists; documentation describes compatibility fixes. This changes a second chip. | Exact rollback to installed build unavailable; bridge update can lose the existing USB/update path. It does not add AT support to an old Himax application. Multiple changes complicate attribution. | Can test behavior of the new bridge after its own separately approved qualification; cannot retrospectively prove the old bridge was faulty. Birdhouse deployment would still be another write. | **Not justified now:** adds a BL702 flash before the intended Himax write without evidence of a matching defect. Reconsider only after bridge-specific evidence and a separate recovery/risk decision. |
| **C. Independent physical UART diagnosis first** | Independent observation could separate Himax electrical TX activity from the USB path without changing firmware. | Correct pins, voltage levels, grounding, active mux and measurement loading must be established. Attachment is a new physical operation; TX injection can contend with the bridge. No current AT Server is guaranteed. | A separately designed passive observation can measure existing TX activity and bit timing. Current-app silence or lack of AT still cannot establish how the uninstalled Birdhouse image will boot, nor qualify UF2 writing. | **No preliminary firmware write required.** A reasonable alternative if preservation or fault isolation takes priority over the first experiment; optional, not a mandatory proof gate for A. No attachment/probe is authorized here. |

Option C would require a separate electrical measurement plan and owner approval;
this document supplies neither an attachment instruction nor a physical UART
pin/voltage contract. Option B is not a recovery shortcut following an ambiguous
result. A factory rehearsal followed by Birdhouse likewise adds a full write
and is not recommended for this objective.

## One recommended sequence, with separate authorization boundaries

1. **Preparation:** publish the reviewed first-party source, tests, protocols and
   sanitized reports on the existing research branch. Verify the final commit
   using `git ls-remote`, a clean worktree and GitHub file visibility. Preserve
   the existing private artifact and its verified identity; generate no new one.
2. **Host-file preparation:** transfer this exact UF2 to an ordinary internal
   Windows folder or trusted non-board storage. Verify its full SHA-256 and size
   with host-file `Get-FileHash` / `Get-Item` checks. This does not contact the
   board and is not permission to copy onto GROVEAI. Keep binaries off GitHub/cloud.
3. **Owner decision:** approve or decline **one direct diagnostic UF2 write,
   retaining the installed BL702**. An approval must name the full digest and
   size above, physical V1 target, and reviewed step-by-step manual Windows
   Explorer/mode-entry/stop procedure. Explicitly accept possible permanent loss
   of the sole board and installed state, unqualified backup/recovery, unknown
   updater behavior and P4. Preparation or Git publication cannot supply this approval.
4. **Only after that future approval:** the owner may perform exactly that one
   manual operation using the reviewed
   [Windows write plan](../birdhouse_v1_first_flash_prep_20261113/WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md).
   Its old missing-artifact blocker is superseded by the exact validated UF2
   above; its physical precautions and separate approval boundaries remain.
   No preliminary BL702 update, factory rehearsal or automatic fallback is included.
5. **Separate console scope after outcome review:** the owner may explicitly
   accept the unresolved bridge open/control-line risks, document the selected
   terminal's DTR/RTS behavior, and authorize one manual open at 921600/8N1/no
   flow followed by one CR-terminated `AT+BIRDINFO?`. The owner's identified
   COM6 is historical context, not a command to open it now. Require actual
   Birdhouse output; bridge enumeration or host-copy completion is insufficient.
   Silence, garbling, disconnect or hang means stop new actions and review;
   do not cascade into baud sweeps, reconnect/reset, factory or bridge updates.
6. **Only after separate microphone authorization:** use the
   [single-capture diagnostic protocol](../birdhouse_v1_pdm_quiescence_diagnostic_20261113/WINDOWS10_SINGLE_CAPTURE_PROTOCOL.md)
   for one arm and at most one capture. Its missing-artifact statement is
   historical; the console-contract uncertainty can be explicitly accepted as
   described above. P1 permanent quarantine stays active. A sampled PASS does
   not establish full DMA quiescence or race-free shutdown for all interleavings.

The earlier first-flash and diagnostic reports are preserved as dated records
of their own blocked sandbox packaging attempts. Later successful native-terminal
packaging and its exact bytes were verified by the forensic audit. Their old
UNCOMMITTED/BLOCKED statements are not the current publication or artifact
status; consult [publication and sync](PUBLICATION_AND_SYNC.md) and its receipt.

**Preparation is complete only to the extent recorded by that receipt. No flash,
console open, baud test, reset, UART attachment or recovery is authorized or
performed by this decision record.** G1/G2/G3/G4 and P4 remain open; physical boot,
real ARC MLI, timing/stack and complete DMA shutdown are not qualified.
