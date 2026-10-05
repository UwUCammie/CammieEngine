# Psych charting and Nightmare Vision fields checkpoint

Date: 5 October 2026. This is a bounded Phase 2 checkpoint, not full Psych/NV compatibility certification.

## Donor revisions

- Psych Engine tag `1.0.4`, commit `5c67ced49e5a98535298a6daa3f8f4ec79ac8399`.
- Nightmare Vision commit `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.
- Implementation and review subtasks used GPT-6.1 Sol with Medium reasoning, as specified in the updated roadmap.

## General implementation rules

All production changes select an engine dialect or inspect declared structure. No production branch identifies Monster, D-sides, a chart ID, or another test example. Donor charts, scripts, images, shaders and videos remain unchanged. Private native checks temporarily add a probe to an isolated test installation and remove it afterward; they restore the original settings and save bytes.

### NV playfields and older charts

`NightmareVisionPlayFields` exposes a bounded live collection: `members`, `length`, `add`, iteration and `getFieldFromID`. Lookup matches mutable IDs first and then the source array-index fallback. Each declared field gets a distinct native receptor bank; fields zero and one retain the existing player/opponent banks, and later fields use additional native Strumlines. PlayState owns update/draw/destruction, so the collection does not double-update its members.

Field zero is initially BF-owned and manually controlled, field one is Dad-owned and automatic, and fields two and later are BF-owned and automatic. Actor ownership, manual control, autoplay and source field identity are independent. Source note/render/input/hit paths resolve the live field rather than collapsing all additional notes into a binary side. Admission rejects rows outside the declared field count before constructing notes. The modifier manager receives the declared count and the same live receptor arrays.

Selected NV runtime context enables source receptor layout, skins and RGB setup even when an older chart omits `format`. `ChartNoteOwnership.nightmareVisionAddress` matches `NightmareVisionChartApi.fromData`'s legacy correction: the first two banks are section-relative, while additional authored banks retain their IDs. The correction occurs in memory; chart rows on disk are not rewritten. `Note.lane` exposes source field identity, while `noteData` remains local key direction.

NV receptors expose retained source RGB graphics through `rgbShader`/`rgbGraphics`. Psych receptors retain their existing RGB shader object. Full-DCE tests exercise reflected NV color methods and live state.

### Following cameras, beat zoom and character cadence

NV scripts can register additional world cameras through retained `followingCams`. End-of-update synchronization copies the current default world camera's zoom and scroll to registered cameras. It preserves each camera's filters, angle, alpha and ownership, does not alias scroll objects, and clears references on scene teardown.

NV `beatsPerZoom` is a live alias of the host cadence. Source beat pulses precede `onBeatHit`, honor live camera-zoom preferences and per-camera zoom tweens, reset zero cadence to four, and use the current `FlxG.camera`. The legacy host pulse is disabled for the selected NV runtime to avoid a duplicate pulse. The donor's uncapped zoom behavior is preserved; no arbitrary visual clamp is introduced.

Shared characters expose retained `danceEveryNumBeats`, `danceIdle` and `recalculateDanceIdle`. Psych's initial idle/pair cadence and later pair changes differ from NV's JSON-defined cadence, so only that semantic boundary differs. Source Alt Idle Animation uses donor actor selection, exact suffix writes, recalculation, and the Psych/NV target-trimming distinction. Psych GF cadence multiplies its speed by the actor interval; NV's live speed setter multiplies the actor interval on every write. Native and Codename retain their existing cadence gates.

Retained NV `Character.onBeatHit` supports script-created stage actors and matches the pinned Character/Bopper cadence and sing/stunned/holding guards. This fills the direct character call used by stage scripts without introducing a stage-specific workaround. Nonpositive intervals, absent/destroyed actors and other engine dialects are guarded.

### Psych editor and menu handoffs

`PsychOwnerChartingMode` stores the flag per canonical selected Psych owner. Direct and class-reflective `PlayState.chartingMode` reads/writes use the same live value. NV and native charts do not acquire a Psych flag, and the store does not retain scene instances.

Gameplay's editor key and pause-menu Charting route through one source-aware editor entry. Editor test play retains the flag; accepted song-end routing reads the flag after the selected callback's cancellation decision and saves scores before returning to the editor. The route does not advance story state or start victory presentation. Explicit editor exit, pause Exit to menu and source Game Over menu return clear the relevant owner flag. Pause captures the outgoing owner before menu creation can select another owner, preserving source reset order.

`RuntimeSourceChartingProbe` is explicitly opt-in and additionally requires smoke-test mode. It verifies an actual native gameplay -> editor -> test play -> editor -> Freeplay sequence, chart identity, owner flag/class reflection and unchanged story playlist. It ends test play early; it does not prove full-song completion, real key input or disk score persistence. Smoke mode suppresses score writes, and the native runner restores editor autosave/save bytes.

## Verification ledger

The final v0.0.13 Windows build/package gate passed (`tmp/v13-build-tests-package-final.log`): 2,165 tests across 685 modules in 145.5 seconds, with 345 skipped and zero failures. Skipped fixtures do not certify unavailable examples. Native receipts and exact source/binary limits are recorded in `tmp/source-charting-nv-fields-checkpoint.json`. Earlier investigation failures remain retained under `tmp/`; they are not passing acceptance evidence.

Executable tests use the actual production helpers and, where indicated, extracted pinned donor functions:

| Tests | Evidence scope |
|---|---|
| `test_nv_hit_dispatch_runtime_guard.py` | Actual extracted hit dispatcher rejects unselected NV runtimes before field lookup/marking, rejects absent active fields, and retains valid callback families/order and captured admission. |
| `test_nv_multifield_routes.py` | Declared bank counts, independent banks, source routing, admission, absent-format setup, live manager arrays and non-NV preservation. |
| `test_nv_legacy_field_address.py` | Address comparisons against actual donor ChartApi correction for multiple key/bank counts and formats; retained input data unchanged. |
| `test_nv_rgb_beat_zoom.py` | Full-DCE reflective color methods, live cadence, current default camera and independent tween/preference guards. |
| `test_nightmare_vision_following_cameras.py` | Actual FlxCamera synchronization, live replacement/removal, scroll independence and non-NV exclusion. |
| `test_source_character_dance_interval.py` | Pair/interval reflection and 1,360 comparisons against extracted NV Character/Bopper beat callbacks; full-DCE method invocation and dialect guards. |
| `test_source_character_dance_lifecycle.py` | Source speed writes/GF cadence, Alt Idle target/suffix/recalculation semantics and native preservation. |
| `test_psych_charting_context.py`, `test_psych_charting_handoff.py` | Owner isolation, direct/reflected flag, callback/live-flag routing, cancellation, save-before-editor order, editor test/exit state and native preservation. |
| `test_psych_pause_charting_handoff.py` | Source-aware pause editor entry and both menu destinations, outgoing-owner capture during owner-changing transitions and reset order. |

Native checks are muted, use full-quality assets/shaders, disable background dim only in the private installation, and compare protected file hashes. Monster checks require background frame data, three real shader filters, intro objects/animation, three unique banks and actual authored third-field hits. Long runs additionally require both videos to play, format and end, with no script/native/video error. Framebuffer readbacks are native software captures; they do not depend on desktop automation.


The complete Monster scene passed at configured 60 and unlimited FPS: intro/stage setup, authored third-field hits, and both videos playing, formatting and ending. Psych editor handoffs and Darnell two-bank gameplay passed at both caps. These six checks preceded the final dispatcher isolation guard; their precise executable hashes are retained in the checkpoint. The final binary additionally passed clean extracted-ZIP Tutorial autoplay/readbacks at 60/unlimited FPS, a Psych editor-handoff regression, and an NV scene/intro/third-field-hit regression at unlimited FPS. Captures were visually inspected, and protected settings/save/source hashes remained unchanged. No performance benchmark or complete pixel parity is claimed.

The first clean-ZIP Tutorial check exposed a native access violation: the shared successful-hit route entered NV callback field lookup outside an NV runtime. The dispatcher now rejects unselected runtimes before lookup or mutation, and safely rejects absent fields during default callback resolution. The fix applies to native and Psych hits by runtime ownership; no Tutorial-specific condition was added. The failing receipt remains `v13-packaged-tutorial-4c65603a`; both final packaged checks pass.

The required API audit passed with both pinned donors available. It is static evidence of bindings and donor call sites, not behavioral parity. Final reports are `tmp/v13-api-audit.md`, `tmp/v13-api-audit.json` and `tmp/v13-api-contracts.json`.

## Remaining contracts and next work

- The NV collection is not full FlxGroup mutation/lifecycle parity. Arbitrary script bank replacement, member removal/insertion, signals, field-owned note collections, receptor-generation callbacks and wider modifier APIs remain open.
- Mutable field IDs can still diverge from attached notes' callback IDs/manual admission. `inControl=false` does not yet reset every receptor animation/timer like the donor setter. Default declared-bank routing does not establish these mutation contracts.
- Full NV holding lease/release and return-animation lifecycle remain open. The exposed `holding` flag and beat suppression are bounded support. Wider sing/stunned/actor update parity is not established by the cadence checks.
- Headless address cases include other key counts; native checks here exercise four-key fields. Source action registry/InputSystem, paused/event input, timestamps/latency, track-swap audio, duplicate row normalization and field-specific effects remain open.
- The host editor returns to Freeplay on explicit exit; Psych's MasterEditorMenu does not exist here. Full editor/pause-menu feature parity, top-mod/menu context restoration, mutable Discord client IDs, and concurrent active owners remain open.
- This supersedes the prior Game Over report's open charting-flag item for the tested handoffs only. Core BF fallback, source Paths/null audio, native Psych retry overlays/Tank mix, typed/tween camera facade consumers and the other prior checkpoint limits remain visible in the roadmap.

Continue Phase 2 with source field mutation/generation and input contracts. Imported custom menus, library/freeplay management and larger performance changes retain their roadmap order. The verified checkpoint is being prepared for the explicitly requested v0.0.13 alpha release.
