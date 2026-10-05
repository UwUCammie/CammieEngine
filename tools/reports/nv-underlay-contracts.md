# NV FIELD underlay checkpoint

Validated locally on 5 October 2026, after v0.0.13. Source: Nightmare Vision revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/objects/note/PlayField.hx` and `source/funkin/data/ClientPrefs.hx`. The root Windows build and canonical suite passed after the default-field attachment repair. The combined package gate passed 2,226 tests across 721 modules in 135.3 seconds, with 345 skips and zero failures.

## Implemented boundary

Each source field exposes its mutable `underlaySpr` and `underlayAlphaMult`. The constructor creates the donor's 1x1 white graphic tinted black, initially transparent, with the donor scroll-factor initialization. Replacing the public sprite leaves the displaced sprite alive; field destruction destroys only the currently assigned sprite and clears its reference.

Initial default banks register while display attachment is disabled. Enabling attachment now installs their underlay draw callbacks without moving existing banks or adding hold-cover groups before notes. Later collection additions still use normal display attachment. The FIELD route runs immediately before the field's native receptor bank draws. It measures existing visible receptors plus existing alive on-screen notes, including notes whose `visible` flag is false. Horizontal padding is 15 pixels. The selected bank camera provides viewport dimensions; opacity is `underlayOpacity * underlayAlphaMult * (1 - alpha) * (1 - dark)`, using the field's live `player` for modifier lookup. No manager means unmodified field opacity. SCREEN selection, nonpositive opacity, missing/dead sprites and absent owner preferences skip this FIELD route. Empty or nonfinite geometry skips drawing safely.

`UnderlayType` exposes donor string values `FIELD = 'Lane Underlay'` and `SCREEN = 'Screen Dim'`, with its qualified source import sharing the owner facade. `toArray()` returns a fresh ordered array each time.

The donor uses `camera.scrollAngle` for rotated viewport coverage. The installed host Flixel camera does not expose `scrollAngle`; the route uses host `camera.angle`. Focused checks cover that host rotation mapping, not independent donor scroll-angle versus display-angle behavior. Full camera parity remains open. SCREEN dim rendering is pending; its enum and FIELD exclusion are covered here.

## Validation

Six extracted/interpreted Haxe tests passed, with no skips, across five modules: `test_nv_field_underlay.py` (1), `test_nv_underlay_draw_route.py` (1), `test_nightmare_vision_source_bindings.py` (1), `test_nv_field_mutation_contract.py` (2), and `test_nv_multifield_routes.py` (1).

The new draw-route fixture executes production PlayState attachment/draw methods and the production Strumline draw method. It covers initial registration with attachment disabled, later draw-hook installation for both default banks with no state-member duplication/reordering, distinct captured field geometry, receptor-bank draw ordering, current geometry, camera fallback/replacement/rotation, live field-player modifier lookup, missing-manager alpha, preference/existence gates, public sprite replacement, and invalid/empty extent handling. The existing geometry/lifecycle fixture covers note/receptor filters, positive/negative/diagonal rotation, source alpha, initialization and repeated destruction. Binding coverage checks qualified import identity, enum string values, ordered fresh arrays and mutation isolation. Existing mutation/multifield checks continue to pass with the narrow sprite/color fixture stubs.

Muted private native runs passed at 60 FPS and unlimited FPS over two scene visits each. Both initialization/enum and geometry/alpha/gate/replacement markers occurred exactly twice in each run, with no native script failures. Each visit produced a visible-note framebuffer capture at song position 20,000 ms. The runner uses 45,000 ms visit duration because the authored intro consumes wall time before song position advances; the prior 25,000 ms / 20,000 ms capture combination timed out despite both script visits completing successfully.

Receipts: `tmp/nv-underlay-native-60-completed.log` records stem `psych-pass-darnell--nightmare-vision-54e1fc6dd6-9d982faa`, exit 0, 131.215 seconds. `tmp/nv-underlay-native-unlimited-completed.log` records stem `psych-pass-darnell--nightmare-vision-54e1fc6dd6-b857bc55`, exit 0, 129.292 seconds. Raw stdout/event logs and `.visit-1.png` / `.visit-2.png` captures are retained under `tmp/compatibility-visual-check/` using those stems. Root inspected both 60 FPS gameplay captures: lane underlays are visible behind receptor/note banks, the configured field multiplier changes opacity, and source notes/scene/TV/HUD remain present. Unlimited capture inspection is delegated to root and was pending when this report was updated.

`tmp/test-nv-underlay-native.ps1` parsed successfully using the Windows PowerShell parser. It uses the private selected-owner fixture, temporary owner-only script, cleanup in `finally`, and the existing 70-file protected baseline before and after execution. Both successful runs preserved all 70 hashes and removed the private probe. No donor, chart or mod content was edited.

Earlier failures are retained as evidence. The first native attempt reported initialization twice but failed geometry assertions; the second explicitly found a missing default-field draw hook. Inspection confirmed a production gap: default fields were registered before attachment was enabled, and existing fields never received their draw callback afterward. The first failure must not be characterized solely as probe timing. The attachment repair installs hooks without changing the existing note/cover group order. The runner also verifies immediately after the native draw callback to avoid previous-draw/current-update drift. No build or full suite was run directly by this validation subtask; the combined build and canonical gate were completed by root.

## Remaining scope

The native probe establishes this FIELD boundary and reflected enum/sprite access only. SCREEN dim, source camera scroll-angle separation, full PlayField visual/splash/group parity, wider-key geometry and Phase 2 acceptance remain open. These bounded checks do not complete Phase 2 or certify all charts. No release was published.

Root visual review also inspected unlimited visit 2 (`b857bc55`): underlays remain behind visible source notes/HUD, matching the 60 FPS layout at the same song position. Full donor rendering parity is not claimed.
