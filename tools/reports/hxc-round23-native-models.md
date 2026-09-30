# HXC Round 23 native model boundary

This note records the reusable native surfaces added for the selected HXC
graph. Donor charts and scripts remain untouched; no build or game launch is
required for these models.

## Native support

- `Strumline.strumlineNotes` is the live typed receptor group and
  `strumlineScale` is the live Flixel scale. `showNotesplash` gates the native
  splash path in addition to the global option. `fadeInArrows()` restores
  receptor visibility/alpha, and `setNoteSpacing()` lays out the existing
  receptor group.
- `Character.characterType` and `ignoreExclusionPref` are lightweight native
  fields. Slot actors are assigned their canonical role by `PlayState`; the
  HXC runtime reads/writes the field while retaining slot ownership as the
  gameplay authority. The current engine has no separate character-exclusion
  pass, so `ignoreExclusionPref` is intentionally retained metadata rather
  than a fabricated preference override.
- `StageHelper.getCharacterPosition()` plus the dad/boyfriend/girlfriend
  accessors expose copies of the native stage slot positions. `addCharacter()`
  routes the three gameplay slots through `PlayState.switchToChar`; an OTHER
  role is a stage-owned spectator with cleanup registration and no invented
  note lane.
- `SwagSong.getDifficulty()` resolves an existing native sibling chart through
  `Song.loadFromJson`. `SongVocalOffsets` provides a data-backed, zero-default
  view for authored offsets, and `stickerPack` is retained as opaque chart
  metadata because this engine has no generic sticker renderer. Native vocal
  playback still uses the shared conductor clock; the accessor does not fake a
  second audio transport or silently apply a donor-only offset model.
- PlayState hit/miss/sustain/release/strum checks use
  `Character.animationName()` or explicit null-safe note/receptor locals, so a
  character whose atlas has no active animation cannot crash the input path.

The extra-line seams are intentionally narrow: `Song.hx:977` wraps each
resolved sibling chart in `CompatSongDifficultyView`; `PluginManager.hx:150-152`
seeds the bounded constructor/style/rhythm aliases; `PlayState.hx:1023`
bridges incoming adapter notes into the existing HXC payload path; and
`ExtraStrumlineAdapter.hx:329-650` owns all copied note data and lifecycle
operations.

## Deliberate remaining boundary

`Strumline` remains the native four-lane gameplay line.  A separate
`ExtraStrumlineAdapter` now owns the bounded foreign stream instead of adding
its notes to `PlayState.unspawnNotes`/`notes`: `applyNoteData` copies chart rows
into private pending/head/hold lists, `processNotes`/`hitNote`/`missNote` judge
only that stream, and `clean`/`handleSkippedNotes`/`vwooshNotes` dispose only
those owned sprites and covers.  `CompatSongDifficultyView` supplies the flat
`SongNoteData`-like reads used by V-Slice/HXC while retaining no donor row or
object reference.  Receptor spacing/scale, incoming callbacks and the small
`GRhythmUtil.processWindow` result are likewise native aliases.

`PluginManager.addVarsToInterp` seeds the three bounded class aliases and
`PlayState.makeHaxeState` obtains that interpreter for generated HXC song
scripts.  The mounted DokiDoggle song therefore retains `new Strumline(...)`
in generated HScript but executes it against `ExtraStrumlineAdapter`, with
`onStrumlineNoteIncoming` terminating at the public PlayState bridge.  The
focused donor contract test executes the generated lifecycle against probe
objects and verifies construction, update/process, hit, hold-cover, retry,
and cleanup dispatch.

The HXC analyzer still owns any additional safety classification.  If the
same names are used from a global module/stage callback, its root/call allow
lists must recognize the bounded aliases and direct
`onStrumlineNoteIncoming` member; the adapter deliberately does not weaken
that safety gate.  The selected DokiDoggle song-script path itself is
classified as safe by the current analyzer and does not require a donor
source rewrite.

The mounted donor call sites for this boundary are:

- `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc`
  (`new Strumline`, `applyNoteData`, `notes`/`holdNotes`, `hitNote`, `clean`,
  and skipped-note handling);
- `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/you-and-me.hxc`
  and
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/catfight.hxc`
  (`applyNoteData`/custom note processing);
- `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dual-demise.hxc`,
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/cheerful-vision.hxc`,
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/epiphany.hxc`,
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/our-harmony.hxc`,
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/love-n-funkin.hxc`,
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/markov-lyrics.hxc`,
  and
  `TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/BF/bf-mcbf.hxc`
  (`processNotes`, `holdNotes`, and donor hold-note state).

When one of these files is selected and its callback is reachable, the
authoritative diagnostics remain `unsupported-hxc-api` and/or
`unsupported-hxc-module-body`; none is relabeled as supported by the receptor
aliases. Optional donor copies outside the selected graph are not treated as
engine gaps.

`stickerPack` has no native visual effect, and non-zero vocal offsets are
readable metadata only; missing metadata follows the native shared-conductor
zero fallback. Donor `VoicesGroup`/transport behavior remains outside this
engine. These are explicit data-model boundaries, not donor-file omissions.
