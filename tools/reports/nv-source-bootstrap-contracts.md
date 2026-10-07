# Nightmare Vision source bootstrap contract

Audit date: 2026-10-06
Donor: `fnf_sources/NightmareVision`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.

`NightmareVisionBootstrap<TState>` sequences the pinned `Init.create()` body behind a typed host. Its operations preserve the donor order: initialize controls; load preferences and highscores; restore `StoryMenuState.weekCompleted`; apply default antialiasing; initialize Discord; push global Mods and load the top mod; configure Flixel services; initialize `FunkinScript`; initialize HotReload, Mod, DebugText and FullScreen plugins; initialize optional video and Tracy services; populate `ModPlugin`; retain `assets/music/freakyMenu.ogg`; call the base state `create()`; then request the selected startup constructor.

The Flixel service hook groups the donor's fixed-timestep, lost-focus frame rate, mute and volume keys, prevented Tab key, mouse visibility, draw-on-top plugins, ratio scale mode and pre-switch scale reset, persistent extended music sound, and auto-pause settings. The separate plugin hooks preserve the order required by plugin population. Source preferences and highscores belong to the authenticated owner scope supplied by the native host.

The donor selects the actual `Class<FlxState>` stored in `Main.startMeta.initialState` when `startMeta.skipSplash || !ClientPrefs.toggleSplashScreen`; otherwise it selects the `Splash` class. The startup metadata value is a typed class field, not a parsed classname. The host supplies typed constructor closures for that class and `Splash`, and the core chooses between them using the source predicate. There is no classname reflection or added fallback policy.

Plugin `onLoad` callbacks run during `ModPlugin.populate()` and can request a state before Init submits its startup request. The bootstrap preserves that order and does not short-circuit based on pending navigation. It passes a constructor closure through `switchStartup`, matching the source `FlxG.switchState(() -> Type.createInstance(nextState, []))` boundary. Errors propagate at the operation that failed, and later operations do not run.

The focused interpreter fixture checks exact ordering, plugin and startup constructor queueing, splash versus initial class selection (including the short-circuited preference read), and failure propagation. Run with:

```powershell
$env:PYTHONPATH='tools/tests'
python -m unittest test_nightmare_vision_bootstrap
```

No build or full suite is included in this bounded contract package.
