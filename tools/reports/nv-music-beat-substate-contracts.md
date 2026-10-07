# Nightmare Vision MusicBeatSubstate contract

Audit date: 2026-10-06
Donor: `fnf_sources/NightmareVision`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`
Scope: native `MusicBeatSubstate` lifecycle base and focused extracted fixture. No donor or chart-content changes. No full build or rendered transition result is claimed.

## Donor contract

`funkin.backend.MusicBeatSubstate` updates its beat clock from the live conductor and note offset. When the step changes, it calls at most one `stepHit`, gated on `curStep > 0`, even when several steps were crossed. A beat-aligned step calls `onBeatHit([curBeat])` before `onStepHit([curStep])`. If a song is active, it then updates or rolls back section timing. It calls `onUpdate([elapsed])` before native child updates. It does not dispatch state-plugin hooks or add state-only callbacks. Its script prefix defaults to `substates`; `initStateScript` optionally runs an empty `onLoad` when no file exists. `destroy` broadcasts `onDestroy` before disposing the script group. Source: `source/funkin/backend/MusicBeatSubstate.hx`.

`ScriptedTransition.create()` changes the prefix to `transitions`, loads its key with `callOnLoad=false`, calls the inherited `create()`, and then broadcasts `onLoad`. The new host subtype carries `createSubstateScript(prefix, name, parent, group)` so that path and interpreter creation stay within the captured source owner. Source: `source/funkin/states/transitions/ScriptedTransition.hx`.

## Implemented and checked

`source/NightmareVisionMusicBeatSubstate.hx` implements the source substate timing, beat/step/section callback order and arguments, one-callback-on-step-change behavior, `onUpdate` ordering, owner-aware `refreshZ`, optional script loading, and `onDestroy` before group teardown. It does not release the captured family session. The dedicated fixture checks default `substates` prefix and class-name lookup, parent binding, beat and section behavior on forward jumps and rollback, callback arguments, update order, sorting, and idempotent teardown.

Focused check: `python -m unittest discover -s tools/tests -p test_nightmare_vision_music_beat_substate.py` passed (1 test, Haxe interpreter fixture). This does not compile the full native target or verify rendered transitions.

## Remaining limits

This base covers the donor `MusicBeatSubstate` contract used by scripted transitions. Full generic source substate switching and lifecycle behavior remains open. The current script-creation callback returns `null` for both missing and failed scripts, so the inherited `initStateScript(callOnLoad=true)` cannot distinguish the donor's missing-file `onLoad` from its parse-failure early return. `ScriptedTransition` itself calls `onLoad` after `create` in either case, matching its donor call site.
