# Chart scripting API coverage audit

Generated: 2026-10-06

This is a static source audit. `implemented` means a literal binding, direct dispatch, explicit callback-name alias, or fully traced source-binder call chain was found; `names-only` means the name occurs without such evidence; `unverified` marks broad reflective reachability; `missing` means no route was found. Every `implemented` entry remains behaviorally unverified unless separately supported by an execution-and-assertion test.

## Source snapshots

| Source | Version | Revision | Tracked tree | Haxe files | Path |
|---|---|---|---|---:|---|
| Engine | 0.0.15 | 454f0bcd | modified | 638 | `C:\Users\uwucammie\Documents\coding\FNF\Cammie-Engine` |
| Psych Engine | Psych Engine 1.0.4 / project 0.2.8 | 5c67ced | clean | 157 | `C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\FNF-PsychEngine` |
| Nightmare Vision | NMV 1.0 / project 0.2.7 | 733165c | clean | 239 | `C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\NightmareVision` |

## Coverage summary

| Dialect | Inventory | Implemented | Unverified | Names only | Missing |
|---|---|---:|---:|---:|---:|
| Nightmare Vision HScript | dispatched callbacks | 40 | 0 | 3 | 0 |
| Nightmare Vision HScript | seeded globals | 91 | 0 | 12 | 23 |
| Nightmare Vision chart state | PlayState member surface | 0 | 100 | 0 | 116 |
| Psych HScript | seeded globals | 61 | 0 | 0 | 1 |
| Psych Lua | registered functions | 236 | 0 | 0 | 0 |
| Psych chart hooks | dispatched callbacks | 39 | 0 | 0 | 0 |

## Wired source binder routes

- **Psych HScript / Psych plain HScript owner preset**: `wired`; 17 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install seeds a SourceIrisBridge owner → installHscriptPreset installs PsychHscriptSourceBindings → installHscriptPreset attaches and supplies callback scope → PsychSourceCallbackRegistry.bridge provides source facades. Behavior remains unverified.
- **Psych HScript / Psych embedded runHaxeCode preset**: `wired`; 17 globals supported by the complete static chain. PlayState.makeHaxeState creates SourceIrisBridge for plain HScript → PlayState.makeHaxeState calls seedEngineCompat(interp) → PlayState.seedEngineCompat constructs PsychRuntimeBindings → PlayState.seedEngineCompat calls runtime.install() → PsychRuntimeBindings.install exposes a runHaxeCode closure using module() → PsychRuntimeBindings.module creates SourceIrisBridge → PsychRuntimeBindings.module installs HScript preset → installHscriptPreset installs PsychHscriptSourceBindings → installHscriptPreset attaches and supplies callback scope → PsychSourceCallbackRegistry.bridge provides source facades. Behavior remains unverified.
- **Nightmare Vision HScript / Nightmare Vision chart owner globals**: `wired`; 11 globals supported by the complete static chain. PlayState.initializeNightmareVisionScripts passes seedNightmareVision to gameplay loader → PlayState.initializeNightmareVisionScripts loads chart scope → NightmareVisionGameplayScripts.loadScope invokes configure → seedNightmareVision calls shared owner seeder → seedNightmareVisionCommon calls bindOwner → NightmareVisionSourceBindings.bindOwner contains literal name bindings. Behavior remains unverified.
- **Nightmare Vision HScript / Nightmare Vision chart-local globals**: `wired`; 22 globals supported by the complete static chain. PlayState.initializeNightmareVisionScripts passes seedNightmareVision to gameplay loader → PlayState.initializeNightmareVisionScripts loads chart scope → NightmareVisionGameplayScripts.loadScope invokes configure → seedNightmareVision calls shared owner seeder → seedNightmareVision calls bindGameplay with inPlaystate=true and fields map → NightmareVisionSourceBindings.bindGameplay contains literal and gameplayNames bindings. Behavior remains unverified.

## Uncovered names

- **Nightmare Vision HScript / dispatched callbacks / names-only (3):** `onCountdownTick, onCreate, onDestroy`
- **Nightmare Vision HScript / seeded globals / missing (23):** `BackgroundDancer, BackgroundGirls, CutsceneHandler, Defines, EaseEvent, EventTimeline, FlxEmitter, FlxSpriteElement, FunkinScript, HScriptState, HScriptSubstate, ModEvent, ModManager, Modifier, NoteModifier, ScriptedModifier, ScriptedState, ScriptedSubstate` … (+5 more)
- **Nightmare Vision HScript / seeded globals / names-only (12):** `DialogueBox, Dynamic, FlxBarFillDirection, FlxSpriteUtil, FunkinSound, OpenFlAssets, StrumNote, instakillOnMiss, script, this, trace, week`
- **Nightmare Vision chart state / PlayState member surface / missing (116):** `KillNotes, _modchartVector, _parsedEvents, addCharacterToList, applyStageData, audio, automatedDiscord, boyfriendGroup, boyfriendPosition, callHUDFunc, callScript, camZooming, camZoomingDecay, camZoomingMult, cameraLerping, canAccessEditors, canReset, changeCharacter` … (+98 more)
- **Nightmare Vision chart state / PlayState member surface / unverified (100):** `RecalculateRating, SONG, arrowSkins, bads, beatHit, beatsPerZoom, botplayTxt, boyfriend, boyfriendCameraOffset, callEventScript, callNoteTypeScript, camCurTarget, camFollow, camGame, camHUD, camOther, cameraSpeed, canPause` … (+82 more)
- **Psych HScript / seeded globals / missing (1):** `Achievements`

## Dynamic surfaces

- Engine HScript uses Nightmare Vision `PlayState` class-parent reflection: `true`. Member-by-member coverage is marked unverified where a matching engine declaration exists.
- Literal Nightmare Vision event dispatches currently found in engine: 48.
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
