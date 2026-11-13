# Birdhouse V1 — first-flash offline artifact preparation
OWNER-AUTHORIZED INTERACTIVE OFFLINE FIRST-FLASH PREPARATION MISSION — 2026-11-13

## 0. Purpose, scope and firm separation
User selected Path B: a deliberately risk-accepted, controlled FIRST firmware experiment on the sole Grove Vision AI V1 board, using Windows 10. The owner is prepared to consider hardware loss and pursue recovery if needed. Your job NOW is to produce the exact CURRENT P1-mitigated firmware as a well-validated local UF2, a minimal Windows operator kit, and an evidence-based READY_FOR_HUMAN_RISK_DECISION or BLOCKED verdict. The user has NOT authorized this Codex session to flash, attach to, reset, recover, or update hardware. Never copy files to GROVEAI or give an unattended script to do so. Keep ALL board operations to a later, deliberately reviewed OWNER action on Windows after verified file identity. A later owner approval must specify the chosen SHA-256 and step-by-step write operation. Do not manufacture safety claims.

LIVE INTERACTIVE Codex CLI session only, not headless exec or a background worker. Owner should be able to follow/interrupt. Continue independently through safe offline work without routine questions. No autonomous use of Windows or other computer.

PUBLIC repo AliAmini93/birdhouse-tinyml-kd. Branch research/birdhouse-v1-first-flash-prep-20261113, forked from exact P1-mitigated code commit 3d0fb3fd4c1889d79462bbc404aee722c1811894. The prior validated images, earlier research branches and factory files are immutable. Do not merge main or edit unrelated projects.

The Grove board must stay on a separate Windows 10 machine throughout this Ubuntu phase. No USB/serial/I2C/drive or /dev, /sys, udevadm, lsusb, flash, bootloader entry, BOOT/RESET, mounted-volume writes, driver/service/power changes, installer or sudo. Do not even perform board-discovery probes. Do not download/execute unreviewed recovery tools. Package only into an ignored, local, non-device path. Do not copy a candidate into a device mount. If any necessary step cannot be isolated from hardware, STOP as BLOCKED.

Python for all research and tooling ONLY via "/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3", exposed as BH_PYTHON, quoted; use -I -B when the import mode supports it. No bare python or python3, pip/uv/conda/venv, and no system changes. Existing installed g++, make, ARC toolchain and bubblewrap may be used, after command preflight.

## 1. Ground truth: do not accidentally package old candidate
- Source baseline P1 patch: 3d0fb3fd4c1889d79462bbc404aee722c1811894. Full repository HEAD after this launcher is baseline plus new mission/launcher/README only; verify that firmware sources are unchanged relative to that exact source SHA.
- Prior corrected ARC ELF is INCREMENTAL, private and NOT FOR FLASH:
  .local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH/arc/birdhouse_pdm_quarantine_OFFLINE_ONLY_NOT_FOR_FLASH.elf
  expected SHA-256 bc49e1610fcff768b2f8aef36a42f17f928e20227494c29de3a6c0e3a34c09af. This is a lineage/reference artifact, not automatically a release candidate.
- Earlier OLD validated deploy-file SHA-256 009799e1ca3b39fa9f3fcee9ce97dd6f5d93a3bedf383b2172bfa873c21600ae is PRE-P1 and must NOT be misidentified as the new candidate.
- Read first: docs/research/birdhouse_v1_pdm_safety_20261113/{FINAL_GO_NO_GO,P1_ISR_STOP_RACE_REMEDIATION,P4_BOOT_ISR_POLLING_DECISION,OFFLINE_TEST_AND_BUILD_MATRIX}.md and results/summary.json.
- Read prior docs/research/birdhouse_v1_windows_uf2_write_audit_20261113/{FINAL_GO_NO_GO,RECOVERY_AND_ROLLBACK_GATES,WINDOWS10_FIRST_WRITE_DRAFT,UF2_WRITE_MECHANISM_AUDIT}.md.
- Read firmware/himax_arc/birdhouse/build/birdhouse_overlay.mk, tools/himax/{sdk_make.sh,package_offline.py,uf2_tool.py,postlink_audit.py,verify_tflm_ops.py}, and precise build sections of tools/himax/run_offline_checks.py. The latter checks /proc/mounts, and has older hardcoded result/candidate paths: DO NOT run its broad default workflow or blindly overwrite older outputs.
- Factory official grove_ai_v02-00.uf2 expected SHA-256 8854e09348cec166c127e3bafda89b0b35e3a7a62916e27661410ff03f4b5b3c; cached local-only. Check digest before use.
- Board USB bridge reports installed TinyUF2 2d5b48b (Aug 2022). Windows GROVEAI READ stability is owner-reported and does NOT prove WRITE10 or durable flash verification.
- Existing source workaround P1 is permanent first-party one-attempt quarantine; real pending DMA and stop quiescence unproven. P4 unbounded PDM ready poll at boot/ISR remains VENDOR_LEVEL_BLOCKED. Model self-test and synthetic pipeline were validated on host; real ARC MLI, microphone, timing and stack are NOT physically validated.

## 2. Concrete execution plan (avoid redundant open-ended research)
A. Before running anything, write a short explicit safe-command plan to new report. Verify Git branch, exact source lineage, SDK clean and pinned to 9dc2370d4dc269dc4bcafcf0354b8f745d08801f, available fixed Python/ARC toolchain, existing factory and old candidate fingerprints, no board attached to Ubuntu by OWNER physical confirmation (do not enumerate devices). Preserve previously validated outputs. Inspect every requested tool invocation and choose a NEW ignored work root:
  .local-tools/port-himax/first-flash-prep-20261113-OFFLINE_ONLY/
  Never overwrite or remove old files. If partially populated from a previous failed attempt, choose a new numbered root and preserve failed artifacts.

B. Run the focused source/host regression suite already validated in the P1 phase, preferably the exact static-first test with mutations at tools/himax/tests/test_pdm_safety.py, and check hashes of source/model/preprocessing. Capture summary without copying raw logs to Git. If runtime suite cannot run within sandbox for an environmental reason, record BLOCKED; do not fake PASS.

C. Build a FRESH clean ARC ELF out-of-tree from the P1-mitigated source. Prefer the existing allowlisted tools/himax/sdk_make.sh with a unique output root, after reviewing that the target and all dependencies are compile/link only (no make flash, OTA, UF2, device enumeration). Fix only build/protocol bugs that are necessary and evidenced; no silent source changes. Do NOT recycle the old pre-P1 ELF or merely rename the previously linked ELF to declare a fresh build. Record original diff, clean SDK state, full build log in ignored storage. On a clean-build failure, STOP and report honestly. Reconfirm model operator overlay and all link-time wraps; run postlink_audit.py and verify_tflm_ops.py with output paths in ignored workspace. Strongly compare relevant first-party code/linkage with the P1 incremental ELF and expected P1 source SHA. Check resource/stack limits and whether tests are absent in production ELF.

D. Package the NEW clean ELF into image and UF2 using the already audited tools/himax/package_offline.py. This script executes a vendor image generator ONLY inside its own bubblewrap sandbox; do not weaken the sandbox or run the generator on the host if nested sandbox fails. Inspect and test its exact new-output-root/no-device constraints, signatures, and outcome BEFORE invoking; source path/toolchain must be pinned and local. This explicit offline execution is permitted for packaging; absolutely no vendor uploader or board tool. Require a clean PASS from the packager including deterministic twice-generated image, section/ELF bytes reconstruction, model payload identity, UF2 headers/family/addresses/block counts/numbering and loader-region matching against pinned factory. Independently cross-check UF2 structure and image via tools/himax/uf2_tool.py. Treat unchanged loader bytes as package parity, not physical write skip.

E. Establish an exact artifact manifest: SHA-256 of source tree/git commit, ELF, image, UF2 and official factory fallback; byte lengths, block counts, family 0xef32c892, addresses, app sections, loader/config comparisons and tail difference. Verify fresh UF2 hash NOT EQUAL to old pre-P1 candidate hash. Name release artifact distinctly such as birdhouse_v1_pdm_quarantine_FIRST_FLASH_REVIEW_ONLY_<SHORT_SHA>.uf2 and leave it in ignored PRIVATE local output; do not rely on a name alone. Do not push binary, ELF, image or vendor files into PUBLIC GitHub. Double-read hash from physical on-disk file. Report whether the first build reproduced the P1 source and whether packaged image can boot is still UNKNOWN. If packaging fails, do NOT copy/edit a prior UF2 and claim success.

F. Write a WINDOWS 10 operator kit AS TEXT ONLY (never a script that writes to GROVEAI):
- Pre-copy method from Ubuntu artifact to Windows normal internal folder or trusted storage that is NOT the GROVEAI volume, with verification of SHA-256 and size on Windows using Get-FileHash. The existing board on Windows must not be contacted at this stage. Avoid uploading proprietary firmware binaries to GitHub or cloud.
- Decision table: direct P1-mitigated Birdhouse flash as one first write versus factory rehearsal followed by Birdhouse as two writes. Treat both as potentially destructive; factory rehearsal is NOT a harmless transport test and adds a write. Recommend based on explicitly named trade-offs, not an invented risk probability.
- Exact target board/product/family identification with no invented COM/drive letter, power, cable, stable Windows environment, known old installed BL702 build, no simultaneous console/driver updater/app clients.
- A finite, human-observable one-time manual Windows Explorer UF2 transfer plan with hash check beforehand, explicit separate owner approval gate for exact digest, stop conditions for copy failure, hang, unexpected disappearance, no boot, and conservative no-cascade recovery. Distinguish successful host transfer from verified Himax program and application boot. No arbitrary universal safe timeout or reset/replug on apparent stall.
- Initial post-boot observation and AT+ self-test/synthetic probes ONLY if a verified safe console-open/DTR/mode-control contract exists and future owner explicitly authorizes it. For real microphone use exactly ONE attempt. Do not assume repeated sampling, auto-restart, or physical quiescence; P4 could hang. Never execute those steps now.
- A fallback decision tree with exact official factory SHA-256, but label it as another risky full write and NOT a guaranteed recovery. BL702 upgrade, WEI erase, BLDevCube and ROM-I2C remain outside first-flash plan.
- A one-page owner decision record indicating potential permanent loss of this sole board, possible loss of installed settings/calibration and no qualified independent backup/recovery. Do NOT pre-check approval fields or interpret choice of Path B as full approval for a specific not-yet-built hash.

G. Stop with a meaningful verdict: ARTIFACT_READY_FOR_OWNER_RISK_DECISION only after ALL offline code/artifact criteria pass; otherwise BLOCKED with exact cause. Even if artifact ready, G1/G2/G3/G4/P4 hardware/recovery uncertainties remain OPEN. Never use FLASH_SAFE, RECOVERY_GUARANTEED or claim physical GO.

## 3. Reports and synchronization
Write only sanitized files under docs/research/birdhouse_v1_first_flash_prep_20261113:
1. BUILD_AND_SOURCE_PROVENANCE.md
2. FIRMWARE_UF2_VALIDATION.md
3. WINDOWS10_SINGLE_FLASH_OPERATOR_PLAN.md
4. OWNER_RISK_ACCEPTANCE_RECORD.md
5. FINAL_ARTIFACT_DECISION.md
6. results/summary.json
Do not embed full machine path, private serial, credentials, raw host/USB logs, proprietary binaries/source, unique device IDs, raw audio or personal data. This is a PUBLIC repository. Raw commands/logs and all binaries remain ignored locally under .local-tools/ only.
If a safety bug requires modifying first-party code or the packaging verifier, stop and document precise proposed patch instead of silently changing the source/verification standard for this release candidate. Build must remain pinned to source commit 3d0fb3f.

Check output integrity with independent parser, JSON, report links, SHA consistency and privacy review. Commit only those six sanitized reports to the dedicated branch. Normal push only (no force, reset, clean, rebase, branch switch or main merge), verify local HEAD equals remote GitHub HEAD and worktree clean. Previous Codex sessions had .git metadata read-only inside sandbox: if so, DO NOT modify permissions or ask for escalation; leave sanitized reports uncommitted and explicitly give a precise ordinary Ubuntu terminal add/commit/push recipe, including re-hash of local artifact and review of staged reports. No invisible sync claims.

Final response in PERSIAN with: ARTIFACT_READY_FOR_OWNER_RISK_DECISION / BLOCKED; exact local UF2 location (private, not GitHub), digest, size and source commit; tests and build results; physical uncertainties; whether one or two Windows writes are proposed and WHY; the next exact HUMAN authorization step, not a device command now. Preserve live interactive Codex TUI for owner follow-up.
