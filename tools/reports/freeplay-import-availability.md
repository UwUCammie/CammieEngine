# Freeplay import availability

Freeplay uses the import manager's revisioned availability snapshot to gate
song rows by owner, publication state, transaction outputs, and supported chart
files. Manager-known owners stay unavailable while queued, active, recovering,
or awaiting main-thread handoff. Unrelated committed owners remain playable.
Unmanaged legacy imports retain their provenance and chart-file fallback after
the manager finishes receipt inspection.

Rows discovered by the import plan appear as provisional, gray Freeplay rows
with an importing reason. Their opaque row identifiers are ephemeral and are
never used as chart paths, favorites, scores, or launch identifiers. Pending
rows are deduplicated against installed rows only by exact owner plus an
authoritative destination folder or source folder. On case-sensitive targets,
path identity preserves case; Windows comparisons are case-insensitive.
Pending rows are included in All, Imported, and explicitly scoped package
Freeplay lists. A refresh-triggered Freeplay rebuild selects the current
registry category again, including reconstructing All's aggregate song list;
explicit owner-scoped selection still takes precedence.

Selection confirmation, HXC capsule dispatch, preview playback, random choice,
and both native launch routes check the current availability and selected chart.
Missing charts stay unavailable. A selected provisional row cannot open chart
metadata; if it disappears, Freeplay refreshes the surviving selection or
returns through the existing empty-list route.

In Import Settings, Back hides an active manual import screen while manager-
owned worker, report, and handoff work continues. Cancel requests a safe stop.
Back on a scan still requests cancellation and waits for its safe completion.
Automatic refresh no longer prevents Back navigation from Import Settings;
manual import actions remain paused while it runs.

Focused verification passed:

- `python -m unittest test_freeplay_song_availability test_freeplay_chart_availability`
- `python -m unittest test_import_refresh_notification_lifecycle.ImportRefreshNotificationLifecycleTest.test_actual_import_settings_wraps_full_refresh_warnings_without_scan test_import_refresh_notification_lifecycle.ImportRefreshNotificationLifecycleTest.test_back_leaves_while_automatic_work_continues`
- `git diff --check` for the Freeplay, Import Settings, and focused test files

These tests include Haxe interpreter fixtures for the pure owner/chart
availability rules and Import Settings navigation behavior. No full app build,
full test suite, or native Freeplay interaction probe was run here. Those remain
with the root integration owner.


## Post-update stale-row repair

A static `FreeplayState.currentSongList` now records the import generation that
selected it. A later Freeplay entry rebuilds the list from the current registry
when a refresh published a newer generation. Category screens retain their
snapshot while open; automatic handoff waits until the next safe menu state, so
Freeplay receives the generation change and rebuilds after entry.

When a lazily materialized row has a blank source label or the legacy generic
container form, Freeplay reads its exact chart receipt. An inferred generic
label is replaced only after destination, independently resolved owner, and
supported engine validation. A stale title suffix is removed only when it
matches that validated generic label exactly. Other explicit package labels and
titles without that exact suffix stay unchanged.

Known incomplete compatibility metadata remains scoped to its owning import and
touched paths. Returning to Freeplay requests a fresh receipt pass when the
manager is idle; a non-empty authoritative pass can clear repaired scoped state.
An empty receipt directory or failed pass preserves the last authoritative
committed and scoped view, while unknown ownerless recovery still gates globally.

Focused verification passed:

- `python -m unittest test_freeplay_source_display test_freeplay_song_availability` (5 tests)
- Four individual `ImportRefreshManagerTest` Haxe eval cases: failed-inspection retention, authoritative scoped recheck plus empty-scan retention, deferred CategoryState handoff, and incomplete legacy compatibility metadata ownership
- `git diff --check` on the affected Freeplay, manager, and focused test files

No full suite, application build, or native Freeplay interaction probe was run
by this focused pass. The retained CategoryState snapshot remains unchanged
until that state is exited; the manager defers runtime handoff there.

## Gameplay work scheduling

`Main` holds an import-work lease while gameplay or chart loading owns the
foreground. Snapshot workers pause at scan, file and hash-chunk boundaries;
conversion uses the existing shared yield checkpoints. Publication waits before
writing its journal. Once publication starts, only its owning worker is exempt
from the pause so it can commit or roll back safely. Unrelated workers remain
paused. Returning to a menu releases the lease and resumes the same work.

No foreground state transition waits for a worker. Cancellation can wake paused
workers, and the progress clock excludes gameplay pauses from phase rates, ETA
and activity age. The opt-in NV state probe verifies snapshots with one worker
because its synchronous game-thread call must not wait for a paused child pool.

The native availability fixture now finishes one owner, keeps another pending,
plays the ready owner, releases the pending worker during gameplay and checks
that it cannot commit. It then finishes the handoff in Main Menu and re-enters
Freeplay with the stale non-empty static list still present. No manual song-list
clear hides the generation check. Its generated legacy generic labels also
exercise the actual receipt-backed subtitle and title repair.

## Registry Unicode preservation

Windows native tests exposed surrogate splitting in both existing JSON printers.
`UnicodeSafeJson` shares one string quoting implementation with TJSON-compatible
engine writes and standard-JSON manifest writes. TJSON parsing, traversal,
class hooks and references remain available to the engine serializer; persisted
manifest metadata retains standard JSON semantics. Fixing the manifest write
also preserves original registry baselines across later refreshes.

Native tests retain the original end-to-end Unicode assertion and cover literal
and escaped astral keys/values in JSON and JSONC, unchanged text and local-edit
conflicts. All production changes remain generic engine/importer behavior.

## Integrated development checkpoint

The final Windows build passed (`tmp/v17-import-session-build-final.log`). The
full suite passed 2,464 tests across 807 modules in 283.7 seconds, with 345
platform/corpus skips and zero failures (`tmp/v17-import-session-full-tests-complete.log`).
Windows manager and registry cases execute the actual C++ fixture; scratch-copy
fixtures include the real scheduler, cancellation and engine identity helpers.

Muted native availability checks passed at 60 and unlimited FPS in 8.828 and
7.434 seconds respectively. Both verified gameplay pause, menu handoff with a
stale non-empty list, corrected legacy labels, ready-row launch and absence of a
provisional duplicate. Four pending/completed captures were reviewed. The final
private installs are `C:/t/cammie-av-6a52b342` and `C:/t/cammie-av-b513755d`.
These generated checks certify the import lifecycle, not whole-chart fidelity or
a measured performance improvement on a heavy authored chart.

The later staged-IO integration adds cooperative checks inside 64 KiB copy and
prewrite hash loops, with the manager's cancellation callback. The actual
Windows C++ fixture verifies pause/resume, cancellation while paused and idle,
foreground progress, and byte-identical completed copies. The rebuilt game
passed the generated lifecycle check again at 60 and unlimited FPS in 8.743 and
7.683 seconds. Its private installs are `C:/t/cammie-av-91ed638a` and
`C:/t/cammie-av-677c435a`; completed rows unlock after menu handoff without a
process restart. Both representative captures were reviewed.

The integrated suite passed 2,490 tests across 808 modules in 233.8 seconds,
with 345 skips and zero failures. Evidence:
`tmp/v17-profile-handoff-checkpoint.json`. These timings do not establish a
heavy-chart performance benchmark.

All 70 protected inputs and the text policy passed. Earlier native serializer
failures, scratch-fixture omissions, the interrupted suite, and the transient
Windows cache rename failure remain recorded in the checkpoint receipt. Source
asset-profile integration and the broader roadmap remain open.

Evidence: `tmp/v17-profile-foundation-checkpoint.json`. This is development
v0.0.17; no release is published by this checkpoint.

## Direct gameplay return and receipt-work follow-up

Freeplay's snapshot revision and rendered revision remain separate, so reading
new readiness for a launch check cannot consume its pending row redraw. A
registry generation change may automatically recreate Freeplay; no application
restart is required. The native fixture now also refreshes an installed owner,
returns directly from gameplay while its worker is held, verifies its row stays
gray, releases the worker and checks that the resulting row is white, playable
and has no provisional duplicate. The original MainMenu handoff and same-state
interaction redraw checks remain covered.

Receipt inspection, committed manifest validation, legacy dependency metadata,
registry reconciliation and recovery metadata now cooperate with the shared
gameplay scheduler at safe boundaries. Asset-index proofs and detached copies
are built outside the manager mutex. Receiptless rollback waits before it
starts, then completes its journaled restoration without pausing halfway.
Publication releases its uninterrupted token after the valid commit receipt;
disposable backup deletion can then pause between files. Staging deletion also
retains its existing pause behavior. Foreground calls remain nonblocking.

Muted native checks passed at 60 and unlimited FPS with the same current Windows
binary, in 12.681 and 12.394 seconds. Their logs are
`tmp/v17-availability-integrated-60.log` and
`tmp/v17-availability-integrated-unlimited.log`; private installs are
`C:/t/cammie-av-5869bb7a` and `C:/t/cammie-av-50fac3c6`. Both required the new
`import_availability_direct_return_pending` and
`import_availability_direct_return_complete` events. All four pending/complete
captures were reviewed.

These are lifecycle and worker scheduling checks, not a measured improvement
on an authored heavy chart. An already publishing or restoring transaction may
finish after gameplay begins, and an individual metadata parse remains one
in-flight work unit. No chart/mod-specific behavior or authored files changed.
Integrated suite and protected-input evidence is recorded with the current
asset identity package in `tmp/v17-asset-identities-checkpoint.json`.
