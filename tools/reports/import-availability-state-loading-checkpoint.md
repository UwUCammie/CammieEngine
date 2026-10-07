# Import availability and source script loading, 0.0.16 development

Checkpoint date: 7 October 2026.

The requested import/reimport availability behavior is already implemented by
the shared owner-readiness snapshot and Freeplay gate. Pending songs remain
visible in gray and cannot launch. Unrelated fully imported mods remain playable
while background work continues. Publication plus the safe runtime handoff
replaces provisional rows with actual charts. Refreshes use the same gate;
affected dependencies and shared outputs stay reserved until they are safe.
The roadmap now states this requirement explicitly.

The related NV state work now uses the existing captured `FunkinScript.fromFile`
implementation rather than another parser/executor. Typed results distinguish
missing files, existing path entries, failed handles and successful loads. State
scripts check exact source paths but use their selected names; substates skip
that check and use their resolved paths as names. The caller explicitly selects
state semantics, since a substate can set `scriptPrefix='states'`. Top-level code
sees the current `FlxG.state`; the wrapper reparents its group before `onLoad`.
Failed handles are destroyed by their owning wrapper without conflating parse
failure with an absent script.

## Verification

- Final Windows build: `tmp/import-availability-state-load-final-build.log`.
- Full suite: 2,387 tests across 782 modules in 242.4 seconds using eight workers,
  with 343 existing skips and zero failures:
  `tmp/import-availability-state-load-final-full-tests.log`. The preceding
  four-worker run passed the same counts in 354.9 seconds. These are iteration
  measurements, not gameplay or large-library import benchmarks.
- Related availability/manager/navigation/state checks: 45 tests, one existing
  skip. Final source-loader/bootstrap/highscore/policy checks: 30 tests passed.
  The extracted loader runs actual Iris modules and exercises the writable
  substate-prefix edge, naming, parenting and failed-handle ownership.
- Final native availability checks: generated fixtures `076c7818` at 60 FPS and
  `34455390` uncapped. The actual import workers, transaction publication,
  Freeplay rows, confirmation and gameplay clock execute with a minimal fixture
  converter. A remains playable while B waits, B is gray and rejected, and B
  becomes playable after completion without losing the Imported category.
  Saves are isolated and sound muted. Captures and receipt metadata are archived
  under `tmp/import-availability-native-evidence/`.
- Final native NV checks: `nv-state-60-933cae7f` and
  `nv-state-unlimited-537eff8b`, in the isolated source-attachment installation.
  Constructor, redirect, reset, transition completion and departure checks pass.
  These are generated source-state component checks, not acceptance of stock
  menus or the complete retained-import-to-menu pipeline.
- Required donor audit: `tmp/import-availability-state-load-api-audit.json`.
  The Psych and NV tracked donor trees remain clean.
- Hashes, protected-input checks and complete results are recorded in
  `tmp/import-availability-state-loading-checkpoint.json`.

An immediate second native run initially encountered a transient Windows lock
while redundantly copying an identical executable. The private runner now
verifies its hash and reuses matching files; the retry passed. No game behavior,
test case, timeout or source safeguard was weakened.

The source Init sequence and owner-local NV Highscore service have bounded
contract implementations and tests. Their runtime bootstrap/save integration
remains pending, as does the real retained-import-to-state fixture prepared in
`tmp/nv-retained-state-native-20261006-234350-f80b0e53`. Phase 2 stays open.
No authored content, graphics quality or release publication changed here.
