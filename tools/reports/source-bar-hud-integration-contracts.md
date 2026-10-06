# Source Bar connected HUD integration

Development 0.0.15. Source target: Psych1.0.4 `5c67ced` and NightmareVision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`. Integration passed independent review and the coordinated canonical/native gates recorded below. No donor, mod, chart or asset edits.

Psych and NV health/time source aliases now reach real typed drawable Bar groups inserted into the state. Native/Codename FlxBar fields remain typed and retain their legacy routes. Removed native fills/backgrounds are kept in a separate owner list and destroyed once after script release; their children do not enter the new groups. Source group children are updated/drawn/destroyed through their one state-owned group. Replacing a public source bar pointer does not replace the original state display member or assume ownership of an unattached replacement, matching source pointer/container boundaries. Replacing writable Psych child pointers likewise retains source member identity semantics.

Each original background is replaced at its current display index before removing its obsolete fill, avoiding stale indices when time elements precede health. Health groups remain before icons; time groups precede the actual time label. Source owner Paths load group graphics. Source0.89/0.11 health placement, hide-HUD/alpha preferences and initial icon positions are applied. This preserves the existing host regression slots, rather than claiming full global donor stack parity.

NightmareVisionHUDAdapter uses the exact typed NightmareVisionBar instances supplied by PlayState in native gameplay and exposes those groups through playHUD. Its members contain the groups, not their background/fill children. The older non-rendering view remains only the explicit standalone/headless fixture path. Adapter release clears its references without destroying state-owned groups. Source updateBar computes geometry without sampling; source group update samples valueFunction once, respecting enabled and null-function behavior. The NV onHealthChange callback explicitly samples and remaps the function through current bounds as donor PsychHUD does, including its null-call failure. The host health setter dispatches this callback after storing health. The production timer publishes songPositionBar and updates text without overriding Bar.percent; natural group update owns custom value functions and disabled state. NV's later generic raw timer overwrite is skipped. Psych time elements receive the source half-second song-start fade.

Physical icon x placement reads the source barCenter. Psych uses the pinned default position formulas without adding an enabled/valueFunction position guard. NV uses its updateIconPos bridge and direction-specific placement. Frame pose thresholds now observe the actual source percent. Full source set_health numeric/icon-animation semantics remain a separate contract: the native host numeric clamp is unchanged, and this package does not claim the donor's complete icon-animation setter.

Actual source Bar imports/constructors receive six source arguments and an owner injected seventh argument. Bare script globals, game/state reads, class-parent aliases, Lua property traversal and retained songPosBar/background aliases resolve the same live source pointers. The existing Iris live-value mechanism now also honors bindings through class-parent fallback. Authored null pointers stay null after source installation; hidden native bars do not substitute for them. Generic global sprite aliases also point to actual groups/children. IUiSprite is bound only to the actual NV source interface implemented by its Bar.

Local immutable Psych history establishes physical HealthBar groups at advertised0.7 and Bar at0.7.3, while0.6.3 used FlxBar. The default shared Psych target remains pinned1.0.4. The different0.7 HealthBar constructor/default callback is not aliased to modern Bar. No imported version profile currently selects pre0.7 HUD contracts; their FlxBar-only HUD APIs remain a gap. Native/Codename HUDs and the explicit generic createFlxBar helper remain intact. No chart-name activation rule was introduced.

## Focused evidence

All commands: `.tools/python/python.exe tools/run_tests.py --pattern <module> --jobs 1`.

- test_source_hud_bar_integration.py: 2 passed,1.2s. Native production-Dflixel adapter and actual source groups with pinned group operations: one callback/child update per state pass, disabled sampling, geometry-only updateBar, NV explicit health sampling/null errors, current timer custom callback, physical boundary placement, draw order, child/root separation, live replacement/null identity, and distinct once-only ownership. C++ generation uses no-compilation. Actual Iris and SourceIrisBridge execute real Bar constructor/import bindings; actual Lua property-part methods and class-parent paths prove shared pointers.
- test_nightmare_vision_hud_adapter.py:1 passed,0.2s.
- test_psych_healthbar_colors.py:1 passed,0.2s.
- test_psych_property_paths.py:4 passed,1 existing mounted-corpus skip,0.7s.
- test_psych_time_hud_aliases.py:1 passed,0.2s.
- test_source_iris_bridge.py:2 passed,0.8s.
- test_nightmare_vision_script_interp.py:1 passed,1.0s.
- test_source_health_wiring.py:3 passed,0.2s.
- test_vertical_health_icons.py:1 passed,0.2s.
- test_nightmare_vision_time_bar.py:1 passed,0.2s.
- test_nightmare_vision_character_hud_refresh.py:3 passed,0.4s.
- test_source_attached_bar.py:1 passed,0.2s.
- test_source_bar_contract.py:1 passed,0.4s, including the sprite owner's complete immutable donor comparisons and C++/interface checks.
- test_codename_hud_utilities.py:1 passed,0.2s.

Total23 passed across14 modules,1 documented corpus skip,0 failures. Extraction fixtures that isolate legacy property traversal now provide inactive source-alias dependencies; the connected production fixture independently exercises active aliases with real groups. Native-shaped group width/camera/scale behavior still requires the native gate, as recorded by the sprite owner's source-bar-contracts.md. Canonical full suite, 60/unlimited probes, actual owner graphics and authored Psych intro regression are pending. Broader source HUD classes, pre0.7 Bar APIs and universal inherited sprite parity are not complete.

The successful coordinated build exposed five isolated fixture dependency failures in tmp/source-bar-full-tests.log. Production was unchanged for the repairs: test_psych_strum_group_property.py passed1/0.6s, test_source_note_timing_wiring.py passed2/0.3s, test_psych_note_splash_disabled.py passed1/0.2s, test_nightmare_vision_health_colors.py passed1/0.2s, and test_psych_property_coercion.py passed1 with its existing mounted-corpus skip/0.2s. The timing fixture now extracts only the actual safe-zone restore block rather than adjacent unrelated HUD cleanup. Static traversal fixtures keep inactive source-HUD alias dependencies while retaining every getter, coercion and note-local splash assertion; the connected group fixture independently covers the active alias paths. Additional focused total6 passed across5 modules,1 existing skip,0 failures. Final canonical/native acceptance remains pending.

## Transparent stock frame correction

The first native captures exposed an actual fallback mismatch despite passed group/API markers: the selected Psych owner had no custom healthBar.png, so PsychOwnerPaths selected the host's legacy601x19 frame with opaque white interior. The correct source group draws its background last; that frame therefore occluded correctly colored fills. The stock Psych health frame has the same601x19 dimensions and transparent center. This was an image fallback defect, not missing color initialization, and no color-policy change was made.

The root authorized byte-identical engine compatibility copies from the pinned source distributions. The native host frame is untouched. Psych image resolution keeps selected-owner art first, then recognizes only stock healthBar/timeBar for source-core fallback before native shared fallback. Unrelated images retain the existing resolver. NV Paths keeps its owner/core scope unchanged; the source Bar owner factory checks its captured owner/core file first and only uses an engine frame when a recognized stock image is absent. Explicit/custom paths are not rewritten. These engine images are packaged through the existing assets/images declaration.

| Engine compatibility asset | Immutable donor image | SHA256 |
|---|---|---|
| `assets/images/source_compat/psych/healthBar.png` | `../fnf_sources/FNF-PsychEngine/assets/shared/images/healthBar.png` | `8e162551c302133fac8210e1d9474dfe98dc4d5e382df9ce8648a029a11eab38` |
| `assets/images/source_compat/psych/timeBar.png` | `../fnf_sources/FNF-PsychEngine/assets/shared/images/timeBar.png` | `935ea71c0219c9b7c999e691666967ba530d51294552f3c6108b05dd0ad3ce2c` |
| `assets/images/source_compat/nightmare-vision/healthBar.png` | `../fnf_sources/NightmareVision/assets/game/images/UI/healthBar.png` | `41aa205c93bed307ccb1988151976b54485d349faf3a45498ba932087ab3dc6d` |
| `assets/images/source_compat/nightmare-vision/timeBar.png` | `../fnf_sources/NightmareVision/assets/game/images/UI/timeBar.png` | `98823261a619d592d2c1825d4cd1a159e160dd18f3c8cee125d3ba1f1d1ddafe` |

Psych donor revision5c67ced and NV733165c42ca71eb0961a70e4173b2d81ba4a29ea are the source attribution for these immutable frames. All four copies retain601x19 health /400x19 time dimensions and center alpha0. The original native health frame has center alpha255; no donor/native image was modified.

Focused test_source_bar_assets.py passed2 tests in0.6s without skips, checking pinned hashes, decoded RGBA pixels/dimensions, actual Psych resolver and actual NV owner-factory precedence/custom-path errors, captured owner identity, and C++ no-compilation generation. Connected test_source_hud_bar_integration.py passed2 in1.0s and updated full-donor test_source_bar_contract.py passed1 in0.3s (now actual native clip rounding). Existing test_psych_owner_paths.py skipped its unavailable private source archive; test_psych_owner_lime_assets.py skipped unsupported symlink creation. Production/assets/tests were refrozen for coordinated rebuild and native rerun; initial white-frame native results remain superseded evidence, not accepted visual parity.

## Integrated acceptance

Accepted bounded source Bar checkpoint, development 0.0.15. Canonical Windows build passed (`tmp/source-bar-build-final.log`). Final full suite: 2273 tests across 741 modules in 144.7 seconds, 345 documented platform/corpus skips, zero failures (`tmp/source-bar-full-tests-final.log`). Compiler PATH was supplied. The earlier five extraction fixture failures were corrected without weakening their behavioral assertions.

Muted native checks passed two visits per engine at both 60 and unlimited FPS. Psych passed twelve markers per visit, including actual constructor/child identity, clip/resize/value behavior, shared Lua/HScript aliases, transparent stock-frame center, authored intro movement, hidden/recovered opponent notes and extra actor visibility. NV passed three combined markers per visit for actual group/interface/dialect behavior, physical HUD layout and value ownership. Root reviewed all eight final gameplay captures. Every run preserved seventy protected files and removed temporary probes.

Visual review caught a real integration defect after the first behavior passes: the old opaque host frame covered source fills. Owner-first stock-frame fallback now uses four byte-identical source PNGs in engine-owned compatibility assets; custom owner images and native assets are unchanged. The final Psych captures show purple/blue health fills. Private probe corrections for clip rounding and nonexistent FlxRect.clone are recorded in the root review, not counted as engine fixes.

- psych 60 FPS: `psych-pass-swag-messiah-f49c6cff`, 96.581 seconds, 12 markers each twice.
- psych unlimited FPS: `psych-pass-swag-messiah-1e7fa172`, 94.58 seconds, 12 markers each twice.
- nv 60 FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-898cd5ce`, 135.628 seconds, 3 markers each twice.
- nv unlimited FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-d590cbad`, 134.012 seconds, 3 markers each twice.

Executable SHA256: `8E4F9C12C81D76342ADCB47D76E48E18001DF79C4A7A1BB14D6FA9BF99A280A9`. Receipt: `tmp/source-bar-checkpoint.json`. Phase 2 remains incomplete. Next connected package is source health setter/update bounds and icon-frame policy (`tmp/source-health-next-proposal.md`); full source HUD and historical Psych variants remain open. No donor/mod/chart edits or release publication.
