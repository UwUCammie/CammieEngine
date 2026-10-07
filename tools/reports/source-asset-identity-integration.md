# Shared Psych and Nightmare Vision asset identities

Development v0.0.17 now publishes source Lime identities alongside supported
raw owner assets. One receipt-verified walk supplies language, media and
identity policies; copying an identical source/destination pair once does not
discard its other logical IDs. The effective key is exact `(library, id)`.
Later declarations win within that key, matching the pinned Lime manifest
maps. Source formats and a bounded HXP-compatible text/binary probe determine
Lime types independently of renamed output extensions. The reviewed probe is
from upstream HXP 1.3.1 `src/hxp/System.hx`, SHA256
`57fb2bfee3f1a474b1cf771713c4534327bef80e3becfa8624d7f12a1ddefa8d`.
The checkout does not establish its external HXP version; this is source
comparison evidence, not a verified local HXP pin. Boundary tests preserve
upstream's EOF-before-BOM behavior for short UTF-16 prefixes.

Each supported engine/scope has a separate staged sidecar below the owner's
`.cammie-asset-identities` directory. Source-owned files cannot replace these
generated indexes. Generic raw-copy fallbacks suppress explicitly claimed
source/destination paths, while structured registry and script/chart conversion
retain their existing paths. Metadata uses the shared `ImportGeneratedOutput`
writer and participates in ordinary ownership, local-edit and transaction
checks. Psych/NV import revision 7 regenerates prior imports from retained
sources; the Project profile parser is version 3.

Runtime acquisition verifies the index hash and every entry's path/hash against
the already inspected committed manifest and exact source-profile identity.
The generation/availability-epoch cache avoids fetching the manifest file list
on each getter. No large asset payload is rehashed during lookup. Psych's
Lime/OpenFL facades and Nightmare Vision's asset adapter share this resolver;
physical paths retain their existing semantics. Declared identity spaces cannot
silently borrow another owner's or a same-named host library's assets.

Bare Lime `<library>` configuration tags are captured but do not themselves
claim runtime AssetLibrary namespaces. The runtime catalog follows actual asset
partitions plus the implicit default library. Unsupported generated library or
bundle inputs remain explicit gaps.

Modern Psych `Paths.sound`, `music`, `soundRandom`, `returnSound`, `inst` and
`voices` now return decoded `Sound` objects. The shared disk decoder and an
owner cache preserve object reuse; source language translation and optional
argument semantics remain intact. Compiled lookup uses Psych's raw default-
library IDs, while host library-prefixed paths remain permitted legacy
fallbacks. Host playback/precache retains Sound identity, tags, volume and loop
flags, and owner retirement drops retained references without disposing active
playback buffers.

## Native evidence

`tmp/v17-asset-identities-build-integrated.log` records the final Windows build.
Fresh generated private Psych/NV imports passed at 60 and unlimited FPS:

- `tmp/v17-asset-identities-native-60-bom.log`
- `tmp/v17-asset-identities-native-unlimited-bom.log`
- `tmp/asset-identities-native-60.json`
- `tmp/asset-identities-native-unlimited.json`

Both checks verify 20 raw output hashes, qualified aliases, typed existence and
list results, duplicate-ID precedence, TEXT/BINARY getters, distinct owner/core
paths, and absence of a runtime library from a bare configuration tag. Actual
OpenFL/NV image decoding preserves exact colors/transparency; Sparrow atlases
retain both frames. Audio/font decoding and native shader rendering pass. Both
captures were reviewed. Video validation covers byte identity and path lookup,
not playback; these are not heavy-chart performance measurements.

The initial native check exposed the obsolete alias-defer guard and missing
text/binary inference. Its logs remain at
`tmp/v17-asset-identities-native-60.log`; the corrected source was rebuilt and
fresh donors were imported for the successful runs. Initial compile errors in
the opt-in probe were repaired before those runs.

Final suite, protected-input and source/binary evidence is recorded in
`tmp/v17-asset-identities-checkpoint.json`.

The integrated suite passed 2,572 tests across 816 modules in 245.5 seconds,
with 344 platform/corpus skips and zero failures. It includes current Windows
C++ import-manager and native profile cases. Three drift fixtures initially
injected changes on a cancellation poll that now occurs earlier; they now use
the explicit post-preflight publication progress boundary and retain their
local-edit/previous-manifest assertions. The failed run remains at
`tmp/v17-asset-identities-full-tests-integration-first.log`.

The same build passed the Freeplay follow-up at 60 and unlimited FPS, including
direct gameplay return while a refresh is pending and live row unlocking after
handoff. Receipt inspection, registry reconciliation and disposable backup
cleanup now honor the shared gameplay pause gate; journaled publication and
rollback still finish safely. See `tools/reports/freeplay-import-availability.md`.
All 70 protected inputs and the engine text policy passed.

## Remaining Phase 2 work

This does not certify full AssetLibrary preload state, bundle/template outputs,
dynamic library registration, class bindings or MovieClip construction. Owner
facades reject those unsupported mutations/constructions instead of changing a
same-named global library. Authenticated mapped assets across sibling/core
receiver owners, complete external/Haxelib build-input capture, Project object
reflection and remaining scripting APIs also remain open. No authored chart/mod
files were edited, and this checkpoint does not publish a release.
