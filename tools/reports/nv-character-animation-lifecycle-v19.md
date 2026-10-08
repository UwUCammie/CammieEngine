# Nightmare Vision character animation lifecycle

The pinned Psych and Nightmare Vision `Character.playAnim` methods both clear
`specialAnim` before starting a new animation. The host now applies that rule
only while a Psych or Nightmare Vision source context is active; blocked
animation requests, native playback, and Codename playback keep their existing
behavior.

Nightmare Vision checks for `<current animation>-return` before using the
ordinary dance pose, then returns to dance or idle after that animation
finishes. The host now implements that path for NV actors only. A missing
return animation falls through to the authored idle selection. Special
animations remain protected from dance replacement, and NV held state defers
special completion and sing-duration fallback until release.

Accepted manual hits on non-autoplay player fields now hold their source NV
singers. Claims are tracked by selected owner, field object, source role group,
and actor, so removing one field does not release an actor still held by another
field. Claims clear when all input actions are released outside a cutscene, or
when their field, role, or owner ends. The donor skips `processHolds` during
cutscenes, so valid claims stay latched there; retired fields and roles are
still pruned. The uncapped update path returns immediately when no claims
exist. A standalone source `Character` used directly as a field owner or singer
uses its own identity as the hold token and remains subject to field, owner,
source-mode, and actor-existence checks.

Focused tests cover source-mode selection, native and Codename guards, return
and idle fallback, held special completion, and hold-claim scope and release.
They do not replace the native visual check.

The pinned `PlayField.characterSing` contract also reads
`Character.vSliceSustains`: it resets `holdTimer` and applies a manual hold
before returning early from regular note animation playback when both that
flag and `note.isSustainNote` are true. The flag is loaded from
`CharacterData.vslice_sustains`, whose missing value defaults to false. The
host previously lacked this property and gate, so Zeph's authored true value
could not stop sustain callbacks from replacing a cutscene animation. The host
now loads the owner-local flag, preserves the existing hold and Hey handling,
and skips only the regular NV sustain animation. Taps, Hey notes, false/default
metadata, and other dialect actors continue through their existing routes.

The same donor `Character.update` accrues `holdTimer` for every actor role and
returns to dance after `singDuration` when no manual hold is active. The host
previously ran its fallback only for `!beingControlled`, which could leave an
NV player actor on a finished sing frame. NV now uses its live `singDuration`
field for all roles, while native and Psych actors retain the existing
controlled-actor split and `dadVar` behavior. Releasing a held NV actor after
the authored threshold also returns it immediately, matching the donor setter.
The source rule is covered by focused interpreter tests. A later no-seek
native build6 capture (`stem a6a50e09`) observed Zeph's Grab animation advance
through frames 0, 16, 32, and 33 at song position 89,535 ms; BF was hidden at
90,015 ms. Sparse one-second samples showed BF on idle at 90,015, 91,015, and
92,015 ms with `holding=false`, `vSliceSustains=true`, and the source actor
flag set. This confirms the event/frame-33 path and normal BF return in that
interval. It is bounded evidence for this natural run, not proof for every
chart timing or later gameplay section.

The harness exited with status 1 because its 96,000 ms run deadline includes
the initial countdown and ended around song position 92,9xx before the
94,000 ms note-render readback. The gameplay observer reported no runtime or
script error. Treat the Grab markers as valid evidence and the screenshot
readback as incomplete; the overall harness run is not a pass.

The Try Harder chart's `Play Animation / Grab / dad` event is at 87,867.592 ms.
The authored Zeph animation is non-looping at 24 fps and its atlas contains 82
`ZephGrab` frames. The stage script listens for frame 33, hides BF, and calls
the Ice Note `forcebreak`; the later `grab intro` event is at 89,225.058 ms.
Static review confirms the host event target resolves to Dad and the source
frame-change callback is exposed; the bounded build6 native markers above
confirm that this event reached frame 33 in the tested natural run.

The final native observation used a lightweight, observe-only HScript with
no note-hit listener or note-list scans. It recorded actor state and the
source frame callback without changing authored events or animations. The
earlier instrumented run had heavy per-hit and Ice-note diagnostics, so its
low frame rate was not used to judge gameplay performance.

Try Harder has no field-skin change before this cutscene. Its Ice Note setup
runs after initial skin application and explicitly sets `noAnimation`,
`rgbEnabled=false`, and custom colors. The `No Animation` chart notes set the
same singer/miss suppression through `Note.sourceKind`. The suspected RGB reset
is therefore not an established cause. The no-seek v19 observer now records
the selected Ice atlas, RGB flag, palette, and scale; pixel-level comparison
against the donor remains outside this lifecycle check.

The follow-up source trace found the texture-path mismatch: Ice Note composes
`ice/` onto `NOTE_assets`, while the field later assigns `EXE_Notes`. The
composed `ice/EXE_Notes` atlas is absent even though the retained
`ice/NOTE_assets.png` and XML are present. The earlier v18 observer reported
the regular `EXE_Notes` graphic, so a green frame name alone did not establish
that the Ice atlas was used.

Field-skin reload now tries its composed atlas, then the last successfully
loaded explicit note-type texture with the same prefix and suffix, then
`NOTE_assets` in the composed field directory. Each candidate must have both
PNG and XML under the selected owner or its explicit same-owner core. A missing
pair reports the attempted paths and stops; it cannot use a sibling family
skin. The 85.0-88.5 second Ice observer records the chosen atlas and explicit
script texture for the 85.8-86.9 second notes. Both observer scripts now pass
through the actual `NightmareVisionGameplayScripts` loader in focused tests.
The natural no-seek v19 run reported `ice/NOTE_assets`, RGB disabled, the
authored palette, and 0.7 scale for the Ice field.
