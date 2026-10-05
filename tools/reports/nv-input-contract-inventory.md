# Nightmare Vision input contract inventory

Source audit of pinned NV revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, followed by the 5 October 2026 input/playfield package. Implementation subtasks used GPT-6 Luna with Max reasoning.

## Reachable gaps

`seedNightmareVisionCommon` now installs owner-scoped source `Controls`, `Action`, `Control`, `Device`, `KeyboardScheme`, `InputSystem`, and `InputEvent` bindings. Bare and `game` controls/input access resolve the matching live owner. `PsychControlsCompat` retains Psych polling and live preference maps; NV's source action registry and event system remain distinct where the donor contracts differ.

## Controls

NV `Controls` extends `FlxActionSet`. `new(name, scheme=None)` creates 35 `FlxActionDigital` objects: held/press/release triplets for four UI directions, four note directions and dodge; just-pressed actions for accept, back, pause, reset, fullscreen, debug display and soft/hard reload. `actions` and `customActions` are mutable maps; `gamepadsAdded=[]`, `keyboardScheme=None`. `init()` constructs `instance` with Solo, adds connected gamepads and connection callbacks, then clears customActions and resets the controls menu groups.

`addCustomKey(name, keys)` lowercases without trimming, copies/pads keys with NONE to length two, registers three digital actions in both maps, calls ClientPrefs.addCustomKey, then binds. `checkCustom(name)` lowercases and returns false for missing actions. `customBind(name, keys)` filters NONE and appends keyboard inputs; it does not replace existing inputs. Built-in `bindKeys`/`unbindKeys` fan out to the control's phases. `setKeyboardScheme(scheme, reset=true)` removes keyboard inputs only; Solo reads current preference arrays, Duo uses fixed donor defaults, None/Custom add nothing. Later preference-map edits alone do not rebind existing action inputs.

`bindButtons(control,id,buttons)`/`unbindButtons(control,id,buttons)` preserve gamepad IDs. `addGamepad(id,?buttonMap)` records an ID and binds the map. `removeGamepad(deviceID=ALL)` removes matching action inputs; the donor removes only that exact ID from gamepadsAdded, even for ALL. `getInputsFor(control,device,?list)` appends IDs to the supplied list or a new array. `removeDevice` clears the chosen device. `copyFrom(controls,?device)` appends shared input objects, merges gamepad IDs and merges keyboard schemes (None adopts source; otherwise Custom).

## InputSystem and InputEvent

`InputSystem` extends EventDispatcher and implements IFlxDestroyable. Mutable static `ACTION_LIST` defaults to note_left/down/up/right. `new(?controls)` defaults to Controls.instance and captures action objects and per-lane physical-input lookup arrays at construction. Missing held/press/release action throws `Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]`. Subsequent remapping does not refresh the event lookup.

`inputPressed`, `inputJustPressed`, `inputJustReleased` directly check captured actions. Stage keyboard and low-level gamepad callbacks queue timestamped events. Keyboard repeat suppression uses native checkStatus. Axis events are resolved during update. `update()` dispatches FIFO; duplicate physical bindings map to the first lane. The donor gamepad lookup uses inputID, without filtering event deviceID. `destroy()` removes keyboard, gamepad and connection hooks; it does not destroy Controls.

`InputEvent` extends OpenFL Event. Constants are `inputDown`/`inputUp`. Constructor takes `(type,bubbles=false,cancelable=false,noteData,device,inputID,timer)`. Fields retain the physical device/input and Lime millisecond timer. Queued events are cancelable. The source documentation mentions `cancel()`, but the implementation supplies only inherited Event APIs, including `preventDefault()`; no invented cancel alias is warranted.

## Implemented integration boundaries

Owner-scoped Controls uses real Flixel action objects and preserves `tools/patch_flixel_input_frame_cache.py`'s update-frame serial, avoiding millisecond cache regressions at uncapped FPS. Psych polling remains separate.

Modules: `NightmareVisionControls`, namespaced `nightmarevision.input.NightmareVisionInputEnums`, `NightmareVisionInputEvent`, `NightmareVisionInputSystem`, `NightmareVisionInputScope`, and `NightmareVisionInputBindings`. Constructor factories take precedence over compiled classes with colliding names. Persistent bindings retain an owner key and current-scene resolver rather than a destroyed scene. Replacing Controls or InputSystem remains scene-owned; teardown releases hardware hooks, queued events, action references and script event listeners. Public InputSystem.destroy retains the source contract of not destroying Controls.

PlayState creates the default system just before onCreatePost, drains input once per host update outside the 60 Hz script batch, and routes press/release to the existing judgment path. A press uses playing audio time minus Lime event dispatch latency, restoring Conductor before source post-input hooks and on error. Field signals invoke the hit/miss core once; mutable field IDs do not change note membership or authored field coordinates.

Focused executable checks cover actual Flixel actions/OpenFL events, FIFO/repeat/duplicate binding rules, cancellation and listener priority, captured action/remap semantics, owner isolation and teardown, factory resolution, and extracted host timestamp routing. Field tests cover collection mutations/signals, receptor generation, alpha target times field multiplier without compounding, and source note membership. Windows native/full-suite results are recorded separately when the checkpoint finishes.

## Remaining contracts

- `ControlsSubState.resetGroups` requires imported menu integration and remains open.
- Physical controller/hotplug/axis behavior has executable contract coverage but has not been exercised with real controller hardware.
- Owner-scoped script-created PlayField construction for supported key counts is verified in `nv-field-construction-contracts.md`. Quant note/receptor colors and reloads are verified within the four-lane Sparrow boundary in `nv-quant-contracts.md`. Wider-key/pixel layouts, full source visual/group/splash/underlay parity, source Note reflection/recycle and broader modifier generation remain open.
- Full timing parity across arbitrary paused/per-event mutations and every donor chart is not established by the bounded input probes.
- No donor or imported mod/chart files were edited for the implementation.
