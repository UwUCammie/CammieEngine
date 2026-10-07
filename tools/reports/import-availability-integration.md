# Import availability and NV family foundation, 0.0.16 development

The importer publishes a revisioned owner snapshot for queued work, active
imports, interrupted recovery and committed packages awaiting the main-thread
handoff. Freeplay and the imported-package picker share its readiness rule.
Source-plan rows are temporary and gray; their identifiers never become chart
paths, score identities or favorite records. Completion replaces them with the
published registry rows, preserving the selected Imported category.

Back hides a manual import while its worker and report continue. Unrelated
finished packages remain playable. Exact transaction outputs, recorded runtime
dependencies and authorized NV family roots protect related packages. Startup
inspection rebuilds these relationships before releasing the inspection gate.
Receipt-backed readiness is published atomically after the complete inspection
and recovery pass. Older receipts recover explicit dependency roots from their
receipt-listed compatibility manifests, with bounded reads and digest checks;
incomplete provenance keeps the affected package unavailable.
Committed roots are kept separate from temporary locks, and cyclic dependency
handoffs drain after the actual publications complete. Failed handoffs remain
pending with diagnostics; failed or cancelled transactions unlock only after
safe recovery. Runtime cache invalidation waits for a safe menu state.

The staged importer uses a thread-local owner identity index, so its reads and
invalidation cannot replace the live thread's index. Availability snapshots are
copies; menus clone them only when the revision changes. Publication and
recovery retain existing digest, local-edit and ownership checks.

The shared progress renderer has a Freeplay lane that leaves the FPS corner and
score column clear. Package headings stay stable, conversion has an explicit
indeterminate phase, and elapsed time precedes the phase ETA and queue count.
The importer still uses one embedded card. No authored content was changed.

## Verification

- Windows build: `tmp/import-availability-build-final.log`.
- Manager/cache/lifecycle focused checks: 49 tests, one existing skip, 25.459s.
- Final manager, row, navigation, category and progress checks:
  `tmp/import-availability-final-focused.log`, 42 tests, one existing skip,
  22.711s. Final elapsed/queue layout checks passed separately.
- Final manager checks covered atomic inspection and legacy dependency receipts:
  32 tests with one existing skip. Workflow/runtime handoff checks covered 39
  tests with one existing skip. The import smoke state waits for the actual
  safe handoff before switching states; the standalone smoke-state compilation
  fixture was updated to include that completion flag (39 tests, seven skips).
- Actual muted native workers and transactions at 60/unlimited FPS:
  `tmp/import-availability-native-60-final.log` and
  `tmp/import-availability-native-unlimited-final.log`.
  A generated B donor was held before conversion while A had committed and
  completed its handoff. The actual Freeplay B row was gray and rejected;
  the common confirmation route launched A into PlayState and its gameplay song
  clock advanced. After releasing B, its placeholder disappeared, its chart
  became playable and the Imported category remained selected. Four captures
  were reviewed, including the progress lane and removal after completion.
  These are component checks, not a large-library speed benchmark.
- The same final executable passed two NV family selection/resource teardown
  visits each at 60/unlimited FPS, with four reviewed red/blue asset captures:
  `tmp/import-availability-family-native-60-final.log` and
  `tmp/import-availability-family-native-unlimited-final.log`.
- Final full suite: 2,359 tests across 769 modules in 151.5 seconds, 344 existing
  platform/corpus skips, zero failures. The Windows native filesystem module
  passed, including actual compiled import and recovery fixtures.
- Required donor audit passed; Psych and NV tracked source trees remain clean.
  All 70 protected inputs matched their original hashes.
- Generated availability installations were removed after archiving and
  verifying captures, logs and receipt metadata in
  `tmp/import-availability-native-evidence/`. This removed about 3.05 GB of
  private copied test files without changing authored inputs.
- Final runtime hashes are in `tmp/nv-package-family-runtime.json`.
  Combined regression, audit and protected-input results are recorded in
  `tmp/import-availability-checkpoint.json`.

## Remaining scope

The family catalog/session/path work is a bounded Phase 2 foundation. It does
not enroll sibling directories from a singleton receipt, implement all source
ModOptions/window/font/UI configuration effects, supply the source TitleState
factory or establish full menu transitions. Current retained NV example
receipts do not authorize the paired roots needed for clean Feaster reset
acceptance. Source CORE_DIRECTORY/profile and complete session lifecycle
semantics remain open; see the two NV package-family reports and
`tmp/nv-package-family-next-proposal.md`.

Large refresh latency and candidate reconciliation still need measured
profiling. The current placeholder deduplication compares pending candidates
with existing rows on revision changes; future indexing must avoid eager
whole-library disk reads. Actual imports keep their complete retained sources,
including applicable executable/package metadata. Queue handoffs remain
deferred during gameplay. No release was published.
