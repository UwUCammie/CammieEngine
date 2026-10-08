# Chart scripting API coverage audit

Generated: 2026-10-08

This is a static source audit. `implemented` means a literal binding, direct dispatch, explicit callback-name alias, or fully traced source-binder call chain was found; `names-only` means the name occurs without such evidence; `unverified` marks broad reflective reachability; `missing` means no route was found. Every `implemented` entry remains behaviorally unverified unless separately supported by an execution-and-assertion test.

## Source snapshots

| Source | Version | Revision | Tracked tree | Haxe files | Path |
|---|---|---|---|---:|---|
| Engine | 0.0.19 | ce671830 | modified | 761 | `C:\Users\uwucammie\Documents\coding\FNF\Cammie-Engine` |
| Psych Engine | Psych Engine 1.0.4 / project 0.2.8 | 5c67ced | clean | 157 | `C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\FNF-PsychEngine` |
| Nightmare Vision | NMV 1.0 / project 0.2.7 | 733165c | clean | 239 | `C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\NightmareVision` |

## Coverage summary

| Dialect | Inventory | Implemented | Unverified | Names only | Missing |
|---|---|---:|---:|---:|---:|
| Nightmare Vision HScript | dispatched callbacks | 42 | 0 | 1 | 0 |
| Nightmare Vision HScript | seeded globals | 74 | 0 | 21 | 31 |
| Nightmare Vision chart state | PlayState member surface | 0 | 111 | 0 | 105 |
| Psych HScript | seeded globals | 62 | 0 | 0 | 0 |
| Psych Lua | registered functions | 246 | 0 | 0 | 0 |
| Psych chart hooks | dispatched callbacks | 39 | 0 | 0 | 0 |

## Wired source binder routes

- **Psych HScript / Psych plain HScript owner preset**: `wired`; 17 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install seeds a SourceIrisBridge owner → installHscriptPreset installs PsychHscriptSourceBindings → installHscriptPreset attaches and supplies callback scope → PsychSourceCallbackRegistry.bridge provides source facades. Behavior remains unverified.
- **Psych HScript / Psych embedded runHaxeCode preset**: `wired`; 17 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install exposes a runHaxeCode closure using module() → PsychRuntimeBindings.module creates SourceIrisBridge → PsychRuntimeBindings.module installs HScript preset → installHscriptPreset installs PsychHscriptSourceBindings → installHscriptPreset attaches and supplies callback scope → PsychSourceCallbackRegistry.bridge provides source facades. Behavior remains unverified.
- **Psych Lua / Psych Lua achievements callbacks**: `wired`; 6 globals supported by the complete static chain. PlayState.makeHaxeState creates LuaCompatInterp for translated Lua → PlayState.makeHaxeState seeds compatibility bindings → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install routes LuaCompatInterp to achievements and standard services → PsychAchievementsIntegration.installLua resolves the owner runtime → installLua returns when the owner runtime is unavailable → installLua delegates callback registration to the owner binding. Behavior remains unverified.
- **Psych HScript / Psych HScript Achievements global**: `wired`; 1 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install seeds a SourceIrisBridge owner → installHscriptPreset installs PsychHscriptSourceBindings → PsychHscriptSourceBindings.install routes to achievement integration → PsychAchievementsIntegration.installHscript requires SourceIrisBridge → installHscript resolves the owner runtime → installHscript delegates the class token to owner bindings. Behavior remains unverified.
- **Psych Lua / Psych Lua Language callbacks**: `wired`; 2 globals supported by the complete static chain. PlayState.makeHaxeState creates LuaCompatInterp → PlayState.makeHaxeState seeds compatibility bindings → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install routes LuaCompatInterp to achievements and standard services → PsychStandardServices.installLua resolves the owner runtime → installLua returns when the owner runtime is unavailable → PsychStandardServices.installLua delegates to PsychLanguageBindings → PsychLanguageBindings.installLua registers getTranslationPhrase → PsychLanguageBindings.installLua registers getFileTranslation. Behavior remains unverified.
- **Psych Lua / Psych Lua Discord callbacks**: `wired`; 2 globals supported by the complete static chain. PlayState.makeHaxeState creates LuaCompatInterp → PlayState.makeHaxeState seeds compatibility bindings → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install routes LuaCompatInterp to achievements and standard services → PsychStandardServices.installLua resolves the owner runtime → installLua returns when the owner runtime is unavailable → PsychStandardServices.installLua delegates to PsychDiscordBindings → PsychDiscordBindings.installLua registers changeDiscordPresence → PsychDiscordBindings.installLua registers changeDiscordClientID. Behavior remains unverified.
- **Psych HScript / Psych HScript Language import (plain HScript)**: `wired`; 1 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install seeds a SourceIrisBridge owner → installHscriptPreset installs PsychHscriptSourceBindings → PsychHscriptSourceBindings.install routes to standard services → PsychStandardServices.installHscript requires SourceIrisBridge → installHscript resolves the owner runtime → installHscript returns when the owner runtime is unavailable → installHscript delegates to PsychLanguageBindings → PsychLanguageBindings.install binds backend.Language. Behavior remains unverified.
- **Psych HScript / Psych HScript Language import (embedded runHaxeCode)**: `wired`; 1 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install exposes a runHaxeCode closure using module() → PsychRuntimeBindings.module creates SourceIrisBridge → PsychRuntimeBindings.module installs HScript preset → PsychHscriptSourceBindings.install routes to standard services → PsychStandardServices.installHscript requires SourceIrisBridge → installHscript resolves the owner runtime → installHscript returns when the owner runtime is unavailable → installHscript delegates to PsychLanguageBindings → PsychLanguageBindings.install binds backend.Language. Behavior remains unverified.
- **Psych HScript / Psych HScript DiscordClient import (plain HScript)**: `wired`; 1 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install seeds a SourceIrisBridge owner → installHscriptPreset installs PsychHscriptSourceBindings → PsychHscriptSourceBindings.install routes to standard services → PsychStandardServices.installHscript requires SourceIrisBridge → installHscript resolves the owner runtime → installHscript returns when the owner runtime is unavailable → installHscript delegates to PsychDiscordBindings → PsychDiscordBindings.install binds backend.DiscordClient. Behavior remains unverified.
- **Psych HScript / Psych HScript DiscordClient import (embedded runHaxeCode)**: `wired`; 1 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install exposes a runHaxeCode closure using module() → PsychRuntimeBindings.module creates SourceIrisBridge → PsychRuntimeBindings.module installs HScript preset → PsychHscriptSourceBindings.install routes to standard services → PsychStandardServices.installHscript requires SourceIrisBridge → installHscript resolves the owner runtime → installHscript returns when the owner runtime is unavailable → installHscript delegates to PsychDiscordBindings → PsychDiscordBindings.install binds backend.DiscordClient. Behavior remains unverified.
- **Nightmare Vision HScript / Nightmare Vision chart owner globals**: `not-wired`; 0 globals supported by the complete static chain. PlayState.initializeNightmareVisionScripts passes seedNightmareVision to gameplay loader → NightmareVisionGameplayScripts.loadScope invokes configure → seedNightmareVision calls shared owner seeder → seedNightmareVisionCommon calls bindOwner → NightmareVisionSourceBindings.bindOwner contains literal name bindings. Behavior remains unverified.
- **Nightmare Vision HScript / Nightmare Vision chart-local globals**: `not-wired`; 0 globals supported by the complete static chain. PlayState.initializeNightmareVisionScripts passes seedNightmareVision to gameplay loader → NightmareVisionGameplayScripts.loadScope invokes configure → seedNightmareVision calls shared owner seeder → seedNightmareVision calls bindGameplay with inPlaystate=true and fields map → NightmareVisionSourceBindings.bindGameplay contains literal and gameplayNames bindings. Behavior remains unverified.

## Uncovered names

- **Nightmare Vision HScript / dispatched callbacks / names-only (1):** `onCountdownTick`
- **Nightmare Vision HScript / seeded globals / missing (31):** `BackgroundDancer, BackgroundGirls, CutsceneHandler, Defines, EaseEvent, EventTimeline, FlxEmitter, FlxSpriteElement, FunkinScript, HScriptState, HScriptSubstate, ModEvent, ModManager, Modifier, NoteModifier, Random, ScriptedModifier, ScriptedState` … (+13 more)
- **Nightmare Vision HScript / seeded globals / names-only (21):** `DialogueBox, Dynamic, FlxBarFillDirection, FlxKey, FlxSpriteUtil, FunkinSound, Main, OpenFlAssets, StrumNote, getInstance, global, initScript, instakillOnMiss, keyToString, practice, script, songLength, startedCountdown` … (+3 more)
- **Nightmare Vision chart state / PlayState member surface / missing (105):** `KillNotes, _modchartVector, _parsedEvents, addCharacterToList, applyStageData, audio, automatedDiscord, callHUDFunc, callScript, camZooming, camZoomingDecay, camZoomingMult, cameraLerping, canAccessEditors, canReset, changeCharacter, changedDifficulty, checkEventNote` … (+87 more)
- **Nightmare Vision chart state / PlayState member surface / unverified (111):** `RecalculateRating, SONG, arrowSkins, bads, beatHit, beatsPerZoom, botplayTxt, boyfriend, boyfriendCameraOffset, boyfriendGroup, boyfriendPosition, callEventScript, callNoteTypeScript, camCurTarget, camFollow, camGame, camHUD, camOther` … (+93 more)

## Dynamic surfaces

- Engine HScript uses Nightmare Vision `PlayState` class-parent reflection: `true`. Member-by-member coverage is marked unverified where a matching engine declaration exists.
- Literal Nightmare Vision event dispatches currently found in engine: 46.
- Runtime-computed callback names and members reachable through dynamic objects cannot be enumerated by this audit.

## Local example corpus

- Windows example root: `C:\Users\uwucammie\Documents\coding\FNF\fnf_example_mods` (available).
- Psych: `C:\Users\uwucammie\Documents\coding\FNF\fnf_example_mods\psych` (available).
- Nightmare Vision: `C:\Users\uwucammie\Documents\coding\FNF\fnf_example_mods\nightmare vision` (available).
- Existing tests with the former Linux example-root literal: 88 modules; use the Windows roots above for local corpus evidence.

## Reproduction

```powershell
python tools/audit_script_api_coverage.py --output tools/reports/script-api-coverage.md --contract-output tools/reports/script-api-contracts.json
```
Use `--json-output <path>` for full coverage evidence and `--contract-output <path>` for the source contract snapshot. Contract snapshots keep exact test-reference counts and sample at most two files per evidence class; neither name references nor semantic candidates are behavior proofs.
