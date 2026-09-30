# Port asset audit

## Mixed-root Auto import audit (2026-09-18)

The mounted `FNF-Example-Mods` selection contains 10 detected roots and 120
song candidates. Auto selection keeps 96 unique songs and marks 24 source
duplicates; the unique-engine breakdown is V-Slice 54, Psych Engine 6, Kade
Engine 6, Legacy FNF/Polymod 23, Modding Plus 3, and FPS Plus 4. The scan found
three unresolved dependencies, all genuine omissions in the PERFEXION donor:
`bedroom` stage assets, `girl-mad` artwork, and the `girl` health icon. They are
not importer-wide path failures.

The song writer now treats instrumental audio and every written chart as
required material. Optional dialogue, event, cutscene, and vocal sidecars stay
best-effort, but a missing/unreadable required file aborts before the freeplay
registry is written. A repair may still reuse valid destination audio when the
donor has since been removed.

## Isolated mounted execution

`python3 tools/audit_mounted_auto_import.py "/run/media/cammie/External Storage/FNF-Example-Mods"`
ran the selected Auto winners through the real chart/audio/registry writer in
a temporary destination (the donor and this checkout's asset library were not
written). Donor audio metadata was validated for every winner, while the
destination uses tiny bounded audio markers instead of copying the mounted
media corpus. The authoritative result was:

```
ROOTS=10  CANDIDATES=120  SELECTED=120
IMPORTED=96  DUPLICATES=24  FAILED=0  MANIFESTS=96  FREEPLAY_VISIBLE=96
V-Slice=54  Psych Engine=6  Modding Plus=3  Legacy FNF/Polymod=23
Kade Engine=6  FPS Plus=4
```

Each of the 96 winners produced at least one readable native chart, a
non-empty bounded `Inst.ogg` fixture backed by a non-empty donor source, a
Freeplay registry entry, and a destination-only
`compatScripts.json`. The audit also caught and fixed a general storage-key
bug: display names such as `Dad Battle` and `Philly Nice` now retain their
donor folder ids (`dad-battle` and `philly-nice`) for chart/audio paths and
DifficultyManager lookup while keeping the presentation text in the registry.

The same isolated transaction now audits the V-Slice visual conversion plan.
Every supported character, stage, and note-style asset mapping must use a safe
relative destination and point to a real, non-empty donor file. The mounted
pass validated 69 distinct visual conversions and 309 supported mappings
backed by 267 donor files, with zero plan errors; all 267 source files retained
the same size and modification timestamp through the transaction, and all 66
generated character/stage HScript adapters parsed successfully. This checks
the production converter's complete source/destination plan without copying
hundreds of megabytes of visual media into scratch space.

This is an execution audit, not a game launch or a full media migration. It
materializes only tiny bounded audio markers plus the selected chart/registry
outputs to a temporary destination and removes that destination afterward; the
mounted donor and this checkout's asset library remain untouched. It does not exercise
the optional visual/support-asset copy operation, ASTC pixel decoding, or native
rendering; visual conversion mappings and their source files are nevertheless
validated as described above.
The three missing donor dependencies reported by discovery therefore remain
limitations of the mounted source, not execution failures in this audit.

## V-Slice split-animation dependency gaps (2026-09-18)

The decoder-enabled Auto scan reports exactly two
`animation-asset-switch` findings, both from the V-Slice `markov-lyrics`
candidate in
`TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/characters/sadbf.json`:

- `deathConfirm`, `deathLoop`, and `firstDeath` reference
  `characters/SadBFDies_Assets`.
- `firstDeath-alt`, `deathLoop-alt`, and `deathConfirm-alt` reference
  `characters/MarkovGameOver`.

A read-only search of the entire mounted `FNF-Example-Mods` tree found no
`SadBFDies_Assets.png/.astc` or `MarkovGameOver.png/.astc` file. The selected
root does contain `SadBF_Assets.astc`/`.xml` for the primary animations and
`DokiGameOver.png`/`.xml`, but the latter exposes `DokiGameOver*` frame
prefixes rather than the authored `BF die *` and `YuriWatches *` prefixes.
Using it would silently change the game-over animation, so it is not a valid
engine-level fallback.

The importer already handles a present split atlas generically: PNG and
decoded ASTC mappings are registered per animation and loaded lazily by the
native `Character` adapter. For an absent atlas it now reports the authored
logical path, the missing-source reason, and the retained-but-unavailable
switch; no chart or donor file is modified. The generated HScript deliberately
omits an unavailable animation alias instead of creating a zero-frame
`FlxAnimation`: the normal game-over no-death fallback can therefore complete
without waiting for an animation that cannot load. Synthetic coverage proves
the present-atlas route and the no-zero-frame guard, while the mounted
regression asserts the two omissions and their precise diagnostics.

The two split-atlas findings retain the exact authored definition path in the
importer report (`data/characters/sadbf.json`) and include the selected
V-Slice source root used for the search. This distinguishes a donor omission
from a path-resolution failure without inventing a death atlas.

## V-Slice Future Sound stage-prop gap (2026-09-18)

The remaining mounted V-Slice stage-prop finding belongs to the `future-sound`
candidate. Its metadata selects stage `concert2`, whose authored definition is
`data/stages/concert2.json`. That file declares a `teto` prop with
`assetPath: null` and an empty animation list. The matching companion
`scripts/stages/concert2.hxc` does not construct or load a `teto` sprite (the
similarly named prop in `concert.hxc` is a different stage and cannot be
borrowed safely).

This is therefore a genuine donor omission, not an importer/runtime resolver
gap: there is no authored asset id from which the engine could derive a safe
source path, and no same-stage HXC owner to recover it from. The converter
keeps the stage JSON unchanged, omits the unresolvable prop, and reports
`missing-prop-asset` with the exact `concert2.json` source path plus an
explicit statement that no donor-backed runtime HXC sprite was found. A
regression checks both the mounted JSON/HXC evidence and the diagnostic
provenance.

## V-Slice multisparrow primary-atlas audit (2026-09-18)

The first mounted scan showed 48
`multisparrow-primary-not-combined` findings, one
`multisparrow-subatlas-not-combined` finding, and 240 `astc-only` findings
(with zero `astc-decoder-ready` findings).
Those 48 warnings were not 48 absent atlases: they were repeated uses of the
TAKEOVER pack's authored ASTC character atlases while the read-only scanner
could not discover the checkout-local `.tools/astcenc` decoder. With the
pinned decoder explicitly available, all 240 ASTC mappings are conversion-ready
and the primary warning count is zero. The importer now searches both the
runtime `tools/` directory and the checkout `.tools/astcenc/` directory, so the
isolated scan and the packaged game use the same plan.

The converter also validates a native fallback's prefixes only against
animations that use the primary asset. Secondary multisparrow atlases may
therefore add their own authored prefixes, and the generated adapter combines
the native primary root with imported sub-atlases instead of looking for the
native `char.png` inside the generated folder. The decoder-ready mounted
counts are:

```
MULTISPARROW_PRIMARY_NOT_COMBINED=0
MULTISPARROW_SUBATLAS_NOT_COMBINED=0
ASTC_ONLY=0
ASTC_DECODER_READY=240
MISSING_ASSET=2
ANIMATION_ASSET_SWITCH=2
```

The remaining two missing asset/switch findings are the genuinely absent
`SadBFDies_Assets` and `MarkovGameOver` split death atlases from the
`markov-lyrics` character. No donor files or charts were changed, and no
unrelated atlas is substituted.

## V-Slice health-icon audit (2026-09-18)

The mounted `reactor-yuri-mix` chart also uses V-Slice's generic
`SetHealthIcon` song event. It is now a centralized native route rather than a
merely preserved foreign event: character slot `0` selects the player icon,
the authored `face` identity resolves through the existing icon registry, and
flip/pixel/offset/scale/bop fields remain in the converted event payload.

The mounted decoder-enabled scan initially reported four missing health icons.
One was an engine-resolution gap rather than a donor omission:
`silhouettemonika.json` omits `healthIcon.id`, marks the character pixel, and
uses `characters/SilhouetteMonikaPixel`; the donor provides the exact pixel
freeplay icon `images/freeplay/icons/monikapixel.png` (alongside the ambiguous
`monika-pixelnew.png`). The importer now derives a constrained
`silhouette`/`shadow` asset-stem alias and resolves the exact pixel icon before
fuzzy matching. The mounted scan consequently reports no missing icon for
that definition.

The three remaining historical warnings were role-resolution false positives,
not destination HUD omissions. Explicit `lav` and the id-less `gf-pixelbar`
and `gf-markov` definitions are used only in the V-Slice girlfriend slot; this
engine has no separate girlfriend health icon. The importer now carries
authored icon metadata into the registry but only requires a donor icon when a
character occupies the player or opponent HUD slot (including a later
`Change Character` event). If one of these ids is ever promoted to a HUD slot,
the same missing-icon diagnostic returns. No unrelated icon is substituted,
and the rerun emits zero V-Slice `missing-health-icon` diagnostics. The
unrelated Psych `girl` health-icon dependency remains in the mounted
three-item missing-dependency total.

## V-Slice animation schema aliases (2026-09-18)

The mounted TAKEOVER V-Slice definition
`data/characters/bigsayo.json` uses the older converter spellings `fps`,
`indices`, and `looped` on all five animations; it does not contain the newer
`frameRate` or `frameIndices` keys. The values happen to be 24 FPS and empty
indices in this donor, but treating those keys as unknown would silently lose
non-default timing or an indexed animation from other exports. The importer
now resolves `fps`/`indices` as centralized aliases for
`frameRate`/`frameIndices` across both character and stage-prop animation
generation. A synthetic regression uses non-default FPS and indexed frames,
and the mounted big-sayori regression confirms the donor shape remains
convertible without chart or donor edits.

## V-Slice FocusCamera payloads (2026-09-18)

The mounted Wacky World chart
`data/songs/wacky-world/wacky-world-chart.json` contains 28 `FocusCamera`
events. It uses both character-only rows such as `{ "char": 1 }` and rows
with authored `x`/`y`, step `duration`, and `ease` fields, including
`INSTANT`. The previous importer routed these events to the coordinate-only
`Camera Follow Pos` event and even used `char` as `x` when no offset existed;
that made the common character-only form pin the camera near the origin and
discarded the authored tween payload.

`EngineCompat` now canonicalizes `FocusCamera` as its own event. The importer
keeps offsets in the first two native values and packs `char`, `duration`,
`ease`, and `easeDir` in the existing event-options slot. `PlayState` invokes
the established native `FocusCamera` helper and composes V-Slice base eases
such as `quart` + `Out` into the destination `FlxEase.quartOut`, so classic
actor following, step-duration tweens, and instant camera moves share one
engine-level path with HScript. Synthetic coverage checks the full payload, and the mounted
Wacky World regression checks all 28 rows, including character-only,
coordinate, and instant forms. Donor charts remain untouched.

## V-Slice stock note styles (2026-09-18)

The mounted corpus contains ten V-Slice song pairs whose `playData.noteStyle`
is `pixel`, including `your-demise`, `your-demise-vip`,
`too-slow-monika-mix`, and other TAKEOVER pack songs. The converter previously
wrote `uiType: "normal"`
for every V-Slice chart, so those songs silently used the normal arrow atlas
and judgement scale even though the destination already has a native `pixel`
UI pack.

The importer now maps the engine-defined `funkin`/`normal` styles to native
`normal` and `pixel`/`pixelated` to native `pixel`, case-insensitively, before
the chart is written. Synthetic conversion coverage verifies the two stock
routes without changing note rows. The five mounted songs using the three
custom definitions (`HatsuneMiku`, `Pomni`, and `libitina`) now use generated
`vslice-*` packs rather than the normal fallback. The generic conversion copies
the authored note and receptor atlases, PNG-only hold sheets, source-backed
splashes, and the NoteKeys prefix/offset/scale/alpha metadata. The three
mounted hold sheets are 416x87 and contain eight 52px cells: body/end pairs
for four lanes; the runtime selects lane*2 for the body and lane*2+1 for the
end-cap.

The mounted Wacky World definition
`data/notestyles/Pomni.json` is the one enabled hold-cover case:
`holdNoteCover.data.enabled` is true and its four exact source atlases are
`shared:holdCoverPurpl1`, `shared:holdCover11`, `shared:holdCover12`, and
`shared:holdCoverRe1` (each has a donor PNG/XML pair). The importer materializes
all eight files under the generated `vslice-pomni` pack and records the authored
start/hold/end prefixes; the pooled HUD runtime starts the cover on the hold
head, follows moved receptors, and ends it at the sustain timestamp. The
HatsuneMiku and TAKEOVER `libitina` definitions explicitly set
`holdNoteCover.data.enabled` to false, so their absent shared cover paths are
donor-optional and produce no missing-cover finding.

Auxiliary countdown, judgement, and combo resources are inspected as part of
the same conversion. Source-backed popup/combo PNGs are copied into the
generated pack and enable the native judgement path (the mounted Libitina
pack supplies all Doki popup/combo files). The authoritative mounted scan now
reports five `note-style-countdown-fallback` and five
`note-style-countdown-audio-fallback` findings: each is an absent V-Slice
base/shared `funkin`/`doki` resource referenced by a mounted custom-style
conversion, for which the
destination already has native `ready/set/go` images and `intro3/2/1/Go.ogg`
fallbacks. They are informational donor-optional diagnostics, not missing
generic importer support. The same classification now covers stock
`shared:noteSplashes` and `shared/default:ui/popup/funkin/*` image ids: when
those base resources are absent, `NoteSplash`, `Judgement`, and the native
combo route already provide the destination-owned fallback. A donor-provided
stock-id PNG or ASTC still wins and follows the normal source-backed mapping;
a custom path still reports `missing-asset`. The decoder-enabled mounted scan therefore
reports four `note-style-native-fallback` summaries and only two
`missing-asset` findings (the two genuinely absent split animation atlases),
instead of repeating 59 base/shared popup/splash omissions. Base/shared paths
no longer emit `missing-note-style-audio`; a genuinely missing custom audio
path still does. The scan consequently reports zero `note-style-hold-cover`
and zero `missing-note-style-audio` findings, while the three unrelated
unresolved dependencies remain `bedroom`, `girl`, and `girl-mad`.
The scan treats native `pixel` as a destination-provided UI route, so those
ten charts are no longer false missing-UI findings. No donor style or chart is
modified. The decoder-enabled mounted scan still reports
`MISSING_DEPENDENCIES=3` (the unrelated `bedroom`, `girl`, and `girl-mad`
omissions) with no missing `ui|pixel` dependency.

Supported custom styles are also planned dependencies during the scan: their
generated `vslice-*` UI id is satisfied from the in-memory conversion plan,
while the report inventories the source-backed atlas mappings, generated
`multiNotePresets.json`, and merged registry entry that the import transaction
will materialize. A style that fails conversion remains a missing dependency
and keeps its precise source diagnostic.

Restored 571 missing support files from the original installation without overwriting existing port edits. Also repaired case-sensitive dependency paths. The copy pass reports zero remaining recoverable omissions in its supported asset scope; this does not establish character completeness. UI text/script reads now normalize parent-directory components before accessing disk.

## Character completeness gate

`repair_imported_assets.py <donor> --character-report tools/reports/missing-characters.json` now checks chart character registry entries, folders and animation implementations after its copy pass. It exits nonzero for unresolved dependencies and distinguishes incomplete donor definitions from dependencies available in the donor. The validator uses the same checks; an icon-only entry or runtime fallback does not count as a playable character.

The current report covers raw chart references, including alternate charts that may inherit defaults at runtime. It records 65 distinct incomplete character dependencies, all also incomplete under the donor's exact character-resolution rules. This is a dependency audit, not 65 verified gameplay crashes. `playableex` is registered but lacks both its folder and implementation in both installations. MILF-G's chart remains unchanged; its original player artwork cannot be recovered from this donor.

The victory screen now uses the character it loaded instead of re-parsing the unresolved chart ID. A private native-runtime probe loaded MILF-G Hard and invoked its real `endSong()` path; the victory screen rendered without the former null JSON parse. The missing player still uses the engine's existing `dad` fallback, not fabricated replacement assets.

Validation covered 1,273 freeplay songs and 3,012 difficulty charts, registered implementations, UI packs, forced UI layouts, and custom-note definitions. Postal's layout initialization, update and beat hooks pass an interpreter test with its actual assets.

## Original-source gaps

These chart-referenced implementations are missing from both installations:

- `bftricky`: Beatstreets and Upside Improbable Outset/Madness, and OMFG (13 charts).
- `nik`: Norsans Hard.
- `playableex`: MILF-G Hard.
- `trickyhell`: Hellset.
- `crystal` stage: Fragmented Surreality Alt/Easy/Hard.
- `innocence` stage: Who Are You Hard.
- Slaybells Expert: four undefined custom-note slots affecting 630 notes. The source has no definitions to restore; their behavior has not been guessed.

The JSON report includes all unresolved static references, including optional paths, inactive branches and unused registry entries. Those are review candidates, not a claim that every reference causes a gameplay failure. Computed script paths and arbitrary modchart behavior still require gameplay verification. No unrelated assets were substituted for unavailable originals.
