# Source health math and icon-frame contracts

Core policy/icon subset frozen after focused verification. Connected PlayState/HUD/reflection orchestration, canonical build and native acceptance remain pending. This is not full NV HealthIcon or Phase 2 parity.

Sources: Psych 1.0.4 revision `5c67ced`, `states/PlayState.hx:1716-1717,1891-1908`; NV revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin/states/PlayState.hx:338-343,1737-1738`, `objects/HealthIcon.hx:140-145` and `game/huds/PsychHUD.hx:231-235`.

`SourceHealthPolicy` implements Psych five-decimal assignment rounding, exact nullable Psych maximum cap, directional NV maximum cap, shared source bound/remap math and strict Psych 20/80 frame thresholds. Separate cap predicates preserve source assignment/callback decisions, including no cap writes when NaN makes comparisons false. Numeric functions retain reversed/equal bounds, NaN and infinity behavior rather than imposing a 0-2 clamp. They do not own mutable gameplay state or dispatch callbacks.

The native `HealthIcon` gains source `updateFrames = true` and `updateIconAnim(fraction)`. This method is the actual donor NV two-frame write through `animation.frameIndex`; updateFrames stops it. It is independent from the existing native/V-Slice autoUpdate flag and does not alter native icon states unless explicitly called. Selected source gameplay must bypass native Winning/Poisoned rewrites at its own update phase; that wiring belongs to the connected integration agent. The NV constructor, frameCount loading, tracker offsets, forced changeIcon and icon IUiSprite/alphaMultipler surface remain separate gaps.

The fixture also preserves the actual `@:keep inline` method metadata and calls it through Reflect.field/callMethod. Generated C++ contains the `updateIconAnim` field resolver and dynamic method entry, so typed inline calls alone are not the callable-surface evidence. Full native HealthIcon script dispatch remains part of the integrated smoke gate.

Focused command: `.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern test_source_health_policy.py`. One fixture passes, zero skips/failures (0.4 seconds), with eval execution and C++ generation (`-D no-compilation`). It compares numeric helpers against actual pinned Psych setter and both update-bound fragments, using the actual NV setter for NV callback-count decisions. Values include negative/out-of-range values, five-decimal and threshold boundaries, a fractional maximum, reversed/equal bounds, NaN and infinities. The actual host icon method is extracted and compared with the actual donor method through the pinned Flixel frameIndex setter/fireCallback and real signals, across zero/one/two/four native-shaped frames and updateFrames states. This is actual method/native-controller behavior, not whole HealthIcon construction or GPU proof.

Related focused checks pass: `test_health_icon_strip_clamp.py` (two tests), `test_nightmare_vision_health_icon_identity.py` (one), `test_source_bar_contract.py` (one), all zero skips/failures. Total owned/related verification: five tests across four modules. Existing native icon loading/state APIs are retained.

The shared Bar test dependency now uses actual pinned FlxMath.roundDecimal/bound/remapToRange/lerp. Its previous tiny bound approximation mishandled reversed bounds by returning after the lower comparison; real Flixel performs lower then upper checks. This is a fixture correction only. Actual donor/host Bar comparisons and C++ generation still pass.

No build, full suite or native launch was run by this agent. No donor, mod, chart or authored asset files were changed. Parent-owned connected fixtures and native gate must establish assignment ordering, flags/null guards, actual current HUD/bar pointers, real NV FlxBounds, Lua/Iris setter routes, source icon update phase and freedom from native frame overwrites before acceptance.

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
