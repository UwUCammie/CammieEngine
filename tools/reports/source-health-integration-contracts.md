# Connected Psych and Nightmare Vision health

Development0.0.15. Targets: Psych1.0.4 `5c67ced`, NV `733165c42ca71eb0961a70e4173b2d81ba4a29ea`. Production/tests frozen for root canonical/native acceptance. No donor, mod, chart or asset changes in this package.

The source health setter now selects the existing source scoring dialect. NV stores the raw argument, calls the current HUD afterward even for equal assignments, and returns the original argument. Psych rounds to five decimals, stores before sampling, and returns the current health field after callbacks. Native/Codename retain0..2 setter clamping. Source hit/miss deltas and existing death eligibility/cancellation remain unchanged.

The earlier proposal's phrase every current HUD was imprecise: pinned NV PlayState562 implements callHUDFunc as a null-checked call to the single current playHUD. There is no HUD collection to recreate. The integration dispatches precisely that current pointer, including replacement, and does not introduce a second callback pass or catch errors from the source HUD value function.

Psych's iconsAnimations flag is reflected and governs the actual setter alongside current bar null/enabled/valueFunction checks. When admitted, the setter samples once, then re-reads the current bar's bounds and percentage before icon writes. A callback may replace the bar; the new bar receives the geometry/frames while the old bar remains untouched. The source pointer/container ownership boundary remains as established by the Bar package. Player/opponent curAnim.curFrame use strict below20/above80 rules. NV uses the separate HealthIcon.updateIconAnim fraction/frameIndex API and updateFrames flag, independently of native autoUpdate.

Ordinary source update caps are separate from assignment. NV preserves both directional strict comparisons against actual healthBounds; equal endpoints do not cap, and NaN does not accidentally dispatch a setter. Psych caps to the current source bar maximum, with its setter rounding applied to that cap. Before source HUD installation, the host may skip the Psych update cap; after installation an authored null bar dereferences/fails as source, while the setter's explicit null guard remains valid. NV healthBounds is now the real FlxBounds<Float>, with actual source import and its min/max/active/set/equals behavior.

After state superclass/group update, the NV HUD updates icon frames, then its timer, then PlayState performs the health cap. A cap callback may change bar percentage while icons retain the preceding HUD phase until its next update. The timer's placement was corrected from the earlier host pre-super call to this source phase. All nine native iconState writes, including winning/poison paths, are limited to source mode0. Native RPC labels, color formatting, hit/miss arithmetic and native/Codename icon behavior remain in their existing routes.

Bare Iris and Psych SourceIrisBridge health, game-property access, and Lua setProperty writes reach the real setter. Source plain-HScript bulk health synchronization removes the scalar preset rather than hiding the live parent setter; legacy/Lua map synchronization remains. Subsequent bare assignments still dispatch after earlier writes. Actual imported FlxBounds construction and methods execute through Iris. Explicit user locals/presets retain the interpreter's existing shadowing rules.

## Focused verification

Commands: `.tools/python/python.exe tools/run_tests.py --pattern <module> --jobs 1`.

- test_source_health_integration.py:2 passed in1.0s,0 skips. Extracted actual PlayState setter/limit/phase with real source Bar classes, actual HUD adapter and pinned FlxBounds/math. Raw/rounded immediate values, store-before-callback, equality, enabled/null/function/icon guards, threshold frames, finite reentrant setter return distinction, callback bar replacement, normal/reversed/equal/NaN caps, native clamps and startup/installed-null distinction. C++ no-compilation generation covers numeric/accessor shapes. Explicit execution trace is group value callback -> icon1 -> icon2 -> timer -> cap value callback. Actual Iris/SourceIrisBridge and extracted Lua compatSetProperty root/game paths verify repeated bare/game setter dispatch after map synchronization, current HUD replacement and imported bounds methods.
- test_source_hud_bar_integration.py:2 passed,1.0s. Added actual health-binding dependency to the existing import fixture; prior real group, alias, callback/order and ownership assertions retained.
- test_source_health_delta.py:2 passed,0.2s.
- test_source_death_wiring.py:2 passed,0.2s.
- test_nv_hit_order.py:3 passed,0.3s.
- test_source_miss_lifecycle.py:7 passed,0.6s.
- test_source_death_policy.py:2 passed,0.2s.
- test_psych_healthbar_colors.py:1 passed,0.2s.
- test_source_iris_bridge.py:2 passed,0.8s.
- test_source_health_policy.py:1 passed,0.4s (peer-owned numeric/full-donor and actual native animation controller comparisons).

Total24 passed across10 modules, zero skips/failures. Policy/icon implementation evidence is separately recorded in source-health-policy-contracts.md. Root build passed and the first Psych60 two-visit private probe passed its four markers per visit with the protected70-file baseline unchanged; these are interim receipts. Final canonical and remaining native caps/dialects remain pending, so this report does not claim complete acceptance yet.

Remaining surfaces include complete NV HealthIcon constructor/frameCount/tracker/changeIcon/alphaMultipler/IUiSprite ownership, broader HUD class APIs, historical Psych profiles and full inherited sprite behavior. The source frame policy and health contract do not certify those broader interfaces.

## Integrated acceptance

Accepted bounded connected source health checkpoint, development 0.0.15, 6 October 2026. Canonical Windows build passed (`tmp/source-health-build.log`). Final full suite: 2276 tests across 743 modules in 219.2 seconds, 345 documented platform/corpus skips, zero failures (`tmp/source-health-full-tests.log`).

The initial full suite reached 2,276 tests/743 modules with one stale exact-line expectation in test_health_icon_owner.py. The fixture now asserts the added source exclusion while retaining its live native/V-Slice autoUpdate gates and authored-animation behavior. Its focused rerun passed six tests with one existing unavailable-corpus skip, zero failures. Production was unchanged for this correction; the failed suite remains historical evidence, superseded by the verified final summary above.

Muted native probes passed two visits per engine at 60 and unlimited FPS. Psych passed four named markers per visit, including raw-to-rounded assignment, store-before-callback, equal writes, live bare/game/Lua setters, guarded frame updates and actual next-update bounds. NV passed three named markers per visit for raw assignment/current HUD callbacks, real bounds/directional caps and exact frameIndex/updateFrames behavior. Root reviewed all eight final captures. The temporary probe holds a 5% bar value independently of gameplay health for the losing-icon visual reference; the probe and its state are removed after each run. All runs preserved seventy protected files and removed temporary probes; the private fixture executable matches the current build.

The first NV attempt `f490c249` was a private phase-check error: multiple fixed script callbacks in the same host frame tested a cap before another state update. A game tick gate corrected the probe. The later `f8152527` attempt passed all health markers but failed note-render-readback-timeout because the shortened 25-second/10-second smoke window preceded notes; restoring the prior 45-second/20-second window corrected that fixture coverage. Neither correction is an engine behavior change or an accepted failed smoke.

- psych 60 FPS: `psych-pass-swag-messiah-7849ded3`, 78.403 seconds, 4 markers each twice.
- psych unlimited FPS: `psych-pass-swag-messiah-25ecf4c7`, 78.199 seconds, 4 markers each twice.
- nv 60 FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-bb522d80`, 139.217 seconds, 3 markers each twice.
- nv unlimited FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-2967b65c`, 146.246 seconds, 3 markers each twice.

Executable SHA256: `220930287E65DB9AC25E4012C0D7607BFD477B59CB0D7C5E3D591F8D44BBF2DA`. Receipt: `tmp/source-health-setter-checkpoint.json`. The earlier 4 October health-preferences receipt remains unchanged. Next bounded package is actual source HealthIcon construction/asset/ownership APIs (`tmp/source-health-icon-next-proposal.md`). Full Phase 2 and complete NV HealthIcon parity remain unfinished. Native/Codename routes and existing source death/hit semantics remain preserved; no donor/mod/chart edits or release publication.
