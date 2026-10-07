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
