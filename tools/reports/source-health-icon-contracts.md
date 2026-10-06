# Typed source HealthIcon contracts

Core classes and focused fixtures are frozen. Connected HUD/import integration, canonical build and native acceptance remain pending. This checkpoint does not establish full Phase 2 or all inherited sprite behavior.

Sources: Psych 1.0.4 revision `5c67ced`, complete `source/objects/HealthIcon.hx`; NightmareVision revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, complete `source/funkin/objects/HealthIcon.hx` and `funkin/game/IUiSprite.hx`.

`PsychSourceHealthIcon` and `NightmareVisionHealthIcon` are actual FlxSprite classes with owner-local image/existence, live UI-prefix and antialiasing dependencies. Psych preserves ratio-derived strips, Void changeIcon, unchanged-name reload suppression, autoAdjustOffset, requested getCharacter, pixel antialiasing and fixed tracker offsets. NV preserves returning-this/forced reload, writable frameCount, its width-derived Y offset quirk, mutable pooled sprOffsets, characterName assignment before loading, updateFrames and compounded alphaMultipler through the real IUiSprite interface. Both retain native animation/frame operations. Selected owner references are cleared during destruction; attempted reload after owner release gets an explicit host diagnostic. Psych owner cleanup is an added host lifecycle boundary.

The actual-donor fixture executes twenty finite comparisons, ten per dialect: direct and fallback paths; unchanged and forced reload decisions and return types; wide strips/frameCount three; pixel and live antialiasing; tracker positions; offset adjustment after scaling; NV alpha/frame flags and Psych requested-name identity; and loading-failure partial state. Existence calls use full `images/<key>.png` paths. NV fallback re-reads the live prefix at each donor lookup. Actual pinned FlxAnimationController add/play/frameIndex/callback methods, FlxAnimation play/curFrame, FlxBaseAnimation curIndex, FlxSignal and FlxDestroyUtil methods are extracted into the fixture. Dependency graphics/frame slicing remain a native-shaped model, so frameCount zero/negative and malformed real atlas loading are explicitly unverified.

The fixture runs eval and C++ generation with `-D no-compilation`. It calls inline updateIconAnim through Reflect and checks generated C++ field dispatch and dynamic method export. C++ generation also checks the NV null-safety owner-release code. This is not a native C++ compiler or runtime gate.

Pinned Psych has an internal signature discrepancy: HealthIcon line 32 calls `Paths.image(name, allowGPU)`, while backend Paths line 229 declares `(key, ?parentFolder:String, ?allowGPU:Bool)`. The class fixture accepts the observed Bool forwarding and proves class semantics, not compilation of that entire unmodified donor tree. Connected owner loading separately owns the source GPU-cache interpretation and isolation from native graphics caches.

Focused commands use `tools/run_tests.py --jobs 1 --pattern <module>`. Results: source icon contract one test (1.0 seconds), source health policy one (0.8 seconds), icon strip guard two (0.4 seconds), NV icon identity one (0.3 seconds); zero skips or failures. Reusable dependencies are in `source_icon_fixture_support.py` for connected real-class/HUD fixtures.

No full build, full suite or native launch was run by this agent. No donor, mod, chart or authored content was changed. Parent-owned native probes must still prove displayed HUD identity, imports/live bare/game/Lua roots, owner-local assets and GPU behavior, reloads and source update/beat phases.

## Integrated acceptance

Accepted bounded typed source HealthIcon checkpoint, development 0.0.15, 6 October 2026. Canonical Windows build passed (`tmp/source-icon-build.log`). Final full suite: 2282 tests across 746 modules in 152.4 seconds, 345 reported skips, zero failures (`tmp/source-icon-full-tests.log`).

Muted two-visit checks passed both engines at 60/unlimited FPS. Psych passed five markers per visit for construction/reload/tracker/fallback, actual displayed HUD identity, live aliases, Lua setters and native GPU upload; NV passed three markers per visit for construction/reload/tracker/fallback, displayed HUD API and live aliases. Root reviewed all eight captures, including the private GPU-face test asset. All runs preserved seventy protected files and removed temporary probes. The fixture executable matches the current build.

The first build failed on GPU-helper private BitmapData access. A narrow @:access and realistic private fixture visibility fixed this static-target issue. Pinned Psych HealthIcon passes its Bool GPU hint where the retained backend Paths signature declares a parent-folder argument; the owner adapter explicitly handles the observed icon GPU hint. This does not certify compilation of the entire unmodified donor tree.

Intermediate runs `73057b38` (probe enabled) and `ced2712c` (probe absent) reached the 90-second timeout, with startup durations 40.438 and 41.579 seconds. Diagnostic run `25fc9481` succeeded in 80.365 seconds; setup/reload took 19.906/21.513 seconds and state initialization 3.56/3.63 seconds. No icon cleanup or cache defect was established. Diagnostics were removed without an engine workaround or smoke-budget change. These runs are historical diagnostics, not the final native acceptance receipts below.

The first full suite (`tmp/source-icon-full-tests-first.log`) ran 2,282 tests across 746 modules in 157.5 seconds, with 345 skips and six failed extraction-fixture modules: test_psych_strum_group_property, test_psych_property_paths, test_source_death_character_identity, test_stage_hud_note_order, test_psych_note_splash_disabled and test_psych_property_coercion. Those fixtures gained the new source icon alias/getter dependencies while preserving existing behavior assertions; death-identity/HUD-layer fixtures also check override reset and actual helper source-icon layering. Production was unchanged by these repairs, so accepted build/native hashes remain valid. The passing final suite above supersedes this retained failed history.

- psych 60 FPS: `psych-pass-swag-messiah-38b63684`, 82.566 seconds, 5 markers each twice.
- psych unlimited FPS: `psych-pass-swag-messiah-32ea9723`, 80.991 seconds, 5 markers each twice.
- nv 60 FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-18a5d1bf`, 138.552 seconds, 3 markers each twice.
- nv unlimited FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-9d3c6895`, 138.929 seconds, 3 markers each twice.

Executable SHA256: `F72A9E8138768A609D7E6301494E1DA452FABF32D59FCF7D3F7E1B1B8277DFE6`. Receipt: `tmp/source-health-icon-checkpoint.json`. Malformed zero/negative frameCount loading, invalid Psych Character metadata fallback, historical profiles and full inherited sprite/Phase 2 compatibility remain open. No donor/mod/chart edits or publication.
