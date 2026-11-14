# Publication receipt

2026-11-14. **PAYLOAD PUBLICATION VERIFIED.**

| Check | Observed result |
|---|---|
| Repository / branch | `AliAmini93/birdhouse-tinyml-kd` / `research/birdhouse-v1-first-flash-prep-20261113` |
| Payload commit | `0030d091c81331941ed1c967e9c36abd063872de` |
| Parent | `5a94940fcce5708ff686c7aaa18ae5606ee035c6` |
| Normal push | PASS, fast-forward on the existing branch only |
| Actual remote read | `git ls-remote origin refs/heads/research/birdhouse-v1-first-flash-prep-20261113` returned the payload commit |
| Local HEAD at that check | Equal to the payload commit |
| Worktree at that check | `git status --porcelain` empty; no unrelated changes remained |
| GitHub visibility | Recursive GitHub commit tree was not truncated; all 32 intended publication paths and all 98 source-inventory paths matched local Git blob identities (116 distinct files) |
| Source provenance | All 98 committed files match build-time SHA-256/size inventory `796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e` |
| Artifact preservation | Existing UF2 / image / ELF hashes match the exact forensic artifact; no rebuild or firmware modification |
| Privacy / content | Reviewed text only; vendor SDK, firmware binaries, maps, raw logs/recordings and device identifiers excluded |

The [manifest](PUBLICATION_MANIFEST.json) identifies the entire publication set.
The 28 initially pending source/report files were preserved byte for byte and
published together, replacing stale staged report snapshots with their reviewed
working-tree contents. Historical UNCOMMITTED/BLOCKED statements in the earlier
dated reports describe those earlier sessions; they do not undo this publication.

The original EROFS blocker was the sandbox's read-only `.git` mount view. Through
the owner's requested normal tool-approval path, host `findmnt` showed writable
ext4 for both the repository and Git metadata. Ordinary approved Git add, commit,
push and remote-read operations succeeded. No permissions, mounts, OS settings,
Git metadata layout or protection were changed; no sudo or alternate Git/index
location was used.

This receipt is a subsequent documentation-only commit. It intentionally records
the verified payload SHA rather than attempting to contain its own commit SHA.
The final session verification must repeat local HEAD versus actual `git
ls-remote`, empty worktree and GitHub blob visibility **after** committing and
pushing this receipt. The final response supplies that final matching SHA and
may say SYNC_OK only after those checks pass.

Exact diagnostic UF2 SHA-256:
`0eb316e68ba5b88c407d9f2f907891bab722820077e40de8d93f167d746f9cf8`;
**1,260,032 bytes / 2,461 blocks**. The firmware source commit is the payload
commit above, reproducing the previously built baseline-plus-diagnostic source;
the receipt changes no firmware byte. Existing build/package results remain
archived evidence, not tests rerun in this publication task.

**No hardware operation occurred or is authorized.** The
[deployment decision](FINAL_AT_BL702_DECISION.md) recommends retaining the current
BL702 and considering one direct Birdhouse write only after separate exact-hash,
step-by-step owner risk acceptance. Git publication does not approve flashing,
console opening, UART attachment, reset or microphone capture.
