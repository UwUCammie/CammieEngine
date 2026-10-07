# Nightmare Vision source Main runtime contract

Audit and implementation date: 2026-10-07
Donor: `fnf_sources/NightmareVision/source/Main.hx`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.

The owner-local Main binding helper exposes the pinned source version constants, the session's actual mutable `startMeta` struct, `resetSpriteCache`, and the owner-bound `onResize` callback when the source session installs it. `startMeta` is a final struct reference in the donor, and its fullscreen member is spelled `startFullScreen`. The donor has no `Main.instance` field.

`Main.resetSpriteCache(sprite)` preserves the source implementation: null is accepted, and the OpenFL `Sprite.__cacheBitmap` and `__cacheBitmapData` fields are cleared through private access. `Main.onResize(width, height)` is available through source `Reflect` and `Type` lookup despite being private in the donor. It preserves the donor's unused scale calculation, clears `flashSprite` caches only for non-null cameras with non-null filters, then clears the current `FlxG.game` cache when present.

The source `Main` constructor registers a `KeyboardEvent.KEY_DOWN` listener on the current Flixel stage with capture disabled and priority 100. It stops immediate propagation only for Enter with Alt held. It then initializes `DebugDisplay` and adds `onResize` to `FlxG.signals.gameResized`. `NightmareVisionMainRuntime.install()` captures those exact stage and signal objects and callback identities; `release()` removes the listeners from those captured objects, even if Flixel globals have since changed. Runtime callbacks retained by an old interpreter fail after owner release.

The imported session cannot safely replay the rest of the application constructor. `Main.main()` calls `Lib.current.addChild(new Main())`, while `new Main()` constructs a new `FunkinGame`; doing that inside the already-running host would create a separate game. The owner-local bindings raise explicit source diagnostics for these calls, and `Main` remains an owner metadata identity rather than an alias for the native host `Main`.

Other constructor operations remain outside this owner-local contract:

- `CrashHandler.init()` is compiled only under `CRASH_HANDLER && !debug` and installs process-level crash handling.
- `initHaxeUI()` is compiled only under `haxeui_core`; it changes the global Toolkit theme, scaling and focus behavior, and tooltip delay.
- `WindowUtil.resetWindow()` changes the application window and has no captured source-window host contract.
- `ClientPrefs.loadDefaultKeys()` and `tryBindingSave('funkin')` act on the donor's application save. The imported owner uses the source session's scoped preference services instead.
- `DebugDisplay.init()` has no matching source-owned host in this integration.
- Under `DISABLE_TRACES`, the donor replaces process-global `haxe.Log.trace`; the imported session does not replace the host logger.
- The donor's static `__init__` runs `MacroUtil.haxeVersionEnforcement()` and changes process-global OpenFL log level. Imported `Main` does not run those app-startup effects.

The focused regression is `tools/tests/test_nightmare_vision_main_runtime.py`. It exercises Alt+Enter behavior and listener priority, real resize-signal dispatch, filtered and unfiltered cameras, game cache reset, exact listener teardown after host references change, reflection through the real `NightmareVisionScriptInterp`, and cache invalidation on the actual OpenFL `Sprite` class. Run only this bounded test with:

```powershell
$env:PYTHONPATH='tools/tests'
python -m unittest test_nightmare_vision_main_runtime
```

The component agent's three focused tests pass. The primary agent performed the integration gates below.

## Integrated checkpoint, 7 October 2026

The source session owns one Main runtime. Init installs its listeners before resetting controls; the common interpreter install also covers cold gameplay entry, with idempotent listener registration. Session departure releases that captured runtime. Main metadata uses the donor's `startFullScreen` spelling, and all source Main bindings now use the single helper rather than duplicated session bindings.

The Windows development build passed. The related suite passed 10 tests, and the full suite passed 2,405 tests across 791 modules in 374.1 seconds with four workers, 343 existing skips and zero failures. Evidence: `tmp/nv-main-runtime-build.log`, `tmp/nv-main-runtime-focused.log` and `tmp/nv-main-runtime-full-tests.log`. Built executable SHA-256: `6AFB4CF5F1CA32B69953C8D7529094BEFFA0169CD3767E213DB86DEA7BA3208C`; the binary gate is `tmp/nv-main-runtime-build-gate.json`.

The actual retained importer-to-Init/state pipeline passed muted at 60 and unlimited FPS using isolated saves. An imported source plugin invoked Main cache helpers directly and through its Type/Reflect scope on real native OpenFL sprites, resolved `onResize`, and exercised the live resize signal. Departure verified removal of the source resize listener and retirement of its captured stage. These native checks also retained the existing constructor, redirect, reset, score and settings-restoration assertions. Alt+Enter behavior and priority have focused component evidence, not a physical-key native acceptance claim.

Native receipts are `tmp/nv-retained-state-native-run-60-d0cf387309.json` and `tmp/nv-retained-state-native-run-unlimited-526a66b5f2.json`. Four generated title/redirect captures were inspected at 1280 by 720. The captures prove the component still renders through the source pipeline; they do not certify stock source-menu visual parity. Expected missing-icon diagnostics from the small fixture remain recorded. The required source audit found both donor tracked trees clean, and all 70 protected input hashes matched. An independent Luna review found no actionable issues.

Checkpoint receipt: `tmp/nv-main-runtime-checkpoint.json`. This is progress on Phase 2, which remains incomplete. Original Main application construction and process-level startup effects remain explicitly unsupported as described above. Native Splash/video acceptance, remaining Psych/NV API and menu destinations, imported entry through I and stock-menu acceptance remain open. No donor/chart/mod files, visual quality or release publication changed.
