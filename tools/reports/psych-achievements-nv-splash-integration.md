# Psych achievements and native NV Splash checkpoint

Development version: 0.0.16. Date: 7 October 2026.

This checkpoint extends Phase 2. It does not complete the compatibility gate
or authorize a release. Changes are confined to engine, compatibility,
importer verification and tooling; authored mod/chart inputs are preserved.

## Shared implementation

Psych Lua, plain HScript, embedded HScript and native-class reflection now
reach one achievement service per authenticated imported owner. The service
keeps live maps, fractional counters, threshold unlocks, source callback
defaults, sound throttling and private save data. Same-owner state changes
retain the service; leaving the owner retires its popups and captured handles.
Multiple authorized providers have independent services.

Popup rendering uses source dimensions, fonts, pixel/fallback icons, stacking
and wall-clock animation. Each popup borrows an icon with an explicit graphic
use-count lease, so normal scene bitmap-cache clearing cannot dispose a live
popup's image. Retirement releases that lease, copied bitmaps and listeners.
As in the pinned donor, the popup's supplied end callback is not invoked.

The existing owner-save backend has an opt-in deferred-write policy.
Achievements use it to preserve source explicit flush boundaries. Existing
owner-save callers retain their default behavior. No separate achievement
storage backend or second Lua implementation was introduced.

The source contract is Psych 1.0.4, revision
`5c67ced49e5a98535298a6daa3f8f4ec79ac8399`, particularly
`source/backend/Achievements.hx` and `source/objects/AchievementPopup.hx`.
See the achievement service, popup and runtime contract reports in this folder.

## Native verification

The final Windows build is recorded in
`tmp/psych-achievements-splash-build-gate.json` and
`tmp/psych-achievements-splash-integrated-build-2.log`.
Executable SHA-256:
`E1029C8E3AC90E8C9D92210C89F9F11F613CC386E23BB9408108B4FC0A45C5D0`.
Lime SHA-256:
`43D4C415F21106B2DDB2EB569560399E74594355BE3A52774CD47B8D6D27098C`.

Two muted Psych runs, at configured 60 and unlimited FPS, first import a
generated package through the real importer. The probe derives its owner from
the registered song and compatibility receipt. Actual Iris HScript, translated
Lua and native-class reflection share fractional score changes and unlocks.
An instrumented native save verifies deferred writes and explicit flushes.
The checks cover same-owner reuse, pixel/fallback popup rendering, stacking,
bitmap-cache clearing, natural expiry, real state-switch cleanup, rejection
of a released captured method, and private-save reload.

Receipts:
`tmp/psych-achievements-native-run-60-89d711f2c5d6.json` and
`tmp/psych-achievements-native-run-unlimited-a7cbd2d516d1.json`.
Both popup captures were inspected. This is native component/API verification,
not a claim that all source gameplay achievement awards or menus are ported.

Eight muted retained-import-to-Init NV runs verify the existing source Splash
port at both configured caps. The cases are branding, actual decoded intro
video, keyboard skip, and cancellation while the branding tween is active.
Checks require visible logo/video output, resource disposal, audio/autopause
restoration and no additional startup during a 1.2-second retirement window,
then complete the existing source-state/reset/title/settings-cleanup pipeline.
The eight Splash captures were inspected. The video fixture copies the real
4.334-second source intro without modifying it; it cannot fall back to branding.
Exact runs, timing and receipts are in
`tmp/psych-achievements-splash-native-cases.json`.
These are bounded startup/lifecycle checks, not stock-menu visual acceptance.

## Import availability regression

Pending imports/reimports remain visible in gray and unavailable until their
owning package commits and completes its safe runtime handoff. Fully imported,
unaffected mods remain playable while other workers continue. This already
verified engine rule is documented in `import-availability-integration.md`.

This checkpoint adds the exact two-owner overlap to the native C++ filesystem
fixture: owner A becomes ready while owner B's refresh worker is active, then
both publish their new songs and drain their handoffs. The full native
filesystem module passed six tests in 42.1 seconds. No chart-specific readiness
conditions, shortened waits or skipped overlap checks were introduced.

## Validation record

The related 21-test group passed. The API inventory now follows only helper
registrations reachable from the donor's Lua constructor and traces the real
engine achievement binding chains; its mutation checks reject disconnected
routes. Static exposure and behavioral acceptance remain separate statuses.

The first full run recorded 2,417 tests across 797 modules, 343 skips and one
Windows Haxe eval timeout in the refresh-overlap module while native checks
were also running. That module passed independently: 33 tests, one existing
skip, 48.243 seconds. The exact overlap also passed in native C++, as above.
The failed log is retained at `tmp/psych-achievements-splash-full-tests.log`.
CPU contention is a plausible contributor, not a proven root cause.

The final idle full suite passed 2,418 tests across 797 modules in 464.3 seconds,
with 343 existing skips and zero failures. All 70 protected inputs and 20
read-only fixture inputs matched their original hashes; both tracked donor
trees remained clean. The text policy and `git diff --check` passed.
Results and source hashes are recorded in
`tmp/psych-achievements-splash-checkpoint.json`. The authoritative suite log is
`tmp/psych-achievements-splash-full-tests-idle.log`.

## Remaining work

- Achievement integration currently supplies the authenticated package's base
  `data/achievements.json`. Full enabled-Psych-Mods ordering and identity are
  still open; arbitrary folder discovery would not establish that contract.
- Language context and popup localization remain open. Source phrase fallbacks
  are used. Donor official-build feature flags and base-achievement profiles
  still need explicit owner profile resolution.
- Source gameplay award checks, achievement galleries and full menu flows are
  not certified by the native component probe.
- Full NV application-host construction remains explicitly unsupported.
  Remaining source API destinations, imported entry through I and stock-menu
  visuals still need acceptance. The preceding Main checkpoint's Splash gap
  is closed only for the bounded cases recorded here.
- The audit still reports four missing Psych Lua callbacks, plus broader NV
  missing/unverified surfaces. Large-library refresh speed needs measured
  profiling. Later library/freeplay/performance roadmap gates remain open.

Continue Phase 2 from these gaps. No release was published.
