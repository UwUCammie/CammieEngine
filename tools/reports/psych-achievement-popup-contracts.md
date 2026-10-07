# Psych achievement popup contracts

Checkpoint date: 7 October 2026.

`source/PsychAchievementPopup.hx` ports the native toast behavior from the
pinned Psych 1.0.4 `AchievementPopup.hx` source (`5c67ced49e5a98535298a6daa3f8f4ec79ac8399`).
It keeps the 420 by 130 panel, icon selection and pixel filtering, localized
text and VCR font, captured-stage resize scaling, elastic entry, three-second
hold, wall-clock exit, and cloned text bitmap disposal. Owner-captured paths,
antialiasing, language lookup, stage/game objects and lifecycle callbacks
replace process-global Psych lookups. The popup only disposes its private text
bitmap copies; shared icon graphics stay owned by the asset cache.
The selected icon carries one use-count lease until destruction, protecting
the borrowed bitmap from normal scene cache clearing without disposing it.

The donor accepts an `onFinish` callback but never stores or invokes it. The
ported constructor keeps the callback parameter for call compatibility and
preserves that no-op behavior. Popup registration is owner-managed. Captured
display objects let the toast survive scene changes; an inactive owner retires
it on the next frame. Destruction is idempotent and removes both listeners,
the captured-game child and owner registration.

The extracted test compiles the actual production class against narrow display
and Flixel stubs. It covers pixel and unknown-icon selection, localized text,
owner font routing, captured objects after global replacement, resize, pause
timing, timed exit, owner departure, unused callback behavior, shared-graphic
preservation and bitmap cleanup. Private lifecycle flags can be inspected by
the native probe through Haxe `@:access(PsychAchievementPopup)`.

## Verification

- `python -m unittest test_psych_achievement_popup -v`: passed (1 test).
- No build, full suite or native smoke gate was run for this component.

That component-only result precedes the integrated Windows build and native
60/unlimited checks in `psych-achievements-nv-splash-integration.md`. Production
language context remains open; the integrated runtime currently uses source
phrase fallbacks.
