# NV source startup integration, development 0.0.16

Status: integrated checkpoint verified. Phase 2 remains open.
Pinned Nightmare Vision donor: `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.

## Source contracts and shared implementation

The source `Init.create()` order now runs through a captured state session:
Controls, private ClientPrefs and Highscore loading, completed-week restoration,
antialiasing, shared Discord setup, Mods selection, Flixel services, source
plugins, permanent core music retention, base create and typed startup choice.
`Main.startMeta` and the source version constants use the same owner-scoped
class reflection layer as the other presets. The native host's FPS mode remains
authoritative, including unlimited rendering.

The source Highscore static methods and maps delegate to one private owner
service. Normal NV song completion saves through it alongside the host ledger.
A bounded migration reads registered rows with paired native best-score and
accuracy records before loading metadata or charts. It validates receipt,
family, difficulty and chart identity, preserves better private scores and
native maps, and restores borrowed difficulty state after failures.

Source backend plugins share the existing script host, Paths and reflection
foundation. Native settings, sound shortcuts, audio and borrowed host music
are captured for conditional restoration; source DebugText/Iris diagnostics
stay scoped to the owner. Destroyed startup states retire their tracking and
resources without discarding constructed states awaiting a switch.
The generic keyboard array retains its actual C++ container through raw field
reflection; typed array conversion would otherwise change its wrapper identity.
Restoration checks both the manager and installed container, preserving an
unrelated replacement.

The Splash adapter preserves source timing, branding and video callbacks with
explicit timer, tween and decoder cleanup. Its narrow contract tests exercise
the video branch. The retained native startup probe skips Splash, so actual
Splash decoding and visual parity remain unverified.

## Importer integration

Missing optional audio/music directories no longer reach the staged file
layer as empty paths. Package-root resolution uses the shared scanner's
authenticated NV container rule, including executable-only distributions,
plus a direct package `meta.json`. Scanned `content/<package>/assets` roots
retain their recorded namespaces while resolving package ownership correctly.
The refresh manager passes the snapshot root, rather than its content folder,
to family discovery, publication and namespace reuse.

NV importer revision 5 schedules regeneration from retained sources. The
manager regression verifies actual snapshot-to-catalog publication and reuse
of prior committed namespaces. Original donor content remains unchanged.

## Verification and remaining scope

Final Windows build and full regression verification pass. Earlier build, focused and native
failures are retained under `tmp/nv-bootstrap-*`; no failing case was skipped
or given a larger timeout. The initial integrated suite passed 2,400 tests
across 790 modules in 380.3 seconds, with 343 existing skips. That run preceded
the final family and startup teardown corrections and is not their exit gate.

The final suite passed 2,402 tests across 790 modules in 404.8 seconds, with
343 existing skips and zero failures (`tmp/nv-bootstrap-final-full-tests-verified.log`,
four workers). The preceding run found two extraction fixtures missing the new
importer helpers and one stale revision assertion; their corrected focused
run passed all 19 fixture/policy checks in 9.081 seconds. Its failures remain
in `tmp/nv-bootstrap-final-full-tests.log`. Four startup-retirement checks also
passed. The required donor audit is `tmp/nv-bootstrap-final-api-audit.json`;
both tracked donor trees remain clean. All 70 protected-input hashes match.

The final binary in `tmp/nv-bootstrap-final-runtime.json` passes the complete
generated retained-import-to-Init/state flow at 60 FPS and unlimited FPS:
`tmp/nv-bootstrap-raw-container-native-60.log` and
`tmp/nv-bootstrap-raw-container-native-unlimited.log`. The importer uses its
actual converter and transaction; the probe derives its roots from the verified
snapshot and committed catalog. Private-score bindings, startup class metadata,
captured state/substate constructors, redirects, two resets, missing-transition
fallback and native-setting restoration all pass. Four captures at 1280 by 720
were inspected. The component fixture intentionally omits the default window
icon; missing-icon warnings are recorded, not suppressed.

Accepted native receipts are `tmp/nv-retained-state-native-run-60-e5b5d7d7f7.json`
and `tmp/nv-retained-state-native-run-unlimited-7c87d5844d.json`. Logs, captures,
private saves, source receipts, committed manifests and generated packages are
archived under `tmp/nv-bootstrap-native-evidence/`. Earlier failures include a
private seed missing its asset-library manifest, the snapshot-root call defect,
companion-file selector mistakes in the probe and the generic C++ array
restoration defect. Each was corrected; none is counted as successful evidence.

The reusable native tools are `tools/prepare_nv_retained_state_fixture.ps1`
and `tools/run_nv_retained_state_native.ps1`. They require explicit private
runtime paths, verify source inputs and built binaries, use isolated muted
saves and retain import receipts, logs and captures. The probe distinguishes
registered playable outputs from retained companion copies.

This work does not wire the full imported-menu entry through I or replace
ordinary host Freeplay with a forced source title flow. Complete Main application-host,
Story/options menu contracts, full source API parity and stock-menu visual
acceptance remain open. Shared LibVLC initialization is process-scoped; source
video instances are retired, but the singleton has no owner lease. No chart,
mod, donor asset, quality setting or release publication changed here.
