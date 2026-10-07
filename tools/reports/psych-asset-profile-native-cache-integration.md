# Psych asset-profile foundation and native test cache

Development checkpoint: v0.0.17, 7 October 2026. Phase 2 remains incomplete.

## Source contract and limits

`PsychAssetProfile` parses ordered Project asset declarations, inherited conditions,
renames and filters from a receipt-bound retained root. It preserves unknown flags
instead of deriving them from the target label or host. Compiler-only haxedefs
remain opaque; disabled sections do not evaluate nested conditions. Repeated
source declarations retain distinct destinations. The language walker rechecks
each emitted file against the snapshot receipt and leaves collision policy to
the importing caller.

The focused matrix models the pinned Psych declaration slice. Native tests also
use the actual pinned Project.xml and Portuguese translation bytes, capture and
verify a real snapshot, and resolve its mappings in C++ on Windows. They check
unknown conditions, repeated mappings, retained-file tampering and unchanged
donor bytes. The native namespace is a test input, not a claim that an actual
ImportRefreshManager record supplied it.

No importer is wired to this foundation yet. Actual manager-record handoff,
source build-context capture, shared publication through both importer routes,
revision migration, all-assets enumeration, variable expansion and included
Project files remain open. The current Psych import revision stays 3 because
publication behavior has not changed. Global packs still have their separate
non-snapshot-backed v1 receipt. This checkpoint does not complete source asset
parity or imported menus.

## Compilation reuse

The Windows filesystem and refresh-manager checks share a persistent native
fixture builder. Keys include generated code, engine/library/compiler/runtime
inputs, sysroot content, patch state and effective compile environment. The
builder compiles captured engine-source bytes that must match the key. Ready
entries publish atomically under a process lock and validate executable hashes
on reuse. Behavior checks still execute the real C++ binary. No game assets are
scanned and no rendering, media or chart content is reduced.

Mechanics coverage includes cross-process contention, interrupted/malformed
entries, executable tampering, build failure, source capture and directory
junction containment. Three symlink cases require privileges unavailable on this
Windows account; the junction cases pass without them. Hashing all engine Haxe
sources deliberately invalidates on unrelated engine edits too; selective
compiler dependency tracking is not claimed.

## Evidence

- Windows build: `tmp/v17-profile-foundation-build.log`.
- Focused profile tests: 5 tests passed.
- Cache mechanics: 12 tests, 3 privilege skips, zero failures;
  `tmp/v17-native-cache-mechanics-final.log`.
- Final native input build: 8 tests passed in 103.876 seconds;
  `tmp/v17-native-current.log`.
- A separate process reused the identical executable/key and passed 35 tests in
  59.646 seconds, with one existing skip, including the full handoff scenario;
  `tmp/v17-native-reuse.log`.
- Process receipts: `tmp/v17-native-cache-profile-results.json`.
- Captured and current profile source SHA-256 both equal
  `5f4ff0750274c708f817c475bbd3b441eec0e4031115ba49b1d472a2afb33214`.
- Full-suite log: `tmp/v17-profile-foundation-full-tests.log`; final results and
  protected-input checks belong in `tmp/v17-profile-foundation-checkpoint.json`.

The earlier 144.311-second native run predates the source-capture cache guard and
is retained as diagnostic evidence, not the accepted cache implementation.
The first full suite reported 2,445 tests/804 modules in 558.0 seconds, with
346 skips and two failures: the shader literal had been changed by whitespace
cleanup, and the development guides still displayed the preceding version.
The donor shader text was restored, the version tool now synchronizes both
guides, and all 29 focused checks passed. The corrected Windows build passed.
A subsequent full run completed in 343.6 seconds with the same counts and one
remaining Windows Haxe eval timeout in receiptless import recovery. Windows
manager fixtures are moving to the real C++ target with all assertions retained;
the final accepted gate is still required.
Cold and warm groups execute different test sets, so their times are not a
whole-suite speedup comparison. They prove the later process avoided compilation.

All production changes are engine-level. Donor/mod/chart inputs remain immutable;
no v0.0.17 release is authorized or published by this checkpoint.

## Final integration gate

The final Windows build and full suite passed: 2,464 tests/807 modules in 283.7
seconds, 345 platform/corpus skips, zero failures. All Windows refresh-manager
and registry reconciliation cases now run through the shared C++ fixture.
Cache mechanics include four deterministic bounded Windows rename retry cases;
16 tests run, with three symlink-privilege skips. Permanent and unrelated errors
still propagate, and invalid executables are never accepted as a cache hit.

The same checkpoint fixes stale Freeplay generations, scoped recovery knowledge,
retained package labels, gameplay import scheduling and Unicode registry
baselines. Muted generated import/Freeplay checks passed at 60/unlimited FPS with
four reviewed captures. The required donor audit, text policy and 70 protected
inputs passed. Evidence: `tmp/v17-profile-foundation-checkpoint.json` and
`tools/reports/freeplay-import-availability.md`.

The profile remains an unwired foundation. Authentic manager handoff, recorded
build context, mapped asset publication and revision migration are the next
package; Phase 2 and later roadmap phases remain incomplete.

## Retained profile handoff integration

The subsequent development checkpoint binds freshly resolved profiles after
whole-snapshot verification and exact root/engine checks. Explicit source build
contexts persist by snapshot and relative root; changed snapshots do not inherit
old context. Derived profiles are rebuilt rather than trusted from the record.
Psych and Nightmare Vision share mapped traversal; the Psych language consumer
filters before hashing unrelated media and plans before copying. Regular and
global-pack imports use the same language publisher. Psych revision 4 schedules
older receipts for retained-source refresh.

Native C++ checks passed 7 filesystem/staged-IO tests, 46 manager tests and 3
shared profile tests. Manager/publisher tests cover donor removal, rebuilt
metadata, Unicode context, local-edit conflicts, ambiguity and cancellation.
The game build and 2,490-test suite passed (808 modules, 233.8 seconds, 345 skips,
zero failures). Muted lifecycle checks passed at 60/unlimited FPS. The donor
audit, text policy and 70 protected inputs passed. Evidence is recorded in
`tmp/v17-profile-handoff-checkpoint.json`.

Other mapped asset publication, complete source build input capture, included
Projects and variable expansion remain open. Phase 2 is still incomplete.

## Project-input integration

Parser version 2 resolves receipt-bound local includes, ordered values, captured
command context and asset metadata. The shared context helper has differential
tests executing the pinned Lime methods for interpolation and conditions.
Unresolved or invalid required inputs preserve managed outputs; absent Projects
retain legacy behavior, and optional absent includes follow `noerror`.

The Windows build and full suite passed: 2,520 tests across 809 modules in 231.6
seconds, 345 skips, zero failures. Actual C++ checks passed 5 profile tests and
50 manager tests, including source hashes, Unicode values, namespace isolation,
retained refresh after source deletion, conflicts and parser pause/cancellation
without foreground blocking. The donor audit, text policy and all 70 protected
inputs passed. Evidence: `tmp/v17-project-inputs-checkpoint.json`.

The production changes are shared engine/importer behavior. Full Phase 2 parity,
mapped media/other assets, external/Haxelib includes, bundles, Project object
reflection and automatic complete build-input capture remain unfinished.
