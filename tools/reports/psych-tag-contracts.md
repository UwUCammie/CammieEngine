# Psych tagged object replacement checkpoint

Verified locally on 5 October 2026 with GPT-6 Luna at Max reasoning.

Psych Lua constructors now retire an existing same-tag object before creating its replacement. The old object is removed from state members, destroyed, and removed from the shared registry and atlas bookkeeping. Static and animated sprites, owner-scoped constructors and text share the existing destructive removal behavior; FlxAnimate already uses it. Detached objects from removeLuaSprite(tag, false) remain reusable until explicitly replaced or destroyed. This follows donor FunkinLua/TextFunctions and LuaUtils.destroyObject, without changing charts or mod files.

The reported corner icon was a retired subtitle portrait still in the render list. The source script moves the old portrait before creating its replacement; registry replacement alone left the old object visible. Proper lifecycle handling allows that original script to work unchanged.

Windows build and run.bat test passed 2,216 tests across 716 modules in 134.9 seconds, with 345 skips and zero failures. Muted native checks passed twice at 60 and unlimited FPS, including source subtitle replacement and the previous intro HUD/actor/opacity contracts; a related NV native check passed. Captures were inspected and 70 protected donor/import/settings hashes remained unchanged. Receipts and binary/source hashes are in tmp/psych-tag-checkpoint.json.

This verifies tagged constructor replacement, not every source object/tween lifecycle API. Full roadmap Phase 2 remains unfinished. No release was published.
