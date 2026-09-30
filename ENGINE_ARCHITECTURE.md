# CammieEngine architecture

This document describes the active working tree. The original README and
`updateLog.txt` retain the project's history. Engine fixes should be made in
shared code, without changing an individual chart or mod to hide a runtime or
import discrepancy.

Codename `MusicBeatTransition.script` stores the authored selector per active
import owner. The importer follows literal assignments and stages the selected
`.hx` dependency; the runtime appends `.hx` to extensionless selectors before
its owner-scoped lookup. Codename `CoolUtil.playMenuSFX` uses numeric IDs, so
literal `Paths.sound` scanning alone cannot discover its assets. The importer
stages the available six shared sound keys from the selected owner or its
installation-level fallback whenever a script calls that helper. A scoped
missing-only refresh is required for already imported owners; source files,
other owners, charts, and user settings remain untouched.

For a Codename-owned state switch, the outgoing transition script reads the
concrete destination as `newState`. Flixel 6 calls `startOutro` with a completion
callback rather than passing the destination to that callback. The selected
owner's transition scope carries the validated FlxState only through that
synchronous call and consumes it once for the script-facing field and event.
The native transition host keeps its own `newState` null on this callback path
so the original completion callback remains responsible for switching states.
Direct owner script switches and concrete `LoadingState` switches use the same
owner-scoped handoff; unresolved lazy factories retain their native path.

### Codename legacy pending-state access (28 September 2026)

Older global HScript reads `FlxG.game._requestedState` and may replace that
field from `preStateSwitch`. `CodenameScriptInterp` maps it to Flixel 6's
`_nextState` through `CodenameRequestedStateCompat`. A known concrete target
is leased to the outgoing game state and the exact request value. If a Codename
outro defers Flixel's assignment, the lease binds immediately after Flixel's
completion callback writes it. Source assignment still writes the supplied
value directly and returns that value. The lease is discarded when the source
overwrites the field, the global callback completes, the transition is
cancelled or destroyed before finishing, or the owner is cleared. A one-shot
`postStateSwitch` listener also releases any surviving lease after state
creation when no global runtime callback is installed.

The bridge leaves an unknown `_nextState` factory unchanged and never invokes
it. The Shift+Escape `resetGame()` request is one such factory: its eventual
state class is not available without calling it, so old `Std.isOfType` checks
against that request still return false. `LoadingState.loadAndSwitchStateFactory`
also remains deferred until Flixel has destroyed the outgoing state and cleared
the bitmap cache. Extracted tests cover the bridge, HScript setter semantics,
cleanup-signal lifecycle, and the production global-script redirect in the
interpreter. They do not establish native timing for every asynchronous
transition. The bounded HL17 native menu startup only observed an imported
state request at `preStateSwitch`; it does not establish the native
`MainMenuState` or `FreeplayState` redirect branches.

A directly constructed `FreeplayState` can bypass native CategoryState.
`FreeplayDirectEntry` resolves the active import owner's registered song rows
from each destination chart's `compatScripts.json` selected root, deduplicates
rows across categories, and falls back to the first populated native category
only when there is no active imported owner. A selected owner with no rows
gets an empty list instead of another package's songs. `FreeplayState` checks
the resulting list before accessing row zero, so an empty or invalid registry
cannot produce the prior
native segmentation fault. `ImportedFreeplayCaller` captures the direct
imported menu's owner and script at Freeplay construction, carries it across a
ModifierState or PlayState return for that same owner, and consumes it on Back.
A native category launch or owner switch clears the route. The Codename
Options host likewise records its imported caller owner and script path at
construction and recreates that same-owner state on exit, including a round
trip through Controls.

Codename note splash styles hold one FlxGraphic use-count reference while
their Sparrow atlas is cached. Each transient splash keeps and releases its
own sprite reference. Style eviction and handler destruction release the cache
reference; this prevents a later animation lookup from using frames whose
graphic was destroyed after the first splash.

## Psych mouse coordinates and current regression audit (24 September 2026)

Psych `getMouseX/Y(camera)` now uses the selected camera's screen transform,
matching the local Psych reference, and returns its pooled point. The former
world-space mouse fields included gameplay scroll and ignored HUD/other camera
selection, making overlay hitboxes inconsistent with their displayed sprites.
The interpreter test executes the production bridge and pinned Flixel transform
with independently translated/zoomed cameras. A private offscreen native
fixture also verifies mouse activation of a custom pause menu.

The current hazard-note audit distinguishes note identity from visual state:
Psych `Note.texture` reload semantics are missing in the host. The reference's
Hurt Note default uses an RGB palette, but an explicit nonempty texture reload
can disable that palette in Psych 1.0.4. The official 0.7.3 source instead
preserves RGB across texture reloads, matching this donor's declared version.
Reference: https://github.com/ShadowMario/FNF-PsychEngine/blob/0.7.3/source/objects/Note.hx
(cached at `tmp/psych-upstream-0.7.3/Note.hx`). Preserve callback order and
version-specific source setter semantics;
do not infer a bespoke bomb skin from a chart name or negative health amount.
The reported ending uses step callbacks and an overlay sprite; presence of its
imported files is not evidence that the ending renders correctly. Shared tween
target resolution now prefers exact object tags, then resolves nested property
owners such as `sprite.scale`. A full-song default-settings native probe
confirmed the authored ending scale reaches 0.67; screenshots confirm the
phone contracts into its centered pose.

## Psych skin metadata and asset resolution (in progress)

`Song.SwagSong` retains `arrowSkin`, `splashSkin` and `disableNoteRGB` through
shared difficulty resolution. Explicit selected values win; empty skin strings
mean source defaults and `false` remains an authored RGB choice. Missing fields
inherit through the existing default selection. Native charts without these
fields acquire no Psych settings. Invalid skin types are not accepted as resets.

`PsychSkinResolver.resolveDetailed` returns a complete atlas descriptor or a
failure reason. A selected owner searches only its `images` and `shared/images`
trees; only unscoped legacy imports may use global `assets/images`. Sparrow
PNG/XML and pixel PNG/ENDS pairs must both resolve in the same directory. A
preference postfix wins only when that variant is complete. Logical keys keep
their source-relative spelling; traversal, case collisions and incomplete pairs
are rejected. The selected Psych owner now supplies this resolver to note/receptor loading.

`Note` and `StrumNote` own their skin configuration and expose a live `texture`
property. Initial skin failure leaves the configuration available for a later
script override; a failed texture reload retains the prior visual. Reloads
validate source animation prefixes before replacing frames, preserve sustain
scale and note semantics, and rebuild static/pressed/confirm receptor animations.
Psych 0.7.3 palette behavior is separate from texture selection: chart RGB disable
is preserved, Hurt Note uses the source palette, and receptor RGB is inactive in
its static pose. Public receptor `useRGBShader` changes apply immediately.
The translated `setStrumLineRGBShader` helper visits the live opponent/player
groups, matching `compatGroupMember`; the unused legacy combined group cannot
represent them. It reads properties before calling their setters because
hxcpp's field-presence query misses native class members, including false
Boolean properties. The isolated native toggle probe requires eight actual
receptors and checks disable/re-enable on each, avoiding an empty-group pass.
Native and other engine owners do not opt into this adapter. A selected Psych
chart also initializes an empty custom-note definition list when noteInfo.json
is absent, allowing string note types to generate their shared definitions at
runtime. Existing definitions and native null behavior are preserved.

The importer copies complete referenced Sparrow and pixel pairs beneath the
source owner's manifest root without replacing existing files. References come
from selected charts, the source default key and bounded static Lua assignments.
Dynamic keys and missing dependencies are diagnosed. Reimporting the same donor
can fill missing scoped sheets without overwriting installed charts.

Synthetic native checks verify atlas/pixel ownership, <=1px tap alignment,
RGB on/off colors and the authored Hurt palette across repeated loads.
Existing imports can be refreshed through the guarded missing-only receipt
procedure documented in `tmp/psych-note-texture/repair-procedure.md`.
Source splash selection and the full
script-facing RGB palette mutation API remain unsupported; do not infer full
Psych visual parity from initial note/receptor skin support.

## Psych custom substates (24 September)

`PsychCustomSubstate` runs script create/createPost, update/updatePost and destroy
callbacks on Flixel's substate clock. A pausing overlay suspends PlayState;
`Function_Stop` from `onPause` does not undo a custom pause opened by that hook.
Queued opens may be replaced or canceled before create without false lifecycle
callbacks. Instance identity keeps an old destroy callback from clearing a new
substate's script globals. Script sprites retain their existing PlayState
ownership; `insertToCustomSubstate` remains unsupported.

The adapter records active unfinished global timers/tweens at each pausing open,
freezes them, and restores that recorded set on resume. Tasks created by the
menu continue during the pause. Previously inactive tasks stay inactive.
Replacement menus suspend tasks created by the previous menu too. Parent
teardown notifies substate scripts before interpreter release. Interpreter tests
cover the real class lifecycle and extracted owner methods. Native synthetic
checks pass for mouse input, resume, restart and exit, including teardown and
a second start after restart. Actual donor-menu verification also passes its
authored five-request gate, frozen song clock and Escape resume. These checks
do not establish complete substate API parity.

Psych script discovery now uses canonical paths only for deduplication while
returning the caller's absolute mounted path for asset reads. Otherwise a
symlinked runtime overlay produces canonical script paths outside its own
working directory. The asset scope boundary is unchanged. A synthetic test
covers mounted stage/global scripts and duplicate shared roots.

Native smoke cases use disposable local runtime overlays with repository seed
options, private XDG saves/cache and no inherited desktop display variables.
Selected compatibility scripts are materialized for older binaries which still
canonicalize their read paths; large media remain linked. Never restore an old
personal-options snapshot after a concurrent user session has changed it.

## V-Slice resting zoom and Psych animation registration

`currentCameraZoom` reads the resting gameplay zoom, independently of the live
camera's temporary pulse/tween. Source custom event bodies run through HXC
translation instead of a named zoom approximation. Native verification of this
follow-up is tracked in the discrepancy report.

Psych animation registration starts the newly registered animation only when
its sprite has no current animation. Prefix and indexed registration share this
rule; existing playback remains intact. This prevents a newly created effect
from displaying the atlas's unrelated first frame before any explicit play call.

## V-Slice camera ownership (24 September)

A selected V-Slice manifest opts into source camera ownership. After initial
stage/character setup, `initializeVSliceCameraFocus` snaps to the opponent's
composed camera focus, unless construction scripts already moved or claimed
`camFollow`. Source camera focus persists across native section boundaries;
converted `mustHitSection` flags retain their note-ownership purpose. Authored
FocusCamera events and explicit script camera modes continue to control focus.
A later stage swap does not replay opening initialization. The per-state policy
is cleared with script ownership. Native/Psych/Codename behavior is unchanged.

The V-Slice PlayState ABI also has positional `tweenCameraZoom(zoom,
seconds, direct, ease)` and `tweenScrollSpeed(speed, seconds, ease,
strumlineNames)` methods. The camera method drives the existing live base zoom;
the scroll method validates each named native line, cancels prior source tweens,
snaps their previous targets, and tweens per-line `Strumline.scrollSpeed`.
`resetScrollSpeed` restores the chart speed. Native/global speed remains the
default until a script changes a line; note travel and sustain scaling then
read the selected line's speed. Source scroll and camera tweens pause, resume,
and cancel with PlayState. The chart-event object payload retains its separate
step-based `tweenScrollSpeed` path. This avoids sending a V-Slice scalar into
the object event handler, which previously SIGSEGV'd on native hxcpp.

Foreign HXC script discovery keeps global modules and per-song companions by
relative path under their import owner. When a manifest retains older roots,
the selected root supplies one executable copy of a repeated song companion;
unique scripts from other roots remain available. The importer retains
package-wide files directly under `data/` inside the owner namespace, so
`Paths.txt/json` reads cannot borrow another mod's same-named sidecar. The HXC
runtime exposes group tween pause/resume and a bounded local-weekday host call.
The translated `new Strumline` and `new HealthIcon` constructors name explicit
adapters because HScript resolves compiled classes before variable aliases;
the health icon adapter delays a missing placeholder diagnostic until its
first update, allowing an immediate source `configure` to choose the real icon.
The owner-scoped `Constants` facade exposes the source V-Slice strumline X/Y
offsets (48/24) and timing defaults used by imported HXC scripts. Missing
fields stay explicit script diagnostics rather than silently becoming arithmetic
with null.
HXC `Paths.font` loads an owner-local file through OpenFL font registration and
returns its family name to FlxText; a valid native font remains the fallback.
Static HXC stage countdown bodies execute when their shader, filter, and actor
operations pass the source-backed safety gates. Dynamic stage camera/preference
branches remain strict diagnostics until their behavior is translated.
Each safe shader descriptor owns a native handle keyed by its source field.
Countdown-owned stage shaders create that handle in the countdown callback;
other stage shaders create it before their song/event callbacks bind a camera
filter. The filter host retains ownership and releases the handles with the
PlayState. Bounded HXC `FlxPoint.get` and numeric `new FlxPoint` class fields
keep their initialized point state across callbacks.

Psych tween entry points now resolve exact registered tags before interpreting
an object argument as a nested property path. This allows x/y tweens on a
sprite's scale point through the existing shared property bridge and preserves
normal tag precedence, cancellation and completion callbacks.

## Codename source-line ownership (25 September 2026)

Codename's legacy Flx3D classes now come from the archived
`CodenameEngine-Dev` wrapper API with the matching pinned Away3D fork. The
runtime exposes them through `CodenameFlx3DBindings` only to selected-owner
interpreters. `CodenameScriptInterp.cnew` places that owner on a narrow
constructor context while creating a view or camera; the bound subclass keeps
the owner for asynchronous model callbacks and loads models, OBJ material
libraries, and referenced textures only through `CodenamePaths`. Missing OBJ
sidecars are reported, and the caller's explicitly supplied texture is passed
to the model loader. The importer follows literal `Paths.obj` references into
the same owner's `mtllib` files and their `map_Kd` textures, rejecting unsafe
paths and symlink escapes; existing destination files keep their bytes. The
runtime retains an explicit missing-sidecar diagnostic when the donor did not
provide a referenced material. `run.sh` verifies the Away3D commit before a build.
The model and dependency readers convert native `haxe.io.Bytes` to OpenFL byte
arrays only after preserving the original dynamic type through Haxe/C++ code
generation. HScript constructs the selected-owner 3D subclass explicitly so
native class lookup cannot bypass its scoped reader. A rebuilt HL17 offscreen
run emitted one geometry and one mesh asset, then produced nontransparent,
nonwhite bitmap samples. Source scene placement and full visual parity still
need direct comparison.


Selected-owner camera sidecars retain ordered source line descriptors per
difficulty, including empty and invisible indices, actor bindings, visibility,
key count, normalized line position, absolute strum-position override, receptor
scale, and spacing. `CodenameInputLine` keeps the stable script and input
identity. `PlayState` maps each nonempty source index to a distinct native
`Strumline`; the first ordinary player/opponent lines may reuse the original
banks, while GF and repeated-role lines get separate receptor groups. Notes
retain their source line and note ordinals and use that group's receptor
coordinates for rendering and judgement. Hidden lines still own notes and
callbacks but do not draw their receptors or note sprites.

`CodenameStrumlineLayout` applies Codename's centered-bank calculation and
absolute `strumPos.x` override. The FunkinModchart adapter now resolves each
authored line to its own renderer row and omits invisible lines. The current
four-lane native note model explicitly diagnoses larger source `keyCount`
values instead of silently truncating them. Independent-line audio and visual
parity, script-mutated receptor transforms, and five/six-key support remain
open. A native Endless Hard accelerated full-song check has reached its natural
ending with complete events and no strict diagnostics after the shared
strumline iterator fix; this establishes a bounded runtime gate, not full
source rendering parity. The audit matrix is at
`tmp/codename-independent-lines-audit.md`.

## Codename scoped video and shaders (24 September 2026)

Codename song, stage and event scripts resolve literal `Paths.video` and
`Paths.file` media inside the selected import owner. `Assets.getPath` checks
that same scope before giving a path to hxvlc. The interpreter constructs
`FlxVideoSprite` with the native library and destroys video bitmaps created
before `add` if script setup fails; scene-owned videos are destroyed with their
script scope. `CustomShader` reads only the selected owner's fragment source.
Before compiling under OpenFL GLSL 100, a bounded shared adapter promotes an
integer literal in a typed float assignment that subtracts or adds a function
result; authored shader files remain unchanged.
The same shader adapter promotes a float-bound GLSL loop iterator only when
the bound is declared float and the iterator is not used for array indexing.
Later GLSL core operations and non-square matrix types are detected from the
fragment source. The shared normalizer selects the minimum required language
version and drops extension directives that became core, while an idempotent
OpenFL patch places `#version` before OpenFL's precision prefix. HXC shader
handles resolve to native filters at camera assignment; invalid values are
rejected at that boundary so OpenFL never receives an opaque script token.
Codename `Paths.getPath` accepts owner-local relative keys as well as resolved
owner paths; the source `Assets` facade reads text, bitmaps and sound through
that boundary. The importer stages bounded top-level song data sidecars and
Animate atlas folders in the selected owner namespace without overwriting
existing files. No lookup borrows another import's asset.
Character conversion also retains each available source
`data/characters/<id>.xml` definition and its referenced
`images/characters` atlas files below that same owner. The native converted
metadata and source runtime definition can then resolve together after an
owner-scoped refresh; missing definitions remain explicit dependencies.

`importScript` evaluates its child HScript in the caller's current scope so
fields declared before the import remain visible afterward. It records child
callbacks separately from the parent callback table, then dispatches both on
the shared lifecycle path. An imported `postCreate` or `update` therefore does
not replace the song or stage's own hook. Errors are tagged with the callback's
source file and kept isolated by callback key. Codename gameplay scripts read
and write the live default game/HUD zoom through this same interpreter boundary.
Substate and focus hooks reach those scripts so they can pause and resume
video. `CodenameScriptInterp` also provides the source `lerp(from, to, ratio)`
helper in song, stage and event scopes, using `from + ratio * (to - from)`.

The shared chart-event pump advances its cursor before invoking callbacks, so a
callback that re-enters dispatch cannot repeat the current row. During ordinary
updates it samples the authoritative song clock for each row, preserving event
seeking behavior. Audio completion inclusively drains events through
`songLength` before `endSong`, covering a final event that falls between the
last state update and the native audio callback.

Native smoke launches can opt into `--smoke-require-song-end`; with that flag,
a timed window is a failure until native audio completion reaches the song-end
path. `--smoke-codename-visuals` emits bounded owner-relative snapshots of up
to 16 objects after selected Codename callbacks, including primitive geometry,
camera zoom, shader class and video state. These test-only markers avoid
absolute asset paths and arbitrary runtime objects. They identify callbacks
and renderer state but do not alone prove final pixels; the FNAS replay pairs
them with an event-time screenshot and a later decoded-video screenshot on a
private Xvfb display. The real-media `better-clone` replay reached natural
audio completion, drained all 204 source events, and recorded the terminal
reversed Camera Flash through the shared native Camera Fade route. Bounded owner
snapshots observed the ConfettiHUD video loaded and playing with its compiled
shader, and the later screenshot shows its rendered green particles over the
office scene. This verifies one song's event/video path; it does not establish
all FNAS menus, cutscene skip routes or song-switch cleanup. Root/global scripts
and custom Codename menu states remain separate work.

## Codename accuracy and ratings (24 September 2026)

Codename scripts read accuracy as a ratio through both the live `accuracy`
global and the `game.accuracy` instance alias. No judged notes returns -1.
Setting accuracy creates a denominator of one when necessary and sets the
accumulated amount using the donor setter. The host retains its percentage
field for native score/HUD code; synchronization does not turn source ratios
into percentages. Direct edits to the two source counters are reflected by
the source getter and the next HUD update.

The per-state `comboRatings` array has the pinned donor's defaults. Selection
uses authored percent thresholds and maxMisses, keeps the first entry at equal
thresholds, and dispatches `onRatingUpdate` to scene and character scopes with
mutable `rating`/`oldRating`. Cancellation retains the old selection. Event
accuracy changes from accepted note hits and misses invoke this same path.
`ComboRating` and `RatingUpdateEvent` have explicit source import bindings.

The accuracy label uses the donor English template, quantization and unknown
value fallback; only its rating substring receives the selected rating color.
Custom/localized donor language loading is still unsupported: authored rating
labels are retained as fallbacks, without introducing a shared mutable
translation hook. Full donor HUD layout and dynamic HUD replacement remain
separate work. Native scripts and the native percentage display are unchanged.

## Codename note events and presentation (24 September 2026)

Source-bound notes use mutable hit/miss payloads and actual Flixel line-local
signals. The supported event classes have explicit source import bindings;
selected note settings/counters use live interpreter globals instead of stale
per-script copies. `CodenameGameplayAccess` maps source `game.misses` to a typed
instance accessor for the host static counter; bare `misses` uses the same
live binding. This prevents silent null reads from static/instance reflection. Keep
scoring separate from presentation: native `popUpScore` also changes health,
accuracy and vocals, so invoking it before applying a source event would apply
those effects twice. Scene hit hooks precede the line signal and the combined
scene/character hook; cancellation and post-hit effects follow the pinned
v1.0.1 source contract. Late notes retained by cancelled misses or disabled
deletion are judged again on subsequent updates, as in the donor. Accepted
sustains retire after their duration, following their one hit callback. The existing native note path remains for unbound notes.

`CodenameNotePresentation` owns a bounded group of judgement sprites and their
fade tweens. It reads the event's prefixes, suffixes, display flags, scale and
antialiasing. Assets resolve inside the selected namespace; the default
`game/score/` pack alone has an explicit fallback to bundled engine score
images. Tweens pause with gameplay and are cancelled on recycling and teardown.

Character `playSingAnim` and `playSingAnimUnsafe` aliases dispatch separate
mutable directional events before `playAnim`. The safe call falls back from a
missing suffix; the unsafe hook may select its final animation directly.
Callbacks can cancel either stage. The donor's unsafe Bool parameter defaults
to true, including when the safe call passes null. Source stun state uses actor
elapsed time and resets on reassignment, with the donor 5/60-second duration;
it has no asynchronous timer that can survive an actor's teardown. Native
characters retain the existing miss-stun preference.

The shared event path has interpreter and two-visit offscreen native coverage
(see the verification report). It does not establish complete Codename
StrumLine, receptor, note-type or audio compatibility.
Judgement thresholds currently use the native configured hit-window size with
source fractional boundaries. Source accuracy and rating callbacks are handled by the model described above;
the host score UI retains its percentage convention. Per-line vocal tracks and
independent receptor banks remain separate work.

## Reopened compatibility corrections (23 September 2026)

- The editor normalizes embedded and companion events through `SongEvents` and
  `ChartEventModel`. Its separate left lane uses the same section timing/BPM map
  as notes. Selecting an event pauses audio and seeks both the playhead and grid;
  saving preserves the normalized event data without duplicating sidecar events.
- Stage validation uses the authored identifier before registry normalization.
  Modding Plus stage registries/scripts resolve inside the selected import
  manifest before native registry fallback; automatic repair copies missing
  stage dependencies through the normal importer.
- `StageHelper` is an ownership group, not a mounted display group. Direct
  `stage.add()` props are attached once to `PlayState`, with explicit cameras
  retained. Stage refresh sorts the actual display list. Removal/teardown detach
  both group and state references; registered groups do not destroy children twice.
- Psych sprites decode filesystem images through `FNFAssets.getBitmapData`,
  including static fallbacks for animated sprites. Passing a disk filename to
  OpenFL's embedded-asset loader can produce placeholders.
- Psych group access uses property getters for `members`; native sprite groups
  expose this as a computed property. Sprite colors are interpolated per
  channel. Psych's `doTweenColor` passes its target to a typed FlxSprite tween;
  a camera becomes null on native hxcpp, so its color tween runs and completes
  without tinting camera pixels. Preserve that null-sprite tween behavior rather
  than applying a new whole-camera tint. Direct camera property APIs are separate.
  The post-update callback runs after
  native note/HUD positioning so authored final icon positions survive.

- Native camera assignment and Lua text helpers use typed Flixel accessors.
  hxcpp Dynamic field writes can bypass property setters; they must not be used
  for `cameras`, text/font/size, or other accessor-backed presentation state.
  Psych text defaults to the HUD with zero scroll factor and foreground order.
  `setTextFont` resolves the selected import's `fonts/` directory before native
  `assets/fonts/`, matching Psych's `Paths.font` instead of passing bare font
  filenames to Flixel's embedded/system-font lookup.
  `setObjectOrder` removes the object and uses the requested final insertion
  index, matching upstream Psych; forward moves must not decrement that index.
- Psych stage points are combined with per-character `position` metadata from
  the selected manifest. Base-engine fallback offsets are packaged in
  `assets/data/psych_base_character_positions.json`, extracted from the local
  Psych source `assets/shared/characters/*.json`; scoped metadata (including
  explicit zero) takes precedence. Initial load, replacement characters, and
  extra actors share this resolver. Stage changes restore the earlier swap bases.
- `Character.imageFile` exposes the selected, existing Sparrow atlas as a
  runtime-relative extensionless stem. The loaded graphic key takes precedence;
  an opaque bitmap key may use the selected character's exact `char.png`/XML pair.
  Psych sprite loaders accept that stem, so trail scripts can reuse the actual
  actor image across swaps without guessed donor names or replacement artwork.
- Scoped imports retain `data/notestyles` alongside script trees and atlases.
  Missing style metadata participates in import repair; styles are not flattened
  into another import's registry or made into the song's global UI preset.

- `HxcNoteStyleCompat` resolves literal registry lookups inside the selected
  import root. Its sprite adapter owns atlas animations, offsets, scale, alpha,
  finish/revive behavior, and attachment through the strumline sprite path.
  Missing metadata or artwork stays invisible instead of substituting art.
- HXC note lifecycle callbacks run only for true HXC scopes. The scope map also
  contains explicit false entries for ordinary scripts, so membership alone
  cannot identify HXC. Psych callbacks retain their ordinary arguments and
  post-judgement dispatch. NoteKind scopes additionally match the live note's
  authored kind; ghost misses use their separate callback without a null note.

Native verification and open issues are tracked in
`tools/reports/engine-discrepancies-verification.md`.

## State and content flow

`Main.hx` starts `TitleState`. Menus route through `MainMenuState`,
`FreeplayState` or `StoryMenuState`, then `ModifierState` and `PlayState`.
`LoadingState.loadAndSwitchState` handles the transition into a song.
`MusicBeatState` emits every crossed step and beat, including catch-up steps,
because per-step modchart events depend on that behavior.

`Song.loadFromJson` resolves charts from lowercase `assets/data/<song>`
folders. Difficulty metadata comes from
`assets/images/custom_difficulties/difficulties.json`. Non-default charts
take their own note, speed, BPM, voice, and mania fields; missing visual fields
inherit from a valid default or sibling chart. Imported Psych charts retain
explicit character and stage IDs even when their assets are unavailable, so
the runtime reports the missing source dependency. Audio resolution is in
`CoolUtil.getSongFile`; native asset access is in `FNFAssets` and `Paths`.
Runtime file paths are relative to the executable's `linux/bin` directory.
`Song.resolveChartData` may borrow missing visual fields from valid fallback
charts, but `stageID` is difficulty-specific and must come from the requested
chart or that difficulty's built-in default.

`PlayState` builds the live stage, characters, notes, cameras, and event
timeline. HScript receives objects and callbacks through the
`makeHaxeState` family. `SongEvents` merges chart and Psych-style events.
`StageHelper` and `Character` own custom stage and character resources.
Legacy names exposed to HScript are compatibility APIs and must be retained
when their implementation changes.
`Character` caches parsed HScript programs for unchanged character sources,
with a 64-entry limit. Each actor receives a separate interpreter and runs
its own initialization, so the cache does not share actor state.
`FNFAssets.getBitmapData` registers cacheable disk images with `FlxG.bitmap`
under a normalized path key. Repeated stage/background loads reuse that
bitmap until the existing PlayState-exit cache clear; callers requesting
`useCache=false` still decode independently.
Imported stage props can carry authored HUD z indexes. After the stage loads,
`layerNativeStageHudOverProps` raises the native receptor, note, hold-cover,
and splash groups above those props in draw order before `refresh()` sorts
members. The note group stays above the receptors, including on imported
stages that request a full state sort.

`ChartingState` edits Psych-format event groups through `ChartEventModel`.
The editor's Events tab handles names, values, timestamps, and individual
events within a group. Companion events copied into the editable chart carry
a source signature. An edited row retains that signature, and deleting one
stores an inert tombstone in the chart. Both editor reload and
`SongEvents.collect` suppress the original companion row by signature, so
the source `events.json` stays untouched and gameplay uses the saved edit.
`EditorSectionLengthCompat` supplies missing editor grid lengths from authored
`sectionBeats`, then falls back to sixteen steps. The editor preview reads
declared split vocal stems into `VocalTracks`, so pause, seek and teardown
operate on every stem in the preview.
`FreeplayState` ties compatibility prompt actions to
the selected capsule through `SelectionActionGate`; changing selection clears
the armed action. It also parses difficulty definitions once while building
the song list. `FreeplayListWindow` keeps only the selected row and twelve
neighbours on either side instantiated as display objects. Song indices,
search matches, difficulty selection, and compatibility capsule identity stay
in the full list, so scrolling does not change which song an action targets.
`HxcFreeplayRuntime` loads safe, manifest-scoped HXC menu modules for
selection callbacks. State factories stored directly as values in translated
HXC map literals use `HxcDeferredValue`: `HxcDynamicMap.get()` constructs
and caches the target state when that key is read. Direct state-factory calls
remain eager. This avoids analyzing an import's full HXC state tree merely
to initialize an unused menu redirect map during Freeplay startup.
The Freeplay translator extracts finite level allowlists, icon overrides,
variation rules, and overlay atlas/animation metadata from literal donor
operations. Native capsule views apply those rules only for the selected
manifest scope. Confirm actions carry a selection generation and one-shot
token; changing selection clears both the action and a pending prompt.
Deferred popup factories capture their module root when installed, so later
accept input cannot borrow another import's asset scope. Imported preference
defaults are seeded from literal constructor assignments into a namespaced
store rather than from a fixed donor key or engine-wide default.
In the same isolated native Imported-category smoke, Freeplay creation fell
from 7,451 ms to 1,470 ms after deferring that map value; the HXC portion
fell from 7,425 ms to 1,441 ms. These are one-machine diagnostic timings,
not a fixed performance guarantee.

Psych stage JSON is applied after native actors are created. Its actor
positions and camera offsets are followed by `refreshPsychStageCameraTarget`,
which chooses the first section's focus with `psychInitialCameraTarget`.
This keeps the opening camera aligned with the later section-follow logic.
`PlayState` creates Psych's transparent `camOther` above `camHUD` as a distinct
camera. Property paths, script aliases, sprite camera selection, shaders,
shakes, and flash events preserve that layer, so fading the HUD does not fade
an overlay authored for `camOther`.
Timed legacy camera zoom events retain the current `defaultCamZoom` while
their camera tween runs and commit the target when it finishes; immediate
events still commit at dispatch. This matches Psych Lua callbacks that update
the base zoom in `onTweenCompleted` and avoids camera decay accelerating an
authored tween.
Native runtime smoke emits bounded `camera_snapshot` markers for PlayState
ready, the first BF-owned section, and the first authored legacy zoom event
and its completion. A Resonance smoke measured 0.15 at ready, 0.165 at first
BF focus, then a chart-authored zoom target of 0.18 after earlier camera zoom
pulses had raised the live value to about 0.256. This distinguishes camera
framing changes from zoom changes without adding normal-play logging.
The generic Psych `Flash` custom-event scope checks the flashing-lights
setting before invoking that event's visual callback. A selected custom
`Flash.lua` handler owns the legacy `Flash` row, so the native flash fallback
does not render a second effect. Charts without that handler retain the native
fallback, and canonical `Camera Flash` rows remain native.
The HXC PlayState facade exposes `isInCountdown` through native
`startingSong`, so imported stage callbacks can read or set that phase
without a missing-field error. `mayPauseGame` reads and writes the native
`canPause` flag used by the pause input and song-end transition.

## Import and compatibility boundaries

`ImportSettings` and `ImportRootScanner` identify a donor. `ImportWorkflow`,
`ModuleFunctions`, and engine-specific importers copy or convert the package
into native registries, charts, and sidecars. `ImportEngine` records the donor
type. `EngineCompat`, `HxcCompat`, `HxcCompatRuntime`, `NoteTypeCompat`, and the
runtime HScript bindings translate donor behavior during playback. A generic
conversion belongs at one of these boundaries, with a regression test that
reproduces the donor format. Song-specific workarounds in assets are outside
the scope of engine compatibility work.

`assets/images/custom_chars`, `custom_stages`, `custom_cutscenes`,
`custom_difficulties`, and `custom_ui` hold registries used at runtime.
`assets/data/freeplaySongJson.jsonc` determines freeplay categories. Imported
content can also write to the runtime asset tree; import behavior must account
for both the repository seed and live runtime files.
For imported Modding Plus or legacy content, a donor's `Base Game` category
means that donor's built-in songs. The import plan maps those selected songs
to `Imported` in this engine, without relabeling unrelated native songs.
Some older Modding Plus releases omit separators in the flat string map at
`custom_stages/custom_stages.json`. The import registry parser has a guarded
recovery for that exact registry shape; it still rejects malformed nested or
non-string maps, and leaves the donor files unchanged.
Psych stage IDs in a chart remain valid when a direct stage Lua/HScript file
resolves inside that song's selected Psych compatibility root. This check is
scoped to its `compatScripts.json` manifest; sibling imports, nested unused
scripts, and non-Psych roots cannot validate a stage. Hard-only Psych charts
therefore keep their authored stage when no normal chart exists.
`LuaCompat` emits optional HScript parameters for translated Lua functions.
Lua passes `nil` for omitted positional arguments, so a helper defined with
five parameters can be called with four without aborting its script scope.
V-Slice scripted NoteKind constructors can name a separate note style whose
identifier differs from the note kind or script filename. The importer reads
the constructor's literal style id, materializes only its note and hold atlas
mappings, and keeps the native custom-note identity. `Note` uses those
per-kind atlas settings even when the song's main UI style is pixel; a partial
note style does not become a selectable full UI preset.
Missing V-Slice countdown media use the native pack fallback only when the
authored path is a `shared:` or `default:` library resource under
`ui/countdown/` or `gameplay/countdown/`. The rule applies to any theme name;
custom paths and traversal paths remain unresolved with a diagnostic.
HXC character sprite construction uses the ordinary native Sparrow adapter
for gameplay effects; only explicitly death/overlay-scoped handles use the
game-over bridge. HXC note callbacks translate the native top `sick` rating
to the V-Slice `perfect` judgement name before companion scripts inspect it.
`HxcAssetPlanner` resolves bounded literal image/atlas references from HXC
source without executing donor code. Its finite evaluator follows nested
literal arrays, simple conditions, indices, assignments, and literal call
arguments while preserving grouped array relationships. Enclosing `for` loops
over a finite literal array expand only their bounded member values, allowing
menu code that concatenates an item into a path to stage each referenced asset.
Unknown loop collections remain unresolved; member and cross-product caps keep
the import bounded. The planner no longer carries
special asset-family path expansions for an individual imported mod.
`HxcEventSpriteDescriptor` extracts a bounded static sprite-event shape from
HXC event source: literal atlas key, animation prefix and timing, camera,
position fields, scroll factor, and finish cleanup. Import writes the accepted
descriptors to a destination-only catalog under the event script's manifest
root and copies a complete atlas pair there. `PlayState` reads only the
selected root. For imports made before the catalog existed, it may derive
the same descriptor from at most 128 HXC event files of at most 1 MiB each
within that root. Missing or ambiguous shapes cannot borrow another import's
asset.
HXC character helpers resolve the live role slot for gameplay callbacks.
The actor being constructed is bound only during its `onAdd` callback, so a
retained interpreter cannot animate a replaced character. The HXC chart
facade maps `currentChart.song.id` to the live native song identity.
The game-over module adapter validates its imported manifest root and its
source-extracted player roster before handing a replacement character to the
native substate. Character visuals still resolve through the shared custom
character registry: older imports flatten those files under
`assets/images/custom_chars`, so their manifest owner cannot be proven after
import. Duplicate character IDs across those older imports remain ambiguous;
future root-scoped construction needs importer-owned character provenance and
distinct materialization before a strict lookup can be enabled.
HXC interpreters bind a limited `ReflectUtil` facade for class-name queries
and anonymous-field reads used by imported modules. The facade maps native
StoryMenuState and FreeplayState to their donor class names and is not exposed
to unrelated HScript scopes.
Characters are constructed before the chart stage exists. Their HXC `onAdd`
callbacks therefore enter `HxcCharacterLifecycleQueue` once per actor and
role, then run after the stage interpreter and all character scopes are bound.
The same flush runs after a successful stage replacement or its neutral
fallback. Stage props created by a character callback can then attach to the
live `curStage` instead of being lost through a null stage reference.
HXC note callbacks identify compiled native `Note` objects by runtime class
and read typed properties even when `Reflect.hasField` omits them. The shared
note view carries the authored lane, singing flag, and alternate animation;
`characterHandled` is set only for a valid note view, so malformed callbacks
leave the native singer available. `Character.playSingAnimation` is kept for
the reflective HXC bridge. The opt-in `--smoke-trace-player-hits` probe queues
primitive hit data and samples the live actor animation on the following
update tick, after note callbacks finish.
The character-scope ownership filter likewise reads native note properties:
an explicit hit/miss side takes precedence, otherwise the source playfield
owner overrides `mustPress`. Forced-GF opponent notes use the native opponent
fallback when GF is absent. Returned `getScreenPosition` points use readable
`x`/`y` properties, including zero coordinates; native field-presence checks
must not discard a script's replacement point. Actor scoping, recursion guards,
and restoration after callback errors still apply.
`goodNoteHit` computes the native rating before it builds the imported note
payload, including the mine/nuke timing multipliers. The same calculation
feeds the score popup, so callbacks receive the displayed judgement even
when custom input calls the hit path directly.
The note proxy also copies finite `offset.x/y` values and boolean `flipY`
back to the native sprite. It exposes a small coordinate view rather than
the native `FlxPoint`, so unrelated script fields cannot mutate the Note.
`HxcCompat` can lower a bounded, literal HXC note-hit text rule into
`HxcNoteTextSpec`. The generated script passes that data to
`HxcCompatRuntime`, while `PlayState` owns the actual text, its selected
manifest's font lookup, lifetime, and cleanup. Song IDs and copy come from
the imported script; the engine has no named-song branch for this effect.
When the same source also provides a complete literal sprite and sound
pattern, the descriptor carries root-relative media, frame geometry,
animation, camera, and alpha bounds. `PlayState` loads the overlay only for
an exact source-listed song, keeps it on the HUD camera, flickers it while
active, and restores its idle alpha on the strict expiry step. A rule with
no text lines can still run the overlay and sound.
Bounded literal miss rules use the same owner and lifetime, with their own
song IDs, probabilities, and text lines. They do not require a hit judgement.
Miss rule IDs must already belong to the descriptor's mounted song set;
unrecognized miss bodies remain diagnosed rather than partially executed.
Malformed rules stay in the diagnostic path instead of running donor object
graphs in the native state.
An HXC class with no PlayState lifecycle hook is still a valid declaration
(for example a class containing only Freeplay metadata). The converter emits
a parseable empty scope so loading that class does not abort gameplay; it
does not invent a callback or execute menu behavior in PlayState.
Literal `FunkinMemory.permanentCacheTexture(Paths.sound/image(...))` calls in
imported HXC module constructors become manifest-scoped native warmups.
Sound warmups decode through `FNFAssets` and retain at most 32 entries,
reused by exact-path playback and loading. Dynamic keys and media outside the
selected root remain rejected. Module regressions check dispatch eligibility
as well as executing the translated callback body.

## Build, settings, and tests

`./run.sh` bootstraps pinned tools, prepares Linux case mirrors, patches the
local haxelibs, and invokes Lime. `tools/launch_cache.py` uses file metadata
to skip an unchanged build without hashing multi-gigabyte media. It watches
the build inputs, so editing the README or change log alone does not trigger
a game rebuild. For repeated
builds, `./run.sh server` starts Haxe's compilation server, which `run.sh`
uses automatically when present. If the server returns a failed compile,
`run.sh` retries once without the server; stale compiler state has caused
false errors after dependency or project changes. The runtime lock prevents a
build from overwriting native libraries while the game is running.
The `run.sh` hscript patch checks a thrown value's runtime kind before asking
for its enum constructor. On hxcpp, calling `Type.enumConstructor` on an
ordinary script error can segfault before a Haxe catch executes. Constructor
names still distinguish HScript control signals from its error enum.

The tracked `assets/data/options.json` is the public default seed. The live
settings file is `export/<mode>/linux/bin/assets/data/options.json`.
`OptionsHandler` reads and writes that live file at runtime. `run.sh` saves
the live settings before Lime sync and restores them afterward. It snapshots
runtime assets with hardlinks so Lime can reuse its existing output tree,
then restores runtime-only imports removed by sync. Import registries have
their own backup because both source and runtime may contain a copy.

`python3 tools/run_tests.py` runs independent test modules in parallel and
reports a failure if any module fails. It removes desktop display variables
from each test subprocess; tests needing a screen create their own isolated
Xvfb display. The serial equivalent is
`python3 -m unittest discover -s tools/tests`.
Most behavior tests extract a small Haxe class or method and run it with the
portable Haxe interpreter; asset tests validate real registries or imported
fixtures. A test should exercise the shared behavior it protects, and stay
bounded so the large media library is never scanned or embedded during tests.
The mounted Auto-import diagnostic caches its compiled scanner under `tmp/`
using the generated Haxe sources and local toolchain as the key. Each run still
reads the current donor corpus and recomputes the diagnostic counts.
Native smoke and import-preparation runners launch the game through an
isolated Xvfb display with dummy audio. They fail before launch if that
off-screen display is unavailable, and kill the process group on timeout.
They never attach test windows to the user's desktop session.
The targeted Freeplay smoke fails if it leaves song select before the
requested row is reached and accepted, so an early transition cannot be
mistaken for a successful cross-selection test.
The native hit trace is enabled only by `--smoke-trace-player-hits`; it reports
the player-one hit owner and post-route actor animation for a bounded smoke.
`--smoke-player-hits` drives due, hittable player notes through the ordinary
`goodNoteHit` route and implies practice mode. It skips avoid notes, leaves
saved input settings untouched, and is separate from demo mode, whose AI
route does not dispatch the same imported hit callbacks. Smoke practice
applies even when the user skips the modifier menu, and all smoke sessions
are excluded from song and week high-score writes.
Accelerated demo playback samples the native music channel as its authoritative
clock. Some native backends report a transient zero at the end of a track
before clearing the channel's `playing` flag or calling `onComplete`.
`PlayState.updateDemoClock` recognizes that zero only after a positive prior
position within a bounded end window, preventing `MusicBeatState` from
rewinding and replaying beat hooks during the final update. The initial zero,
paused clock, and ordinary backward seeks remain distinct in the focused
clock test. A rebuilt 20× Linkinteen replay and 1× post-transition actor
motion check are recorded in the verification report.

## Source-data observations

The mounted V-Slice tied-girlfriend definition requests frame indices 0–30,
but its `EX Tricky GF.xml` atlas contains only 20 matching frames (0–19).
The missing artwork cannot be reconstructed by a format adapter. The engine
keeps the source animation order; this remains a donor-data limitation.
The mounted Expurgation chart contains 47 sign events, and the imported chart
retains those 47 entries in 33 timestamp groups. A complete offscreen event
census matched all 47 timestamps, including simultaneous entries, without
missing or extra dispatches. Reducing that authored frequency would change
chart behavior.
The long run also exposed missing scoped note-style metadata and the HXC
`NoteStyleRegistry`/`NoteSplash` bridge. The importer now retains that metadata
and the runtime provides a shared style descriptor and native sprite owner.
Subsequent manual-input testing found that unrelated NoteKind scripts received
ordinary notes; dispatch now checks each note's authored kind. The earlier
splash warnings therefore do not prove those charts authored that behavior.
See the verification report for the current native acceptance checks.

## Load and swap diagnostics

`RuntimeDecodeMetrics` is enabled only during smoke load/swap measurements.
It counts disk bitmap cache hits, decode attempts and decode duration along
the `FNFAssets.getBitmapData` path, with phase and character-swap markers in
`RuntimeSmokeHarness`. Direct `FlxAtlasFrames.fromSparrow(String, ...)` calls
use OpenFL's separate asset cache; these counters do not measure every image
load. Total swap elapsed time includes both paths.

`FNFAssets.exists` uses one case-insensitive resolver attempt per native lookup
and then checks the embedded asset manifest. It does not cache misses: imports
can add a previously absent file while the process is running, and the next
lookup must see it. This matters during note creation because legacy UI packs
may omit `multiNotePresets.json`, causing repeated lookups before the default
preset is selected. Exact native disk hits skip the OpenFL manifest probe;
the resolver optimization reduces duplicate directory walks. Neither change
is evidence that the unrelated native heap abort is fixed.

`NoteKeys` keeps a bounded cache of parsed preset templates for one song.
Each note receives a deep clone, preserving independent mutable keys and
definitions. Song creation and the main-thread import-completion handoff clear
the cache, including cached missing paths, so the next chart observes newly
imported preset files. Parse failures still reach the caller.

An experimental per-song atlas holder was removed after a native same-binary
comparison found equivalent swap times with and without it. OpenFL already
reused decoded images for the sampled direct-string character loads. The
existing preload and state-exit cleanup behavior is retained.

Null-operand warnings include the script source and current callback, with
deduplication per operator/source/callback; nested callback dispatch restores
the previous diagnostic context even on failure.

## Translated Lua runtime boundary

`LuaCompatInterp` applies Lua truth values, operand-returning short circuit
operators, and one-based table access only to proven translated Lua programs.
`LuaCompat` marks newly generated sources. `PlayState.luaProgramFor` also
recognizes an older generated HScript only when its entire contents match the
translation of a surviving Lua sibling; it then uses the current translation
in memory. Edited or native HScript is not reclassified. The UI interpreter
uses the same selector.

Lua-created tables retain mixed keys, object-key identity, nil deletion and
sparse numeric keys without allocating an array up to the largest index.
`pairs`, `ipairs`, length, clearing and copying use interpreter-owned helpers;
those helpers are installed after shared engine bindings. Native API arrays
retain their existing direct-access ABI, while Lua iterator helpers expose
one-based keys and corresponding values. Ordinary HScript/HXC retains the
normal interpreter and zero-based arrays.

In translated Lua scopes, an unset global reads as `nil`; ordinary HScript
still reports an unknown variable. Lua arithmetic on `nil` throws a scoped
diagnostic, matching LuaJIT's failure behavior instead of silently producing
a null HScript result. The numeric `for` lowering evaluates its start, end,
and explicit step once, advances the variable after each body execution, and
keeps the existing loop watchdog as a safety bound. The non-unit step route
is covered by executable ascending and descending fixtures; the Xfracture
`noteMoveOnPress.lua` source is one installed case that previously spun.

This is a bounded language adapter, not a complete Lua VM. Unmarked
`PsychStageCompat` wrappers combine native scaffolding with translated
callbacks and retain native interpretation; shared helper aliases keep their
existing behavior but do not provide the new table semantics inside those
embedded callbacks. HScript-ex module parsing also remains native. These
boundaries need an explicit source-language representation before broader
interpreter selection is safe.

## V-Slice stage prop geometry

V-Slice applies prop scale, updates the hitbox, then assigns the authored
position. Updating the hitbox also computes Flixel's sprite offset; omitting
it scales art around the old center and shifts the drawn image away from its
stage coordinates. `VSliceImporter` emits this order for every prop.

For existing imports, `VSliceStageCompat` normalizes the old generated prop
construction blocks in memory before parsing. It requires the song's selected
manifest root to be V-Slice and a native stage scope, and matches only the
generator's `vSliceProp_*` declaration/creation/graphic/scale/scroll structure.
Already corrected, custom, non-stage and other-engine sources are left alone.
No chart, donor asset or generated script file is rewritten.

The importer also records each prop's numeric `zIndex` through
`StageHelper.setZIndex`. Coarse `BEHIND_*` insertion alone is insufficient:
the subsequent stable depth sort would otherwise move default-depth props
behind characters. Older generated scripts did not retain numeric prop depth;
their scoped normalizer uses the recorded target actor depth and stable
insertion order to preserve actor-relative occlusion. Exact original numeric
depth requires regeneration from the donor definition.

Stage HXC resolves JSON props by their authored `name`, which may contain
spaces and differs from the generated HScript identifier. New V-Slice imports
register the exact authored name in the stage's element map after adding the
sprite. Older generated scripts had only local `vSliceProp_*` variables; the
selected-owner stage normalizer registers structurally verified generated
sprites into that same map at load time. `StageHelper.getNamedProp` derives the
old identifier from the requested name and returns it only when the match is
unique. This keeps existing imported files intact and prevents lookup across
stage instances or import owners.

## V-Slice animation and note visual defaults

Animation loop flags follow the shared V-Slice
[AnimationData schema](https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.7.3/source/funkin/data/animation/AnimationData.hx):
omitted `looped` means false for characters and stage props. The legacy `loop`
alias is accepted and explicit flags are preserved. Animation names do not
imply looping. Existing generated character scripts require regeneration to
recover whether their old `true` flag was authored or invented by the converter;
the runtime must not blindly change every dance animation.

NoteKind lookup accepts a literal constructor identity even when the HXC file
has a different name. When an older `noteInfo.json` lacks custom visual fields,
the runtime can recover them from the selected namespace's NoteKind constructor,
note-style JSON and complete atlas pair. This overlay is in memory and preserves
existing visual overrides; another import's identically named style is not used.

Imported note-style tap notes center their full Sparrow frame canvas on the
lane, following V-Slice `Strumline.buildNoteSprite`. The alignment is reapplied
after every `Note.updateHitbox`, including strum snapping, so large frame
canvases cannot drift horizontally and authored offsets survive hitbox resets.
Trimmed subtextures retain their position inside that canvas. Sustains and
ordinary native note definitions retain their existing layout. Opt-in smoke
diagnostics report the actual graphic key and rendered/lane centers.

## Refreshing generated V-Slice visual scripts

Ordinary imports remain additive and skip existing generated HScript. Use
`tools/refresh_vslice_visuals.py plan --donor-root <root> --runtime-root <bin>
--output tmp/<plan>.json` to preview a scoped refresh. It invokes the current
converter and real compatibility helpers, with the engine JSON parser extracted
for interpreter use. It selects charts by the exact donor namespace, rejects
IDs referenced by other owners, and requires existing mapped media to match.

Review every candidate diff before `apply --plan tmp/<plan>.json --reviewed`.
An old generated-script marker alone does not prove the absence of local edits.
Applying verifies source, output, converter/tool and media hashes, acquires the
runtime locks, backs up all replaced scripts plus the plan under
`tmp/import-refresh-backups/`, and replaces only the reviewed character/stage
scripts. Settings, charts, registries and media are retained. Hash drift requires
a new plan. Do not reset entire import namespaces to update generated code.

`tools/refresh_vslice_visual_owner.py` handles the broader selected-owner visual
refresh. It fingerprints one mounted package, snapshots the owner's installed
charts, audio, registries, Freeplay entries and options, then runs the native
import under the runtime lock. It accepts only new files belonging to that
owner and restores protected existing bytes; postflight failures roll back the
transaction. Its receipts distinguish transaction success from remaining
source dependency diagnostics.


## V-Slice hit routing, botplay policy and animation geometry

The V-Slice importer stores source rows outside the active two-strumline lane
range in `vSliceUnroutedNotes` on the selected difficulty chart. They are not
added to gameplay `sectionNotes`. `Song` carries only the requested
difficulty's raw rows into the editor, and Quick Save keeps the JSON payload.
The private native editor smoke compares those rows by JSON value before and
after autosave reload, since object field iteration order can change.

HXC note-hit payloads distinguish scored player ratings (`sick`, `good`, `bad`,
`shit`) from autonomous opponent/botplay `perfect` hits. Converted legacy sustain
segments do not each emit a V-Slice note-head hit. Both autonomous sides use the
same cancellable pre-hit dispatch; canceled automatic hits are not retried each
frame. This preserves authored chance-based effects without binding them to
manual input or multiplying them by sustain length.

Optional harmful NoteKinds can declare `avoidAutoHit`. The converter also derives
this policy from the bounded combination of literal hit damage and a canceled
miss callback. It does not infer hazards from names, priority, or artwork. Older
V-Slice definitions recover missing policy in memory from NoteKind scripts in
the selected import namespace; explicit policies are retained. Player botplay
skips these hazards while opponent behavior keeps its authored route.

`NoteOffsetState` preserves absolute script writes to each offset axis across
later hitbox updates. V-Slice character rendering preserves Flixel's hitbox
alignment and applies Bopper's scaled animation/global offset difference through
`hxcBaseScreenPosition`. Translated `super.getScreenPosition` shares that baseline
without recursively dispatching the companion hook. Other character formats
retain their existing offset convention. Before stage placement, V-Slice actors
refresh their hitbox after the opening dance/idle selection, matching donor
BaseCharacter creation/reset. This also repairs older generated character
scripts that sized the first atlas frame instead of the opening idle frame;
the stage then anchors the correct feet dimensions without per-character offsets.
The importer stores CharacterData's global offset separately from role placement.
Existing generated scripts that only set role offsets snapshot their source
values immediately after character initialization, before a stage changes those
fields. HXC indexed `animOffsets` and `globalOffsets` reads resolve against the
active native animation and this stored global offset.

Native smoke flags `--smoke-botplay` and `--smoke-frame-stats` exercise the actual
demo route and record gameplay frame timing with song position. These are opt-in,
do not save modifiers, and must be launched on the private offscreen display.


V-Slice receptor alignment is selected by the imported UI pack's `vSliceAlias`.
The donor receptor anchor and positive authored position offsets are mapped
into the host lane coordinates after frame changes. The setup atlas frame
establishes the retained receptor anchor; active animation canvases alter the
render offset without moving that anchor. This follows donor centerOffsets
with its retained setup hitbox and omits the classic atlas confirm nudge. Native/Psych paths preserve their
existing behavior. Smoke receptor snapshots are deduplicated before allocating
the diagnostic payload, so ordinary frame measurements do not build snapshots
for every receptor on every frame.


The Lua translator accepts token-delimited compact `then`, routes `math.exp`,
and lowers literal `string.gsub` patterns through `luaStringGsub`. Escaped
punctuation is supported, including a replacement limit; classes, captures and
replacement substitutions remain diagnosed rather than approximated. Mounted
corpus checks validate every available source and allow the fixture inventory
to grow without fixing its total file/call count in the tests.


Stage role replacement retains raw V-Slice feet position, stage scale, alpha,
angle, scroll factor and camera offsets. `StageHelper` applies those values to
the incoming actor's constructor-captured base scale/flip and its own hitbox,
not the outgoing actor's already-scaled presentation. Role reassignment drops
obsolete depth/presentation references. New converter output registers this
data; strict structural normalization recovers it in memory from eligible older
selected-import stage scripts. HXC stage replacement and ordinary native
character creation share this operation, with legacy behavior as fallback.
Older generated solid-color props can encode their fill as a decimal or Haxe
hex literal. Both forms participate in the same bounded hitbox, layer and
named-prop recovery; authored handwritten stage code is left unchanged.


### Import ownership and recovery

`ImportSongOwnership` rejects a repair when an existing song manifest includes
another donor root. The batch loop checks before skipping or writing a song,
the direct writer checks before copying audio, and the manifest writer checks
before selecting scripts. Non-overwriting repair cannot replace chart/audio
ownership by changing only `selectedRoot`. Legacy imports without a manifest
still use the additive path; ambiguous historical imports need review.

`tools/reset_mixed_imports.py --runtime-root <runtime> --owner
assets/imported_mods/<namespace>` previews only mixed songs selecting that owner.
`--apply` acquires both runtime locks, requires the game closed, moves song data
and audio to `tmp/import-reset-backups/`, and backs up/removes their Freeplay
entries. It preserves shared media, namespaces, donors and options. Run the
normal Auto importer against the intended donor afterward. Current reset input
requires the runtime's serialized JSON registry; arbitrary commented JSONC is
not rewritten. Keep the backup until playback is verified.

### Chart-event video skip

`VideoCutscene` distinguishes an enabled explicit Space skip from natural
completion/error and exposes VLC duration. V-Slice chart-event videos use the
source event's non-skippable path; other video callers retain their own skip
policy. Event media is imported below the selected package owner and playback
resolves that owner, so two packages can use the same clip name independently.
An early enabled skip waits at most one second for metadata; unknown duration
closes the video without inventing a seek target.
`EventVideoSkip` computes a forward-only endpoint bounded by song length.
`PlayState` seeks instrumental/vocals/Conductor, retires prior notes without
scoring, updates BPM/step/section and replays crossed chart events in order,
omitting nested video events. Retired notes are killed before destruction;
surviving sustain pieces detach destroyed heads and re-root destroyed
predecessors while retaining their horizontal anchor. This keeps normal
upscroll and strumline code from reading cleared sprite fields on the next
frame. The private native forward-seek smoke checks synchronized clocks,
event cursor, note retirement and post-seek continued play. Natural
completion retains the running clock.
The type-2 HXC video module keeps its bars on the HUD during the authored
fade and transfers them to the cutscene camera only when that fade completes.
HXC video paths resolved to `assets/imported_mods` are checked against the
active script owner and the file's canonical path before playback; the Psych
stage route supplies its own selected owner explicitly.
The HXC sound proxy first uses an owner copy, then maps V-Slice's logical
standard and pixel countdown sound keys to the native shared countdown pack.
The image proxy similarly resolves only the shared `ui/countdown/<style>/<cue>`
namespace through the active UI pack, normal pack and native pixel pack when
the package omits V-Slice's base image library. Other image names keep their
ordinary owner and native lookup rules.
The HXC `Paths.file` proxy validates relative keys and canonical owner
containment before reading an owned file. Safe keys can still fall back to a
native base-game asset when the package has no copy; traversal and symlink
escapes cannot borrow files from a sibling import.

### Imported split vocals

Charts may carry a `vocalStems` list for separate player and opponent voices.
`PlayState.initializeVocalTracks` resolves each entry inside the active song
audio folder and hands the selected sounds to `VocalTracks` for synchronized
transport. When imported metadata lists the same stem in multiple encodings,
`VocalStemSelection` keeps one file per basename and favors the platform's
native sound extension. Distinct stem basenames and their roles stay separate.

HXC loading hands the translation result into note-kind/companion registration
within that load. This avoids duplicate analysis without a persistent cache or
changing script lifetime. Psych scopes receive the engine's actual story flag
and `lowQuality=false` because the engine currently has no reduced-quality mode.


### Script lifecycle and partial packages

HXC lifecycle callbacks are Void and cancel through their event payload. Their
interpreter's incidental last-expression return must not enter Psych's
`Function_Stop` collection. Pause uses the configured control action and a shared
HXC cancellation payload. Native chart-event videos suspend VLC playback and
hide their OpenFL children while the pause menu is open, then restore on resume.

HXC character `start` and `createPost` run with the current actor bound to the
interpreter and restore the previous binding when they finish or throw. The
companion receives the native actor's recorded definition scale through its
source `setScale` callback before `onAdd` and screen-position dispatch. The
character translator preserves explicit reads and writes to the native actor's
position, idle suffix, pixel flag, `originalPosition` and `characterOrigin`,
plus inherited reset and animation methods; script-owned class fields remain in the
interpreter. This lets scale-dependent visual callbacks use their initialized
source state without overwriting the actor's stage placement. The selected
import root owns mutable `Constants` defaults, including the full
difficulty list, for the duration of that PlayState session. String helpers
lower null-sensitive donor calls through bounded runtime functions. HXC
`destroy` uses one lifecycle payload for both event-taking and no-argument
donor callbacks, so cleanup runs without an arity mismatch.
The HScript null-read, null-write, null-call and null-iterator guards attach
the selected source file and callback to each diagnostic and deduplicate only
within that context. A later callback can therefore report the same missing
receiver again without terminating gameplay.

For selected V-Slice owners, each native `Strumline` exposes `notes.members`
and `holdNotes.members` as live, side-filtered HXC views. A hold view follows
one authored head through its duration while the native engine retires its
per-step sustain sprites; accepted hits and misses update that same view.
The view carries the authored note kind through `CompatSongNoteData` and is
discarded with the PlayState. `Strumline.applyNoteData` rebuilds only that
line's unresolved native notes and hold views from copied source descriptors;
the receiving line determines scoring ownership, allowing source scripts to
swap chart sides while the audio clock and other line continue. The active
`currentChart.notes` read is lowered to copied `CompatSongNoteData` descriptors,
so source scripts can partition those rows without mutating the installed
chart. Direct HXC
`FunkinVideoSprite` instances use owner-bounded media paths and retain source
loop, seek, camera, and layer control until PlayState cleanup. Gameplay pause
and resume suspend only videos that were playing at pause time; state teardown
releases their decoders and inserted HXC cameras. The camera bridge implements
ordinary FlxCamera operations used by mounted scripts; cross-camera blend
rendering has no compatibility implementation yet. `HealthIcon` exposes authored animation selection
and an `autoUpdate` gate; health and beat updates honor that gate until a source
script restores it. `PlayState.stageZoom` reads the current stage's unmodified
camera zoom separately from the event-adjusted `currentCameraZoom`.
`PlayState.disableKeys` gates native gameplay lane input during scripted
selection sequences while the script can still read its own keyboard events.
Generated HXC visual-event sprites enter a disposal queue when their animation
finishes. PlayState removes them after Flixel's group update returns, because
Flixel dispatches its animation finish signal after invoking the callback;
destroying the controller inside that callback invalidates the signal.
For direct HXC video sprites, the media resolver checks the selected owner's
`videos/`, `videos/videos/` and `assets/videos/` layouts before shared video
assets, and rejects canonical paths outside the owner. HXC camera filter
assignments resolve opaque owned shader handles to native BitmapFilters and
discard invalid entries before OpenFL can clone them during rendering.

Psych note compatibility exposes the authored `noteType` through the live
`Note`, and carries Lua writes to `hitHealth`, `missHealth`, `ignoreNote`, and
`hitCausesMiss` into live note state. Explicit health values and ignored-note
rules enter native judgement. A manually hit player note with
`hitCausesMiss=true` takes the native miss route, skips ordinary hit scoring,
health gain, and singing, then still completes the good-hit callbacks; botplay
avoids both ignored and hit-causes-miss notes. Eligible hazard heads use the
native global and strumline splash gates. The host `Note` carries a fresh
`noteSplashData.disabled` flag for each note; both ordinary and hazard splashes
honor it. Numeric writes arriving as Lua strings
are converted at the property boundary. Ignored player notes do not count as
misses or botplay hits. The live note visual marker records these fields so
offscreen source checks can distinguish an imported atlas from effective
gameplay behavior. Psych stage conversion also carries literal
sprite flip properties, and the song interpreter exposes `setHealthBarColors`
through the native bar refresh path.

Psych `addLuaScript` uses script identity, a recursion guard, and the caller's
selected import scope. `PsychLuaScriptDependencies` follows literal references
recursively within bounded script-directory walks, preserving relative paths
inside that namespace; repair checks detect missing referenced scripts. Dynamic
script paths still require the corresponding files to be available in scope.
Psych `removeLuaScript` resolves the same bounded path and closes every active
scope for that source file. The current chart's copied song script may remove a
script in its selected imported owner; a script from another imported root may
not. Closing stops later callbacks while keeping stage objects already created
by the script, and clears the running identity so a later add can reload it.
The running check also drops self-closed interpreters and stale stage records
whose scope key was reused by a different stage.
`flashingLights` reflects the user's current preference when the scope is made.
Psych Lua `getPropertyFromClass('flixel.FlxG', ...)` reaches the live native
game, state, input, sound, camera and scale objects through a bounded static
root map. The ClientPrefs judgement-window fields read the active native
Judge thresholds; `ratingOffset` is zero at that bridge because native note
strum times already include the selected timing offset. This keeps script
class reads aligned with the live settings rather than a detached class value.

Partial Modding Plus packages may provide an exact-name character HScript and
Sparrow atlas without a registry. `ModPlusCharacterRegistry` adds only missing
entries whose supplied script and atlas are byte-identical to the materialized
files; comparison streams fixed-size chunks. It preserves existing metadata,
uses explicit default icon/color metadata when none was supplied, and does not
infer animation aliases. A directly named stage implementation similarly does
not require a registry the donor never supplied; provided JSON/JSONC registries
remain required dependencies.

PauseSubState owns a transparent, non-default screen-space camera for its entire
lifetime. Gameplay HUD alpha, visibility, zoom and filters are authored state and
are not changed to reveal the menu. Closing or replacing the substate releases
its camera; event-video suspension separately hides the native video surface.
This keeps menus visible during HUD fades while preserving their resume state.

### Codename runtime boundary

Codename chart conversion and static stage XML composition are supplemented by
an explicit classless-script loader. It selects the manifest owner's immediate
song scripts, selected difficulty scripts and authored stage sidecar using
`CodenameScriptPlan` metadata. Scopes receive ordered create/postCreate,
onSongStart, update, stepHit, beatHit and destroy callbacks, scoped Paths,
and owned sprites/timers/tweens. Standard `Std` is available as a script global
and explicit import. postCreate waits for scene initialization.
Failed initialization releases owned objects and restores camera alpha.

The selected owner's classless global script is hosted separately from song
scopes. Its `preStateSwitch` runs before Flixel creates the next state, and
`postStateSwitch` runs from Flixel's matching signal after creation. The
handler is removed when that owner is cleared. Global callbacks carry source
and callback context into nested timer diagnostics; menu objects constructed
after a state switch are then ready for the next global update.

A private native title-card/restart check confirms this initial execution path.
Codename structured chart-event callbacks now have their own runtime adapter;
broader APIs and native event actions remain incomplete. XML stage prop names
are refreshed into each interpreter through `CodenameStageBindings` before
callbacks and immediately on stage replacement, including timer-only scopes. Only valid bare identifiers are exposed; existing engine globals and
script reassignment take precedence. Stage replacement refreshes still-owned
aliases and removes vanished/null props, preventing references to destroyed
objects from surviving into the new stage. Camera ownership and reversible native HUD membership now have
separate shared adapters, with native failure-rollback verification. Dedicated
camera probes verify sprite zoom/rotation composition and transformed culling
in two measured cases; this does not establish complete rendering parity. Do not feed arbitrary `.hx` into the HXC adapter:
its event payload ABI differs. Shader support is another unresolved dependency.

Codename event conversion retains its four native route columns and adds an
optional versioned `CodenameEventMetadata` object in column five. It records the
exact source event name, typed parameters, timestamp, global flag and chart/shared
ordinal, with a fingerprint of the native route. Collection validates that
fingerprint and retains distinct authored rows even if their native route is
identical. Only exactly equal timestamps share a group. Editor saves and companion
merges preserve metadata; timestamp-only moves update it, while native name/value
edits invalidate it without shifting unrelated extension columns. Existing
imports without metadata retain the old native behavior and report that a chart
refresh is needed before structured callbacks can run. Event script discovery
uses exact chart-authored names in the selected owner root. Built-in names are
registered by the engine; custom names require a nonempty matching `.json` or
`.pack` schema, following upstream EventsData. The importer copies eligible
scripts, schemas and literal dependencies through the same non-overwriting
copy/repair plan. They load after song/difficulty scripts and share the stage,
song and event script callback sequence.

`CodenameEventDispatch` keeps the Codename ABI separate from native four-argument
`onEvent`: each dispatch passes a mutable `CodenameGameEvent` wrapper containing
`event = {name, time, params, global}` and fresh `data`. A runtime event object is
retained per collected row, so in-place edits survive replay while replacing
`wrapper.event` affects only that dispatch. Import metadata stays untouched. Upstream cancellation has different defaults: `preventDefault(false)`
stops later scripts, while `cancel(true)` allows later scripts to run. Both cancel
the built-in action and its `onPostEvent` callback. A noncancelled event runs
one recognized native route after script mutation, then `onPostEvent` with the same
wrapper. Unknown custom events have no default action and still receive the post
callback. They cannot fall through to a coincidentally named native API from
another engine. Missing built-in routes and malformed replacement payloads get
explicit bounded diagnostics. Released scopes are skipped during dispatch;
newly loaded scopes can participate in the subsequent post phase. Codename
character script packs, pre-countdown camera event seeding and the full set of
built-in parameter semantics remain incomplete.
`PlayState.applyCodenameNativeEvent` applies the zoom and scroll-speed native
contracts after script mutation, before the legacy route adapter:
`Camera Zoom` takes `[tween, zoom, camera, steps, ease, easeDir, mode,
multiplicative]`. A false tween flag assigns immediately; `CLASSIC` changes
the selected camera's recovery default only. Direct mode scales by
`FlxCamera.defaultZoom`; other modes scale by the stage default. Multiplicative
mode additionally uses the selected camera's live zoom. Each camera owns a
separate replaceable tween, and its recovery default follows tween progress.
`Scroll Speed Change` takes `[tween, speed, steps, ease, easeDir,
multiplicative]`; multiplication uses current scroll speed, not chart speed.
Both durations use the current `stepCrochet * steps / 1000`. These contracts
cannot be implemented by passing the parameters unchanged into the legacy
packed camera or Psych scroll-speed handlers. Separate state-owned tween
channels cancel replacements without completing the old action, suspend during
pause, and clear on teardown. `game.scrollSpeed` proxies the native
`daScrollSpeed`; `defaultHudZoom` supplies the independent HUD recovery target.
Typed `Camera Position` also uses this lifecycle, with absolute or relative
coordinates based on the current `camFollow`, immediate snaps, default CLASSIC
following and eased scroll motion. Fixed-position ownership bypasses native
section/animation follow without repeatedly overwriting `camFollow`, so scripts
can still edit it. A legacy FocusCamera handoff releases that ownership.
`CompatCamera` adds a `followEnabled` gate to automatic follow while preserving
the script-visible target. Both `updateFollow` and `updateLerp` must honor that
gate: pinned Flixel calls them separately, so gating only target calculation
still lets paused scroll drift toward the stale interpolation target.
Explicit `snapToTarget()` temporarily bypasses the
gate and restores its prior value. Movement tweens restore the previous follow
flag before replacement or teardown; a stale completion cannot restore a newer
tween's follow state. Other cameras retain their existing class and gameplay
automatic following defaults to enabled.

Codename camera identity is stored separately from the existing stage-script
plan in selected-root `songs/<source>/__cammie_compat_camera.json`. Exact
difficulty entries preserve authored strumline order and character occurrences,
role/type/position, character global and camera offsets, and named stage camera
offsets. Missing character definitions stay explicit. Re-import builds the
reserved script and camera sidecars from the same current selected-owner chart
set, validates their difficulty keys and stage names, then reconciles the pair
together with rollback on a failed write. Existing imported charts and source
scripts are outside that generated pair. These identities supply authored
indices for the live Camera Movement
controller; runtime actor construction and script callbacks remain separate
from metadata storage.
The stage converter now uses `CodenameStagePlacement` to resolve named character
placeholders before chart position slots, preserve role aliases/last-definition
precedence and apply omitted-role defaults (BF 770,100; GF 400,130 with .95
scroll). Absent chart position stays null; an explicit empty or unknown position
does not select a role slot. Generated scripts update both live coordinates and
stored stage offsets, plus live/stored scroll factors. The pure model also
retains occurrence spacing, flip and presentation fields for the unfinished
instance renderer; conversion diagnoses unsupported presentation and dynamic
placement. Existing generated stage scripts are not overwritten automatically.
The stage placement classifier treats startup opacity writes as visual state,
while geometry writes and delayed geometry hooks remain explicit placement
metadata.
`CodenameActorPlan` can use selected-owner XML slots for extra actors when the
verified stage script has no actor geometry writes or confines those writes to
named primary actors; this also covers opacity-only scripts without borrowing
placement from a different stage.

The current character adapter still folds XML global x/y into native world
placement. Conversion now preserves XML `playerOffsets` and composes X as
`slotX + (slot.isPlayer == playerOffsets ? globalX : -globalX)`, with Y always
`slotY + globalY`. Upstream applies that translation through sprite offsets;
the representation still differs even when the rendered anchor agrees.
Consequently, neither adding global offsets again nor assuming the native
midpoint always equals the donor midpoint is correct for future camera hooks.
When the rendered translation `dx` is baked into world X, the camera residual
is `globalX - dx` (zero for matching donor role/playerOffsets, twice globalX
otherwise); the Y residual is zero. Camera role bias still uses the donor role.
Animation flipping, live property mutations and stage presentation need the
character adapter as well. One definition used by several primary roles now
supplies its XML offset metadata to each role instead of only the first one.
The camera sidecar now has an optional `stagePlacement` model containing every
named/role placeholder, spacing, flip, scroll, scale, alpha, angle, skew, zoom
factor and camera offsets. `CodenameStagePlacement.toData/fromData` transports
this model without flattening named slots to the three primary roles. Numeric
fields and structural completeness are validated; unknown runtime dependencies
remain diagnostics. Old sidecars retain a null model rather than inventing one
from role-only camera offsets. Slot names are data keys, not filesystem paths.
Character script packs, visible actor averaging, camera-position hooks and
initial movement-event seeding remain to be integrated.
Native note rows now retain the original Codename line/note indices in column
13 through head, sustain and generated lift construction. GF/extra-line notes
remain in selected-difficulty metadata until additional gameplay lanes exist.
`CompatSongNoteData.strumlineIndex` belongs to the HXC/V-Slice side adapter and
must not be treated as Codename provenance. PlayState binds the source line
index to `CodenameInputLine` and dispatches hits to that line's live actors;
the old primary-role path cannot choose among several characters on one line.
An old chart without column 13 now emits a provenance diagnostic instead of
silently presenting a static visible actor. Actor ownership survives stage
replacement independently of stage props; existing stage cleanup protects the
three native role actors. Ordered stage metadata and live slot anchors preserve
XML prop/primary-actor interleaving.

`tools/refresh_codename_notes.py plan --donor-root <original-root>
--runtime-root <bin> --output tmp/<plan>.json` prepares older selected-owner
charts for a reviewed note-only refresh. It proves owner/song identity, matches
the existing row multiset to the donor's old converter projection even when
equal-time rows were reordered or numeric milliseconds were truncated, and
rejects edited or ambiguous routing. The apply command revalidates the plan
under the runtime locks, backs up every target below
`tmp/import-refresh-backups/`, and appends source metadata while preserving
all other installed chart fields. A repeated plan is a no-op. The three HL17
Buck charts were refreshed this way; no donor file or personal setting was
edited. This repair restores the generic source-line route. Source behavior
still requires native replay evidence after the refresh.

Codename converted character atlases, generated scripts and registry rows now
live under the selected `CompatScriptManifest.destinationRoot`, using the shared
character materializer's explicit destination root. Discovery prefers a donor
XML definition even when its name is `bf`, `boyfriend`, `dad` or `gf`; built-in
aliases apply only when no donor definition exists. Existing files are preserved
by missing-only merges. Discovery now visits every ordered character list in
every converted difficulty, materializing each exact character identity once
while retaining repeated occurrences in the camera sidecar. Case-distinct XMLs
and scoped registry entries stay distinct; ambiguous casefold lookup remains
unresolved. Each generated chart keeps its own primary character choices. The
generated stage initialization uses the first chart referencing each exact stage.
A shared stage with differing actor placements across difficulties is diagnosed;
live indexed actors and that per-difficulty placement remain to be implemented.
Converted Codename stages, prop assets and registry
rows also use the selected destination root, including event-only stages.
Donor stage XML takes precedence over a native stage alias.
Each difficulty now resolves its own stage independently. Additional distinct
stages use the shared `convertedStages` materialization path; case-distinct
Codename registry keys remain separate. Missing or failed stage conversions
produce an owned registry declaration without a script or invented visuals,
so chart validation preserves the missing dependency instead of selecting a
sibling's stage. Native aliases remain available when no donor XML overrides
them. A collision between distinct authored identities that convert to the same
native character/stage name rejects the song candidate with a diagnostic before
materialization, avoiding ambiguous assets. Broader identity encoding remains
unfinished.

`ImportedStageRegistry.resolve` is shared by Song chart validation/normalization
and PlayState initial loads/swaps. It reads only the selected Modding Plus or
Codename owner's stage registry. Exact spelling wins; a unique case-insensitive
match is accepted. A declared owned stage with a missing/unsafe script, malformed
registry or ambiguous key returns an unavailable descriptor, preventing a
same-named global stage from taking over. Initial loads retain the authored
identity and report the missing dependency; unavailable swaps leave the active
stage untouched. Stage swaps compare the resolved registry identity exactly:
case-distinct owned keys can replace one another, while a unique case alias
resolving to the same key remains a no-op. An absent owned entry still permits existing native fallback.
Other engines retain their existing stage resolution. Existing imports require
a provenance-safe refresh to materialize newly scoped conversions; this does not
rewrite their prior generated files automatically.

`Song.characterRootForSong` accepts selected Psych/Codename owners for character
registry/visual resolution and chart normalization. `currentCharacterRoot`
requires the owning PlayState to be active. `currentPsychCharacterRoot` retains
its engine filter, so Codename XML metadata never enters the Psych camera parser.
Owned definitions retain their identities through chart validity checks and GF
fallback even when their media is incomplete; the character resolver reports
missing owned dependencies instead of selecting a foreign registry row.
HealthIcon uses that same owner; Freeplay supplies its row's song as the optional
fifth constructor argument so simultaneous rows do not borrow the current game
or another row's icon. Other callers retain the active-gameplay default.
If a selected owner's registered character has no custom `icons.png`, the HUD
checks that same owner's direct `images/icons/<id>/icon.png` strip before using
the neutral grid. A present custom strip retains precedence; no sibling owner
can supply the missing icon. Smoke runs log the selected direct path.
Older converted charts that already replaced authored IDs with native aliases
still require a provenance-checked refresh; adding an owner namespace alone does
not reconstruct those lost IDs.
Reference: [upstream cancellation implementation](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/scripting/events/CancellableEvent.hx)
and [ScriptPack event iteration](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/scripting/ScriptPack.hx).

`tools/refresh_codename_events.py plan --donor-root <original-root>
--runtime-root <bin> --output tmp/<plan>.json` prepares existing Codename event
metadata for a reviewed refresh. The ownership proof uses `CompatScriptManifest.destinationRoot` with
`ImportEngine.CODENAME` and the original import root, matching both selectedRoot
and its engine-tagged manifest entry; the manifest alone does not retain the
source donor path. `CodenameScriptPlan.song` identifies the exact original song
folder. The migration compares the entire destination event field against
a frozen pre-metadata converter projection, then replace only that field with
current conversion output. Exact old-output equality permits correcting the old
EPSILON timestamp grouping as well as adding metadata; the dry-run must expose
those timing/group changes. Preserve all other chart bytes, reject edited or
ambiguous event data/difficulty mappings, revalidate all inputs under runtime
locks and keep verified recoverable backups. Apply with
`tools/refresh_codename_events.py apply --plan tmp/<plan>.json --reviewed`.
The Haxe renderer reproduces original chart-then-shared insertion order before
legacy EPSILON grouping. Generated `Focus Camera` option JSON and preserved
Codename foreign-event payload JSON accept object-key serialization-order
differences; the latter must have only the importer's `engine`, `name`, and
optional `params` fields, with the Codename engine and matching row name.
Keys, types, values and array order must still agree, and duplicate keys are
rejected. Missing selected namespaces or source-song plans are explicit skips.
An already current metadata array is a clean no-op before the legacy-output
comparison, so a repeated plan reports no candidates and no skips. Apply holds
both runtime locks,
regenerates the reviewed plan, saves verified copies below
`tmp/import-refresh-backups/`, and rolls back earlier replacements if a later
replacement fails. A dry-run is evidence of eligibility, not of native gameplay
parity after refresh.

Psych gameplay character resolution now consults the active song's selected
Psych manifest root before the legacy global registry. The importer materializes
converted character implementations, atlases, icons and registry metadata under
that root as well as retaining legacy global materialization. Existing complete
files and registry rows are preserved. A scoped row with incomplete media stays
an explicit failure instead of resolving to a case-colliding global character;
characters absent from the scoped registry retain native fallback. Health icons
follow the same owner and support both donor icon filename conventions. This
boundary fixes ownership; it does not establish JSON position/camera-position or
all character-role semantics.

The Psych `version` global uses the full `0.7.0` API-baseline representation.
This preserves the previous 0.7 generation while supporting both lexical version
comparisons and legacy scripts that remove dots before numeric comparisons. It
is a compatibility target, not a claim of complete upstream feature parity.

Psych's deprecated `characterPlayAnim` routes `dad`, `gf`/`girlfriend`, and the
legacy default to the native role actors, checks the requested animation, and
forwards the force flag. This follows the local upstream DeprecatedFunctions
implementation and remains separate from tagged sprite animation playback.
Standard Psych character generation now chooses danceLeft/danceRight pairs or
idle from the actor's live idleSuffix, with the initial paired dance on Right.
`PsychCharacterDanceCompat` also reproduces the previous generator bytes solely
for provenance checks. `tools/refresh_psych_character_dance.py` plans namespace
refreshes and rerenders both versions at apply time; only exact old generated
scripts can be replaced. Customized scripts are preserved. Apply holds both
runtime locks and saves verified backups under `tmp/import-refresh-backups/`.
When Psych character JSON names multiple atlas files, import stages each
Sparrow image/XML pair within that character's selected owner and generates a
`FlxAtlasFrames.combineSparrow` call. The HScript binding is a static atlas
facade, so constructing `FlxAtlasFrames` directly is invalid. The private
2Hot replay attached the 421-frame `pico-playable` atlas after this correction;
that check does not establish the surrounding stage's visual parity.

`PsychSourceStageCompat` reads the donor's compiled `PlayState` stage dispatch
and corresponding stage class file during dependency scans. If a chart selects
a compiled class whose behavior has no executable imported implementation,
the scan and runtime retain an explicit unsupported-stage diagnostic even when
JSON placement metadata or neutral native scenery can be loaded. Stage JSON
still supplies zoom and character start positions; it cannot substitute for
that compiled rendering and event code.

Chart visual normalization must select Psych-owned registry spelling before
falling back to the global registry. Otherwise a case collision can load the
right scoped atlas while losing the exact-case character metadata lookup. The
Psych importer preserves source JSON non-overwriting under the owner's original
`characters/` or `shared/characters/` layout, even when optional atlas conversion
is unavailable. `PsychCharacterPosition` consumes those scoped position values,
including explicit zero offsets. Character.cameraPosition retains the raw
Psych camera_position array for script property reads and writes. Camera target
composition subtracts BF's character X offset and adds opponent/GF X and all Y
offsets, then adds the stage camera_boyfriend/opponent/girlfriend contribution.
Stage contributions are replaced on load and cleared on stage teardown; they
are never accumulated into native followCam fields. Character swaps therefore
read the new actor's live metadata without retaining the previous actor offset.
Psych mode requires a nonempty selected Psych manifest root. Its role baselines
are BF `[-100,-100]`, opponent `[150,-100]`, and GF `[0,0]` relative to midpoint.
Native character init values are recorded after initialization so only later
script changes to followCam become additional deltas. Other engines retain their
native/authored camera composition; event focus excludes turn nudges as before.

#### Codename upstream lifecycle/rendering audit (23 September 2026)

The importer now preserves immediate song `.hx` files, matching difficulty
subdirectories and the selected stage sidecar in the donor namespace. The same
plan resolves literal image/atlas/audio/shader dependencies and checks for
missing files during repair. Copies are non-overwriting; canonical path checks
exclude symlinks escaping the selected source. Raw Codename data is not merged
into native asset registries. This preservation alone does not execute scripts. The later runtime foundation
below adds a dedicated loader; broader Codename API bindings remain open.

A parse-only audit of 120 mounted donor Haxe files found 47 accepted by the
pinned ParserEx with allowTypes and allowJSON. Removing declaration lines for
the probe raises that to 84, including all 17 sampled song scripts and 9 of 13
stage sidecars. This is diagnostic preprocessing, not an implemented loader:
imports still need explicit runtime bindings and scope validation. Quoted
tween-property keys require allowJSON. Remaining stage syntax includes null-safe
access and top-level public variables; class declarations need a separate module
path. Neither parse success nor blindly deleting imports establishes execution
compatibility. Evidence: `tmp/codename-parser-audit-summary.json`.

The upstream PlayState loads immediate scripts from a song's scripts directory,
its selected difficulty directory, legacy `data/charts/`, and top-level `songs/`,
then chart-selected event and note scripts. Stage-side scripts are stage-owned.
Its postCreate dispatch happens after state construction, not immediately after
each individual script is parsed. A native adapter must therefore load scopes
first and dispatch the creation phases in order, rather than merely adding
Codename callback names to the global Psych alias list. Source:
https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/PlayState.hx

Codename FunkinSprite applies zoomFactor and angleFactor to its draw matrix using
the camera scale and viewport center. A plain FlxSprite alias would silently
ignore authored rendering behavior (including zero zoomFactor HUD content).
This checkout's Flixel 6.1.2 has drawComplex rather than Codename's newer
prepareDrawMatrix override boundary; a bridge needs a matching rendering
adapter and a native camera-zoom check. The local commented FunkinSprite.hx is
unrelated legacy scaffolding and must not be mistaken for that implementation.
The pinned Flixel drawComplex delegates to drawFrameComplex: frame flip/origin,
sprite scale/rotation, screen position and pixel rounding precede drawPixels.
The compatibility transform belongs between that matrix construction and
drawPixels. A custom adapter must also handle the simple-render shortcut and
visibility bounds: ordinary isOnScreen runs before drawing, so changing only
the draw matrix can incorrectly cull a zoom-independent sprite. Verify camera
scale, rotation, viewport center, clipping and multiple-camera ownership in a
native render test before exposing a FunkinSprite alias to donor scripts.
Source: https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/FunkinSprite.hx

#### Codename runtime foundation under integration

`CodenamePaths` belongs to one selected import namespace. It resolves image,
atlas, audio, data and shader paths within that root, rejecting traversal and
symlinks that escape it. Missing assets do not fall back to global content.
Sparrow/Packer metadata selects the frame loader; a plain image is the remaining
supported case. Animate directories currently produce an explicit unsupported
format diagnostic. This boundary does not imply all Codename asset formats work.

`CodenameScriptInterp` injects that resolver into each constructed FunkinSprite.
Timers created through its constructor and tweens created through its facade
belong to the interpreter; `release()` cancels those resources independently of
other scopes. The lifecycle loader must call release on failed initialization,
stage teardown and state destruction. Focused interpreter tests establish scope
isolation and cleanup using rendering-boundary stubs; native rendering and full
scene lifecycle still require release-build verification.

Codename interpreters suspend their owned timers/tweens after a gameplay pause
substate opens and restore the recorded active states after it closes. Flixel's
global timer/tween plugins otherwise continue updating while the state is
paused. Repeated suspend calls are idempotent; cancelled or finished resources
are not revived on resume. Scope release discards all pause snapshots.

A failing callback is disabled for that hook in that scope after its first
reported exception, avoiding repeated per-frame error output while retaining
unrelated hooks. This is fault containment, not a substitute for implementing
missing APIs. Difficulty selection uses the requested difficulty directly,
first matching exact authored case and then one unambiguous case-insensitive
name; it never selects a different difficulty through native defaults chaining.

The Codename dependency plan opts into literal `Paths.font/xml/json/txt` calls
in addition to image/atlas/audio/shader references. Font names retain their
authored extension; data names use the matching extension under `data/`.
The original HXC planner call contract remains unchanged unless this option is
enabled. Copy and repair consume the same scoped plan and preserve customized
destination files. Runtime-only path expressions remain an explicit gap.

#### Codename camera and borrowed scene ownership

Each Codename interpreter now receives its own `CodenameFlxGFacade` in both the
bare global and explicit import binding. `CodenameScriptInterp.cnew` registers
new FlxCamera instances immediately, including cameras created before a failing
initializer reaches `FlxG.cameras.add`. Scope release destroys owned cameras and
restores only its recorded host-camera changes. Host camera destruction is
prevented. Same-owner scripts can reorder host cameras in sequence; the
journal unwinds their changes even when an earlier stage scope is released
before a later song scope. Foreign-camera removal and cross-owner host-camera
reorders still report explicit unsupported operations.

`CodenameCameraFacade.list` and `.defaults` are snapshots, so scripts can
query ordering and default draw targets without bypassing ownership by
mutating the native lists. Main-camera restoration captures
selection before removing owned cameras, allowing native cameraRemoved listeners
to change selection during cleanup without losing the prior registered camera.
A later unrelated main-camera selection is preserved.

`CodenameSceneMembership` is a separate tested coordinator for borrowed scene
nodes. It records membership and neighboring nodes, then restores only actions
owned by a released scope. Releasing an earlier scope preserves a later scope's
placement. It never destroys borrowed nodes. Codename HUD add/remove/insert
bindings use this shared coordinator, while new script objects retain separate
creation ownership even after remove. HUD globals and the live members array
refresh before callbacks, including stage postCreate after native HUD creation.
Only the latest action per owner/node is retained, bounding repeated reorders.
Native verification exercised a deliberately failing stage callback: the health
bar returned to its original membership and the added camera was released.

### Empty chart note alignment

`PlayState.generateSong` calls `initialNoteAlignmentWidth` after sorting notes.
A populated chart retains its original first-note width for legacy setup; hold
trail placement does not use that global width. An empty/event-only
chart uses a valid loaded player receptor width, then opponent receptor width,
then the engine lane width if no receptor is available. It does not create a
placeholder note or alter event/song timing. This prevents the native null
first-note dereference during an otherwise valid empty chart's initialization.

For every hold, `Note` retains a reference to its own head and the head's last
drawn-frame center. Native snapping and Codename's moving receptor alignment
both place each sustain piece by the difference between that head center and
the piece's current drawn-frame center. The head caches its center while alive
so later pieces remain aligned after it is judged. The same source-bound hit
path also schedules the shared receptor confirm-to-static timer; a cancelled
Codename strum-glow event leaves the receptor untouched.

Generated Codename chart notes record their x after native lane construction.
When a source line binds, only movement since that baseline becomes the
note-to-receptor offset. This keeps authored script placement while excluding
the fork's old constructor padding. Script-created notes lack that baseline
and retain their explicit source x offset.

### Codename source note identity and editor row preservation

`CodenameNoteMetadata` owns optional native row column 13. Columns 0–12 keep
their legacy meanings and are null-padded when omitted. The versioned tag
records the original ordered `lineIndex`, pre-filter `noteIndex`, nullable source
`lineType`, and absolute native side. The reader validates the schema and the
row's side using its section's authored `mustHitSection`, before gameplay input
modifiers. Invalid, stale, non-four-key or absent tags resolve to null; old
imports never infer a source line from a native role.

`Note.codenameOrigin` is initialized in the constructor before visual setup.
PlayState reads a separate metadata object for each head, sustain segment and
generated osu-style lift. This supplies identity for future actor/camera
routing; it does not yet instantiate additional Codename actors or receptors.

Notes on unsupported GF/extra lines retain their original JSON records in
`song.codenameUnsupportedNotes`, including source line/note ordinals. The Song
difficulty resolver takes this field exclusively from the selected chart and
clears sibling records when absent. These records are retained data, not
currently playable notes. Existing imported charts are not rewritten.

`ChartNoteRowCopy.withTimestamp` deep-copies the entire JSON-safe chart row
for editor section copies, replacing only its timestamp. This preserves legacy
alt/lift/health/timing settings, event values and nested compatibility metadata
without shared mutable objects. Other editor field edits retain the row;
cross-side changes invalidate source identity on the next metadata read.

Both Codename and V-Slice section sort callbacks explicitly accept
`Array<Dynamic>` rows. On hxcpp, leaving callback parameters inferred from
`a[0] < b[0]` generated `Array<Int>` arguments and coerced mixed rows in place,
losing fractional timestamps, null optional fields and object metadata. This
requires native compiler/runtime coverage; interpreter-only tests missed it.

The next indexed-actor integration must also preserve XML display-list order.
The pinned donor inserts invisible character anchors among props in XML order,
keeps the last duplicate-key anchor for placement, and appends absent default
anchors in GF/dad/BF order. Each actor occurrence is inserted before its selected
anchor; repeated IDs still create distinct actors. Selected slot `flip` controls
constructor player orientation, with line type used only when no slot exists.
Stage placement metadata now retains optional ordered prop/anchor records;
older sidecars without them decode with an explicit unknown order. Live XML
anchors and primary actor binding are described below. Additional indexed
actors and their camera/note routing remain pending.

### Codename XML anchors and stage ownership

New generated Codename stages create props and invisible character anchors in
XML element order through `StageHelper.addCodenameProp` and
`addCodenameAnchor`. The XML element ordinal identifies each prop independently
of names, which may repeat. Every duplicate slot keeps its own anchor, while
placement selects the last anchor for that key. Missing GF/dad/BF anchors append
in donor order. An explicitly empty named slot is valid; a missing name is not.

`placeCodenameActor` inserts a PlayState-owned actor immediately before its
selected anchor, or appends it when no slot exists. Multiple occurrences bound
to one anchor retain insertion order. Actors are kept in a separate binding
list and never added to the stage's ownership collection. Native character
replacement rebinds these references before character-added callbacks, allowing
subsequent script changes to remain authoritative. This currently connects the
native primary actors; it does not instantiate all authored strumline actors.

`codenameOrderNodes` is an ownership ledger for props and anchors even after a
reversible removal. Runtime stage teardown snapshots that ledger along with
mounted stage objects, then destroys each collected object once. Direct
`clearStage(true)` also releases detached order nodes without destroying the
actor bindings. Stage replacement creates fresh anchors while keeping actors
alive. This ledger does not change ownership of unrelated legacy script objects.

`CodenameStagePlacement` serializes an optional ordered list containing kind,
ordinal and key. Decoding checks ordered unique ordinals and anchor references;
old metadata stays readable without fabricating XML order. Conditional nodes,
extensions, unsupported prop forms and stage-script effects retain diagnostics
rather than being declared fully reproduced by the static representation.
The importer scans direct actor-pose writes in a stage companion. Writes in
`songEvents` and `stepHit` are recorded as `runtimeMutationHooks` and leave
the XML startup slots usable; writes in `postCreate`, other hooks, or top-level
code continue to mark the initial placement unsupported. This lexical split
does not prove that delayed mutations render correctly, and ambiguous aliases
remain conservative startup findings.

`CodenameActorPlan` preserves `(lineIndex, occurrenceIndex)` rather than
deduplicating character IDs. New camera sidecars retain `nativeCharacters`, an
exact authored-ID to native-registry mapping, and `nativeStage`. An explicit
null mapping marks an unresolved character while retaining other known entries;
an absent map in an older sidecar means the mapping is unknown. The runtime
validates the selected owner, song, difficulty, authored stage and native stage
before caching an initial construction plan. Primary actors match only the
converter's first nonempty role occurrence and its exact native name; edited
charts cannot borrow a later occurrence's settings.

Initial native actor construction uses the selected slot's `isPlayer` when the
placement dependencies are resolved. This happens before `Character.new`
changes sprite and animation orientation. Missing/old metadata or unresolved
placement keeps the existing construction path and records a diagnostic.
This plan contains construction records, not extra live character instances.

For an active selected Codename owner, the character registry's
`codenameCharacter` data supplies XML `playerOffsets` and `flipX`.
`CodenameCharacterOrientation` runs after animation registration and before the
first dance: it swaps sing-left/right and miss frame arrays plus their named
offset entries exactly when slot `isPlayer != playerOffsets`, then toggles
the definition's flip when slot `isPlayer` is true. It does not swap hold
animations or exempt dance-pair characters. Characters without this selected
Codename metadata continue through the existing native constructor branch.
This does not yet implement Codename's complete draw-time offset transform or
per-instance character script lifecycle.

`tools/refresh_codename_actor_metadata.py` upgrades existing camera sidecars
from a fresh isolated import preview in repository-local `tmp`. It compares
the exact selected namespace and source-song/stage plan, validates both camera
files through `CodenameScriptPlan`, and requires every existing metadata value
to agree before adding `nativeCharacters`, `nativeStage`, or `stagePlacement`.
Older placement models can also gain an order list without replacing their
existing slots. The preview owner's converted character/stage bundles must also
exist byte-for-byte in the installed owner; metadata cannot assert an owned
implementation that is still absent or custom-edited. This bounded check never
walks the global media library. Changed values, extra custom fields, missing
namespaces and changed difficulty sets are left untouched and reported. This tool does not
repair missing import assets, rewrite charts, or refresh generated stage scripts.

The normal importer separately revisits missing converted visuals and scoped
runtime dependencies for complete, same-owner Codename and V-Slice songs.
Chart/audio completeness does not imply that every owned stage or character
bundle is present. This path retains the skipped-song count and bypasses
`importSong`; existing chart and manifest bytes stay untouched. The shared
missing-only merge helpers preserve existing generated or edited files, and
the ownership check runs before any repair. Registry caches are invalidated
at the normal main-thread completion handoff. This repairs absent files; it
does not upgrade stale generated implementations or metadata.

`tools/repair_codename_owned_bundles.py` provides a reviewed repair for older
installed namespaces from a fresh isolated native importer preview. It derives
the namespace with `CompatScriptManifest`, matches the selected installed songs,
and inventories only that owner's generated tree with explicit size limits.
Plans hash charts, manifests, preview files and existing matching owner files.
Apply takes both runtime locks, regenerates the exact plan, stages local files
and uses atomic no-clobber links to add missing files. Existing files are never
replaced. Conflicting character/stage implementations or incomplete registries
prevent repair; existing song scripts and old camera metadata remain unchanged
and are reported. Receipts under `tmp/import-refresh-backups` record additions
and rollback; rollback preserves files replaced or edited after this tool added
them. Actor metadata upgrades remain a separate validated step after assets
are present. File repair does not implement unsupported donor script APIs.

The plan freezes tool and input hashes. Apply reacquires both runtime locks and
regenerates the exact plan before writing, saves verified originals under
`tmp/import-refresh-backups`, and rolls back earlier replacements if a later
write fails. The generated preview is an input produced by the current engine,
not a donor tree; donors remain read-only. Chart identity mismatches still take
the explicit initial-actor fallback, so a metadata upgrade alone does not
constitute a complete migration of older imports.

Further stage replacement work must select
the replacement stage's placement data, preserve actor instances, and rebind
them to fresh anchors. The initial difficulty's placement is insufficient for
an arbitrary stage swap. Indexed actor scripting, camera averaging and note
dispatch are still pending; the existing note-origin metadata and ordered
anchors are their foundations, not proof of complete Codename compatibility.

## Codename song metadata views (24 September)

`CodenameSongMetadata` preserves the parsed base metadata in the owned
`__cammie_compat_song_meta.json` sidecar. An additive
`__cammie_compat_song_meta_resolved.json` sibling records exact chart difficulty
names, selected metadata file, file data, inline chart metadata and resolved
values. Discovery selects `meta-<difficulty>.json` before `meta.json`; source
defaults are applied before non-null inline fields. Effective BPM and voices
are used during chart conversion. Declared variants and flags.ini overrides
are diagnosed as unsupported, rather than silently claimed as compatible.

`PlayState.getCodenameSongView` validates the selected owner's source folder
and selects the difficulty record. Runtime loading rebuilds the derived
`resolved` fields from retained source metadata, so a stale generated cache
cannot discard an otherwise valid owner's song view. The importer still rejects
an inconsistent cache when generating its sidecar. Invalid owner, difficulty,
or source-file records do not fall back to base metadata. Older raw-only owners use normalized base metadata with a
reimport diagnostic. `CodenameSongView` forwards ordinary chart reads/writes
to the live native SONG while storing script metadata separately per PlayState;
`CodenameScriptInterp` implements this property access. Global SONG and imported
PlayState.SONG share the view. Metadata mutations remain local to that play
session and do not add metadata to the native chart or another import owner.

Both sidecars are missing-only import outputs. Existing generated/custom files
are preserved; older installations require a reviewed shared repair plan.
Focused interpreter tests cover owner isolation, cache lifetime, malformed
records, difficulty ambiguity and live native chart writes. Native verification
and full-suite status are tracked in the discrepancy report.

## Codename live occurrence ownership (24 September)

`CodenameActorRuntime<T>` retains one binding per source line and character
occurrence. Equal character IDs do not collapse to one sprite. Exact primary
records borrow existing native actors; additional records construct owned
instances. Unresolved records retain null array positions. Cleanup destroys
only owned instances, once; native role swaps rebind borrowed references.

New generated stages publish a validated placement model through
`StageHelper.setCodenamePlacement` before constructing props and anchors.
PlayState captures constructor presentation baselines, creates additional
characters after the native stage start, and places all occurrences in source
order. Stage swaps reuse instances and compose presentation from those
baselines and the replacement stage model, preventing repeated scale/alpha
accumulation. Stage teardown treats these actors as borrowed objects.
Older scripts without a published model preserve the legacy native path;
unsupported placement dependencies and inconsistent primary chart identities
are diagnosed rather than creating extra characters at guessed positions.

The script helper `getCodenameLineCharacters(lineIndex)` exposes an ordered copy
with unresolved null slots. This does not implement the donor's full strumLines
API. Additional playable lanes, source note/camera/event routing, original
Codename per-character script ABI and per-character zoomFactor remain open.
Full draw-offset compatibility also remains separate from the existing baked
global-offset representation. Focused and native verification results belong
in the discrepancy report.

## Same-process native reload probe (24 September)

`--smoke-playstate-visits 2` opts into two PlayState creations through
RuntimeSmokeState in one process. The default remains one visit. Each visit
gets its own ready-to-deadline gameplay window; a wall-clock watchdog also
covers queued transitions. PlayState.update returns after a requested switch.
Before the second start, the harness requires validated owned-actor cleanup
counts and a destroyed marker emitted after the first state's super.destroy.

Codename snapshots contain source occurrence indices, primitive presentation
values, ownership and instance tokens. Tokens are assigned lazily to a private
Character field by the probe, with a monotonic process allocator: an accidentally
reused character keeps its token, without retaining old sprites in a global
map. The process runner captures the actual PID; markers share a run token and
visit number. This does not write options or save data. Malformed visit counts,
missing cleanup evidence, duplicate teardown and stalled transitions fail the
probe. Native results are recorded in the discrepancy report.

The optional `--smoke-next-song`, `--smoke-next-chart` and
`--smoke-next-difficulty` values select a different chart only after the first
PlayState is destroyed. They require two visits; otherwise configuration fails.
The Python runner's `--next-case` supplies these values and copies metadata
files for both selected owner namespaces into the private runtime overlay.
Cross-song results require start/ready markers for each visit and the first
destroyed marker. This tests state cleanup and owner selection in one process;
it does not establish a full-song playthrough.

### Codename character interpreter parent binding (in progress)

`CodenameScriptInterp.bindScriptObject` provides an optional per-instance parent.
Lexical locals and explicit script globals (including null globals) take
precedence; remaining known parent properties/methods resolve against the live
actor. Bare assignments, compound assignments and increments write back to that
actor, including property accessors. Unknown identifiers retain normal HScript
errors. Rebinding replaces the parent field map; release drops the parent.
Unparented song/stage interpreters retain their previous lookup behaviour.

The real-interpreter test covers separate actors, method calls, accessors,
closure mutations, shadowing, replacement and release. This binding now underpins the character constructor/runtime described below.
It does not establish complete character, strumline or rendering compatibility. Parent precedence follows Codename's `HScript.setParent` and
hscript-improved's script-object lookup. Codename v1.0.1 references a moving
`codename-dev` dependency; the inspected dependency revision is
`ca71db271f81f46c359592384de6a898d3dcb3cd`, retained with provenance under
`tmp/codename-upstream-v1.0.1/hscript-improved/`.

Character source preservation is owner-scoped: discovery resolves each selected
chart character ID component by component, preferring exact case and rejecting
ambiguous fallback or escaped paths. Original XML and `.hx` files remain under
`data/characters`, including nested IDs. The runtime-file planner preserves
static XML sprite atlas paths and literal Haxe asset references without scanning
whole media trees. Missing-only repair preserves existing source and generated
files. Absent optional scripts are normal; missing XML, invalid identities and
ambiguous/escaped references produce diagnostics. Dynamic script dependencies
and XML extensions still require runtime-compatible discovery and execution.
The generated visual converter now receives the authored ID explicitly for XML
without a `sprite` attribute, rather than using its renamed native registry key.

### Codename character construction and owned scripts

`CodenameCharacterConstruction` carries a validated selected owner, exact authored
ID, native registry identity and source XML into `Character.new`. Initial primary
actors and extra occurrences receive separate contexts; exact mapped primary
replacements use the same path. Older imports without preserved source XML keep
the generated native visual constructor. Arbitrary dynamic character selection
outside the authored plan remains incomplete.

The character exposes XML before executing its companion body/`create`, dispatches
mutable `onCharacterXMLParsed`, applies the resulting root and each animation
node, then dispatches `onCharacterNodeParsed` after that node. Orientation and
opening dance precede `postCreate`; stage baselines capture the resulting live
scale, offsets and camera offsets. Generated `init` is skipped for a successful
source XML build, avoiding duplicate atlas/animation registration.

`CodenameXmlAccess` makes the erased `haxe.xml.Access` API available to HScript,
including attribute/node proxies. `CodenameCharacterVisual` resolves the final
sprite through the selected owner. XML extensions are explicitly diagnosed;
static import-time definitions never override callback-mutated XML.

Each actor owns a `CodenameCharacterRuntime`, its interpreter, callback failures,
timers/tweens and scene objects. Character scopes remain separate from stage/song
scopes; stage swaps refresh aliases without destroying them. Actor update,
beat/step, dance and animation events, draw/postDraw, gamePostCreate and song-start
callbacks are wired. The character camera-position method exposes its mutable
point event; indexed camera following uses the same live actor slots as input.
Live source actors retain stage world x/y separately from XML global draw
offsets. Stage camera offsets compose from the captured character cameraOffset
baseline on each placement; repeated stage swaps do not accumulate them. Native
primary camera following calls the actor's source camera method (including its
mutable point event) and does not add classic direction nudges. Older imported
actors without source XML retain their generated placement fallback.
Default Codename camera following selects line 0, then averages the visible
characters on the script-mutable curCameraTarget line. Empty, invisible-only,
negative and invalid selections retain the last target instead of falling back
to native chart-section following. Scene scripts receive mutable/cancellable
onCameraMove with position and focusedCharacters. Its strumLine is the same
stable input model returned by getCodenameInputLine: script changes to characters,
cpu and controls persist across input and camera calls. Metadata actor arrays
are only a fallback when no live input model exists. The model still lacks full
donor notes/receptor groups and signals.
`onCameraMove.position` is a script-visible mutable point because Flixel's
inlined `FlxPoint.addPoint` is unavailable through HScript reflection.
Codename-authored notes expose their bound input line as `note.strumLine`.
Explicit native camera modes and authored
Camera Position retain precedence. Structured Camera Movement selects authored
indices directly, including extra/empty lines, with source snap/CLASSIC/tween
semantics. Scroll interpolation suspends camera following but does not suspend
live camFollow updates or onCameraMove callbacks. Absolute Camera Position keeps
its separate fixed target until a movement event selects a line again.
Cancellation prevents default dance/animation actions. Character parent aliases
and references from any Codename script scope preserve authored `curCharacter`,
`tryDance` and the donor five-argument `playAnim` API. The interpreter identifies
these references through `CodenameCharacterAccess` plus an authored source ID;
song/stage calls and references to another actor therefore use the same bridge.
Unrelated objects, native characters without a source ID and native engine calls
retain their existing signatures. The donor animation call preserves
nullable `force` through `onPlayAnim`; only afterward does an omitted/reset force
resolve from the final animation name's metadata. Explicit false/true remain
explicit, including when a callback renames the animation. A consumed request
slot isolates nested calls and is restored when dispatch exits.
The script-facing NONE context is represented by null. Accepted generic sprite
animation calls always replace lastAnimContext, including omitted/explicit NONE;
they must not retain a previous LOCK context. Rejected missing/null animation
requests retain the prior context.
Character XML `type="loop"` plays immediately after registering that node's
animation/offset, before storing its raw nullable force descriptor and before
onCharacterNodeParsed. Type matching trims whitespace and ignores case;
the separate loop attribute controls frame repetition. Initial force defaults
to false for idle/danceLeft/danceRight prefixes and true otherwise, while an
explicit forced attribute wins. This initial default is not written back into
the raw descriptor. Duplicate-name force lookup uses the latest descriptor
already stored, so the current node becomes visible only after its play returns.
A private construction flag and descriptor array enable source play callbacks
from create/XML hooks through node parsing; the completed public definition is
published only when building succeeds. Both success and failure clear private
construction state, and failure releases the character script runtime.
Missing animation requests outside debug mode, and null requests in all modes,
retain the current animation and context after the mutable callback. The donor's
post-call SING/MISS timestamp update is kept
separate from a successful animation switch. Finished animations enter an
available authored `-loop` successor before the script update callback, using
nullable force and preserving the current animation context; debug mode skips
that automatic transition.
Legacy countdown timer dances exclude live Codename actors: their source beat
and update callbacks own dancing, including cancellation. Native/legacy actors
in the same scene retain their countdown behavior.
Pause affects character resources;
actor replacement and PlayState teardown release each scope once, including
recursive destroy callbacks.

Remaining gaps include XML extension packs, dynamically computed dependencies,
complete note/strumline/camera routing, time-signature-dependent dance cadence,
full Animate/3D
transform support and unsupported
script imports/classes. The source constructor bridge is not a claim that every
Codename character script or 3D scene is supported.

Live character rendering keeps global Flixel offset separate from animation
frameOffset. The latter is subtracted before scale/rotation/skew through the
inherited FlxAnimate matrix preparation, shared by drawing and bounds; raw
getScreenPosition remains unchanged. Temporary extraOffset and flip reversal
wrap drawing and restore state even when drawing/bounds throw. The base flip
is captured at character orientation, before postCreate. Debug/ghost modes
follow their source transform rules.

Legacy player-facing character orientation discovers every matched
`singLEFT<suffix>`/`singRIGHT<suffix>` pair, then exchanges its frame lists
together with their named `animOffsets` entries. An alt-only pair works even
when the character has no unsuffixed `singRIGHT` animation.
V-Slice characters keep their authored directional names and offsets because
their donor plays those names directly; the player slot still flips the
sprite. Psych and Codename use their own source orientation paths. A missing
animation pair leaves both frames and offsets untouched.
Codename instead enumerates every authored `singRIGHT` animation name in XML
order and swaps its matching left/right frame lists and offset entries when
the player slot and `playerOffsets` convention differ. This includes arbitrary
suffix poses such as alt, dodge, and loop rather than only the base and miss
names; its sprite facing flip is independent of the direction swap.

The donor's v1.0.1 libs.xml references unpinned cne-flixel/cne-flixel-addons git
dependencies. Both current inspected sources and historical revisions preceding
the release tag use negative pre-transform frameOffset. Reference snapshots and
commit provenance are under `tmp/codename-upstream-v1.0.1/cne-flixel*-at-release/`.
The generic CodenameFunkinSprite adapter also subtracts frameOffset before
scale and rotation. Its nullable frameOffsetAngle applies the donor's rotation
sandwich around that translation. Culling corrects the native bounds for signed
frame spans under negative scale, translates by the same transformed offset,
then applies viewport-relative camera transforms;
pixel-perfect rendering allows conservative rounding margins. Extracted draw
matrix tests compare rendered corners with culling bounds across these factors.

The pinned Character override does not call the base FunkinSprite beat handler:
generic beat-animation cycling must not be added to character dance dispatch.
XML `type="loop"` requests immediate playback during node application; it does
not imply `loop="true"`. Full Animate/3D rendering remains incomplete.

### Codename input ownership

`CodenameInputLine` retains a stable authored line index, mutable source `ID`,
`cpu`, `controls` and actor slots. Initial CPU/control-bank selection follows the
source constructor, including nullable line types, opponent mode and co-op.
Local botplay is a separate gate and does not rewrite the source CPU flag.
`CodenameActorPlan.lines` preserves empty lines as well as actor occurrences.
`Note.codenameInputLine` carries runtime ownership independently of the native
player/opponent projection; autoplay consults it before native side defaults.

`CodenameInputEvent` carries mutable held/pressed/released arrays and the stable
line view. Event cancellation and scene/character propagation use the existing
source event dispatcher. The character input lock is granted explicitly by held
input for attached actors outside DANCE context; playing an animation alone
never grants it. The existing character update releases this one-frame lease.

PlayState initializes models after actor materialization and binds both queued
and live notes from validated origin metadata. `getCodenameInputLine(index)`
exposes the stable model to source scripts. Press, lift and held-note candidate
selection is isolated by that model; the <=2 ms duplicate tolerance only applies
within one source line. Extra empty pressed lanes do not suppress valid hits.
Source misses and singing target the current actor array, with scoring/callbacks
remaining once per note. Native untagged notes retain their original path.
Primary replacement changes matching actor references without recreating arrays
or discarding script-added slots. Teardown releases actor/control references.

Input callbacks receive four supported lane entries; mutation/cancellation
controls judgement, while the shared native receptor bank uses raw key state.
Only the first controlled source line per native side performs that bank's visual
input update, to avoid later empty lines resetting it. This does not provide
independent source receptors or covers. Camera callbacks share these input
models and respect script-edited actor arrays.

This is partial strumline support. The model is not the donor's full StrumLine
class: independent receptor groups, note signals, unprojected GF/extra-line
notes and arbitrary key counts still require further shared runtime work.

### Native scanner recycler diagnostics

`tools/diagnose_example_auto_import.py --recycle-diagnostics` builds against a
private, source-hash-guarded hxcpp copy under repository tmp. Its cache key
includes the diagnostic version; it must not reuse a normal or ASan executable.
The probe checks live-list removal, both recycler insertions, reuse removal
and live-list re-entry, and exact duplicate pointers before GC frees the vector.
A fixed 256-entry transition ring records pointer values, thread IDs, indexes,
vector storage and logical sizes under the existing allocator lock or stopped
collector. It reports truncation explicitly. Prefix fingerprints detect many
unexpected vector changes but matching fingerprints do not prove equality.
Equal-size candidate changes before acquiring the lock are recorded, not treated
alone as corruption. Version 4 also validates both allocation and object
row-mark spans before either writer touches the block's row table. Invalid
spans emit `HXCPP_ROW_MARK_VIOLATION` and a native backtrace, then stop before
the write. This private diagnostic retains ordinary GC configuration; enabling
GC-debug would also change marking and worker behavior. These checks establish
invariant failures, not the origin of a damaged header. The normal
`run.sh` setup now applies `tools/patch_hxcpp_large_free.py` to the exact pinned
hxcpp 4.3.2 `Immix.cpp` source before native compilation. `FreeLarge` takes the
existing large-list lock and checks successful removal from the live allocation
list before touching the allocation marker/header, decrementing accounting, or
returning the pointer to the recycler. Failed ownership returns untouched; the
upstream no-capacity path still only clears the marker. The patch refuses
unknown source hashes and is idempotent. This guards the observed unchecked
recycle route, but a passing scanner alone cannot prove the absence of other
native allocator defects.

### Legacy generated Psych character dimensions

Standard Psych character conversion updates the hitbox after non-unit scale.
At runtime, older generated implementations can be repaired before their first
dance if the selected imported owner supplies matching character JSON, the
implementation path is a standard global/owned character path, and its complete
contents match the legacy standard converter. Edited character scripts are
excluded. This restores scaled midpoint/camera semantics without changing
authored positions or animation offsets. See `PsychCharacterDanceCompat` and
`Character` for the ownership and exact-provenance checks.

### Psych countdown script state

The compatibility seed supplies `allowCountdown=true` and `seenCutscene` from
the engine history before loading scripts. Countdown dispatch preserves any
script-local gate across callback re-entry and honors Function_Stop. Donor
Story/Freeplay conditions see a shared policy: with Always Do Cutscenes enabled,
translated Lua scopes receive story context even in Freeplay, covering initial
script declarations, intros, delayed callbacks and ending gates. Native
PlayState mode remains Freeplay, so this does not enter the story playlist or
change native completion/menu flow. With the option disabled, scripts receive
the actual mode. The default and current personal settings enable this option.

### Psych sound and dialogue handoff

Psych `playSound`/precache resolve first in the chart's selected import owner
(`sounds/`, then the inherited music and global paths). Import merges donor
root/shared sounds into that owner without overwriting existing files. The Lua
bridge exposes camera flash/fade and starts the prepared native dialogue at
`startDialogue`; its completion calls the native countdown, which clears
`inCutscene` and restores gameplay input. This path is shared across Psych
songs and selected owners. Missing-only refreshes use a receipt under repo
`tmp/` to keep installed content and personal settings auditable.

### Codename mixed chart discovery and line ghost input

Codename discovery registers native strumline charts and section-based
`song.notes` charts that meet the embedded chart shape contract. The section
adapter copies note rows/events and BPM sections, normalizes section length
and girlfriend field spelling, and merges shared Codename events. Files
without either chart structure remain sidecars or unsupported formats; they
are never advertised as empty difficulties. `Song.resolveChartData` keeps the
selected difficulty's gameplay and visual fields at runtime.

For section-based charts, Codename's legacy parser constructs camera line 0
from `player2` (girlfriend position only when the ID starts with `gf`), line 1
from `player1`, and an invisible line 2 from `gf`, `gfVersion`, `player3` or
`gf` unless the opponent is a girlfriend or the selected ID is `none`.
`CodenameImporter.cameraLegacyStrumlines` preserves these exact indexed slots
in the selected difficulty's camera sidecar. An absent donor character
definition stays unresolved and is reported during the actor plan.

Codename HScript may pass its `camFollow` FlxObject to `FlxCamera.focusOn`.
The script interpreter converts that one camera call to a position before
Flixel's native typed method is entered; other camera method calls retain
their normal dispatch. The conversion prevents an unchecked hxcpp argument
cast from crashing the game while retaining the same target coordinates.

Each Codename input line has a nullable `ghostTapping` override. Null reads the
live game default, and a script override affects only that line. The input
path emits ghost misses according to the line's resolved value while valid
notes on other pressed lanes remain hittable. This does not create separate
receptor groups or independent audio channels for extra lines.

Codename input lines also hold mutable `animSuffix`, `defaultAnimSuffix`, and
`altAnim` state. `Alt Animation Toggle` updates the selected line's sing
suffix and its current actors' idle suffix independently. A note's authored
sing suffix is stored separately from `Note.animSuffix`, which the native note
skin rewrites for rendering; an explicit note suffix takes precedence over the
line suffix at hit dispatch.

`CodenameCameraModulo` builds a cumulative float step/beat/measure timeline
from selected chart metadata plus merged BPM, continuous BPM, and time
signature events. `PlayState` samples it each frame before due events, uses
the configured camera modulo axis/interval/offset for bops, and synchronizes
the native conductor's current BPM/step anchor. Codename's cancelable bop
callbacks, configurable zoom multipliers and cap, and non-four-step legacy
beat callbacks are not fully represented by this adapter yet.

### Codename nullable lines and stage camera starts

Codename strumline arrays may contain null entries. Import/chart planning and
actor/input models retain those indices as empty slots so later lines keep
their authored identity, camera references and controls. Dispatch and cleanup
guard null line instances. The stage's authored `startCamPosX` and
`startCamPosY` apply independently after the initial stage is available or a
stage change installs its replacement. An omitted axis leaves the current
camera target on that axis. Actor placement on stage swap reads the newly
selected stage's placement object.

Within a non-null input line, `actorSlots` likewise retains nullable authored
character occurrences for note routing. The script-facing `characters` array
contains only live actors and keeps a stable array identity across primary
swaps. Script edits map back to their source slots before native hit and miss
dispatch. A missing authored actor emits a structured diagnostic with its
source line and occurrence instead of exposing a null script character.
Each non-null line also exposes a live `notes` group keyed by the imported
chart's authored source-line index, including auxiliary type-2 lines. Its
`members`, iterator, indexed `get` and `forEachAlive` surface return native
note sprites so source scripts can mutate current graphics; release drops its
resolver. Codename's `onStrumCreation` payload can cancel that receptor's
entrance animation without cancelling creation or later input animations.
`CodenameScriptInterp` routes HScript reads and writes of the computed
`CodenameInputLine.characters` property through `CodenameInputLineScriptAccess`.
The typed bridge preserves the filtered, mutable view on native builds where
reflective field access can bypass the getter and expose nullable slots.

### Codename owner configuration metadata

Codename importer metadata resolution reads chart defaults from the selected
owner's `data/config/modpack.ini` for mods or `data/config/flags.ini` for source
assets. Authored file and inline chart metadata take precedence over those
defaults. Resolved sidecars record default provenance; other configuration
flags and chart variant selection remain explicitly diagnosed as unsupported.

### Imported song identity and base ownership

Import ownership is independent of an archive's display name. Each detected
source root and engine maps to a destination-only namespace, and a song whose
native folder is already owned by the engine or another import receives an
owner-qualified storage key. Chart, audio, scripts, Freeplay registration and
difficulty discovery use that key together. `assets/data/baseSongKeys.json`
records the engine's tracked base chart folders; the importer fails closed if
that registry is missing, and it does not infer ownership from a foreign
`compatScripts.json` left in a base folder. An existing folder without a valid
owner manifest is also reserved. The importer does not merge chart variants
from different owners into one folder.

During a qualified import, accepted charts may materialize the destination
folder before finalization. The finalization loop writes `importProvenance.json`
before asset merging creates `compatScripts.json`. The ownership guard accepts
that intermediate folder only when bounded provenance names the same engine,
destination folder and destination-only owner namespace. A missing or malformed
record remains reserved; an existing invalid manifest never falls back to
provenance. This also lets an interrupted import resume under its original
owner. The older per-song `ModuleState` import screen also invokes the batch
planner and package-name prompt, so its Modding Plus staging path uses the
same ownership and Freeplay naming rules. The direct low-level song writer
remains a conflict-checked primitive for editor callers.
The offscreen import harness accepts one explicit package label through
`--smoke-import-package-name` only when its scan finds exactly one selected
package without authored metadata; it passes that label through the same
validated `ImportPackageNamePrompt` map as the interactive importer.
`tools/repair_base_song_import_collision.py` backs up and restores one or more
previously overwritten base charts only after their foreign charts have been
safely refreshed into a qualified destination. It removes proven foreign
sidecars and byte-identical donor audio while preserving seed-owned audio.

Discovery groups duplicate views by physical chart directory as well as song
name. Two selected packages can therefore both provide the same song name;
the importer retains each candidate's chart and audio paths through the write
and asset merge. A compiled Codename release with one inner mod retains the
release root as its historical owner, while sibling inner mods use separate
owners. This keeps existing manifests repairable without mixing independent
packages.

Freeplay keeps both entries when an imported song shares a base title. The
imported entry includes its package label. `FreeplaySourceDisplay` renders
that label as a smaller parenthesized line below the chart title. New imports
store it separately in Freeplay metadata; older owner-qualified entries
recover their exact suffix from destination provenance only when a row enters
the bounded visible window. Older unqualified imported rows can also recover
their package label from matching same-folder provenance. For early records
without a mod-name field, the
reader checks the selected owner's authored chart title before splitting a
source suffix. The full display remains searchable; an empty search result
cannot launch or delete the previously selected hidden song.
`FreeplaySongOrder` groups versions by normalized chart title in the generated
All category, with the base entry first and original order retained among
other versions. For an older import whose title differs from its storage key,
it reads the small owner receipt to recover the exact chart title for sorting.
It does not rewrite the saved order of other categories.
Labels come from authored package
JSON metadata (`_polymod_meta.json`, `pack.json`, `mod.json`) or a bounded
standalone HaxeFlixel `Project.xml` app title. A single inner Codename mod
keeps its own metadata/folder identity ahead of the host engine project's
title. Interactive imports ask for a name when there is no authored metadata;
unattended imports use the inferred folder label.
`importProvenance.json` records the label and whether it was authored, entered
or inferred, alongside the destination owner. `ImportSongOwnership` reconnects
a moved package through an authored package ID, or through a package label
paired with a bounded fingerprint of selected chart bytes and audio filenames
and sizes. A label alone cannot claim an existing owner; duplicate labels with
different fingerprints receive separate destinations. Existing receipts with
no stored identity/fingerprint remain untouched and fail closed on a moved
source root. This fingerprint is calculated during import discovery, never by
the build or normal game launch.

### Qualified Codename owners and script globals

The native chart's `compatStorageFolder` is its import identity even when its
`song` field is a display title. `PlayState.codenameSourceFolder` reads that
folder's `importProvenance.json` and accepts a donor source directory only when
its version, engine, selected owner, destination, and contained source path all
match. Legacy imports use a unique case-insensitive directory match inside the
selected owner. Stage registries and character manifests use the same storage
folder, so a title-matched folder owned by another package cannot supply them.
Script and camera sidecars are checked against the resolved source directory.

Codename's `Paths` resolver collapses repeated separators inside a relative
asset key before resolving it under the selected owner. It still rejects
absolute paths, drive prefixes, and `.`/`..` components. This matches donor
scripts that concatenate two slash-terminated fragments without opening a
path out of the import namespace. The bounded static `Paths.*` asset planner
applies the same separator normalization before staging these referenced
files, so runtime and importer agree on the selected owner's path.

Song and character scripts receive live `state`, `cpuStrums`, and
`playerStrums` values, and `postUpdate(elapsed)` runs after native and Psych
update callbacks. The shared import bindings expose Flixel's actual
`FlxTextFormat` class and tween type. `DiscordUtil.user.globalName` is a
nullable offline facade because the local RPC wrapper does not provide the
Codename account identity; scripts can use their own authored fallback.

### Modding Plus character and cutscene owners

For an accepted Modding Plus chart, the importer reads its authored player
character ids and keeps their registry rows, atlas folders, and `like` script
implementations below the chart's selected `assets/imported_mods/<owner>`
namespace. Character visual resolution checks that owner before the merged
native registry. Existing owner files are left untouched on a same-source
refresh. This prevents a shared `bf-dark` or `gf-dark` atlas from another
import from silently replacing the chart donor's frames.

The importer also keeps the Modding Plus `custom_cutscenes` tree under that
owner. Chart validation and `PlayState.customIntro` resolve cutscene keys
through the selected owner's registry and script, including case-correct
keys. A missing owner registry or script yields an explicit dependency
diagnostic and a countdown handoff, rather than borrowing a global script
with the same key. The normal Story or Always Do Cutscenes gate still decides
whether the intro runs.

### Codename stock note types and private native checks

`CodenameNoteTypeCompat` applies the stock `No Anim Note` rule to the mutable
hit and player-miss event after source callbacks, before native character
animation. It preserves the authored `noteType` text and other callback
mutations. Importing arbitrary owner-authored `data/notes/*.hx` remains open.
Codename scripts may call `executeEvent({name, time, params})`; that event now
uses the same mutable `onEvent`, native action, and `onPostEvent` dispatch as
authored chart events.

The offscreen harness can enter one chart through the normal Story cutscene
gate with `--smoke-story-mode`. Selected owner scripts and media are copied
into each disposable runtime because a symlink target outside the runtime
working directory is intentionally rejected by `FNFAssets`. `song_start`,
pause, and resume markers let tests check cutscene handoff and music-clock
behavior without changing saved options.

Codename's `funkin.options.Options` import receives a detached per-script
view of native downscroll, ghost tapping, song offset, camera zoom, flashing
lights, and the current FPS cap. Codename's source default `antialiasing=true`
is also available within that detached view. Script writes stay in that view; `save()` and
`applySettings()` diagnose their unsupported native effects without touching
personal settings. Unsupported Codename fields diagnose on access and return
`null`, so shader and low-memory branches are not silently reported as
source-equivalent.

The shared Codename `CoolUtil.playMenuSFX` facade maps source CoolSfx IDs 0–5
to the selected owner's menu/editor sound keys. Missing owner audio is reported
explicitly, and the facade never takes another import's same-named sound.
`HxcFreeplayRuntime` seeds `hxcAssetRoot` alongside its scoped `Paths` binding
before executing translated Freeplay modules, including V-Slice video modules.
Codename `FlxTween.tween` targets declared scalar shader uniforms through a
numeric mirror; update and completion callbacks write the tweened value back
through the same shader setter used by HScript field assignments. A requested
unknown or non-scalar uniform produces an explicit diagnostic.
`CodenameScriptInterp` reads each OpenFL shader parameter's declared GLSL
type before assigning a script value. Native HScript can box `1.0` as an
integer; FLOAT uniforms still receive a float, while INT and BOOL retain
their own setter paths. Vector and square-matrix arrays use their declared
widths. OpenFL's native path does not upload non-square matrices, so requests
for those produce an explicit compatibility diagnostic. This common bridge
also handles camera shader assignments before the first rendered frame.

The Codename importer discovers bounded owner `source/**/*.hx` files and
stages them under the selected owner. `CodenameClassScriptPlan` inspects their
class and method declarations as text, identifies literal asset keys passed
through recognized `Paths` calls, and includes those assets in the import
plan. It reports imports that need executable private classes. HScript cannot
execute arbitrary Haxe class declarations. `CodenameScriptClassLoader` now
loads supported selected-owner classes before song-script import validation,
with the same trusted Flixel and owner Paths bindings used by menu states.
`CodenameScriptInterp` unwraps a class instance for scene insertion only when
it is a loader-created, still-owned proxy around a native `FlxBasic`; release
removes and destroys that native object once. The mounted HL17 `Bopper.hx`
passes the focused interpreter fixture, including owner isolation and cleanup.
An `insert` request for an object already in the owning Flixel group leaves its
first position intact, matching `FlxGroup.insert`; callers must remove the
object before inserting it at another index. The Codename 3D view keeps the
stage's requested bitmap dimensions and disposes its native view and mesh
resources once on teardown. A death replacement can have owner character
metadata without a live XML definition; orientation then reads its initialized
animation names instead of the absent definition.
The sampled Flixel layer order and current offscreen capture do not establish
donor parity for the Away3D floor-versus-desk depth appearance; that visual
question remains open independently of the allocation patch.
The 3D view renders at the stage's requested width and height, including
2560×1440 source stages. There is no internal resolution or draw-rate cap in
this compatibility path. With `dirty3D` true, the shared renderer retains one
full-size `BitmapData`, asks Away3D for a snapshot, and Flixel uploads the
changed bitmap as a texture. OpenFL's separate-backbuffer-texture readback
branch reads the frame and copies it into that bitmap. The borrowed-texture
experiment produced a blank result, so no compatible zero-copy replacement has
been verified. `run.sh` applies an exact-source OpenFL 9.5.2 patch that keeps
one CPU readback byte array and source `Image` per `Context3D`, replacing them
on backbuffer resize and dropping their references on disposal. This removes
recurring full-frame staging allocations while leaving framebuffer readback,
destination bitmap copy and Flixel texture upload intact.

`FlxSprite.draw()` already loops through eligible cameras in one call,
submitting the sprite before `FlxGame` flushes the camera render queues. The
existing `FlxView3D` override therefore performs one snapshot per game draw;
gating that work on `postUpdate` would add no per-camera savings and could skip
a draw when update and render cadence differ. No additional draw gate is used.

Bounded Gordonteen receipts taken after the OpenFL staging-buffer patch measured
active-scene median sampled FPS of 60, 104
and 100 at configured caps 60, 240 and 480. Peak RSS was 1,003.9, 1,012.6 and
1,005.1 MiB; median RSS was 896.5, 912.5 and 904.2 MiB. These short receipts
show the staging-buffer patch improved observed performance in that run, but
do not establish that the reported 1.3 GiB memory oscillation has been
eliminated. No resolution or draw-rate cap was added. These receipts do not
establish source-matching 3D depth-order appearance; the readback patch does
not address depth-order visual parity.
Codename Animate characters begin with the source `applyStageMatrix=true`
before their `create` callback. Character XML can explicitly override it after
the atlas loads, so Animate recomputes its bounds; an omitted attribute leaves
a script's create-time choice intact. XML `useRenderTexture` remains an extra
field because the source character parser does not apply that attribute.
Unsupported Haxe syntax or private dependencies remain explicit diagnostics;
full HL17 source visual and stage behavior still require separate checks.

Character discovery also inventories the selected owner's flat
`data/characters` definition directory, bounded to 512 entries. This includes
characters created by scripts from runtime arrays, while each definition and
its referenced atlas still pass the owner path and asset checks. The chart's
character list remains part of discovery for nested definitions and for
explicit missing-character diagnostics.
`Character` reports a missing visual only after its source-backed Codename
definition has also failed; the merged native registry alone is not proof
that an owner XML character is absent.
When an imported Codename mod lacks its installation's configured
`DEFAULT_CHARACTER`, discovery can select the compiled installation's base
asset root. `CodenameBaseCharacterDependency` copies only that exact character
XML and its referenced Sparrow or Animate atlas into the selected owner's
`compat-engine-base` directory, recording SHA-256 for every file in a
versioned receipt. Existing owner paths are never replaced. Runtime fallback
requires the matching receipt and rechecks its bytes; an owner-local
definition or character script has precedence. The mounted HL17 Buck charts
currently resolve all actor IDs within their owner, so they do not exercise
the installed default-character fallback in normal gameplay.

For full-song checks, the private harness can finish after the real song-end
callback leaves `PlayState` and five seconds of teardown pass. Its original
deadline remains a fallback for delayed Story endings. This shortens the idle
tail of natural-ending tests while retaining a window for immediate teardown
failures.

Psych stage setup accepts literal `setPropertyFromClass()` writes for
`GameOverSubstate` character and death/loop/end sound names. The values live on
the current `PlayState`; death construction selects the authored character and
audio resolves through the selected owner's sound path. Both disappear with
that song. The same per-song bridge handles finite nonnegative `deathDelay`
and pauses gameplay progression until its timer opens game over. Dynamic or unrelated class properties remain
diagnosed. The offscreen input driver can press Accept at bounded intervals
until a real `song_start` marker, allowing multi-line donor dialogue to be
tested without changing saved settings.
Psych `playSound(path, volume, tag)` stores its returned sound under a
PlayState-local tag for `soundFadeOut`, `soundFadeIn`, and `stopSound`; a Boolean
third argument still selects looping for older scripts. Tagged sounds are
stopped and their names cleared during song teardown.
Static Psych stage conversion also carries numeric `setProperty` alpha values
for sprites constructed earlier in the stage callback. Unknown sprite tags and
dynamic alpha expressions stay explicit diagnostics.

Psych import keeps the source chart's `song` title for HUD text, script
`curSong`, and other authored identity uses. `Song.loadFromJson` attaches the
selected native data/audio folder as `compatStorageFolder`; Psych song-script
discovery uses that folder, and `Inst.ogg`/`Voices.ogg` are resolved there.
The loader also retains each difficulty's authored `format`. The
`psych_v1_convert` format declares absolute note sides: lanes 0–3 belong to
the player and 4–7 to the opponent, independent of `mustHitSection` (which
still controls camera focus). `ChartNoteOwnership` keeps the older
section-relative rule for charts without that format. This applies to both
tap and sustain notes and does not rewrite imported rows.
The importer marks these charts with `compatPreserveSongTitle` so the native
HUD displays the title's spelling and punctuation directly. Existing owner
charts can receive a title-only, backed-up refresh from a verified private
import via `tools/refresh_psych_song_titles.py`; it checks owner manifests and
source note/event payloads before changing chart metadata.

When a Psych chart omits `stage`, discovery reads the selected donor's
`StageData.hx::vanillaSongStage` switch and stores its source-owned default in
the imported chart. Explicit chart and `info.txt` stages win. The bounded
parser reads literal cases and fallback values without executing donor Haxe
or using a built-in song-name table; existing imports require a scoped refresh
before their stored stage changes.

Psych's `gfVersion` is converted on each source difficulty before song-level
metadata fills missing visual fields. A sparse difficulty keeps `gf` absent
when the only candidate is the stock default, allowing the selected Normal
chart to supply its authored girlfriend. Older owner charts can receive only
the corrected `gf` field from a verified private import with
`tools/refresh_psych_girlfriend_fields.py`; the tool backs up every changed
chart and checks ownership, source notes/events and personal options.

### Codename global song scripts and imported-state endings

Codename runs `.hx` files directly below an owner's `songs/` directory for
every song. `CodenameScriptDiscovery` inventories only immediate files there,
with a 256-file cap, stages them under that owner, and loads them before the
song's own `scripts/` files. A song-local `hud.hx` also loads when present.
Both `onStartSong` and `onSongStart` run once after audio starts. The source
layout follows [Codename's gameplay-script documentation](https://codename-engine.com/wiki/modding/scripting/playstate-scripts/gameplay-scripts).

The selected owner's `data/states/PlayState.hx` enters the same gameplay
script lifecycle before stage and song scopes. Its `scripts.set` registry
publishes values to later scopes; the owner of each key controls cleanup on
failure or state teardown. Bare `health` is a live native gameplay global,
including during top-level script initialization. A failed `postCreate`
callback releases that scope and its exports, as the HL17 HUD asset probe
demonstrates. The importer must stage dynamically indexed HUD assets before
the corresponding state script can complete.

`CodenamePlayStateFacade` exposes the live song view, current instance and
story-mode state to imported gameplay HScript. `CodenameInstrumentalFacade`
exposes the playing Flixel sound's time, length and optional authored
`onComplete` callback. Natural audio completion flushes chart events first,
then lets that callback choose the next state; the native ending runs when no
authored callback exists. The legacy `resetSongInfos` route clears story
selection without nulling the chart while `PlayState.destroy` still needs it.
Offscreen `--smoke-require-song-end` checks continue ticking after a song
callback switches into `CodenameImportedState`; the imported state owns that
single smoke tick until the harness observes the new state and exits. This
keeps a genuine non-botplay callback transition verifiable without changing
normal game-state timing.

Codename note construction is deferred until the selected owner's gameplay,
global-song, HUD and song scripts have run `create()`. Receptors are rebuilt
once at that boundary while preserving scripted line placement and effects;
note objects are then built before `postCreate` and countdown tweens. This
lets `onNoteCreation`/`onStrumCreation` change atlas paths, animation prefixes,
scale and cancel default visual setup before native frames are assigned.
Their post-creation callbacks receive the live note/receptor objects. Atlas
loading goes through owner-scoped `CodenamePaths.getFrames`, preserving Sparrow
trim and rotation. `CodenameCreationVisual` follows Codename's shared
purple hold-end prefix fallback; `Note.frameOffset` is a writable, lazy
FlxPoint applied to the sprite frame transform, and only host-created points
return to its pool. A combined native FNAS replay applies the owner's
opponent atlas to notes and receptors and reaches the authored ending;
custom note-splash rendering and unnamed pixel receptor prefix changes are
still explicitly diagnosed unsupported paths.

Imported-state `FlxG` collision and overlap calls use each interpreter's
private world bounds and restore native bounds after the synchronous call,
including on callback errors. `FlxGroup` resolves to Flixel's typed group
constructor. The interpreter destroys constructor-created Flixel objects that
were never accepted by a scene; scene-owned groups retain their members for
host teardown. An opt-in `--smoke-owner-root` validates a chart's installed
owner manifest before a direct story smoke activates that owner, matching the
Imported Mods menu's owner selection in offscreen tests.

`CodenameModCatalog` records validated owner roots independently of whether
they contain a launchable custom state. The Imported Mods picker lists only
validated state rows; `CodenameModSwitchMenu` groups by owner and can activate
a global-script-only package or disable imported owners. Catalog refreshes
remove missing owners and transition-helper state rows with backups, without
rewriting owner trees or charts. An accepted Flixel state target is removed
from its outgoing interpreter's cleanup list before a scripted menu switch.
The selected-owner menu facade resolves literal font paths to registered font
families and validates `FlxG.openURL` targets. Codename's shared Options menu
maps supported native preferences and selected-owner XML checkboxes to their
own save buckets; unsupported XML option types and source-only preferences
emit diagnostics instead of silently changing settings.

Generated imported charts are written with Haxe's standard JSON encoder.
TJSON remains the permissive reader for hand-maintained JSONC assets, but its
native encoder crashed while serializing a converted Codename note array.
Section-based Codename charts retain an explicit authored song title while
pure Codename charts use the normalized storage and audio key.
`CodenameImportBindings` exposes `FlxPoint.get` through a reflectable facade
and maps Codename's flattened `FlxBasePoint` import to Flixel 6's secondary
class; the gameplay interpreter also seeds the implicit `FlxPoint` global.
The same shared imports expose Flixel's score formatting through a reflectable
`FlxStringUtil` wrapper. `CodenameScriptParser` lowers indexed key/value
loops through `CodenameKeyValueIterator`, including nested-loop bodies. Its
iterator handles arrays, imported map literals and native maps in source
order. Parsed numeric range loops use a reflectable iterator because
HScript cannot call the native `IntIterator`'s inline methods dynamically.
Top-level typed `Int`, `Float`, and `Bool` fields are predeclared with Haxe's
zero or false defaults before script functions capture them; later authored
initializers still run at their original position. This keeps an uninitialized
camera-tracking value numeric when a stage's first `postUpdate` reads it.
Owner-scoped chart refreshes accept a case-only title correction when its
folded value matches the storage folder, while rejecting a changed owner or
unrelated audio identity. The D-Sides `blammed` Easy/Normal/Hard refresh used
this guard and saved the prior chart bytes under `tmp/owned-chart-backups/`.

Codename note timing now uses a PlayState-owned `CodenameRatingManager`. Its
default windows come from Codename's Etterna preset; scripts may replace the
manager with Classic, Week 7 or V-Slice presets and add ratings such as
D-Sides' `epic`. The shared script imports expose `RatingManager` and
`HitWindowData.WindowPreset`. Imported Codename notes use the manager's
`lastHitWindow` for the source strumline input gate and per-note early/late
scales. Hits use the selected rating's score, accuracy, health, splash and
combo-break fields, while non-Codename notes keep the existing Judge path.
The manager belongs to one PlayState, so a replacement does not carry to the
next song. The remaining Codename scoring signal API is not yet exposed.

### Codename editor, transition assets, and HUD surface

`CodenameCharterAdapter` subclasses the native `ChartingState` and validates
the active selected-owner song and difficulty before a Codename script can
open it. It exposes the source constructor's song, difficulty and variation
arguments; nonempty variation and non-reload paths currently diagnose because
the native editor cannot represent them. The native editor still needs an
offscreen open/save/return round trip before parity is claimed.

`ModuleFunctions.codenameScriptFiles` follows bounded literal
`MusicBeatTransition.script` references in owner scripts, while
`codenameRuntimeFiles` stages bounded files returned by literal
`Paths.getFolderDirectories` and `Paths.getFolderContent` calls. It also
follows bounded `data/stickerpacks/*.json` keys to their owner-local images.
Both keep the selected owner as their filesystem boundary. The shared
`CodenameMusicBeatTransition` host runs the imported transition script on
outgoing and incoming state changes. `CodenameScriptInterp` retains selected
top-level static declarations in the interpreter variable map so
`CodenameTransitionScope` can hand their values to the incoming transition;
the outgoing scope captures them before it finishes. The transition host
owns its timers, cameras, stickers and cleanup independently of the song.
Native Freeplay charts choose their installed Codename owner from the chart
manifest, without activating a global mod session. A transition carries that
owner through the outgoing/incoming pair; callbacks push an executing-owner
context so sticker assets still resolve from the transition's source when the
destination chart has a different owner. The incoming lease is consumed only
after the transition opens. A failed open or non-MusicBeat destination abandons
the lease, and completing the incoming half releases temporary owner state.
Pause and resume use the outgoing lifecycle transition's recorded script path
for the incoming half, even if a callback changes the owner's selected script
while the pause substate is open. This also selects the matching per-script
static variables. A real state handoff keeps the live selector semantics above.
The Soretro Hard offscreen pause/resume fixture checks this pairing, the
music clock and completion after both transitions.
For callback-driven state changes, `CodenameModRuntime.switchTarget` queues
the concrete selected-owner destination in `CodenameTransitionScope` before
Flixel starts the outgoing transition. `CodenameModStateRuntime.switchState`
uses that same path. The source transition reads this destination through
`newState`; the native host remains callback-driven so Flixel performs one
switch after the outgoing script completes. The D-Sides Options route exercises
both an outgoing Options target and an outgoing imported-state return target
in private native sessions. `LoadingState` also passes concrete targets when
available; a target created only inside a lazy callback has no pre-switch
`FlxState` to expose and still needs source-behavior verification.

`CodenameInputLine.members` resolves authored player, opponent and girlfriend
lines to live native receptors. Unmapped extra lines return no fabricated
receptors. `StrumNote.getAnim()` reads the current native receptor animation
for scripts that inspect it. Independent Codename lines map to their own
renderer rows. The FunkinModchart adapter shares those live native notes and
receptors with the source renderer.

`PlayState.draw()` prepares one arrow snapshot before the ordinary FlxGroup
draw. When a visible, attached FunkinModchart `Manager` owns that PlayState's
arrow draw, the adapter bypass-hides the native sprites for that ordinary pass;
`CtxRenderer` still reads their preserved `_fmVisible` flags and draws the
transformed items. The manager consumes the prepared snapshot instead of
collecting the arrows again. If the manager is hidden, detached, destroyed, or
belongs to another state, the adapter restores the native visibility. The same
restoration applies when a pause substate prevents the parent state from
drawing its members. This shared ownership path fixes the duplicate static and
transformed note pass without chart or package checks. An owner-active D-Sides
Endless capture confirms a source lane relocation remains visible; it does not
establish full visual or gameplay parity across Codename charts.

The runtime-file planner also stages the selected owner's bounded flat
`images/game/score/*.png` folder because rating names are chosen dynamically
and have no literal image reference in source scripts. Shared import bindings
expose the native OpenFL display/text classes, Haxe reflection and clock,
OpenFL memory usage, `Main.instance` as the real display root, and
`CodenameFramerateCompat.instance` as the live FPS counter. Its debug mode is
adapter state; it does not write the native options or save data. The
owner-scoped `CodenameScriptClassLoader` resolves explicitly imported
HScript-ex classes under the selected owner's `source/` tree. It registers
their declarations in one script scope, binds native imports through the
existing compatibility map, and reports unsupported syntax or unavailable
dependencies. Paths, module count, source size, and dependency depth are
bounded; a class file present on disk does not silently count as executable.
On a class parse failure, a bounded syntax retry inserts a missing terminator
only when a multiline array field ends on its own `]` line immediately before
another access-modified class field. If the retry still fails, the original
parse error remains visible. This accepts the mounted options-window source
without altering its owner file or broadly rewriting class syntax.
Before parsing, the loader also expands only referenced direct modules from
an owner-local wildcard package and normalizes initialized `final` fields,
unambiguous import aliases, and `StringTools` calls with statically proven
String receivers. Reassignment, unknown extension receivers, alias shadowing,
and syntax outside that subset remain explicit diagnostics. The selected
Psych `BaseStage` runtime described below supplies its own host and bindings.
The bounded normalizer also erases balanced constructor type arguments only
when the target resolves to an owner class or an explicitly available native
class. A `Map<String, T>` or `Map<Int, T>` constructor selects its corresponding
native map class; other key types stay unsupported. Unreferenced bare imports
without an owner source or explicit binding are removed after a token-aware
use check, while referenced unsupported imports retain their diagnostics. The
curated native class map includes the pinned Flixel animation controller,
sort helper, and destroy helper needed by the Psych character dependencies.
Untyped prefix `cast expr` drops only its compile-time keyword when the
operand position is provable; parenthesized typed or ambiguous casts still
fail explicitly. This admits the donor Psych `backend.Song` grammar without
changing the donor file. `CodenamePaths.limeAssets()` binds the used Lime
`Assets.getText` import through the selected owner. It returns null for a
valid missing owner file as Lime does, rejects path traversal, sibling owners
and escaping symlinks. Compiled Psych stages additionally use the owner-aware
OpenFL asset view described below.
The StringTools normalizer also accepts the inherited
`animation.curAnim.name` chain only for a class directly extending the real
Flixel sprite binding, after proving the pinned `FlxBaseAnimation.name` field
is a String and ruling out a shadowing `animation` declaration. The mounted
Psych `StageWeek1` dependency now advances to
`ClientPrefs.data.noteSkin.trim()` in `objects/Note.hx`; that chain has not
yet been admitted by a similarly bounded type proof.
Psych stages have a separate `PsychCompiledStageRuntime`: it registers a
selected owner's `BaseStage` subclass, runs its `create`/`createPost` and
gameplay callbacks against a live host, and releases its scope at teardown.
The runtime script interpreter resolves the source package's global
`using StringTools` instance syntax on strings (including chained `trim`,
`contains`, and `replace` calls). The compiled stage event bridge passes
Psych's post-handler numeric event values; for `Hey!`, an empty or
nonpositive duration becomes the source default of 0.6 seconds before
`BaseStage.eventCalled` runs.
Psych `dadGroup`, `boyfriendGroup`, and `gfGroup` facades expose actor placement
and member reads when the native host stores each actor directly. Scene
add/remove/insert and actor-index lookups resolve those facades to their live
native actors before crossing into Flixel's display group, preserving both
native type safety and authored layering operations.
`Character.skipDance` is mutable in the shared character runtime: when true,
the beat-driven `dance()` path returns before selecting an idle pose, while
sing and direct animation calls still run. Source-only constructor defaults
can be derived from the selected donor's retained `source/objects/Character.hx`;
character JSON alone does not encode that policy. The bounded
`PsychMappedAnimsSource` parser recognizes a source-declared companion chart,
static note-list handoff, initial pose and dance setting. Before `createPost`,
the native stage runtime reads that chart only inside the selected song folder
and gives the note array to the matching actor and owner class static field.
HScript-ex static variables are stored once per `ScriptClassScope`, initialized
on first read and released with the owner. Script property reads/writes and
native compatibility writes share that storage; no descriptor is published
globally, so equal class names in different imports remain isolated.
Its explicit source binding map includes `haxe.Json`, native Flixel graphic
types, and selected-owner Lime and OpenFL Assets facades. Relative IDs resolve
inside that owner before native fallback; sibling-owner, symlink escape and
traversal paths fail explicitly. Its bound Psych `GameOverSubstate` static
surface forwards source stage sound/character writes and finite nonnegative
`deathDelay` to the native per-song class-property map. The native death
transition waits that delay before stopping audio and opening game over;
zero retains the immediate path. The
class loader lowers indexed key/value loops and erases
runtime-irrelevant generic annotations in class type positions, including
structural generic fields. These grammar bridges preserve expressions and do
not imply that every imported dependency can be executed.
The Psych importer preserves bounded `.hx` files below each selected owner's
`source/` directory. It copies additively with canonical source/destination
containment, file and byte limits, and explicit reject diagnostics. Imported
source still needs every referenced class and API binding before its stage can
run; a JSON-only fallback is reported as a compatibility failure.
The repository-owned HScript-ex patcher executes nested script-class methods
with a saved interpreter frame. It restores caller locals, declaration stack,
return state and try state after the nested call or error, so outer methods can
use their local fields after invoking another imported class method.
It also resolves inherited native properties by their declared instance fields,
including properties currently holding `false` or `null`, and still rejects
unknown fields. The patcher recognizes earlier owner-scope patches in the
generated hscript-ex dependency and applies newer additions once.
`CodenameOptionsFacade` exposes Codename primary and alternate key fields from
the two keyboard slots of native player one. Its reflected supported fields
read the native options snapshot; `save()` commits changed gameplay options
and controls through the native persistence paths. Private offscreen testing
proved that an HL17 Downscroll toggle survives a second process without
touching the live user's settings. Unsupported source toggles remain nullable
and are never saved as native preferences.

The shared settings map `naughtyness` to a persisted preference with source
default true, `colorHealthBar` to existing character-colored health bars, and
`volumeMusic`/`volumeSFX` to Flixel's default music/sound group volumes with
source default 1.0 and [0,1] clamping. The Codename quality adapter applies
LOW (`antialiasing=false`, `lowMemoryMode=true`, `gameplayShaders=false`), HIGH
(`true`, `false`, `true`), and CUSTOM (preserved individual choices). Existing
saves without a quality field migrate a complete non-HIGH triple to CUSTOM,
keeping those values; the menu locks individual choices in LOW/HIGH. The
`week6PixelPerfect` flag is available to imported scripts and persists in
native settings. Pixel camera, shader, and low-memory source effects require
separate native source-parity checks; developer/config controls remain
explicitly unsupported. A token-aware source scan records
owner-relative lines for direct `Options` references and literal menu pointers
in loaded class modules and classless companion scripts. Its separate
diagnostic channel reports static references, never an observed runtime read;
the native harness also lists unsupported capabilities independently of script
execution. The HL17 class UI uses vertical
child layout in `HLUIWindow` and `HLUITable`, while an `HLUIComponent` wrapper
without a real graphic skips Flixel's empty-frame fallback draw. `HLUILabel`
updates font formatting only when its actual style changes, avoiding repeated
text-atlas regeneration. This renders the private Options window with ordered
rows and checked controls; the remaining null class-method writes and source
option semantics are still under investigation.
Codename global scripts run `new()` after loading, receive frame `update()`
while active, and receive `destroy()` only after successful creation. Their
`FlxG.save.data` view is stored under the canonical import owner instead of
exposing the user's native save. A state switch lets Flixel reset and destroy
old cameras before PlayState releases its script scopes. Camera journals
therefore skip the old host-camera journal after a reset, including hosts
that a script detached before Flixel's destruction pass; already-destroyed
owned cameras are not destroyed again. A two-visit offscreen Endless Hard check passed both
with and without the selected owner after this cleanup change.
The interpreter initially owns a `FlxState` that an imported script constructs
with `new`. Once `FlxG.switchState` accepts that target, the facade removes it
from the outgoing interpreter's unclaimed-object cleanup list; Flixel now owns
the queued state. A refused transition leaves the state in its creator's scope
and destroys it on release. The real-interpreter lifetime fixture covers both
branches, and the FNAS menu-to-PlayState native replay exercises the accepted
branch.
Actor construction rechecks the exact selected-owner stage script when an
older imported camera sidecar contains a broad `stage-script` placement
marker. It uses authored XML slots for extra actors when source analysis
finds no unresolved geometry writes, including scripts that move named
primary actors or change only the alpha of indexed secondary actors. Unknown
geometry writes and getter-derived actor aliases keep the
placement dependency visible. The classless script parser names the kind and name of
each unsupported owner module declaration rather than treating a staged
class file as executable.

Validated Codename stage XML slots publish `stage.characterPoses` camera
offsets for authored character-change scripts. Stage teardown clears that map
with the rest of the stage's owned placement state. Song-end transitions use a
state factory so the victory state's graphics are allocated after the old
PlayState is destroyed; `Main` trims the bitmap cache at `preStateCreate`,
before any new state's `create()` uses those graphics.

Codename song scripts receive the native HUD's `missesTxt`, `iconArray`,
`scoreTxt`, `accuracyTxt`, live score/miss/scroll values, and icon bump
callbacks. `HealthIcon` uses the Codename elapsed-time scale decay only when
its gameplay owner is Codename; its `setIcon` source method changes the
existing native icon through `switchAnim`. The shared utility facade implements
`fpsLerp` and `quantize` with source formulas; `Flags.ICON_LERP` is 0.33.
`window` is the live Lime window and `FlxG.timeScale` is live, with song
teardown resetting time scale. These are compatibility surfaces, not a claim
that Codename HUD styling or full-song behavior matches every source mod.
`CodenameModBindings.coolUtil` is shared by menu, song and character hosts;
its music methods use Codename's persist/volume/loop/BPM argument order.

Owner-scoped HScript-ex classes may compose a native Flixel superclass.
`ScriptClassScope` unwraps those proxies only when a same-owner class crosses
native group mutation or FlxTween target arguments; other script values and
cross-owner proxies stay isolated. The Flixel bridge is compiled only in the
native Flixel build, leaving standalone interpreter fixtures usable. The
class scope resolves an unambiguous owner superclass inherited through
`source/import.hx` across packages. Inherited HScript methods dispatch through
the owner class chain before reaching a native superclass. Actor group views
are iterable, and native group `forEach` callbacks receive their corresponding
owner script object so authored methods remain callable. These behaviors are
needed by compiled Psych stages with layered script sprites. The compiled-stage
interpreter also unwraps scope-owned native group bridges on indexed reads of
`members[i]`. Property writes on that returned owner object update the
composed sprite; native group storage remains the original Flixel bridge and
foreign owner scopes stay isolated. The compiled-stage
binding table also exposes installed Flixel trail and typed-text classes to
source stages and their imported dialogue classes. The class-module loader
can lower top-level payload-free enum constructors used
for assignment, equality, switch and string conversion. Payload, generic,
abstract and ambiguous enum declarations remain explicit load failures.
The Codename interpreter reads and writes Flixel's setter-backed camera alpha
through typed camera access, while other dynamic property paths retain normal
reflection. These shared adapters also serve selected-owner Psych archive
compiled stages; a natural ending alone does not prove a stage executed.
The Codename `FlxTween.tween` facade resolves an owned HScript class proxy to
its native `FlxBasic` target before Flixel's reflective per-frame writes.
The interpreter's existing owner check guards that resolution, and ordinary
anonymous tween targets still pass through as they were. This matters for
script classes that extend native sprites but expose their fields through a
proxy; Flixel cannot write `alpha` to the proxy itself.

Imported Codename Options views persist shader and low-memory preferences
and apply the antialias default to subsequently created sprites. The
GPU-only bitmap control is retained as a visible unsupported capability
because this runtime has no matching storage backend. The key-7 editor
picker keeps the source choice list; Chart opens the native chart editor with
a partial-compatibility diagnostic, while unavailable editor choices remain
visible and report their missing adapters.
The shared asset planner expands only finite literal audio paths, including
inclusive `FlxG.random.int(min, max)` ranges of at most 128 integer values.
It stages discovered `Paths.sound` and `Paths.music` files under the selected
import owner; dynamic or excessive ranges stay unresolved instead of causing
an unbounded donor scan.

Psych source-project imports retain mapped media libraries inside their
selected owner namespace. The media copier accepts image, video, font, shader,
sound, and Animate atlas trees from the primary `assets/base_game` mapping and
supplemental shared mappings. It preserves relative library directories,
rejects paths that escape the selected source or owner, and never replaces an
existing owner file. Compiled Psych stage `Paths` calls resolve against that
owner and the stage JSON `directory` before shared media. `Paths.image`
returns a `FlxGraphic`, matching the source API needed by tiled sprites;
folder-based Animate atlases are loaded through the installed FlxAnimate
library. External JSON/image Animate overloads remain explicitly unsupported.
Psych's character-group view reads each role's StageHelper placement anchor,
inserts scenery relative to its live actor, and synchronizes group moves with
the placement used by later character swaps.
The selected-owner class loader reuses the classless parser's Haxe
single-quoted interpolation transform, including balanced `${...}`
expressions. A Psych FlxAnimate subclass keeps the installed renderer but
adds the source controller's `curFrame` and `length` properties, mapping a
clip's frame cursor through its actual atlas indices.
Its completion signal presents Psych's `add`, `has`, and `remove` callbacks
over the installed controller's finish signal. The adapter detaches listeners
when the Animate object is destroyed.
Psych compiled shader classes need their `@:gl*` metadata expanded at owner
class load time. The native Flixel shader adapter stores numeric and sampler
uniform wrappers in OpenFL `ShaderData`; the interpreted subclass receives
its named fields from that data. The original GLSL is retained for rendering.
This avoids native reflection writes to undeclared uniform fields on the
compiled adapter. Source stage callbacks can also set `Note.blockHit`; shared
player input and botplay gates honor it until the script clears the flag.
The owner class loader also initializes declared fields without expressions
to Haxe's type defaults before constructing source objects, so later source
setters can write them. Compiled Psych stage `create()` runs after this fork
has already added characters; the BaseStage adapter inserts those early
scene objects ahead of the first actor to preserve Psych draw order. From
`createPost()` onward, ordinary `add()` appends after actors as in Psych.
The HScript-ex class patch seeds uninitialized instance fields before method
execution and binds method parameters in local frames. A parameter that shares
a field name can then be read locally while `this.field` still refers to the
instance; nested calls restore their own frames without replacing field writes.
The same interpreter handles FlxColor's Int-backed channels through typed
getters and setters. Direct and compound HScript assignments write the
updated color bits back to the original local, field, or array slot while
ordinary object properties keep their normal reflection behavior. Owner
class descriptors can also appear as runtime values when the source imports
them. `FlxTypedGroup.recycle` uses a scope-local class symbol to create or
reuse a script instance behind a native FlxBasic bridge; cross-owner symbols
are rejected and a released scope cannot supply new instances.
Owner HScript-ex classes that compose native `FlxBasic` instances enter
Flixel groups through a scope-owned lifecycle bridge. The bridge forwards
`update`, `draw`, and destruction to the authored object, while native groups
retain a real Flixel member; removals and scope release detach it. The
compiled Psych binding surface exposes the active `FlxG.state`, live control
actions through `Controls.instance.pressed`, and the native transition flags
used by source cutscenes. These facades do not create separate input saves.
Source `BaseStage.songName` comes from chart `SONG.song` through Psych's
`formatToSongPath`; the native HUD has an unrelated `songName` text object.
Psych's story and seen-cutscene getters read PlayState static flags. The stage
may replace the countdown and song-ending callbacks; this PlayState keeps
those callbacks only for its lifetime and invokes them once. A source stage's
`startVideo` resolves media inside its selected owner and returns to the
countdown or ending transition when native playback completes or is skipped.
It exposes the active native video as `game.videoCutscene` with mutable
`finishCallback` and `onSkip`, so an authored stage can hand off from a video
to another cutscene before countdown. Psych video skipping samples the held
state of the live Accept action's configured keyboard/gamepad bindings for
one second of game update time; other native videos keep their own skip rule.
The transition checks the skip request separately from `skipped`: missing
video duration still calls the authored skip callback, while `skipped` remains
the flag used for chart-time seeking. Psych source stages can call
`game.moveCameraSection()` or `game.moveCamera(isDad)` against the native
character and stage camera offsets. Their `cameraSpeed` and
`isCameraOnForcedPos` fields control native follow speed and temporary
cutscene camera ownership.
Successful compiled-stage countdown handoff sets `watchedCutscene` even when
the chart has no native cutscene metadata, matching Psych's retry gate.
Psych characters read authored `flip_x` from their selected owner's preserved
JSON and apply `flip_x != isPlayer` without swapping named directional frames
or offsets. Other character formats keep their respective orientation rules.
The owner class parser mirrors available native `sys`, `cpp`, and video
capabilities when selecting Haxe `#if` branches. The owner-scoped HScript-ex
patch implements Haxe `Function.bind` on interpreted functions so source
stages can register partially applied callbacks with their native PlayState.
It also evaluates assignment values once and invokes function-valued source
class fields, including cutscene finish and skip callbacks.

### Scoped Codename owner refresh

`tools/repair_codename_owned_bundles.py` plans changes from a fresh private
import of the exact selected donor root. An addition is confined to the
selected import owner. A generated replacement requires the explicit
`--allow-generated-replacements` flag and matching source identity, owner,
destination and SHA-256 evidence; an unmatched candidate is a conflict. Apply
holds the runtime locks, writes timestamped backups under `tmp/`, and can
roll back exact applied bytes. Files outside the plan and both settings files
are protected by independent hash checks.

Owner-qualified chart folders are resolved through
`importProvenance.json.sourceFolder` by
`tools/refresh_codename_events.py`. This prevents a same-named base chart from
being used as evidence for an imported chart's event sidecar. The selected
owner remains the unit of asset and script lookup after refresh.
For a changed Codename camera sidecar that maps missing source characters,
the planner can also prove a selected owner's local `DEFAULT_CHARACTER`.
Legacy provenance must identify one source package with a matching song
folder; the source fallback config, XML, atlas, converted owner assets,
generated character script and registry must agree byte for byte with both
the private preview and installed owner. Only listed missing IDs may change
from null to that native fallback. An ambiguous source root or changed asset
keeps the installed sidecar untouched. The existing receipt-verified engine
base dependency path remains available when a package has no local XML.

Codename character conversion also retains each referenced source
`data/characters/<id>.xml` and its atlas at the original
`images/characters/<sprite>` path inside that same owner. The converted
`images/custom_chars` entry serves native character selection; source XML
and atlas paths serve Codename script construction, camera swaps and
constructor hooks. The importer copies only paths proven within the selected
source subtrees, preserves their case, and skips existing owner files. A
missing source definition can use the receipt-verified default character
from its selected compiled installation; sibling imports never supply one.

`ChooseCharState` derives its visible roster from the current global character
registry on each entry. `CharacterSelectRoster` asks the same
`Song.resolveCharacterVisual` loader used by gameplay whether each entry has a
complete visual under its own asset name. This keeps stale registry names from
appearing in clean release installations whose imported media was excluded,
while installed characters become selectable without a restart.

The Codename script parser lowers local Haxe `final` declarations to HScript
`var` bindings while leaving comments and string literals intact. Its script
scope exposes the live owner splash group as `splashHandler`; killing that
group also gates the native splash fallback. Paired generated script/camera
sidecars are refreshed only when every existing member still matches the
generated value, so an edited installed sidecar is preserved. The Freeplay
registry is written only for a new registration or a logical JSON change;
re-importing an already registered song preserves the original file bytes.

### Mixed-owner V-Slice visual refresh

`ImportSongOwnership.planDestination` keeps base-song folders reserved and
qualifies genuine foreign-owner chart collisions. An older chart folder can
also contain several compatibility roots while selecting the exact source
being refreshed. In that case the planner returns `visualOnly`, and the batch
importer revisits only that source's non-overwriting visual mappings. It does
not write a second chart, audio folder, Freeplay row or source provenance for
the mixed folder. The selected root and engine must match the requested
source; an unselected root cannot use the repair path.

V-Slice discovery includes every safe character definition in the selected
package because HXC scripts can create characters that no initial chart role
or Change Character event names. Converted characters, registry rows and
paired atlases live under the selected owner. A usable primary atlas and at
least one available animation make the character playable; missing secondary
animation sheets stay diagnosed and their zero-frame animations are omitted.
The HXC pulse adapter checks dynamic sound arguments in compiled runtime code
so generated HScript does not need to resolve a `String` type at callback
time. These rules are source-format behavior, not song-name exceptions.

An HXC countdown callback can choose an ordered camera filter list with a
boolean switch over a root-scoped preference. The analyzer requires the
preference getter to lower to that owner's isolated save view and every array
entry to resolve to a declared shader filter for the selected camera. It then
lowers both authored branches to native shader handles and assigns the exact
selected list. Unknown filter expressions or extra camera writes remain
diagnostics rather than partially executing a callback.

V-Slice HXC media discovery accepts both flat `music/<key>.<ext>` and source
`music/<key>/<key>.<ext>` files, including the package's shared asset tree.
The imported flat alias remains the path `Paths.music(key)` resolves at
runtime. Missing references are kept as diagnostics rather than fabricated
media. Static HXC planning currently scans scripts outside the selected
song/stage path, so import diagnostics need a reachability check before they
are counted as gameplay blockers.
Imported HXC `Paths.file` keys resolve under the selected owner. If a file is
absent, the returned candidate remains owner-scoped; the window icon bridge
reports its script origin and searched owner path as a missing donor
dependency, leaving the current native icon in place. This prevents a host
or another package's same-named file from silently filling the gap.

Overlay planning, application and asset resolution share
`ImportOverlayPath`. Native hxcpp returns null from `FileSystem.fullPath` for
a destination that does not exist yet. The helper resolves the longest
existing prefix, then appends missing components; it checks the original
component sequence before normalization so symlinks followed by `..` cannot
escape the selected asset root. A valid patch with no base is retained as
`missing-merge-base` rather than mislabeled as a target escape.

## Codename package states, charts and live notes (29 September 2026)

The imported package picker uses each verified owner as one entry and starts
its authored title state when one exists. Constructor calls from that state
resolve sibling or qualified state scripts inside the same owner. This lets
an authored title hand off to its main menu and Freeplay without routing
through another imported package. A package without an authored entry point
can still use owner-filtered native Freeplay. Menu names and source labels
come from package metadata or the import-time name prompt, not root folder
spelling.

`CodenameImportBindings` supplies `Chart.parse` as an owner-scoped facade.
When an original source chart is retained, the adapter reads it from that
owner and merges its authored metadata. Older imports may contain only the
converted native chart plus the resolved Codename metadata sidecar. In that
case `Chart.parse` exposes the converted chart and exact owner metadata,
marks `sourceChartAvailable=false`, and leaves source-only strumline and
note-type fields null. Missing variants are reported explicitly. Haxe
`import ... as Alias` declarations are parsed with their original module
path and bound in the classless script without a line-width restriction.
`HighscoreChange` and `FunkinSave` expose Codename's score defaults, distinct
variation/opponent/co-op keys, and best-score replacement rule; normal-mode
keys keep their previous on-disk spelling so existing records remain readable.

Codename strumline `.notes.members` remains a full, ordered live note view.
`CodenameLineNoteIndex` records source-line buckets and object identities
once at chart load, then merges dynamically created active notes in time
order. `forEachAlive` follows source `NoteGroup` behavior: it skips absent or
retired notes and stops at the live song clock plus the mutable `limit`
(default 1,500 ms). This keeps scripts' full member access while avoiding
whole-chart callbacks each frame. Try Harder Hard's private 480 FPS hardware
replay rose from a 37 FPS baseline to 468 FPS median with this shared change;
the verification report records the setup and still-open visual parity work.

Codename runtime asset planning also reads simple script-local string
bindings that form the directory prefix of a dynamic `Paths.getSparrowAtlas`
call. It collects direct PNG/XML children from that selected owner's
`images/` directory, then from a structurally verified shared installation
assets directory when available. It preserves authored filename case and
reports unsafe or unresolved expressions. The installed D-Sides Freeplay
owner received a backed-up, missing-only refresh of 31 icon atlas pairs;
the native route after that refresh reached the owner's title, main menu,
and Freeplay, navigated its first two entries, and emitted no script errors.

`PlayState.hscriptSafePlay` reuses one decoded sound and one `FlxSound` per
path during a song. `PlayState.destroy()` now destroys its live script sound
instances and clears the four static playback/decode maps after callbacks
and owned script cleanup have stopped. This prevents those per-song objects
from remaining rooted across subsequent PlayState loads. The active bitmap
set in the 480 FPS Try Harder sample was stable, so that single-song RSS
measurement does not establish a cache leak.

## Current-state Example Mods chart evidence

`tools/refresh_example_chart_matrix.py` takes a reviewed source-key matrix
and the non-chart package catalog, then reads the mounted source charts and
installed runtime without changing either. It verifies previously recorded
source hashes, records hashes for newer rows, and recomputes installed chart
hashes, selected import owner, and playable note counts. A moved source root
may resolve only by its exact basename at the examples root or one engine
category below it; a chart nested inside an installation may resolve at most
two folders below that selected root. Ambiguous matches and paths escaping
the selected source are rejected. ZIP charts are read directly from the
archive. The output is a new snapshot under repository `tmp/`, leaving the
reviewed baseline intact. Structural coverage here is a preflight for native
tests and does not certify presentation, audio, scripts, or interactions.

`tools/run_example_full_playthrough.py` records the actual binary and selected
chart SHA-256, compatibility manifest and default-options hashes, selected
owner, playback rate, and completion mode in each launched row's `provenance`.
The binary is hashed once per batch while holding the runtime lock. Only the
selected inputs are read; this does not fingerprint the full asset tree.
Receipts without these fields remain historical evidence. Even a matching
binary and chart cannot establish unchanged script/media dependencies or
source parity. Accelerated botplay receipts establish completion and observed
diagnostics, not normal-speed presentation or human input behavior.

`tools/audit_natural_ending_coverage.py` joins explicit receipt files/globs to
the selected matrix by `runtimeChart` and `difficulty`; changing a matrix row
index does not change that identity. It deduplicates receipts and reports
historical endings, diagnostic outcomes and binary/chart provenance separately.
A supplied current binary hash can identify matching ending evidence while
older failed attempts remain visible. This ledger supports targeted test
selection; it never certifies full compatibility or silently clears failures.

Psych script discovery has an opt-in forensic traversal enabled by
`tools/diagnose_example_auto_import.py --trace-psych-discovery`. A chart header
records source identity, followed by section and row coordinates flushed
before dereferencing each row. Coordinates refer to the latest chart header
in the synchronous traversal. The ordinary traversal has no per-row trace
branch. The compact trace avoids repeating full source paths at each array
access; it diagnoses native faults without making ordinary scans verbose.

`ChartNoteOwnership.address()` retains normalized Nightmare Vision field IDs,
local directions, character ownership, and source autoplay separately from
the legacy `mustPress` bit. Only normalized `nmv2` and exact `psych_v1` attach
a character-owner override. Other formats retain a null override so scripts
can change ownership through the live `mustPress` property. These fields are
propagated to heads, sustain segments, and lift notes. They are groundwork
for additional fields, not complete support: the importer still diagnoses
unsupported third-field charts until rendering, hit dispatch, callbacks,
input, and scoring route through independent field instances.

`NightmareVisionPlayfieldLayout` implements the supplied ModManager's field
centers and receptor-center formulas. Normalized charts configure the native
two-bank `Strumline` through `setCenteredLayout`; the engine-neutral
`centerReceptors` policy survives `resetStrums` and skin replacement without
applying legacy mania spacing. Ordinary charts retain their original layout.
`Song` carries `keys`, `lanes`, `arrowSkins`, and `trackSwap` through difficulty
merges. The NMV chart adapter materializes source defaults so a selected chart
does not inherit a sibling difficulty's different layout. Retaining these
fields does not implement custom skins, extra fields, or track-swap audio.
Opt-in native smoke runs snapshot initial receptor geometry at ready and song
start separately, keeping countdown tween positions identifiable.

`NightmareVisionScriptDiscovery` records source-ordered direct gameplay scripts
without executing them. `ModuleFunctions` attaches its unsupported-script and
incomplete-inventory diagnostics to per-song import analysis. Discovery keeps
selected-package ownership, source extension precedence and TJSON parsing;
legacy event sidecars are explicitly provisional. Dynamic script loading,
runtime global-pack selection and non-gameplay contexts remain unverified.

NMV script retention preserves source-relative `data/characters`, `data/stages`,
`data/notetypes`, `data/events`, and their character/event/note-type fallback
directories. Song scripts retain the immediate `songs/<song>` and
`songs/<song>/scripts` locations. This script-only pass does not copy song audio
or arbitrary song media. Its iterative traversal checks path ownership and
symlink ancestry, honors cancellation, and reports incomplete walks without
adding a file-count or depth cutoff. Existing owner files are not overwritten;
repair checks verify promised destination files rather than only a manifest.
Base assets and runtime global-mod layers still need separately owned staging
and resolution; they must not be flattened over the selected content package.

The NMV execution core uses pinned `hscript-iris` 1.1.3's separate
`crowplexus.hscript` namespace; the other engine interpreters keep their
existing dependencies. The supplied NMV source names an unpinned Iris git
dependency, so the stable package is not assumed to match its full grammar.
The NMV execution core is separate from the legacy HScript callback aliases:
`NightmareVisionScriptParser` lowers public module declarations to the source
`:sharable` metadata, and `NightmareVisionScriptInterp` resolves locals,
presets, imports, live parent members and shared values in source order.
Assignment, compound operations and increments write through to that scope;
plain local/shared assignment also materializes a preset, matching the supplied
interpreter's `setTo` behavior. Releasing a module drops its parent, closures,
and binding references without clearing the group's shared map.
`NightmareVisionScriptGroup` registers modules before executing top-level code,
calls `onLoad` immediately on success, and leaves later lifecycle dispatch to
the host. STOP (1) preserves broadcasting while requesting native cancellation;
HALT (2) stops broadcasting and retains the preceding result. `clear` broadcasts
`onDestroy` with stops ignored, whereas `destroy` only releases ownership.
Import and extension adapters belong to each interpreter via `bindImport`
and `bindUsing`, rather than owner data in Iris's global registries. Native
class resolution remains available as a fallback. Iris parses imports,
aliases, typedefs, using directives and final declarations. NMV key/value
loops preserve Iris's `EFor` node and place their extra binding in metadata
on the iterator; the source iterator adapter handles that binding, including
array comprehensions and loop control. `HaxeStringInterpolation` lexically
lowers single-quoted interpolation for both NMV and Codename, preserving
double quotes/comments and interpreting `$$` as a literal dollar.
The adapter also removes absent local slots during scope restoration, avoiding
Iris 1.1.3's null-slot dereference after a loop shadows an outer preset. Module
calls restore interpreter frame bookkeeping on exceptions, retaining captured
value mutations while preventing a failed callback from corrupting later calls.
The core is tested independently but is **not connected to PlayState yet**.
Gameplay integration still needs NMV API bindings, staged owner/base-layer
resolution and the source callback/cancellation boundaries. Wildcard imports,
the release's older plugin API and all compiled-class dependencies still need
source-specific verification; successful parsing is not execution coverage.

### Windows release updates

The Windows release ZIP carries `RELEASE_TAG` beside `Funkin.exe`. Settings
checks GitHub's release list because the `latest` endpoint omits prereleases.
`UpdateChecker` accepts only a matching Windows x64 archive with a SHA-256 asset
digest and checksum sidecar. It downloads in a helper process, verifies both
hashes and ZIP paths, then waits for the running executable to close. The
installer backs up files it replaces and restores them if copying fails; the
release tag changes only after a successful overlay. Existing files under
`assets/`, `mods/`, and `imported_mods/` are retained because older packages
have no ownership manifest. This preserves imports and settings but means
changes to previously installed static assets need a clean extraction.


### Cross-engine default results observation

`PsychGlobalPackImporter.defaultProvider` uses a valid user-selected imported
global pack first, then the bundled V-Slice-style results pack. The packaged
provider lives at `assets/imported_mods/bundled-vslice-results`; it is a fixed
engine-owned path, not an imported song owner. `Project.xml` copies that tree
into native builds. The release packager includes only this fixed tree inside
the otherwise excluded imported-mod namespace, verifying each file against
the source checkout. A newly imported global pack can still become the user's
selected provider without rewriting the bundled files or their settings.

The default Psych results provider receives committed native note outcomes.
Codename hit/miss dispatch runs its source event and scoring first, then sends
an observer callback while the note is still in the live notes array. Lua note
IDs are current group indices, including holes, rather than persistent sprite
IDs. Note detection reads public properties because hxcpp field-presence checks
do not identify ordinary native class members. Cancelled source judgements
produce no observer hit. Sustain callbacks
carry an unknown rating so they cannot inflate head-note judgement totals.

`CodenameRatingManager.psychJudgement` projects additional source rating tiers
onto the four-category Psych observer API using their accuracy weights and the
current source standard tiers. Source rating names, timing windows, scores,
accuracy and combo rules remain unchanged. The default provider's root scoring
property writes are ignored through its own `setProperty` binding; presentation
writes and selected-mod script bindings keep their ordinary behavior.

When the default provider claims an ending, PlayState moves its overlay camera
above the current gameplay camera list, preserving gameplay camera order and
default draw targeting. Selected mod endings retain their own camera behavior.
Psych Animate sprites use the authored stage matrix by default, retaining atlas
registration origins. Scripts can still override `applyStageMatrix` explicitly.

`CodenameTransitionSongLease` carries the outgoing chart and source metadata to
one matching incoming transition. It stores no PlayState or gameplay runtime;
owner mismatch, chart replacement, consumption and abandonment clear the lease.
The incoming transition exposes that source song view through the existing
PlayState facade, keeping metadata available after gameplay is destroyed.

## Optional song audio normalization

`OptionsHandler.normalizeSongAudio` defaults to false for missing/invalid saved
values. Main settings and imported Codename Gameplay settings expose the same
option. Gameplay and editor instrumental/vocal loaders pass freshly loaded
Sound assets through `SongAudioNormalizer.prepare`; sound effects, menu music
and script volume controls retain their existing behavior.

`SongAudioLoudness` measures 50 ms PCM blocks, excluding blocks below -60 dBFS
or 20 dB below the loudest block. Each stem receives a constant gain toward
-18 dBFS gated RMS, constrained to a 0.95 sample peak. This is RMS normalization,
not a LUFS implementation or a dynamic compressor. Sparse vocal silence does
not drive the gain upward. Peaks can prevent a stem reaching the RMS target;
this does not guarantee a clipping-free sum of multiple stems.

Scaling occurs once into a private PCM buffer because native audio backends
can clamp channel gains above one. Original PCM, cached assets and donor files
remain intact; authored fades, miss muting, seeking and pause use the unchanged
FlxSound controls and sample count/rate. Repeated loads cache only the gain,
keyed by canonical source path, size, mtime and ctime. There is no retained PCM
cache or per-frame analysis. Current native 8-bit unsigned/16-bit signed PCM
is supported; unavailable streaming PCM/other formats produce a diagnostic and
retain original playback. First-load analysis and a temporary PCM copy add
load-time work only when enabled.

### Default results character selection

Only scripts loaded as the configured default results provider receive a
results-facing `boyfriend.curCharacter`. `ResultsCharacterCompat` resolves the
requested gameplay identity (the current source player-line character for
Codename), falling back deterministically to `bf`. Ordinary scripts and the
actual character retain their identities. Standard BF/Pico families require
an owned animation atlas; BF/car and Pico/speaker-style variants use their
family. Arbitrary substring matches do not identify a family.

Providers can declare additional exact aliases in their existing `pack.json`:
`resultsCharacterFamilies: {nene: {characterIds: ["nene"], requiredAssets:
["images/nene.png", "images/nene.xml"]}}`. Every declared dependency must exist
inside that provider. The provider's script must implement the declared family;
this metadata does not generate animations or rewrite a provider script.
Explicit provider settings such as BF Only/Pico Only remain authored choices.

Codename `dad`, `bf`/`boyfriend`, and `gf` script globals are live references to
the first actor in source strumlines 0, 1, and 2. Swapping a line character
therefore changes later script and timer reads without changing native legacy
actor fields. Stage binding excludes native character registrations that collide
with live aliases, so original character entries cannot shadow a swapped actor.
Actual XML sprites may still use those names, matching Codename's stageSprites
injection; explicit script-owned variables keep their normal precedence.
Setters replace that line's character list. Structured
`Play Animation` events retain authored force/context and target every character
on the selected line after mutable event callbacks, including cancellation.

Codename asset resolution prefers an exact complete file, then accepts only a
unique complete case-insensitive match inside the selected owner. It can cross
partial case-variant directory trees without borrowing another import's files.
Explicit Sparrow/Packer loading uses raster input (`image(..., false)`);
ordinary `image` calls retain Animate/paged-atlas detection. Failed Sparrow
construction raises an asset diagnostic before a null native frame assignment.

Authored Codename note-type tables are retained per difficulty in chart metadata
and a generated owner sidecar. Only scripts named by the selected table load
from `data/notes`, before deferred note creation. Source type IDs retain their
one-based table positions; optional same-name note atlases, hit/miss/input
callbacks and sustain-clip cancellation use the shared note lifecycle.

Direct gameplay launches call `CodenameModRuntime.synchronizeChartOwner` after
clearing the new PlayState's script bookkeeping and before constructing actors
or notes. The selected chart manifest determines the Codename owner; its
installed catalog entry authorizes global-script activation. The unmodified
`data/global` constructor can therefore initialize that owner's private save
defaults before note creation reads them. Same-owner loads retain a successful
session; foreign/native charts release its global callbacks and resources.
A failed global constructor can retry on the next launch, and a failed owner
selection cannot leave the previous owner's callbacks active. Settings are
still read/written through the per-owner save facade.


### Nightmare Vision gameplay host

`NightmareVisionGameplayScripts` owns a main Iris script group for each
PlayState, using the chart manifest's selected Nightmare Vision namespace.
The installed owner is the only runtime discovery root. Stage and global
modules load before role actors; character modules load during role creation;
song modules load after the HUD and camera exist, before note generation.
Stage `add` is rebound after top-level execution but before `onLoad`. Matching
the supplied `startCharacterScript`, the character-specific `parent` variable
is assigned after `onLoad`; interpreter bare fields still refer to PlayState.

The host dispatches no-argument create/beat/step/song/end/destroy hooks,
elapsed-seconds update hooks, and the three-argument event hook after native
action dispatch (including native early-return paths). Pause and spawn STOP
returns cancel native work. End STOP retains the state and gives the mod
priority over default results. Teardown broadcasts before releasing the group.

`NightmareVisionStageData` retains the selected StageFile without replacing
missing fields with native defaults. Lookup uses the source's directory/flat
forms under `data/stages`, then `stages`; a wholly absent file uses the source
template. Import staging and missing-file repair retain these JSON files in
that same owner namespace. Existing destination files remain protected.
`CoolUtil.getEaseFromString` implements the source's 36 easing aliases.

This is an incomplete host integration. Stage-object rendering, source
CharacterGroup containers and z-order, the plugin service, full preset APIs,
event/note-type groups, dynamic loads, and additional gameplay callbacks need
implementation and native checks. Missing APIs/scopes remain diagnostics;
a loaded main module does not establish chart compatibility.

The NMV interpreter identifies control-flow exceptions by their actual enum
identity rather than a typed enum catch. Native hxcpp execution otherwise
accepted a missing-variable error as a control signal and reported a partial
module as initialized. Function returns, while/do-while/for loops, and script
try/catch use this shared check; real errors reach module/callback reporting.


### Nightmare Vision source APIs and retained dependencies

`NightmareVisionAssetCollector` walks all files under the selected content root
and its explicit engine `assets` dependency. It preserves relative paths,
checks canonical containment, and prevents ancestor symlink cycles without
limiting tree depth or file count. `ModuleFunctions` copies missing files only.
The dependency is staged below `<owner>/__nmv_core`; a core-only import stages
its scripts there as well, preventing duplicate main-group execution.
Discovery gives installed core scripts distinct relative identities. Stage
JSON lookup checks owner then core for each source candidate in order.

`NightmareVisionPaths` implements source path prefixes, extension and atlas
precedence. `checkMods=false` resolves only the staged core; true prefers the
selected owner. Neither mode searches another import or the native library.
Missing required media and shader files produce attributable errors.
`NightmareVisionShaderFactory` passes unchanged GLSL to the runtime shader
and keeps absent shader stages at their source defaults. Compile failures
are diagnosed before the source's fallback-fragment recovery.

`NightmareVisionClientPrefs` exposes a shared, detached data view per active
owner. Source defaults and exact native boolean equivalents seed the view;
only explicit flushes persist to the owner save bucket. Same-owner song loads
reuse it; a foreign owner releases it. Arrays and maps retain source types.
Control rebinding and process-wide display actions remain explicit unsupported
calls. Preference writes do not yet implement every associated native HUD or
playfield behavior. `ScriptConstants.getInstance()` resolves the current state
or active game-over substate dynamically. The color helpers follow the source
wrapper; camera-position and snap helpers retain source formulas and live
stage offset arrays. These APIs do not close the remaining automatic camera,
HUD, plugin, note-type, or event-group integration gaps.


### FunkinModchart and Flixel camera/atlas contracts

`run.sh` applies the tracked `tools/patch_funkin_modchart_uv.py` patch under the
runtime lock. `ModchartHoldUVCompat` uses Flixel 6.1.2's actual UV bounds and
12-float UVT stride, including packed rotated frames. `ModchartCameraCompat`
resolves explicit sprite/container cameras, then playfield cameras, then the
adapter's arrow-group camera. Calling `FlxBasic.getCameras()` before checking
for an explicit assignment would capture the global gameplay camera outside
`FlxTypedGroup.draw`; native notes would inherit stage zoom while sprite-group
receptors continued using the HUD. The Cammie adapter supplies the native
note group's camera and preserves per-sprite overrides without mutating them.


### Codename script sprite timelines and pause transitions

`CodenameFunkinSprite` derives from `animate.FlxAnimate`, which retains the
ordinary Flixel frame path while rendering composite Animate timelines.
`addAnim` resolves source symbol names and frame labels through the Animate
controller; indices, forced playback, offsets, stage matrices, skew, camera
factors, and animated bounds use the same shared sprite API. Loading an
Animate frame collection into a plain `FlxSprite` would expose packed limbs
without assembling the authored animation.

Opening or closing a native pause substate emits source lifecycle callbacks
without automatically starting the selected transition. Source
`canOpenCustomTransition` controls which substate can host an explicitly
requested transition; it is not an instruction to play one on every pause.
Explicit script transitions and state handoff transitions retain their hosts.


Codename scripts read an effective CPU flag (`authored cpu || demo botplay`)
through `CodenameInputLineScriptAccess` for bare `player.cpu` and through the
strumline view for `playerStrums.cpu`. Writes still update authored CPU policy.
Native ownership and `mustPress` calculations retain the authored field, so a
presentation flag cannot move notes between players. The input-line constructor
receives demo mode before source creation callbacks.

Nightmare Vision's interpreter routes `zIndex` reads, writes, and compound
assignments through the existing compatibility side table and stage map.
This supplies the source field on native Flixel sprites without adding a new
automatic sorting policy; explicit refresh behavior remains unchanged.


Codename import collection includes `images/game/notes/default` even when no
script names that implicit engine asset. Creation events resolve this default
inside the active owner, using one frame-resolution cache per owner per
PlayState. Script replacements and cancellation keep their existing priority.
The shared note/receptor atlas loader preserves Sparrow trim/rotation metadata;
plain native note sprites explicitly reject composite Animate collections with
an unsupported-format diagnostic before fallback. Keeping those files in the
import is asset coverage, not evidence of supported timeline note rendering.


### Nightmare Vision plugin, save, callback and HUD bridges

`NightmareVisionScriptDiscovery.discoverPlugins` selects immediate plugin scripts
separately from the per-chart plan. `NightmareVisionPluginHost` owns a persistent
native group, pre/post state-switch signals and updates. Its runtime preserves
core-before-owner loading, duplicate script names, `onLoad`/`onDestroy`, and real
callback return values. Re-entering the same owner reuses the group; selecting a
different owner releases its interpreters, members and signal listeners. Plugin
bindings capture owner paths/preferences rather than the outgoing PlayState.
The release's `PluginsManager` and source `ModPlugin.instance` route to that same
runtime/group. NMV menu entry-point startup remains a separate coverage gap.

`NightmareVisionFlxGView` replaces script save access with owner-scoped data.
`NightmareVisionSaveData` shares live arrays/maps between sibling interpreters,
encodes StringMaps for persistence, and keeps the ClientPrefs record independent.
These views preserve import ownership; the interpreter still exposes native APIs
and is not a security sandbox. Save failures are reported after owned script
cleanup, so they cannot strand the remaining song or plugin objects.

`NightmareVisionModManager` currently implements the source callback timeline:
ordered one-shots, inclusive repeating intervals, due callbacks after a forward
seek, and no resurrection of finished events after a backward seek. Decimal steps
use the BPM map, note offset and the source pre-clock-advance sample. Modifier
value/easing/rendering APIs remain explicitly unsupported. This must not be
reported as a complete modifier implementation.

`NightmareVisionHUDAdapter` forwards script access to existing native HUD objects;
it does not place those objects in another draw group. The source `timeBar` view
references the actual fill/background; `timeTxt` references the live text field.
The native legacy `timeBar` text alias remains available to other engine adapters.
Source HUD popup rendering and additional HUD behavior remain diagnosed gaps.
See the verification report for the built/native status of this integration.


### Windows alpha distribution

Windows alpha packages are built locally and uploaded to GitHub Releases. No
GitHub Actions workflow runs on release tags; pushing a tag does not start a
second Windows build.

On Linux, `build-windows-release.sh <tag>` runs toolchain setup, `build.sh
windows`, and `tools/package_windows_release.py` as one command. It uses the
local LLVM-MinGW toolchain when available. The build holds the runtime lock and
stages the Windows runtime DLLs and ASTC decoder. A fresh cross-built
runtime reached gameplay and exited cleanly under isolated offscreen Wine for
base Tutorial and an imported Codename chart; native Windows playback remains
to be verified on actual Windows hardware.

`tools/package_windows_release.py` retains native libraries, VLC plugins/manifests
and the ASTC decoder. Game content is limited to tracked source asset paths,
including the Project.xml mappings for templates and bundled example modules,
plus the fixed bundled results tree when its runtime files match the source
checkout.
The settings file always comes from the committed repository seed. Packaging
skips other import owners without touching them and excludes untracked flat content.


### NMV source context and native utility views

The selected owner shares its Mods context and Difficulty adapter between gameplay
scripts and persistent plugins. Import provenance records `sourceModDirectory`
separately from the display name and stable identity; older inferred-name receipts
can supply their retained folder label. Foreign/missing receipts are diagnosed,
and changing a directory label without switching its asset owner is rejected.
Source difficulty names retain their authored case, and native selections map to
the source list by name rather than assuming both engines share numeric indices.

`NightmareVisionConductor` exposes source timing names over the live transport,
including the initial BPM event and millisecond-based conversions. Window helpers
use typed Lime properties, and camera-stack queries resolve the live list. Source
camera construction with advanced blending, scale-mode changes, global Mods
loader operations and other unimplemented utility APIs remain explicit gaps.

`NightmareVisionPaths` implements source sanitization and the source-defined beep
fallback for absent sounds, retaining a dependency diagnostic. `FunkinAssets.exists`
is restricted to the selected owner and its installed core assets. A fallback does
not establish that a missing donor asset is present or that the package is verified.

`EngineBranding` separates the host application version from foreign compatibility
API versions and Flixel's version. Release names do not change executable, save,
or package identifiers.
