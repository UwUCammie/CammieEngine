# Nightmare Vision input and field lifecycle checkpoint

5 October 2026. Bounded Phase 2 implementation; full Psych/NV compatibility remains open. Subtasks used GPT-6 Luna with Max reasoning.

## Source and implementation

Pinned NV revision: `733165c42ca71eb0961a70e4173b2d81ba4a29ea`. Input contracts come from `source/funkin/input/Controls.hx`, `InputSystem.hx`, and `InputEvent.hx`; field/note contracts come from `source/funkin/objects/note/PlayField.hx`, `Note.hx`, and `StrumNote.hx`, plus the gameplay consumers in `PlayState.hx`.

Source Controls now uses real Flixel actions, preference bindings, custom action maps and device APIs. Source InputSystem uses OpenFL events, captured action/physical lookup lists, queued timestamps and source repeat/duplicate-binding rules. Its scene scope owns replacement systems/controls and hardware-hook teardown. Public InputSystem.destroy does not destroy Controls; owner release additionally clears event listeners, queues and captured references. Namespaced enum types avoid collisions with the native Controls module.

Exact imports and constructor factories resolve the selected owner. Bare and game controls/input access remain live; persistent scripts retain an owner key and scene resolver. The generic interpreter resolves script constructor identities before falling back to compiled classes, preserving local shadowing.

The gameplay host creates source input before onCreatePost and drains it once per host update, independently of the 60 Hz script callback batch. Input reaches the existing judgment path once. Press timing uses playing music time minus timestamped dispatch latency, with Conductor restored before post-input hooks and on exceptions. Psych retains its distinct polling contract.

Field collection attachment/removal, receptor generation/clear, skin changes, alpha/fade and note membership now have native hooks. Mutable IDs preserve note ownership and authored base coordinates. Field hit/miss signals invoke the native core once; ghost misses fan out through field signals. Receptor alpha separates target opacity from the field multiplier, so repeated writes do not compound. Field teardown preserves the native notes group as the owner of note resource cleanup.

All production changes are engine/compatibility rules. No mod/chart name selects behavior and no donor files were edited. Temporary native probe scripts were created only in the private fixture and removed afterward.

## Verification

- Canonical Windows build passed: `tmp/nv-input-fields-build-3.log`.
- Canonical `run.bat test` passed 2,196 tests across 701 modules in 134.8 seconds, 346 skipped, zero failed: `tmp/nv-input-fields-tests-final-2.log`. Skips do not certify unavailable donors.
- Earlier failures are retained: initial enum module collision, then 18 modules with outdated extracted-fixture dependencies/assertions. Those fixtures were repaired without removing their behavioral checks; the final suite includes the added membership/teardown check.
- Muted NV native runs passed at configured 60/unlimited FPS, two gameplay visits each. Checks exercised real stage keyboard delivery, 128 action checks, exactly 32 press/release callbacks, receptor clear/regeneration, alpha multiplication, native detach/re-add/clear, live note membership and ID changes. Field/membership checks repeated after re-entry. The keyboard probe completes on the first visit; this is not a second-visit keyboard certification.
- Unlimited NV input included 21 updates sharing a millisecond timestamp. Psych's separate unlimited input path also passed 128 checks and 32 press/release callbacks.
- Representative capped/unlimited NV and Psych framebuffer captures were inspected. They show notes/receptors and authored scene graphics; this is not an exhaustive pixel comparison or a performance benchmark.
- Private runs use isolated save roots and restore settings. Twenty-nine protected source/import/settings file hashes remained unchanged.

Native receipts: `tmp/nv-input-fields-native-60.log`, `tmp/nv-input-fields-native-unlimited.log`, `tmp/nv-input-fields-psych-regression.log`. Binary/source hashes and exact receipt paths are recorded in `tmp/nv-input-fields-checkpoint.json`.

## Remaining work

Quant receptor coloring/reload has an explicit unsupported diagnostic; imported ControlsSubState group reset, arbitrary script-created PlayField construction, wider-key layouts and broader modifier generation remain open. Physical controller/hotplug/axis operation was not exercised with hardware. Full paused/per-event timing, hold/release/return animation, all reflected Note members, complete source inventory and Phase 2 acceptance remain open. The bounded native probes do not certify all songs or full-song completion.
