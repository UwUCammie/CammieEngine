# Nightmare Vision mod config contract

The compatibility core follows `Mods.applyModConfig` at pinned donor revision
`733165c42ca71eb0961a70e4173b2d81ba4a29ea` in
`fnf_sources/NightmareVision/source/funkin/Mods.hx`.

After `getPack(directory)` returns a pack, `NightmareVisionModsContext` assigns
that pack to `currentModConfig` and applies effects through the typed
`NightmareVisionModConfigHost`. If lookup returns null, it performs no effects.
An explicit lookup directory does not select a family member: the donor options
and `Paths` calls continue to use `currentModDirectory`. Config assignment
precedes the host callbacks. Callback exceptions propagate without rolling back
the config or prior effects. A missing host or missing selected family root
throws after config assignment, before native side effects.
Changing `currentModDirectory` only changes family selection; config effects run
only after the source separately calls `applyModConfig` or `loadTopMod`.

The runtime binds one config host per live context. An unbound call retains the
parsed pack and throws a diagnostic; a second bind throws rather than replacing
captured native services. After a callback failure the same context and host
remain live, so a later source call retries the whole source application. On
release, the context retires its applier and detaches the family session; it
does not own or dispose the host's native services.

The applier calls the live-config callback, owner option initialization, title,
default icon path, optional icon path and existence check, icon assignment,
transition, RPC id, font lookup and assignment, then the four prefix checks and
assignments in `UI_PREFIX`, `COMBO_PREFIX`, `RATINGS_PREFIX`,
`COUNTDOWN_PREFIX` order. Missing window title uses the host's default title.
Missing icon keeps `images/branding/icon/icon64.png`; a missing configured icon
also reports the source warning. Missing transition selects the donor default,
`SWIPE`. The transition parser accepts base/swipe and fade without case
sensitivity; other values retain their original case in `SCRIPTED(key)`. A
missing RPC id restores the donor's `DiscordClient.NMV_ID` through the host.
The configured font path is resolved for the existence check and resolved
again for assignment when present, matching the donor expression; otherwise
the resolved `vcr.ttf` path is used. A prefix is accepted only when its
selected-package `images/<prefix>` directory exists.

## Native host integration boundary

The host is intentionally typed, and config application fails loudly until it
is bound. The root runtime supplies the native effects and must preserve these
source semantics:

- `resolveSelectedPath` uses source `Paths.getPath(relative, null, true)` for
  the selected imported member. `resolveSelectedFont` uses source
  `Paths.font(key)`. Existence and directory checks use the same owner-aware
  asset layer.
- `initializeOptions(selectedDirectory, selectedRoot)` shares the expanded
  `NightmareVisionSourceOptions` owner-private service. It must preserve source
  `ModOptions.init` flush-on-owner-change, clear, load and order-validation
  behavior without binding donor `FlxSave` or touching user settings.
- `updateLiveConfig` publishes the config identity immediately after
  `currentModConfig` assignment. The state factory implements the donor
  `FunkinGame.switchState` redirect check against the requested class name,
  verifies `scripts/states/<scriptName>` through the selected owner, logs a
  missing script, and uses the source scripted-state handoff when present.
- Window title/icon, both transition fields, RPC id, default font, and each
  prefix are assigned through current native services. The prefix callbacks
  remain separate so callback failures preserve prior assignments.
- The pinned Discord source defines `NMV_ID` as
  `1252033037680513115` in its native Discord branch and `''` in its dummy
  branch. The root host supplies the branch-appropriate value.

`tools/tests/test_nightmare_vision_mod_config.py` exercises source callback
order, absent values, missing icons, fallback values, scripted transition case,
exception partial state, and family selection. The existing
`test_nightmare_vision_source_api_contexts.py` suite now binds an explicit
recording host where valid `loadTopMod`/`applyModConfig` calls occur, retaining
its family-list and corrupt-config checks.

These tests cover the pure application core and recording host. Native window,
save, RPC, transition, path, and state-factory behavior remains the root
integrator's responsibility and is not claimed by this report.

Subsequent root integration, native component evidence and remaining state-factory
limits are recorded in [the integration checkpoint](nv-family-config-integration.md).
