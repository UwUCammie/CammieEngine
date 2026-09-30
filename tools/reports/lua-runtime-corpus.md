# Mounted Lua runtime compatibility audit

Audit input: `/run/media/cammie/External Storage/FNF-Example-Mods` (read-only),
checked 2026-09-18. The mounted corpus contains 122 `.lua` files; this report
does not include generated destination files or donor edits.

| Metric | Before adapter pass | After adapter pass |
| --- | ---: | ---: |
| Lua files discovered | 122 | 122 |
| Files translated without diagnostics | 121 | 122 |
| Files with a diagnostic | 1 | 0 |
| Files with a raw-Haxe diagnostic | 1 | 0 |
| Parseable generated HScript files | 122 | 122 |

The final camera-angle `runHaxeCode` near-match is now routed through the same
whitelisted native adapter as the other camera-angle blocks. The mounted
`camAngle.lua` template uses the legacy callback-local spelling `els` in its
second update callback even though the actual callback parameter is
`elapsed`; the adapter maps that spelling to the callback delta without
executing interpolated Haxe or editing the donor script. All 21 `runHaxeCode`
calls in 9 files now translate without diagnostics and remain behind the
strict native route allow-list.

The runtime adapter pass covers the highest-frequency general gaps found in the
same scan:

- Psych `Function_Stop`/`Function_Continue` callback results, including
  `onStartCountdown`, `onPause`, and `onEndSong` gates.
- Psych/Kade callback ABI differences for 18 three-argument `onEvent` hooks,
  the one-argument `onMissNote`, and no-argument `onGameOverStart`/`onEndSong`.
- `ClientPrefs.sickWindow`, `ClientPrefs.splashAlpha`, `PlayState.isPixelStage`,
  and `PlayState.chartingMode` class-property aliases.
- `grpNoteSplashes` aggregate property/group access and animated Lua sprite
  Sparrow atlas loading.
- Psych `runTimer(tag, time, 0)` infinite-loop semantics (8 calls across 7
  files); ordinary omitted-loop timers remain one-shot.
- Indexed Psych/Kade property paths now traverse both native arrays and
  `FlxGroup.members`, covering 9 `healthColorArray[0..2]` reads in
  `custom_events/coloredSilhouette.lua` and 4 indexed touch reads across the
  mounted `CAMERA KNOE.lua` variants.
- Text colour helpers now normalize bare six/eight-digit hex values before
  calling FlxColor, covering 14 bare-hex `setTextColor`/`setTextBorder` calls
  in the mounted scripts.
- The same color normalization now feeds Psych `doTweenColor` and
  `makeGraphic`; the mounted corpus has 54 color tweens (49 literal bare-hex
  targets) and 14 graphic calls (8 literal bare-hex targets). Omitted graphic
  colors default to opaque white, matching Psych's optional argument.
- Psych's `camOther`/`other`/`camHUD`/`hud` camera spellings now share one
  native HUD-camera route for object cameras, camera shake, and shader filters.
  The mounted corpus contains 37 `setObjectCamera` calls, including 9 explicit
  `camOther` calls that previously fell through to the game camera.
- Generic Psych property writes now coerce event strings to the live field type
  for numeric and boolean fields, and route generic `color`/`borderColor`
  writes through the shared bare-hex parser.  The mounted corpus has five
  `defaultCamZoom <- value1` writes in `PERFEXION Demo1/custom_events/`
  (`Set Cam ZoomBoom.lua`, `Set Cam ZoomBoomSlow.lua`, `Set Cam Zoom.lua`,
  `Set Cam Default Zoom.lua`, and `Zoom Camera.lua`), plus a bare
  `Silhouette.lua` `setProperty(...'.color', '000000')` write.  These now use
  the same typed property boundary instead of passing Lua strings directly to
  native reflection.
- The legacy Psych camera-angle template now accepts the callback-local `els`
  spelling as an engine-level alias for `elapsed`. This removes the last
  mounted-corpus `lua-raw-haxe` diagnostic while keeping arbitrary
  interpolated Haxe rejected.
- The mounted HellBeats Kade Engine tutorial modchart uses the legacy `songPos`
  global in its live update calculation. Compatibility interpreters now seed
  and refresh `songPos` from `Conductor.songPosition` before ordinary updates
  and again before beat/step dispatch, so Kade/FPS timing remains live without
  a chart-side variable shim. This covers the exact Kade sidecar at
  `hellbeats_kade_engine/HellBeats Kade Engine/assets/data/tutorial/modchart.lua`.
- The same mounted tutorial now has executable compatibility coverage against
  fake native receptors/camera/timing: its difficulty/step gate, live BPM
  calculation, `defaultStrum` reads, all eight `setActorX`/`setActorY` writes,
  and player-turn camera zoom callbacks are exercised after Lua translation.
  Inclusive Lua numeric ranges route through the native `makeRangeArray` helper
  so interpreted HScript does not hand an `IntIterator` to the callback. The
  bare Kade `bpm` alias is refreshed from `Conductor.bpm`, including after a
  section BPM change, while a missing `Voices.ogg` uses a silent native vocal
  track when the chart requests voices. Whitespace-only `0.offset` markers are
  inert; non-empty markers are diagnosed and ignored because no generic timing
  semantics are evidenced by the mounted corpus.
- Psych compatibility interpreters now expose the centralized
  `EngineCompat.psychCompatibilityVersion()` value (`0.7`) as the legacy bare
  `version` global. The two mounted `20changeNote.lua` copies use eight version
  checks to select old versus modern `ClientPrefs`/property paths; those checks
  now execute through the modern compatibility aliases instead of failing on
  an unbound script variable.
- Psych timing globals are now seeded and refreshed from `Conductor`: the
  mounted corpus has six bare `stepCrochet` uses in `Kaboom.lua`,
  `10scriptnote.lua`, and `Used later/scriptnote.lua`, plus four live `curBpm`
  uses in the two `noteMoveOnPress.lua` copies. They now observe BPM changes
  instead of failing as unbound HScript variables or retaining stale beat
  lengths.
- Psych judgement-counter properties now route through the static
  `PlayState` counters. Both mounted `noteMoveOnPress.lua` copies read
  `sicks` and `goods` through `getProperty`; the shared counter alias also
  covers `misses`, `shits`, and `bads` for reads and writes instead of asking
  instance reflection to find static fields.
- Psych's side-specific bare receptor globals now route through an engine-level
  baseline adapter. The mounted `PERFEXION Demo1/data/Xfracture/FuckSake.lua`
  uses `defaultOpponentStrumX0` and `defaultOpponentStrumY0` while shaking the
  opponent receptors, and `PERFEXION Demo1/data/Resonance/Recolor2.lua` uses
  all four `defaultPlayerStrumX0..3` reset globals. The importer rewrites these
  names to side-aware native reads and captures opponent/player baselines from
  their own strumlines, so the route does not depend on combined group order or
  require chart edits. The same allow-list now covers computed `_G` aliases for
  both sides.
- Psych's engine-owned `allowCountdown` gate is now seeded as `true` in every
  compatibility interpreter before `onStartCountdown` is dispatched. Both
  mounted `PERFEXION Demo1/data/Extra/function.lua` and
  `PERFEXION Demo1/data/Extras/function.lua` read the gate twice; they now use
  the native countdown gate and can still return `Function_Stop` or
  `Function_Continue` without requiring a chart-local variable declaration.
- The static judgement-counter audit remains coherent: `getProperty('sicks')`,
  `getProperty('goods')`, and the `misses`/`shits`/`bads` aliases all resolve to
  the same `PlayState` static counters that native judgement code resets and
  increments. Counter writes through `setProperty` use that same route; no
  mounted donor writes a separate script-local counter.

These are centralized in `EngineCompat` and the PlayState Lua boundary. No
chart-specific Lua, donor file, or `HxcCompat*.hx` file is changed.
