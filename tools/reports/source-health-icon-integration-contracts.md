# Connected source HealthIcon integration contracts

Development 0.0.15. Production implements real source HUD icon identity and owner-local construction, with native, Codename and V-Slice HealthIcon fields retained. This report covers the connected integration; full sprite donor comparisons are in `source-health-icon-contracts.md`. Canonical build/native acceptance is pending root validation.

## Source comparison and implementation

Pinned Psych 1.0.4 `5c67ced`, `source/objects/HealthIcon.hx` and `source/states/PlayState.hx` (538-548, 1719-1720, 1873-1907, 2209/2231, 3225-3229); pinned Nightmare Vision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/objects/HealthIcon.hx`, `source/funkin/game/huds/PsychHUD.hx` (72-82, 201-234, 258-302).

- PlayState keeps native `iconP1/iconP2:HealthIcon` and its native icon array. Separate typed PsychSourceHealthIcon and NightmareVisionHealthIcon pointers are installed in the original display slots. Old native icons are detached and retained for one owner teardown; source sprites update/draw once in the state display list.
- Source constructor factories bind actual dialect classes and captured image owners. Bare globals, game/class fields through Iris, and Lua/property reads and writes resolve the current source pointers. NV playHUD holds actual typed source icons. A script replacing a public pointer does not automatically rewrite an already-added display member, matching source pointer versus group ownership.
- Current source pointers receive character reloads, health frames, position/scale and beat effects. Native icon-state, compatibility-offset, debug icon toggle and dance writes stay in the native route. Character.healthIcon is writable, retains NV metadata and selected Psych JSON `healthicon`, and accepts subsequent script overrides independently of the character identifier. Character reload resets that override before loading new metadata.
- Psych uses scale decay `lerp(1, scale.x, exp(-elapsed * 9 * playbackRate))`, then hitbox updates and barCenter-based positions. Its health setter updates the current typed icons after valueFunction callbacks, including finite pointer replacement. Beat pulses use scale 1.2 before source script beat dispatch.
- NV HUD presentation follows actual group update, position, scale decay, animation and timer, then state health cap. Position obeys updateIconPos and physical bar direction. Scale decay and 1.2 beat pulses obey writable updateIconScale; frame updates retain independent updateFrames control.

## Image/cache ownership

SourceHealthIconAssets owns a Psych graphic cache shared by factories with the same captured PsychOwnerPaths root. Distinct roots have separate clones and teardown, even when an explicit factory facade differs from the current song owner. The cache follows donor image-key-first behavior: a repeated image key returns the first cached graphic without applying a later GPU hint. Source-only bitmap clones keep GPU disposal away from generic/native caches. Native Lime ImageBuffer.clone allocates and copies its data; source clones do not share the original data buffer. Assets release after displayed objects are destroyed.

The GPU branch uses both HealthIcon.allowGPU and live ClientPrefs.data.cacheOnGPU, with pinned Paths upload/getSurface/dispose ordering and narrow `@:access(openfl.display.BitmapData)` for actual private/read-only fields. NV uses its existing typed owner Paths.image(name, null, allowGPU) path; its source icon forces allowGPU false.

Pinned Psych's HealthIcon passes a Bool second argument to Paths.image, but pinned backend Paths.image declares parentFolder:String second and allowGPU third. The adapter explicitly treats the HealthIcon public Boolean as the GPU hint. Donor class tests use this intended adapter seam; they do not prove that the inconsistent full donor tree compiles unchanged.

Source final face fallbacks are byte-identical engine-owned copies, selected only if the owner's stock final face path is absent. Native host assets and retained donor files are unchanged:

| Engine-owned path | Immutable donor path | SHA-256 |
|---|---|---|
| assets/images/source_compat/psych/icon-face.png | FNF-PsychEngine/assets/shared/images/icons/icon-face.png | 7b49841651538ff79aa25d6f437e6202551ea7a4554619f31f3c826eb9fc494e |
| assets/images/source_compat/nightmare-vision/icon-face.png | NightmareVision/assets/game/images/UI/icons/icon-face.png | e9ac8814eb17d4a03e6d2fa72a7d77550a8a99ed894cac9a70a8a4438a3689f7 |

## Focused evidence

Latest focused checks: 26 tests across 12 modules, 25 passed, one existing missing imported-character corpus skip, zero failures. Commands used `.tools/python/python.exe tools/run_tests.py --pattern <module>.py --jobs 1` for:

- test_source_health_icon_integration (3): actual typed sprites/HUD and Iris import/factories; preserved native pointers/display slots; writable current aliases and detached replacement semantics; real owner/factory cross-root caching and face precedence; scale/position/beat flags; instrumented production group/HUD/timer/cap ordering; health callback icon-pointer replacement; current character reloads; actual Character getter/setter through Iris/property writes.
- test_source_health_icon_assets (2): GPU/pref combinations, repeated cache hints, isolated originals/owners, owned release, immutable face byte comparison, eval and C++ generation. GPU stubs model actual private __texture and readonly image/readable visibility.
- test_source_health_integration (2), test_source_hud_bar_integration (2), test_health_icon_owner (7, one corpus skip), test_vertical_health_icons (1), test_health_icon_strip_clamp (2), test_nightmare_vision_health_icon_identity (1), test_nightmare_vision_hud_adapter (1), test_nightmare_vision_character_hud_refresh (3), test_source_bar_contract (1), test_source_health_icon_contract (1).

Fixture-only maintenance adds the new typed source dependencies, preserves existing health/bar/native behavior assertions, and extracts multiline expression getters through their terminating semicolon. Native isolated layout fixtures explicitly select native timing mode. Unrelated camera/save/audio paths are stubbed in the icon integration fixture; the actual source classes, HUD adapter methods, parser/interpreter imports and constructor factories are executed.

## Limits and pending acceptance

Missing/non-string Psych `healthicon` in a retained JSON currently preserves the host character-ID fallback; the donor directly assigns that JSON value. Missing full Character definitions, malformed metadata and source defaults remain wider Character parity work. No full Character, HUD, arbitrary historical icon variant or full Phase 2 completion claim is made.

Full native parent sprite behavior, GPU renderer/context lifetime, repeated scene loading, captured visual appearance and capped/unlimited acceptance are root gates. The initial Psych native GPU visit passed its markers and visual review, but its second visit timed out after playstate_destroyed; a subsequent no-probe diagnostic run passed both visits within the unchanged budget (80.365 s). Setup took about 20-21.5 s before PlayState, compared with about 40-41.6 s in the timed-out runs. The measured wrapper setup variance is recorded in `tmp/source-icon-reload-observation.md`; no icon ownership defect was established and no timeout or setup shortcut was introduced. Temporary diagnostic blocks were removed before the final build. That failed receipt is not replaced by a headless passing result. Canonical and final native receipts will be appended only after validation.

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
