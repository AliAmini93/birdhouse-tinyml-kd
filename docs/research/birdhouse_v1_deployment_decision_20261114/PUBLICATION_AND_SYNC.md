# Publication scope, Git blocker diagnosis and verification

2026-11-14. This record governs the combined publication of previously pending
first-party diagnostics/tests, first-flash protocols, diagnostic reports and
console forensic audit, plus the [final AT/BL702 decision](FINAL_AT_BL702_DECISION.md).
The [sync receipt](SYNC_RECEIPT.md) records the outcome; this document alone is
not a claim of successful publication.

## Exact read-only diagnosis

The existing branch is `research/birdhouse-v1-first-flash-prep-20261113`, starting
at `5a94940fcce5708ff686c7aaa18ae5606ee035c6`. The earlier
[publication snapshot](../birdhouse_v1_console_forensic_20261114/PUBLICATION.md)
correctly reported EROFS creating `.git/index.lock`, but did not distinguish
per-mount restrictions from the underlying filesystem's state.

Passive `stat`, `findmnt -T` and `/proc/self/mountinfo` inspection now establishes:

| Object | Permissions | Mount-view options | Filesystem / superblock options |
|---|---|---|---|
| Repository | directory mode 0775 | `rw,nosuid,nodev,relatime` | ext4 / `rw` |
| `.git` | directory mode 0775; index and HEAD mode 0664 | `ro,nosuid,nodev,relatime` | same ext4 / `rw` |

The separate read-only `.git` mount view matches this task's explicitly declared
sandbox read-only Git-metadata policy. The underlying superblock reports writable;
there is no evidence here of disk-wide read-only failure. Unix write mode bits
cannot override the read-only mount. The earlier error is consistent with this
sandbox restriction; its original process namespace cannot be retrospectively
inspected. No test lock file, permission change or remount is necessary.

The owner now explicitly authorizes an ordinary terminal/workspace approval path
for Git publication when the underlying filesystem is writable. Only the normal
tool approval mechanism may be used; no alternate Git directory, redirected
index, metadata deletion, chmod, sudo, mount operation or protection bypass is
part of this work. If the approved normal host view also reports the underlying
filesystem read-only, stop all publication attempts and leave the preserved files
for owner filesystem diagnosis. The safe manual action is inspection from an
ordinary Ubuntu terminal and resolution of the host/workspace access policy;
do not repair Git by removing metadata or changing permissions.

## Reviewed publication and artifact preservation

All 28 initially pending files and both staged/worktree patches were copied into
a new ignored private preservation root before publication work. No old report,
source, model, SDK or firmware artifact was edited. Earlier reports are retained
as chronological snapshots; their then-current blocked/package/publication
statements are superseded by this record and the later forensic findings.

The reviewed patch retains P1 permanent quarantine, original capture/ISR bodies,
vendor stop/reset order and memory ownership. The opt-in observer adds bounded
main-context status/buffer-change observations and a forwarding enable-event
wrapper. It adds no ISR printing, unrelated IRQ masking, capture retry or recovery.
The new host tests and mutation controls cover its functional contracts. Existing
test/build/postlink results were inspected; no firmware or host test was rebuilt
for this publication-only task.

All 98 source files still match their build-time inventory; its canonical digest
is `796a930d078b1bfa83a6c869d66a55a0df0571313c5948ff3b38d3138891084e`.
The exact UF2, image and ELF hashes were reread and match the forensic audit.
Archived checks remain postlink 28/28, operators 83/83, diagnostic postlink 14/14
and packaging 41/41 PASS. This does not create a new physical validation claim.

The [publication manifest](PUBLICATION_MANIFEST.json) lists every intended pending
source/report file with byte length, SHA-256 and Git blob identity, plus the full
98-file first-party source inventory. The manifest and mutable sync receipt do
not recursively hash themselves; their exact identities are supplied by the
commit tree. Existing repository base files and pinned SDK/tool requirements
remain part of reproduction; vendor internals and the installed bridge remain
outside the published first-party source.

No SDK/vendor file, firmware/ELF/UF2/image/map, raw log, raw recording, device ID,
credential or unrelated project change is eligible for staging. Ignored private
files remain private. The one-time exact UF2 name in documentation is an identity
reference, never a device write command.

## Required publication checks

1. Validate UTF-8 text, JSON, report links, privacy scan, source/artifact digests,
   whitespace, exact allowlist and staged content before commit.
2. Commit the reviewed payload on the existing branch with ordinary Git. No
   force push, branch replacement, reset, clean, rebase or main merge.
3. Push only `HEAD:refs/heads/research/birdhouse-v1-first-flash-prep-20261113`.
   Read the actual remote with `git ls-remote`; require its SHA equals local HEAD.
4. Inspect the GitHub commit tree and compare intended file blob identities,
   including the first-party source inventory. A local remote-tracking ref alone
   is insufficient.
5. Record the verified payload commit in the sync receipt, commit/push that
   receipt normally, and repeat local/remote/worktree/visibility checks. The
   receipt cannot contain its own commit SHA; the final session response supplies
   the final matching local and remote SHA.

Only all successful checks permit **SYNC_OK**. If approval or transport prevents
completion, the receipt must say BLOCKED and distinguish current equality of an
old HEAD from publication of this work. Git approval covers repository operations
only; no hardware or firmware generation is included.
