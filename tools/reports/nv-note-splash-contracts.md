# Nightmare Vision NoteSplash sprite contracts

Pinned source: `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/objects/note/NoteSplash.hx`, `FunkinSprite.hx` animation/offset methods, `PlayField.hx:418-427,555-579` and `PlayState.hx:1895-1902`. Sprite subset frozen after focused checks. Integrated acceptance is recorded below; Phase 2 and broad inherited-sprite compatibility remain incomplete.

## Implementation

`NightmareVisionNoteSplash` is the actual typed native tap sprite, separate from native, Codename and Psych generic splash behavior. Its constructor takes source x/y/direction/player plus a host-selected owner dependency. That owner supplies the existing source skin resolver; each skin's explicit-texture loader uses its own paths. The host constructor requires a selected owner instead of reading a process-global singleton.

Constructor stores data/player, loads current splashTexture animations and captures constructor scale/baseScale without playing an animation. Setup accepts source receptor/note/texture/RGB/field arguments. It retains source texture caching, hardcoded FPS 24/nonlooping animation definitions, metadata animation names/offsets, null note/default texture behavior, nullable field's invalid dereference, copied RGB and tracking-disabled setup centering. It does not reset alpha, visibility, angle, liveness or scale/baseScale. It does not reload metadata merely because metadata changed while the texture key stayed equal. Update checks finished animation before parent advancement; an animation finishing during the parent update retires on the next update. Null animation is inert.

`NightmareVisionSplashSprite` shares only the already verified splash animation fallback, offsets, baseScale, scale/rotation/offset-only skew transform and accepted native owned-point teardown. SustainSplash now inherits that common code while retaining its separate constructor/setup/finish-listener/tail semantics and RGB draw. It is not a general FunkinSprite replacement. Full sprite quad skew, other inherited methods and externally retained destroyed-point behavior are not certified by this package.

`NightmareVisionNoteSkin.loadNoteSplashFrames(texture)` honors the caller's exact explicit texture through the selected owner. The sprite owns the cache. It does not silently substitute the skin texture for an explicit empty/custom texture, borrow another owner or mutate imported assets. The previous omitted legacy sustain-default behavior remains intact.

## Focused evidence

All commands use `.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern <module>`, with zero skips/failures:

- `test_nv_note_splash_contract.py`: one fixture passes (0.6 seconds), comparing the actual host class with the full immutable donor class in twelve finite scenarios. Coverage includes constructor/seed, tracked versus untracked setup, exact texture/cache invalidation, copied colors, hardcoded FPS/looping, metadata mutation without invalidation, constructor scale retained on recycled setup, null note/texture, null/finished animation, pre-parent retirement boundary, missing direction metadata, null offsets, disabled animation centering, invalid nullable field, coloring and default catalogue. Actual sprite RGB drawing and shared teardown are checked. A separate C++ generation pass with `-D no-compilation` verifies static typing without native compilation.
- `test_nv_sustain_splash_contract.py`: one fixture passes (0.6 seconds) after common-code extraction, preserving ten full donor lifecycle comparisons, eight actual donor offset flag combinations, real pinned Flixel finish signals and C++ generation.
- `test_nightmare_vision_note_skin_runtime.py`: one fixture passes (0.8 seconds), including explicit tap texture/blank-path loads through actual skin owner paths, existing mutable skin/factory checks and legacy-default owner layout precedence.
- `test_nightmare_vision_note_skin_defaults.py`, `test_nightmare_vision_note_skin_precache.py`, `test_nv_modifier_execution_bridge.py`: one fixture each passes, retaining source defaults, warming and ordered live renderer behavior.

The shared test dependencies model native sprite operations and use the pinned actual Flixel signal implementation. They do not replace native atlas/framebuffer/shader verification. The primary agent's planned native probe separately exercises live hit spawn, public low-rating spawn, recursive callback-before-pointer publication, actual field ownership, inert seed, untracked centering, animation retirement/recycle and normal/pixel reference frames at both frame caps. Reference sprites frozen outside field modchart prove construction/frame rendering, not the entire live/global render stack.

No donor, retained mod, chart or authored asset edits were made. The prior inert generic tap-seed correction is not counted as new work. Psych has different configuration, randomization, RGB, receptor-copy and broken-animation rules; this package does not claim those are identical to NV or fully implemented.

## Integrated acceptance

Accepted bounded NoteSplash checkpoint, development 0.0.15. Canonical Windows build passed (`tmp/nv-tap-build.log`). The full eight-worker suite passed 2,268 tests across 738 modules in 179.0 seconds, with 345 reported platform/corpus skips and zero failures (`tmp/nv-tap-full-tests.log`). Existing compiler PATH was supplied so compiler-dependent fixtures ran.

Muted native checks passed two visits at 60 FPS (psych-pass-darnell--nightmare-vision-54e1fc6dd6-1db0a8fd, 141.176 seconds) and unlimited FPS (psych-pass-darnell--nightmare-vision-54e1fc6dd6-003d5dd8, 143.675 seconds). All four markers appeared twice: actual hit/public spawn and atlas frames, callback-before-pointer publication, animation retirement and pool reuse. Root inspected all four gameplay captures, including normal and pixel reference effects. The normal effect uses the retained imported atlas; pixel references use immutable private donor copies. Frozen references establish frame rendering, not complete live modifier/global draw-stack parity. The first probe incorrectly wrote read-only ratingMod; correcting only the probe to rating.ratingMod made the source-shaped check pass.

A further two-visit 60 FPS SustainSplash native regression (psych-pass-darnell--nightmare-vision-54e1fc6dd6-39d71f9f, 141.052 seconds) passed all four hold lifecycle markers twice after shared helper extraction, with both captures reviewed. Every run preserved seventy protected files and removed temporary probes. Donor source checkouts remained clean. Executable SHA256: `CF5E9D804424E8339C2AC8A64DC9C79E5C34E2BFE732B8A90CA204B52B6A1821`. Receipt: `tmp/nv-tap-checkpoint.json`.

Phase 2 remains unfinished. Next proposed shared package is the actual Psych/NV three-sprite Bar API and HUD identity (`tmp/source-bar-next-proposal.md`). Broader inherited sprite/Note APIs, full quad skew/global draw stack and Psych-specific splash behavior remain open. No donor/mod/chart modifications or release publication.
