# Nightmare Vision SustainSplash contracts

Implementation checkpoint for pinned donor `733165c42ca71eb0961a70e4173b2d81ba4a29ea`. Focused and integrated acceptance evidence is recorded below. This does not complete Phase 2 or establish the full inherited FunkinSprite API.

## Source sprite and owner boundaries

`source/NightmareVisionSustainSplash.hx` is a distinct native sprite, independent of the V-Slice hold-cover timer. Its selected owner supplies skin lookup and the current splash preference. `NightmareVisionNoteSkin.loadSustainSplashFrames()` uses that skin's existing owner-local atlas loader on every call. No process-global owner or authored asset changes are introduced.

The executable donor `source/funkin/objects/note/SustainSplash.hx` determines constructor, setup, finish callbacks and tail behavior. Constructor arguments select frames without assigning stored direction/player/skin. Setup reloads frames, captures scale, centers on the receptor and snapshots the last tail. It sets alpha to one, ignores its time argument and `susSplashAlpha`, and neither revives the sprite nor resets `completed`. Each setup adds another finish listener. Input colors are copied; null colors leave the prior RGB state. Parent animation update precedes tail watching. Missing/garbage tails kill the effect; hit tails mark completion; dead tails choose a player ending animation only for the current Both/Hold Covers preference. Position follows the receptor during setup only.

The sprite owns animation and skin offsets in `getScreenPosition`, with source scale, rotation and offset-only skew order from `FunkinSprite.hx:327-349`. RGB uses the engine's existing per-object shader bridge. Native quad skew, the remaining inherited FunkinSprite methods and full global container order are outside this checkpoint. The host constructor requires an explicitly selected owner, a diagnostic boundary for invalid host calls rather than donor global singleton lookup.

The renderer's source path matches donor PlayState line 1860: angle tracking requires a hit sustain, `note.tailState.splash` and `note.playField.trackSustainSplashes`. It does not substitute `note.sustainSplash`, require splash liveness or invent a positive tail-state pointer assignment. The existing pure/V-Slice cover fallback remains separate.

## Focused evidence

Commands use `.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern <module>`:

- `test_nv_sustain_splash_contract.py`: one executable fixture passes, zero skips. The full donor SustainSplash class and actual host sprite run against identical native-shaped dependencies and the actual pinned Flixel signal implementation. Ten finite scenarios compare constructor/setup, copied colors, start/end callbacks, tail completion/garbage/death, live preferences, nonplayer ending, recycle state, accumulated listeners, captured tail identity, parent-update ordering and disabled/fallback animations. The actual donor offset method is compared across all eight scale/rotation/skew flag combinations. Host shader application and owned-point teardown are also checked.
- `test_nightmare_vision_note_skin_runtime.py`: one fixture passes, zero skips. The actual skin adapter reloads sustain atlases through its owning paths twice, alongside its existing mutable skin/factory contracts.
- `test_nv_modifier_execution_bridge.py`: one fixture passes, zero skips. Tracking disabled preserves both pointers; enabled tracking writes the shared tail splash even when dead; the separate head pointer and null shared pointer remain unchanged.

These headless dependencies intentionally do not substitute for native atlas, framebuffer, shader or gameplay acceptance. The later parent-owned integration/native receipts are recorded below. No donor, retained mod, chart or source asset files were edited.

The initial canonical C++ build rejected two basic-Float/null comparisons in setup and live skin refresh. Inspection confirmed donor NoteSkin declares `susSplashScale:Float = 1` and resolves absent metadata to one; its setup's optional-skin check is redundant after the preceding skin dereference. The host preserves that Float/default contract and applies its value directly. The sprite fixture now also generates C++ with `-D no-compilation` and a basic-Float skin dependency, passing without invoking a native compiler. This catches the target-specific type failure missed by eval. The actual skin adapter fixture also passes after this correction. This initial build issue was resolved before the integrated acceptance recorded below.

## Retained legacy atlas default

Native investigation found a source-version layout mismatch, not an omitted import. The original D-Sides core and imported `__nmv_core/images/sustainHold.png` share SHA256 `4452bc4ae3062a910396d381cfed3441721e250857ff5907b2cc3b7188440276`, also matching the pinned modern `assets/game/images/UI/notes/sustainHold.png`. Original/imported XML share `02663f4c441efca1a206862d998665014ba696e417ea6cbaf0079932b1053ca3`. Both retained skin files omit the sustain texture, while their core stores the atlas at the image root.

Owner-loaded skins now select the flat `sustainHold` default only for an already detected `legacy-shared` core layout and only when the authored value is missing/null. Modern and unknown layouts retain `UI/notes/sustainHold`; explicit custom, modern or empty paths remain exact. The public owner-independent `resolveData` still uses the pinned modern defaults. Resolution never falls back to another owner or rewrites retained assets.

Focused default and runtime fixtures pass. The runtime fixture executes actual core-profile detection: complete legacy digits select flat, complete modern digits take precedence when both exist, partial legacy retains modern, and explicit custom paths win across all layouts. The resolved atlas goes through the exact owning paths. Precache and sprite eval/C++-generation fixtures also pass. Native acceptance must use the actual retained legacy atlas after the integrated rebuild; a private copied modern reference alone does not certify this correction.

## Integrated acceptance

Accepted bounded SustainSplash checkpoint, development 0.0.15. Windows build: `tmp/nv-sustain-splash-layout-build.log`. Full suite with eight workers: 2,264 tests across 736 modules in 175.7 seconds, 348 skipped and zero failures (`tmp/nv-sustain-splash-full-accepted-tests.log`). Three of those skips only lacked compiler PATH in the direct runner; both affected modules then passed all six tests with the existing compiler, zero skips (`tmp/nv-sustain-cpp-fixtures-recheck.log`). The remaining 345 skips retain their reported platform/corpus limitations. Earlier parallel updater/filesystem compilation timeouts passed isolated rechecks; no test timeout was raised or case removed.

Muted native two-visit checks passed at 60 FPS (885820cf, 136.624 seconds) and unlimited FPS (e2f1b49f, 134.334 seconds). Each run emitted all four assertion markers twice: real hit-driven group spawn with native atlas frames, callback-before-head-pointer publication, tail retirement and actual pool reuse. Root reviewed all four gameplay captures, including frozen normal and pixel reference effects. The normal effect uses the actual retained legacy atlas through corrected default resolution; only the pixel reference uses a private immutable donor copy. Reference sprites certify native constructor/setup/frame/shader behavior, not independent live-field positioning. Seventy protected source/settings files remained unchanged. Executable SHA256: `103719A2A2483F6343D20A08E6E68D1C566134828B2F125B90A3BDF35827871C`.

The first native failure exposed C++ dynamic access bypassing the field's `members` getter. Typed access now preserves the note's actual owning field; the regression asserts generated C++ calls `get_members()`. A separate probe parse error was fixed only in the temporary probe. The legacy missing default was a layout mismatch, not an importer omission. All temporary probes were removed after testing. Receipt: `tmp/nv-sustain-splash-checkpoint.json`.

Phase 2 remains unfinished. Next confirmed work: actual NV NoteSplash API and field lifecycle (`tmp/nv-note-splash-next-proposal.md`). Broader NoteUtil/Note/FunkinSprite APIs, full quad skew and the complete global draw stack remain open. No donor/mod/chart edits or publication.
