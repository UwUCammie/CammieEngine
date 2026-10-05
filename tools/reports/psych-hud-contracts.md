# Psych composite HUD movement checkpoint

Verified locally on 5 October 2026 after v0.0.13 with GPT-6 Luna at Max reasoning. This follows `psych-opening-contracts.md` and addresses the additional intro HUD motion report.

Psych scripts now move a bar's native fill and state-owned background together through ordinary property/tween writes. The shared SourceAttachedBar class preserves existing offsets, clamps effective alpha and retains local background-alpha factors; rebinding is idempotent and destruction releases the reference without destroying the separately owned background. It is used by both source Psych health and time fills. Native/base behavior and NV's existing composite HUD adapter retain their own paths.

In source Psych mode, timeBar and the matching global sprite name point to the actual progress fill, while timeTxt points to the native text. Legacy/base and NV label aliases remain unchanged. Moving notes already use live receptor Y; the previous opacity fix makes the source hide/reveal work alongside that movement. No chart/mod names are used in production branches and no donor/imported mod files were edited.

## Validation

Windows build and run.bat test passed 2,215 tests across 715 modules in 130.8 seconds, with 345 skips and zero failures. Focused tests exercise real subclass reflected property writes, offsets, alpha, rebind/destruction, mode-specific aliases and background-binding order.

Muted native checks passed at 60 and unlimited FPS over two song entries each. They verify both fills/backgrounds and both receptor banks move away and return, live note Y follows the moved/returned receptor, enemy note opacity recovers, both extra wizards remain present, and Lua getter arrays retain source indexing. Captures were inspected. Related NV native checks passed at both caps. 70 protected donor/import/settings hashes remained unchanged. Receipts, captures and binary/source hashes are in `tmp/psych-hud-checkpoint.json`.

## Remaining scope

This verifies the reported relative intro movement and upscroll note-Y route. A complete modern source Bar port (child/clip/absolute-origin parity and all group transforms) and full Psych note copyX/copyY/copyAngle/offset parity remain roadmap work. Phase 2 is unfinished. No release was published.
