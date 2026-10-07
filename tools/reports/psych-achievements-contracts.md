# Psych 1.0.4 achievements service contract

Audit date: 2026-10-07
Donor: `fnf_sources/FNF-PsychEngine`, revision `5c67ced49e5a98535298a6daa3f8f4ec79ac8399`.

## Donor behavior

The source `backend.Achievements` record contains `name`, `description`, and
optional `hidden`, `maxScore`, `maxDecimals`, `mod`, and `ID`. It keeps three
public static collections: `achievements`, `variables`, and
`achievementsUnlocked`. `init()` registers the core achievements and computes
the boundary used by mod-list reloads. The pinned donor project enables
`PSYCH_WATERMARKS` by default, so `pessy_easter_egg` is part of this source
default. `BASE_GAME_FILES`, `TITLE_SCREEN_EASTER_EGG`, and associated base-game
achievements are under the donor's `officialBuild` section. See donor
`source/backend/Achievements.hx:12-68` and `Project.xml:23-37`.

`load()` initializes defaults on first use and reads unlocked keys and score
variables. `save()` writes `achievementsUnlocked` and `achievementsVariables`.
`getScore`, `setScore`, and `addScore` initialize missing counters, reject
achievements without a positive `maxScore`, clamp at the maximum, and unlock
when the threshold is reached. The default `saveIfNotUnlocked` value controls
the post-save flush. `unlock()` rejects unknown keys, avoids duplicate unlocks,
rate-limits `confirmMenu` to one sound per 100 milliseconds, flushes the save,
and starts a popup unless suppressed. See donor
`source/backend/Achievements.hx:76-178`.

`reloadList()` removes existing mod-owned records when needed, resets sort IDs,
then reads the base achievement file followed by each enabled mod's file. The
JSON loader skips null records, missing or blank `save` keys, and duplicate
keys; parse failures are reported and do not stop later source files. New
records get sequential IDs and the active mod name. See donor
`source/backend/Achievements.hx:201-278`.

## Owner implementation

`PsychAchievements` keeps those maps and operations on one service instance,
and `PsychAchievementsBindings` exposes the actual class token under
`backend.Achievements` in `SourceNativeClassScope`. Its `install()` binds the
HScript global/import; `installScope()` installs the same static routes for
captured Lua class reflection. The helper composes `Reflect.fields`,
`Reflect.hasField`, and `Type.getClassFields` with routes already present on the
interpreter, including the source methods and mutable maps. Returned method
handles retain the owner guard.

Save data uses only the selected import's `CodenameOwnerSaveData` view and the
donor field names. `variables` are encoded as a JSON-safe ordered entry list and
restored as a typed live `Map<String, Float>`; `achievementsUnlocked` is restored
as a live `Array<String>`. The source maps remain directly mutable, and callers
can persist direct changes by calling `save()`, as in the donor. The shared
storage integration uses the opt-in non-flushing write mode for this service:
`save()` writes both fields without an implicit flush, while `unlock()` and the
score path retain the donor's explicit flush points. Other owner save clients
continue using the default immediate-write behavior.

The host supplies the already ordered, owner-authorized base and enabled-mod
JSON paths, a reader restricted to those paths, the captured Psych Paths
facade, diagnostics, clock, sound, and popup-manager callbacks. The service
never changes global mod selection state or exposes native save data. The
popup manager owns live popup stacking and visibility; `startPopup()` passes
the selected record and donor `endFunc` argument to that manager. As in the
pinned popup class, `endFunc` is not called by the popup itself.

`PsychAchievementsLuaBindings.install()` registers the six donor Lua callback
names on the translated interpreter and delegates to this same owner service.
Unknown score callbacks report their callback-specific diagnostic and return
`-1`; unknown unlock/unlocked callbacks return `null`; existence checks return
`false`. The score defaults are `0` for set and `1` for add, both defaulting to
save when unlocked, while unlock defaults to showing the popup. See donor
`source/backend/Achievements.hx:286-334`.

Windows file errors are reported through the captured owner diagnostic callback
instead of opening a process-wide OS alert. Enabled-mod discovery remains the
host's responsibility; `reloadList()` consumes the provided list and does not
mutate the engine's global Mods context.

## Validation

The focused Haxe fixture exercises default registration, ordered base/mod JSON
loading and diagnostics, duplicate handling, reload cleanup, typed owner-save
restore, direct map mutation, score reads/writes, unlock thresholds and
rate-limited audio, popup metadata, owner isolation, static class imports,
Reflect/Type field discovery, and captured owner guards through both the Iris
interpreter and a shared source class scope.

```powershell
$env:CAMMIE_TEST_TMP='C:/t/cammie-test'
$env:PYTHONPATH='tools/tests'
python -m unittest test_psych_achievements
python -m unittest test_psych_achievements_lua_bindings
```

Result: the service fixture's 2 tests and the Lua callback fixture's 1 test
passed. No game build or full suite was run.
