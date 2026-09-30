# Example Mods compatibility inventory — updated 30 September 2026

**Latest shared rendering checks (30 September):** Try Harder Hard's missing
Animate lyric scene now renders, advances through the source 418-frame
animation, and hands back to gameplay in a normal-speed offscreen replay.
The corrected demo CPU flag prevents the source ice-note script from freezing
the automated player. Endless Hard's notes now use the correct camera, owner
atlas and sustain UVs; the inspected 25/28-second captures show aligned notes
and a continuous sustain. Native pause/resume emits no unwanted sticker
transition. Latest build: `357392e762c1c1be7d136c7ba0a6998096d207a0fe769b7bd7371b6dd4e800b0`.

Both charts separately pass **50x** natural-ending/Freeplay handoff checks:
Endless dispatches all **464/464** due events; Try Harder dispatches all
**657/657** due events (one additional chart event is after the audio end).
These accelerated receipts establish execution/cleanup only. Two missing
default atlas files were added without modifying the owner's 1,034 existing
files or 42 protected settings/ownership records. Receipts:
`tmp/codename-render-completion-20260930.jsonl`,
`tmp/try-harder-scene-20260930/final-scene-check.json`, and
`tmp/endless-geometry-20260930/after.result.json`. No chart is promoted to
complete source parity solely by these targeted checks.

**30 September targeted verification:** Shared Codename note-type discovery and
callbacks now pass the private Try Harder Hard probe for all 68 ice heads,
including authored atlas, freezing, input release, and hit/miss cancellation.
Its normal-speed grab/first-person transition passes on build
`239e71845478b8d307ce02baea8e69879ce7f64a17480f0e13ab481544235b8c`:
the grab animation advances and the current player renders above the HUD corner
effect. Seven missing dependency/metadata files were added to the live import;
all 1,087 protected existing files remain unchanged after the build. Default
results selection on Satin Panties Nightmare independently chooses BF, with
unknown characters consistently falling back to BF and supported Pico requests
retaining Pico. These are targeted behavioral checks, not full-song parity or
a native import-scanner pass. Receipts and remaining gaps are recorded in
`engine-discrepancies-verification.md`.

The follow-up build `2d4ab706…` additionally initializes selected-owner globals
on direct chart launches. Fresh private-save probes now verify that the 68 ice
heads are enabled/visible by default, and that a second source note script
(GunshotNote) provides bullet art, dodge/shoot animations, authored miss damage,
and camera tween recovery. Both botplay and no-input normal-speed replays retain
the corrected grab/layering. The remaining owner tables were refreshed with
20 additional missing files and 1,094 existing files unchanged. These checks
expand the verified mechanisms; the package's full-song/difficulty coverage
and native scanner status are still incomplete.

**Newly mounted material after the 256-row snapshot:** The `psych/Marios
Madness` release was not part of the 256-row matrix. Its packaged layout has
41 song-data folders and 44 parseable chart JSON files under
`assets/data/songData/<song>`, with 50,430 raw note rows, 3,848 legacy event
rows, 32 song-local Lua scripts, and instrumentals for all 41 chart folders.
One older chart folder has no Voices track. This is an extracted Psych-family
Windows release, not a source checkout; the bundled manifests have no named
shader files or text shader calls, although compiled effects in its executable
have not been ruled out. The read-only preflight is
`tmp/marios_madness_psych_preflight_20260929.json`. Shared importer discovery
for its `songData` layout is now implemented; these 44 charts have not yet
been added to the installed matrix or certified in gameplay. The expanded
mounted import diagnostic reports 75 missing dependencies across all
packages, including 68 stage references. Many Mario stage names have no
editable stage Lua in this extracted release; the presence of charts and
media therefore cannot establish source-matching runtime behavior. Receipt:
`tmp/auto-import-counts-nmv-mario-20260929.log`.

The new `misc/` tree also contains Codename 1.1.0 and Psych 1.0.4 source
checkouts, a separate Nightmare Vision 1.0 source checkout derived from Psych
0.5.2h, and a 138-file Psych global results-screen pack. The pack has a
1,986-line `onEndSong` Lua script and a malformed `data/settings.json` with a
missing comma after the `resultsChar` default. These source trees are
compatibility references; the result pack is a new import target. Nightmare
Vision now has its own detection identity. Its mounted release contains 60
song folders across two content packs, 180 chart payloads selected by the
isolated importer, and 14
older `events.json` sidecars with chart-shaped envelopes. All 60 songs have
instrumentals; two lack vocals. Four of the 180 chart payloads declare three
playfields and remain unsupported because the current native note model has
only two. Its chart/runtime compatibility and the default-results fallback
are still under implementation. The existing
256-row counts below refer to the earlier snapshot and do not include Mario's
Madness or the result pack.

**Current mounted-source snapshot:**
`tmp/example_mods_chart_matrix_runtime_20260929.json` refreshes the reviewed
256-row baseline against the current mount and installed selected owners
without changing any import. All 256 source chart paths resolve, including the
moved FNAS tree. All 233 rows with prior recorded source hashes still match;
23 newly hashed rows have no earlier hash to compare. The natural-ending
preflight accepts 250 rows and blocks six: five source packages omit their
instrumentals (PERFEXION Extra, Extras, and Gallery; Psych archive Ridge and
Smash), and DDTO Baka's undeclared empty Normal placeholder has no matching
source notes. This is an inventory and launchability result, not a gameplay
or source-presentation pass. Dry-run receipt:
`tmp/current-matrix-full-preflight-20260929.jsonl`.

The later declaration-aware refresh
(`tmp/example_mods_chart_matrix_runtime_declared_20260929.json`) keeps 242
source-declared chart/difficulty rows, 237 with structural import coverage,
and separately records 14 raw V-Slice note-map keys that sibling metadata
does not declare for selection. This preserves the empty Baka Alt Normal key
as a diagnostic while keeping Baka Alt and base Baka Normal as separate
playable entries. The refreshed catalog copy points to the mounted FNAS tree
and extracted Psych archive source; original inventory snapshots were not
modified.

For the Psych ZIP, direct ZIP-to-installed comparison confirms that all 76
installed difficulty charts preserve every source `song` field and the entire
ordered note-section array exactly. The three Blazin charts add native default
metadata but leave every authored field unchanged. Ridge and Smash have source
charts but no installed playable rows because their source instrumentals are
absent. Receipt: `tmp/psych-archive-source-field-parity-20260929.json`.
This static match does not verify runtime lane ownership, animation, audio,
or cutscenes; those require separate native/source checks.

**Rebuilt-source first native batch:** The first 60 rows of that refreshed
matrix were replayed offscreen at 20× with natural endings required. The
pre-fix build passed 34 strict rows, failed 23, and blocked three PERFEXION
rows whose source instrumentals are absent
(`tmp/example-mods-current-build-rows-0-59-20260929.jsonl`). The failures
include a Linkinteen end-of-audio clock wrap, a native heap
abort during Relentless-Bitchass note creation, source Lua/dependency errors
in PERFEXION and Bruce, and source-missing Vs. Whitty actors. The Linkinteen
clock path was corrected in shared engine code and its same 20× row passed
on the rebuilt release (`tmp/linkinteen-rebuilt-20x-20260929.jsonl`). This
targeted replay changes that row's evidence only; the other failed rows and
the remaining corpus still need current-build verification.

**Rebuilt Psych archive batch, rows 60–119:** All 60 inventory rows were
accounted for in the offscreen 20× natural-ending sweep. Fifty-six passed
strictly. Monster Easy and Pico Easy aborted in native note setup with glibc
heap-corruption diagnostics and no song ending; their other difficulties
passed. Ridge Normal and Smash Normal remain blocked because the archive
supplies no instrumentals for them. The receipt is
`tmp/example-mods-rebuilt-rows-60-119-20260929.jsonl`; the failing process
logs and coredumps are retained for engine-level diagnosis. These crashes
prevent a current-build archive-wide compatibility claim, despite the
earlier isolated sweep passing all 76 installed chart difficulties.
One fresh offscreen replay of each crash row subsequently reached a natural
ending under `MALLOC_CHECK_=3 MALLOC_PERTURB_=165`; the private settings files
were unchanged. The crashes are therefore intermittent in current evidence.
The saved stacks detect damaged heap metadata while allocating in Psych skin
path resolution or missing note-preset path resolution; neither identifies
the earlier corrupting write. Valgrind stopped in the host loader before game
code, so it provided no memory diagnosis.
The DDTO V-Slice package's own `CustomTitleBar.hxc` requests `dokicon.png` but
checks `Assets.exists` and retains the current icon when that file is absent.
The mounted source and selected import both lack that file, and the shared
window-icon adapter takes the same fallback while emitting a structured
missing-source-dependency diagnostic. Rows carrying that diagnostic remain
strict failures in the native matrix; the reported absence is source-backed,
not an unexplained script exception.

**Rebuilt rows 120–179:** The offscreen natural-ending sweep completed all 60
inventory rows: 37 strict passes, 22 strict failures solely from the same
missing DDTO window icon, and one blocked empty Baka Normal placeholder. All
22 icon-only rows reached a natural song ending in native smoke with zero
native diagnostics. The receipt is
`tmp/example-mods-rebuilt-rows-120-179-20260929.jsonl`. This confirms those
runtime paths on the rebuilt binary while retaining the source dependency
as an explicit gap; visual, audio, editor and interaction parity remain open.

**Rebuilt rows 180–239:** All 60 rows finished the offscreen natural-ending
sweep: 39 strict passes, 20 DDTO failures solely from the same missing source
window icon, and one Cursed Expurgation failure with 62 native stage/script
diagnostics. Cursed Expurgation's selected donor stage calls undefined
`cstaticthing` and `doStopSign*` helpers and requests a sound at a path the
donor does not supply. Its byte-identical donor modchart also writes
`gramlan.x` during `update` before `beatHit(5)` first constructs `gramlan`;
the interpreter diagnoses and safely ignores that null write.
The receipt is `tmp/example-mods-rebuilt-rows-180-239-20260929.jsonl`.
Wacky World Normal/Hard and its empty metadata-unlisted Nightmare key all
reached natural endings with no current classifier error. Source video/audio
presentation still requires direct real-time comparison.

**Rebuilt rows 240–255:** All 16 D-Sides tail rows passed the strict offscreen
natural-ending sweep, including the Monster, Soretro and Tutorial regressions.
Receipt: `tmp/example-mods-rebuilt-rows-240-255-20260929.jsonl`. The first
60 rows were then replayed on the same release binary: 34 strict passes, 23
failures and three source-audio blocks
(`tmp/example-mods-rebuilt-rows-0-59-20260929.jsonl`). Linkinteen Parks
passed; Relentless-Bitchass reached its ending without another native abort
but retains three `nullspace.lua` missing-fork API diagnostics. Two long Psych
chart variants stopped before gameplay at `PsychRGBShader` construction with
`Invalid field:null`; the shared shader path is under investigation.

**Consistent-release 256-row summary:** 182 strict passes, 68 strict failures
and six blocked rows. Failure groups are 42 DDTO source-missing window icons,
15 Vs. Whitty source-missing character/icon references, three PERFEXION
Lua/asset diagnostics, three Bruce `nullspace.lua` missing-fork API diagnostics,
one Cursed Expurgation donor script failure, two intermittent native heap
aborts and two Psych shader-constructor failures. The six blocks are five
source-missing instrumentals and Baka's empty undeclared Normal placeholder.
These counts are natural-ending/diagnostic gate results, not source-matching
visual, audio, script, menu, cutscene or editor certification.
The selected Psych source `FunkinLua.hx` defaults
`removeLuaSprite(tag, destroy=true)` and passes `runTimer(..., loops=0)` through
as an infinite timer. The shared bridge matches both. PERFEXION's
`Loading Screen.lua` reads `loadingCD.alpha` after explicitly destroying that
sprite, and `THEGOUSET.lua` removes old trail sprites destructively before a
continuing timer reads their alpha; these diagnostics are source script
behavior rather than grounds for changing Psych's removal default. The Bruce
`nullspace.lua` stage references `dadOpponent` and `fpSong()` without a
definition in the supplied package; the exact donor fork/API contract is
missing, so no replacement alias has been invented.

**Complete 256-row baseline sweep (pre rebuild):** The exact current import
matrix was exercised in private Xvfb with default options, dummy audio,
20× botplay, and a required natural ending for every playable row. Of 256 raw
rows, 164 passed the strict gate, 86 failed, five were blocked by instrumentals
absent from their mounted source packages, and one had an empty undeclared raw
key. No row was skipped. The original result and settings receipt are
`tmp/example-mods-current-256-sweep-20260928/rows.jsonl` and `receipt.json`;
both default options copies stayed byte-identical. This is baseline evidence
for the older release binary, not a source-presentation parity verdict or a
pass for the pending engine changes. The 86 failures include V-Slice HXC API
gaps, missing authored assets, imported-script errors, and a few later
Codename diagnostics. Three Wacky World rows reached natural endings and had
no strict runtime errors; the sweep's broad text classifier marked an
informational video-adapter message as error-like because that message
contains the word `playback-error`. They remain failed in the original
machine-readable receipt until the classifier and rebuilt replay are checked.
The donor Cursed Expurgation stage invokes `cstaticthing` and three
`doStopSign*` helpers with no active definitions in its package; the source
dependency remains unresolved rather than receiving a song-specific shim.

**V-Slice raw and routed note counts:** In the refreshed matrix, `sourceNoteCount`
is the raw length of each source difficulty's note array. V-Slice 0.3.2 routes
only source lane values `d=0..7` to its two strumlines; the separate
`sourceGameplayNoteCount` records those rows, and `sourceUnroutedNoteCount`
records other lane values. For Vs Tricky `madness` (rows 216–218), source raw /
routed / installed totals are Easy 656/652/652, Normal 840/832/832, and Hard
1072/1064/1064. The excess raw rows use `d=12..15`, which the reference runtime
does not route. For the routed rows, a read-only comparison confirms that
timestamps, lengths, and lanes match after the import's `trickyhell` lane
encoding (`d=4..7` becomes `d=44..47`). Thus `sourceNoteCountMatched=false`
is an expected raw-total comparison on these rows; the gameplay-count match
is true and the rows remain structurally covered. Do not treat this flag alone
as a missing-note or engine-compatibility failure for V-Slice.

The normalized non-chart catalog is
`tmp/example_mods_nonchart_entity_inventory_20260929.json`. Its base catalogs
were generated for 14 source package roots plus the Psych ZIP, with package-local stages,
characters, scripts and events, cutscenes and videos, difficulty records,
required asset references, and full source file catalogs. The 14 package
catalogs recorded 5,909 listed files; the ZIP catalog records 1,276
entries, including 992 previously audited references. Its scope reconciles
113 mounted-package songs/178 chart rows plus 28 archive songs/78 rows to
the installed 141-song/256-row matrix. This catalog proves source discovery,
not that every referenced object imports or runs. The artifact lists donor
gaps such as missing PERFEXION instrumental tracks and atlases, missing
vswhitty actors, DDTO death atlases/conversations/video, and Ridge/Smash
instrumentals, alongside source script references whose helpers are absent.

The catalog now includes a bounded current-mount overlay audit generated by
`tools/inventory_nonasset_overlays.py`. All 15 prior package-root records,
including the Psych ZIP, resolved against the current mount; the FNAS record's
old `/run/media/cammie/External Storage/FNF-Example-Mods/fnas_after_hours`
root resolved by unique basename to
`/run/media/cammie/External Storage/FNF-Example-Mods/codename/fnas_after_hours`. Its
`mods/fnas/songs/better-clone/charts/normal.json` chart is present (64,159
bytes). The audit records two operation-folder files: DDTO's
`_merge/data/players/pico.json` (70 bytes, already in its base catalog), and
Modding Plus `mods/introMod/_append/data/introText.txt` (20 bytes, newly added
to overlay coverage). `mods/modList.txt` contains `introMod`, confirming the
overlay is enabled. The depth-two mount census also found the previously
unlisted `nightmare-vision` and `nightmare-vision/source_code` directories;
neither contains a recognized package operation file. These are recorded as
mount candidates, not assumed to be package roots. Eleven depth-two candidates
did not match a base package root; none had operation files. The supplement
does not revalidate every path in the original 5,909-file catalogs. The scanner
descends only operation folders, records file sizes without reading or hashing
their contents, and reads ZIP central directories without extraction.

The V-Slice importer now carries selected-owner `data/songs/<song>` text
sidecars without overwriting existing files. A missing-only installed-owner
refresh added `ajena/creditos.txt` and `our-harmony/lyrics.txt` from the exact
DDTO donor root. It kept all 459 preexisting owner files and both options
files byte-identical and backed up the affected manifests and options before
applying. The plan and receipt are under
`tmp/vslice-sidecar-refresh-20260928/`; a rebuilt native Our Harmony replay
is pending.

**28 September FNAS import update:** the user supplied `FNAS After Hours` for
the package without an authored name. A backed-up, scoped native import added
the owner-qualified Better Clone Normal chart, 104 assets, and its menu states.
The installed chart has all 1,224 source note rows and 204 events; both audio
files match source SHA-256. Prior catalog entries and personal settings were
preserved (`tmp/fnas-live-owner-import-20260928/postimport-verification.json`).
Direct offscreen gameplay reached PlayState readiness. The first imported-menu
launch crashed during PlayState creation after the outgoing Codename menu
released a pending state object. A shared state-ownership repair passed its
interpreter lifetime regression and an offscreen installed-owner replay: the
FNAS main menu rendered its four authored options, New Game reached Better
Clone gameplay, no runtime diagnostics were reported, and settings stayed
byte-identical. The successful receipt and screenshots are in
`tmp/fnas-live-owner-import-20260928/installed-menu-smoke-result.json` and
`tmp/fnas-live-owner-import-20260928/fnas-new-game-route.png`; original crash
evidence remains in `tmp/fnas-live-owner-import-20260928/coredump-bt.txt`.
A 5× offscreen story-mode botplay reached the 206,896 ms audio boundary and
dispatched all 204 due events with zero strict diagnostics, then entered the
native victory state. That botplay flag activates demo mode, whose completion
path intentionally bypasses the donor HUD script's `inst.onComplete` callback.
The run is therefore **inconclusive** for the authored minigame ending. A
story/practice replay without botplay dispatched all 204 events, captured
the donor's checkerboard minigame room after audio completion, emitted smoke
`success` after the imported-state handoff, and exited 0 without a timeout or
strict diagnostics
(`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-result.json`,
`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-after-song-end.png`).
The generic state-handoff smoke tick passed 25 focused runtime-smoke tests.
The same donor script sets custom opponent note/receptor
atlas keys through creation callbacks. The first owner import omitted that
source atlas; a generic importer rule and scoped missing-only refresh have now
staged both donor-matching files with existing owner bytes/settings preserved
(`tmp/fnas-live-owner-import-20260928/missing-hud-refresh.json`). The
combined build and private native replay now confirm `hud/oppNOTE` on opponent
notes and receptors, the first opponent tap's `frameOffset=25,0`, and a
visibly custom opponent lane during gameplay. All 204/204 due events were
dispatched, the authored checkerboard minigame appeared after the song, and
the process exited 0 with no strict diagnostics or settings changes
(`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-result.json`,
`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-mid-song.png`).
Full rendered source and audio comparison remains open.
Ending receipt:
`tmp/fnas-live-owner-import-20260928/natural-ending-5x-result.json`.
Source visual/audio parity, other menu paths and editor checks remain open.
A read-only menu audit found that Credits uses `FlxG.openURL`,
the switch-mod action requests `ModSwitchMenu`, and three donor
fonts referenced through text formatting were omitted from the first import.
A scoped missing-only refresh copied those fonts with source hash parity and
unchanged existing owner files, charts, registries, and settings
(`tmp/fnas-live-owner-import-20260928/font-refresh.json`). Shared URL,
font-family and grouped owner-switch bindings are staged. The final private
offscreen route now passes Continue → owned Freeplay → authored menu,
Options → menu, Credits link activation → menu, and New Game → PlayState,
with unchanged protected settings and no strict runtime diagnostics
(`tmp/fnas-live-owner-import-20260928/ui-routes-final-recheck-20260928/menu-routes-result.json`).
This route does not establish complete FNAS gameplay, visual, audio, editor,
or source presentation parity. A backed-up catalog reconciliation
removed six stale owner roots and transition-only launch rows while keeping
the three valid owners and preserving owner trees, charts, audio, other
registries, and settings
(`tmp/fnas-live-owner-import-20260928/catalog-refresh.json`). The private
route exercised the installed owner chooser and selected its FNAS entry.

The updated structural matrix is
`tmp/example_mods_current_chart_matrix_after_fnas_install.json`: 250 playable
rows now have owner-matched charts and instrumentals; five remain blocked by
media absent from the source packages. The undeclared empty Baka key is an
additional raw inventory row, not a playable difficulty. A fresh runner
preflight of this matrix reported 250 ready and six blocked raw rows; the six
are the five missing-source-media difficulties plus the empty Baka key
(`tmp/all-example-preflight-after-fnas-install.jsonl`). Readiness is a
chart/owner/audio gate, not a source-behavior pass.

**28 September Psych archive update:** a physically isolated import
selected 26 archive songs and produced 76 owner-matched chart difficulties with
source note-row parity. The two remaining inventoried rows, Ridge Normal and
Smash Normal, have no source instrumental and were not imported. All 76
imported rows subsequently passed one offscreen, single-binary natural-ending
strict script gate; complete source presentation and interaction checks are
still pending. The same owner was then installed through a backed-up native
import without changing any of 517 existing charts or personal options. The
private and installed receipts are `tmp/psych-archive-isolated-import-v5/result.json`
and `tmp/psych-archive-live-promotion-backup/receipt.json`.

The first complete private natural-ending sweep passed 67/76 archive rows
strictly. Focused rebuilt replays subsequently cleared all six Cocoa/Eggnog
and all three Stress difficulties, the nine failures in that sweep. The
single-binary 76-row rerun then passed every imported difficulty. Frame-level
source comparison, editor round trips and interaction checks are still pending.
Receipts:
`tmp/psych-archive-isolated-import-v5/direct-all-76.jsonl`,
`tmp/psych-archive-isolated-import-v5/replay-mall-after-hey.jsonl`,
`tmp/psych-archive-isolated-import-v5/replay-stress-after-static-map.jsonl`,
and `tmp/psych-archive-isolated-import-v5/direct-all-76-after-static-map.jsonl`.

The installed-runtime preflight (`tmp/all-example-preflight-after-fnas-install.jsonl`)
has the following package totals. These count chart/media/owner readiness
only; they do not count source-matching playthroughs or rendered parity.

| Package | Ready | Blocked |
| --- | ---: | ---: |
| bully-mod | 1 | 0 |
| hl17_v3 | 3 | 0 |
| D-Sides REDUX Codename Engine (Cancelled) | 22 | 0 |
| fnas_after_hours | 1 | 0 |
| modding-plus | 9 | 0 |
| moddingpoop | 1 | 0 |
| Hey kid do you wanna weiner | 1 | 0 |
| PERFEXION Demo1 | 3 | 3 |
| vs_brucedaworst_update_2_hotfix | 3 | 0 |
| vswhitty | 47 | 0 |
| FNF-PsychEngine-main.zip | 76 | 2 |
| DDTO++_V10_RELEASE | 67 | 1* |
| HatsuneMiku-ProjectFunkin-V-Slice | 3 | 0 |
| Vs Tricky | 10 | 0 |
| Wacky World UPDATE [V-Slice] | 3 | 0 |
| **Total raw chart keys** | **250** | **6** |

\* DDTO++ Baka `alt/normal` is an empty, undeclared chart key, retained as an
inventory finding rather than a playable difficulty. The playable total is
therefore 250 ready of 255, with five blocked. The three PERFEXION blocked
entries have no package-local instrumental, and the archive Ridge and Smash
rows have no source instrumental. The FNAS owner uses the user-selected
`FNAS After Hours` label.

This is the source and installed-runtime inventory for the current mounted
`FNF-Example-Mods` selection. A row counts a song within its own package;
same-named songs in different packages remain separate. V-Slice difficulty
counts are the keys in chart note maps, while the other package counts are
source chart files. Source path, script, stage, character, cutscene, event,
note-type, audio, and other asset details are in the linked JSON inventories.
The inventories read metadata and file paths without hashing donor media. The
mounted set contains 14 mod package roots across Codename, Modding Plus,
ModdingPoop, Psych, V-Slice and FNAS, plus the separate Psych Engine source
archive. A source-root audit found that the Psych `Hey kid do you wanna
weiner` package was omitted from the linked inventories and matrix. Including
it gives 113 package song entries / 178 chart rows, plus 28 archive songs / 78
chart rows. The linked source JSON inventories were generated on 24 September
and the normalized chart matrix on 25 September; their counts are dated
structural snapshots, not a fresh runtime audit.

A read-only follow-up on 27 September rechecked all 14 mounted package roots
and the Psych Engine archive ZIP, then enumerated 113 package song entries /
178 package chart rows and 28 archive songs / 78 archive chart rows. The
[source dependency and coverage audit](../../tmp/example_mods_source_dependency_coverage_audit.json)
separates assets absent from the mounted source from importer/engine gaps and
lists every chart/difficulty row without complete source-matching visual,
audio, interaction, and editor evidence. Rows with narrower startup or
natural-ending evidence are called out separately. This does not refresh the
older 255-row matrix below; that matrix still omits Weiner and predates the
D-Sides owner repair.

An earlier normalized matrix snapshot recorded **249/255** inventoried chart
rows with installed or private structural evidence. D-Sides has strict startup
passes for **22/22** chart rows across the latest sweep and targeted replays.
Neither measure establishes complete source-matching gameplay. Missing source
media, Psych compiled stages, full HL17 menu and settings parity, and the
package-wide visual/audio/editor/transition checks remain open. The
[verification report](engine-discrepancies-verification.md) records the
current evidence and unresolved dependencies.

A 27 September dry-run of that older matrix against the current live export
found 159 ready rows and 96 blocked rows; it launched no game. Seventy-eight
blocked rows are Psych archive references without an installed archive owner,
and nine D-Sides rows still point at base chart folders that were subsequently
repaired. The Psych `Weiner` row is absent from the 255-row snapshot. These
numbers identify stale inventory and ownership evidence, not 96 new gameplay
failures. The row receipt is
`tmp/example-mods-current-preflight-after-padding.jsonl`; its preflight now
accepts terminal NUL padding in legacy charts just as the engine does.

A 256-row test matrix replaced those stale D-Sides paths with the
22 owner-provenance-matched destinations and adds the separately inventoried
Weiner Hard row. Its read-only live-runtime preflight finds **173 structurally
ready** and **83 blocked** rows. The blocked group includes all 78 Psych
archive rows, which were privately imported but have no installed live owner;
three PERFEXION entries without package-local songs, one undeclared empty
DDTO++ chart key, and one FNAS entry. This preflight does not establish source
gameplay or visual parity. Receipts: `tmp/example_mods_current_chart_matrix.json` and
`tmp/all-example-current-256-dry-run.jsonl`.

After the backed-up Psych archive promotion, the refreshed 256-row matrix
finds **249 structurally ready and seven blocked** rows in the installed
runtime. The seven are Ridge and Smash without source Inst, three PERFEXION
entries without package-local songs, one undeclared empty DDTO++ key, and
FNAS `better-clone` pending its installed import. This is structural evidence
only (`tmp/example_mods_current_chart_matrix_after_psych_promotion.json`,
`tmp/all-example-preflight-after-psych-promotion.jsonl`).

The empty DDTO++ key is not a metadata-declared playable difficulty, so the
same receipt represents 255 playable rows: 173 structurally ready and 82
blocked. The raw key stays inventoried for audit completeness.

The package table below summarizes installed paths and private evidence; it
does not imply every listed chart or asset is in the live export. Private
replays have imported all 20 selected D-Sides songs with 22 source
chart difficulties and staged the FNAS `better-clone` chart. A subsequent
owner-scoped, backed-up refresh replaced only the three live `blammed` charts:
Easy/Normal/Hard now contain 788/858/1,019 source notes. A newer private
D-Sides sweep checked all 22 source note/event sets and reached PlayState on
22/22, but passed the strict script diagnostic gate on 0/22 because of
owner-wide Codename script errors. The earlier 18/22 strict startup result
predates the owner-wide script load. The FNAS owner menu starts
`better-clone` Normal. A private practice-mode natural-ending replay
dispatched all 204 events and followed the authored audio callback into the
rendered minigame state. A later private source-script input replay traversed
all four rooms, reached the authored `it's over` outcome, and returned to a
rendered owner menu with no script diagnostics. Neither package has a
complete compatibility pass. The [verification report](engine-discrepancies-verification.md)
records the exact fixtures and failures.

The latest strict private Xvfb sweep passed all three HL17 Buck charts through
natural endings in 5x practice botplay with zero diagnostics and unchanged
options: Gordonteen dispatched 126/126 events, Huggyteen 120/120, and
Linkinteen 5/5. Two separate Linkinteen replays on the typed actor-access
build also passed; the bridge addressed an intermittent null script-character
access found on the preceding build. Linkinteen's reviewed note-provenance
refresh and a later 1× real-time capture show the large playable character
singing after all four authored swaps. A read-only comparison to the donor
script confirms that both background videos are torn down and the game/HUD
cameras hide at the terminal step; the final black frame is authored. Full
frame-by-frame source parity and menu/settings coverage remain open. Gordonteen
and Huggyteen still report the donor's missing `testStage.mtl`. A read-only
audit found source `plane.obj` references this file but the mounted HL17
package has no `.mtl` file anywhere; the imported OBJ matches source SHA-256.
The stage supplies an explicit texture for that model. Their 3D material
appearance lacks a source-rendered comparison. Evidence:
`tmp/hl17-menu-native/post-strumline-full-buck-sweep.json`,
`tmp/hl17-menu-native/linkinteen-provenance-verified.result.json`, and
`tmp/hl17-menu-native/linkinteen-full-visual.result.json`.
Earlier import and script failures were resolved by shared class/strumline
bridges and a backed-up selected-owner asset/provenance refresh; they are kept
in the history below only where they explain the fixes.

HL17 private menu probes rendered Options, Load and Credits; a checked
owner-only refresh added three missing song portraits, and the Load screenshot
shows the donor Gordonteen portrait. The selected-owner global
`postStateSwitch` callback initializes the volume tray before updates; a
rebuilt private Options, Load and Credits click probe reports zero runtime
diagnostics and unchanged default settings. This still does not verify every
menu path or compare the full source 3D stage.

Shared Codename point, indexed-loop and string-formatting bridges subsequently
removed those specific diagnostics in a rebuilt two-chart D-Sides check. Its
scoring imports are also recognized after the source rating-manager adapter.
On that scoring build, a fresh exact-owner sweep matched all 22 source
note/event sets and started all 22 charts; **0/22** passed strict diagnostics.
The editor `Charter` import has since gained a native adapter in a newer
build. The transition host and sticker-pack metadata importer were added
later; a scoped, backed-up refresh supplied the D-Sides sticker assets and
private Darnell pause/resume probes rendered both transition directions.
`composerIntro.hx` type declarations, other global imports, and private
script dependencies remain blockers. Specific
charts also report unresolved dark-character assets, modular modchart imports,
stage placement, camera ordering, and a Bomb Bash shader value error. Receipt:
`tmp/dsides-current-build22/rating-full-22-result.json`.

The latest private exact-owner startup sweep again matched all 22 source
note/event sets and reached PlayState on 22/22, with 19 strict passes.
Rebuilt targeted replays passed Bomb Bash after Haxe primitive defaults were
applied to imported script fields and Tutorial after a shared
`HealthIcon.setIcon` method was added. Ghastly then passed a rebuilt two-visit
strict replay after shared stage-placement analysis admitted secondary actors
whose scripts only change alpha. All six actors were bound on both visits.
Across these startup checks, 22/22 D-Sides rows have a strict pass. This does
not prove full-song source parity. Evidence:
`tmp/dsides-line-refresh/current-22-startup-result.json`,
`ghastly-bomb-post-float-result.json`, and
`tmp/tutorial-icon-probe/native-result.json`.

A later owner-scoped, backed-up add-only refresh staged 83 sticker images,
two missing sticker-pack JSON files, and 15 dynamic score PNGs. Private
Darnell pause/resume transitions now finish in both directions. Endless Hard
starts without the earlier rating-image, global-import, combo, receptor
animation or shader-tween diagnostics. A later shared stage-script recheck
also cleared its stale startup actor-placement errors. It still fails strict
compatibility on a source enum declaration and FunkinModchart's real
renderer dependency; the 0/22 full-sweep result has not been superseded by a
new 22-chart strict sweep. Receipts are in the verification report.

The earlier 18 D-Sides strict startup passes also reached natural endings in
accelerated offscreen practice replays with no tagged interpreter errors and
no reachable chart events missed. Source rendering, audio mix, cutscene,
editor, pause/seek, full-song repeated-load and owner-switch parity remain
unverified. A shorter same-process two-visit Endless Hard reload now passes
after a shared camera teardown fix; it is not a full-song parity check.

Later strict natural-ending checks passed 10/10 Vs Tricky, 3/3 Wacky World,
9/9 installed VS Freddy chart difficulties, and 12/12 difficulties in Psych
vswhitty's standard, beta, HQ, and remix Ballistic family. A private VS Freddy
refresh then proved owner-scoped dark-character atlases and its Slaughter
Story intro can load from the donor. These are bounded runtime and
materialization checks; they do not establish source parity for all
difficulties. The 27 September HL17 sweep supersedes earlier strict Gordonteen
and Huggyteen failures, while 3D stage and `Bopper` behavior still lack source
visual/execution parity evidence. See the linked verification report for
receipts and limits.

The Ballistic family audit found exact imported source notes and events for
all twelve charts and byte-identical copies of 29 checked source/runtime
files, including song audio, scripts, stage definitions and the HQ death and
rumble sounds. The native gate checked natural endings, complete event
dispatch, interpreter diagnostics and unchanged test options; it does not
establish frame-by-frame visual or audio mix parity, the HQ game-over sound
playback, editor round trips or all menu paths.
The broader 47-chart vswhitty source audit found identical notes and events,
but 37 installed `song` titles were normalized storage keys rather than the
donor's authored titles. A protected fresh import retained all 47 source
titles, and a backed-up, owner-scoped refresh updated only the installed title
and preservation metadata. HQ Normal and Faucet HQ passed again afterward.
The prior Ballistic and Faucet/Hungry batches still need complete replay on
the refreshed charts; the native gate alone does not establish full source
parity.
The refreshed-title Low-Rise HQ rows passed 3/3 after the shared numeric
stage-alpha fix. All nine Underground variants then reached strict natural
endings after shared Psych `removeLuaScript` support, with full event counts
(180/180 standard, 208/208 HQ, 166/166 in-game mix) and no interpreter errors.
That gate was incomplete: Underground Easy's authored `bf-santa` was replaced
by the default chart's `bf` during difficulty visual fallback. A shared Psych
chart-loader fix now retains the explicit source ID. The corrected Easy replay
reached song end with 180/180 events but failed strict checks on the missing
`bf-santa` character and icon. The other eight rows are being replayed; the
former Easy pass is invalid as source compatibility evidence.
The other eight corrected Underground runs kept full event dispatch and no
interpreter errors, but an independent 47-chart graphic-field audit found
that in-game mix Hard/Normal had stock `gf` where source `gfVersion` requires
`gf_JUICY`; Easy's synthetic `gf` also blocked inheritance. A fresh private
import verified all 47 explicit girlfriend fields and a backed-up owner-only
refresh changed 13 installed `gf` fields. The three in-game mix difficulties
then passed strict natural endings with 166/166 events and both loaded-chart
and rendered girlfriend markers showing `gf_JUICY`. The other ten changed
charts also passed strict natural endings with their default `gf` selected
after fallback. Receipts: `tmp/vswhitty-graphic-fields-audit.json`,
`tmp/vswhitty-graphics-preview/result.json`, and
`tmp/vswhitty-graphics-preview/live-gf-receipt.json`,
`tmp/vswhitty-ingame-mix-gf-refresh.jsonl`, and
`tmp/vswhitty-graphics-preview/remaining-gf-playthrough.jsonl`.
The six Overhead rows reached song end with complete events but remain blocked
by the missing exact `bfwhit` character/icon.
Receipts: `tmp/vswhitty-lowrise-hq-alpha-final.jsonl`,
`tmp/vswhitty-underground-remove-lua-final.jsonl`,
`tmp/vswhitty-underground-scope-final-check.jsonl`, and
`tmp/vswhitty-overhead-underground-refreshed.jsonl`.

| Source package | Songs | Chart difficulties | Installed runtime status |
| --- | ---: | ---: | --- |
| Codename D-Sides REDUX | 20 | 22 | All 20 songs and 22 chart files are present; the old 18/20 status was stale. The latest scoped native refresh found 40 source views, imported nine previously incomplete owner-qualified base-name collisions, skipped 31 duplicate/already-owned views, and reported zero failures or missing dependencies. A backed-up repair restored the nine affected base-song folders from repository seed charts while retaining their separate qualified D-Sides folders and provenance; all 29 reserved base folders pass the post-repair owner and seed audit. Freeplay lists both base Monster and the D-Sides entry. A full 22-row selected-owner offscreen sweep reached every ending; 16 initially passed the strict diagnostic gate. Shared sidecar and opacity-placement fixes plus a backed-up 21-file generated metadata refresh raised the strict total to 20/22. Blammed Easy and Normal now reach their endings but report missing selected-owner `pico-dark`, `bf-dark`, and `gf-dark` character definitions. Source visual/audio, cutscene, editor, menu, pause and seek parity remain open. Evidence: `tmp/dsides-current-full-playthrough.jsonl`, `tmp/dsides-six-post-refresh-playthrough.jsonl`, and `tmp/import-refresh-backups/20260927T110802376317Z/receipt.json`. |
| Codename bully-mod | 1 | 1 | Owner-matched |
| Codename hl17_v3 | 3 | 3 | All three pass natural endings in 5x offscreen botplay with 126/126, 120/120 and 5/5 events dispatched, zero diagnostics and unchanged settings on the typed actor-access build. Two additional Linkinteen strict repeats passed. The checked owner-only event/note-provenance and asset refreshes preserve the selected owner. An earlier real-time capture shows the large playable character moving across its transitions. Screenshots were omitted from the full sweep, so source visual parity remains open. Gordonteen and Huggyteen warn that donor `testStage.mtl` is absent; 3D material parity is unverified. |
| Psych PERFEXION Demo1 | 5 | 6 | Two owner-matched songs; `Extra`, `Extras`, and `Gallery` lack package-local audio and are not installed |
| Psych Hey kid do you wanna weiner | 1 | 1 | Omitted from the 25 September matrix but separately inventoried in `tmp/psych_weiner_inventory.json`. The current export has the owner-matched 1,046-row chart, both stems, and a scoped manifest refresh. A rebuilt 5× strict offscreen natural-ending replay used its authored stage and owner-scoped custom-note atlas, with zero script diagnostics and unchanged settings after the shared note-health and ignore-rule changes. Death/retry, editor, menu, and source visual/audio parity remain open. |
| Psych Bruce hotfix | 3 | 3 | All three source charts, note payloads, events and required audio match the exact parent-root owner; stage API gaps remain |
| Psych vswhitty | 17 | 47 | All 17 songs owner-matched; 47 titles and 13 `gf` fields refreshed with backups; 31 bounded strict natural-ending passes across builds, 16 rows blocked by missing `bfwhit`/`bf-santa` assets |
| V-Slice HatsuneMiku ProjectFunkin | 3 | 3 | Three song directories and owner manifests present |
| V-Slice DDTO++ V10 | 50 | 68 | 50 base-song outputs present; four populated variations imported separately with source note/event/audio parity and passing native startup; 49 pre-existing base destinations have mixed-owner roots that block blanket re-import |
| V-Slice Vs Tricky | 4 | 10 | Song directories and owner manifests present |
| V-Slice Wacky World | 1 | 3 | Song directory and owner manifest present |
| Codename FNAS After Hours mod | 1 | 1 | `better-clone` Normal, its source-matching stems and owner manifest are installed under the user-selected `FNAS After Hours` label. The installed owner menu renders four authored choices and New Game reaches gameplay. A combined-build non-botplay story/practice run dispatched 204/204 events without script diagnostics, visibly entered the authored minigame after the song, and exited 0 through the generic smoke handoff. The custom opponent note/receptor atlas and first tap frame offset were verified through native markers and a gameplay capture. A prior private replay completed all four rooms and returned to the owner menu. Other menu paths, editor and complete source visual/audio parity remain open. |
| Modding Plus VS Freddy | 3 | 9 | All nine installed charts match note rows and lanes; 38 selected-owner character/cutscene files refreshed after a 9/9 private natural-ending replay |
| ModdingPoop Cursed Pergation | 1 | 1 | Hard chart installed with matching 1,584 rows and lanes 0–15; source script/audio defects below |
| Psych Engine v0.2.8 source/base-game archive | 28 | 78 | The 26 songs with source Inst and all 76 associated difficulties are now installed under one owner-qualified archive namespace; colliding song keys preserve existing base and D-Sides charts. All 76 passed an isolated-runtime strict natural-ending sweep, and three installed collision/stage samples passed. Ridge Normal and Smash Normal remain blocked by missing donor instrumentals. Complete source visual/audio/editor/menu/interaction parity remains open. |

The 14 imported mod package roots contain **113 package song entries and 178
chart-difficulty entries** before cross-package deduplication. The Psych
archive is also in scope: it is a complete Psych Engine v0.2.8 source project
with bundled base-game assets, rather than a standalone mod folder. Its 28
songs and 78 chart rows bring the combined source target list to 141 song
entries and 256 chart rows; that total is separate from the older imported-
package coverage matrix below.
The [normalized chart matrix](../../tmp/example_mods_chart_matrix.json),
refreshed 25 September, finds 168 of its 177 package entries structurally
represented by the live export when chart presence, selected owner, and
source-variant provenance are all required. That snapshot matches source raw
note-row counts for **165 of those 168**; three installed structural rows
still differ. The matrix also records 99 privately staged structural rows, 81
of them absent from installed coverage. Installed and private evidence
together therefore represents 249
of the matrix's 255 chart rows structurally. The matrix excludes the newly
counted `Weiner` row even though a separate read-only check found it in the
current release export with source-owner provenance and 1,046/1,046 raw note
rows. Do not treat 249/255 as current all-package coverage: D-Sides owner
repairs also postdate this matrix. The six rows it marks uncovered are PERFEXION's
Extra, Extras and Gallery; Psych archive ridge and smash, which lack source
instrumentals; and V-Slice `baka` alternate-normal. That last key is an empty
placeholder not declared by its variation's metadata; the importer preserves
the populated `alt` chart. These are chart-path, owner, variant, and row-count
checks, not full-song gameplay passes. The [refresh evidence](../../tmp/example_mods_chart_matrix_refresh_2026-09-25.md)
separates installed from private coverage and records D-Sides' 22/22 private
chart and event-count parity without claiming runtime compatibility.
The read-only six-row audit found no structural importer failure behind those
gaps: PERFEXION's Extra and Extras have identical source chart payloads and
no per-song audio, while Gallery has zero notes and no source stage definition;
Psych ridge and smash have no source instrumentals or archive owner provenance;
DDTO++ baka alt/normal is an empty note-map key omitted by the variation's
declared difficulty metadata. Exact paths and hashes are recorded in
`tmp/uncovered-six-audit.json`. Owner matching in this older matrix did not
prove namespace isolation. A 27 September scoped refresh and backed-up repair
restored the live unqualified Monster Hard and all other D-Sides-contaminated
base charts; all 29 reserved base folders now match their repository seed JSON
files. Nine base-name-collision D-Sides folders and a separately qualified
Improbable Outset folder retain their owner manifests and provenance. Personal
settings and the Freeplay registry were unchanged. A fresh read-only remap
joins all 22 D-Sides source rows to present runtime charts using exact selected
owner, import provenance, destination paths, and matching raw note-row counts;
all ten qualified destinations have Freeplay entries. The older 9/22-ready
preflight does not account for those current qualified paths, leaving the
affected source rows blocked against stale base-name chart paths. This remains
structural evidence, not gameplay parity. See
[`tmp/dsides_current_runtime_provenance_matrix.json`](../../tmp/dsides_current_runtime_provenance_matrix.json).
The structural matrix predates this repair and needs regeneration. The omitted
Psych package is at
`/run/media/cammie/External Storage/FNF-Example-Mods/psych/Hey kid do you wanna weiner`.
Its 47 source files contain one Hard chart (`Weiner`, 1,046 note rows, including
10 `Hotdog_Note` rows), one week definition, two character JSONs (`SansWeiner`
and `GameOverSprite`), a `weiner` stage JSON/Lua pair, two song Lua scripts, one
custom note-type Lua script, two song stems, three sound effects, four music
files, seven PNGs, three XMLs, and two fonts. It has no authored cutscene or
video (the videos folder only has a readme); its custom-events folder also has
only a readme. The stage script uses the stock `stageback`, `stagefront`,
`stage_light`, and `stagecurtains` images, which exist in the current export.
The release export has the converted chart and both stems, and its provenance
points at the existing owner root
`assets/imported_mods/psych-engine-hey-kid-do-you-wanna-weiner-aeec7514ea`;
the live chart retains the same 1,046 raw note rows and ten custom-note labels.
This is structural/import evidence only. The custom-note callback,
health/death overrides, custom characters and stage, Freeplay/week behavior,
and source visual/audio behavior were not replayed or compared.
The V-Slice packages contain 62 chart JSON files with 84 difficulty note-map
keys; six keys have empty note arrays and are still inventoried. The live export
has all 58 default V-Slice song directories and owner manifests plus four
separate variation directories (62 V-Slice song outputs total), and 79 of 79
expected default-chart difficulty outputs. The four authored variations
`baka-alt`, `epiphany-lyrics`, `love-n-funkin-pico`, and
`shrinking-violet-alt` now have separate native charts, Freeplay entries,
selected-owner manifests, and matching source notes/events/audio; each passed
an offscreen native PlayState startup smoke. A whole-root import over the
existing export still reports 49 mixed-owner conflicts on pre-existing base
song folders; the four new variation destinations were absent and imported
cleanly. Detailed evidence and refresh receipts are in the verification report.

Detailed source inventories:

- [Mounted source dependency and unverified coverage audit](../../tmp/example_mods_source_dependency_coverage_audit.json)
- [Current D-Sides source-to-runtime provenance matrix](../../tmp/dsides_current_runtime_provenance_matrix.json)
- [Codename, Psych packages, and Psych archive](../../tmp/codename_psych_inventory.json)
- [Psych archive chart, owner, and audio path audit](../../tmp/psych_archive_runtime_audit.json)
- [Psych archive per-chart audio/stage dependency audit](../../tmp/psych_archive_source_dependency_audit.json)
- [Psych archive private staging assessment](../../tmp/psych_archive_staging_plan.md)
- [Bruce hotfix exact-owner provenance audit](../../tmp/bruce_hotfix_owner_audit.json)
- [Bruce hotfix owner-safe play plan](../../tmp/bruce_hotfix_import_play_plan.md)
- [V-Slice packages and FNAS installation](../../tmp/inventory_vslice_fnas.json)
- [Modding Plus and ModdingPoop](../../tmp/inventory_mplus_poop.json)
- [Installed Modding Plus/ModdingPoop chart and owner cross-check](../../tmp/inventory_mplus_runtime_crosscheck.json)
- [Psych Weiner package file and source-reference supplement](../../tmp/psych_weiner_inventory.json)

The mounted-source file manifests reconcile to 14 source package roots, 113 songs
and 178 package chart/difficulty rows, plus 28 songs and 78 chart rows in the
Psych archive. The archive's 1,276 entries include every inventoried chart,
stage, character definition, video, support asset and Haxe source file. The
Modding Plus `assets/` catalog covers all 616 files in that tree. The current
supplemental overlay audit now includes the enabled
`mods/introMod/_append/data/introText.txt` (20 bytes), which was outside the
base `assets/` catalog. It also indexes DDTO's existing `_merge` file and
records the current FNAS root relocation and the new `nightmare-vision` mount
candidate. See `nonAssetOverlayAudit` in
`tmp/example_mods_nonchart_entity_inventory_20260929.json` for per-root
resolution and the complete bounded candidate census.

## Source and compatibility blockers

- The previously omitted Psych `Hey kid do you wanna weiner` package is now
  counted in the source totals above. Its current release-export chart and
  song stems are present under owner provenance and its source/runtime chart
  row counts match, but its four Lua scripts and custom character/stage assets
  have no runtime compatibility pass. The source has no cutscene or video.
- Psych vswhitty references `bfwhit` in 15 chart difficulties and `bf-santa`
  in one. Neither exact character definition or atlas is present in the
  mounted package, Psych archive, or installed custom-character registry.
  Nine Lo-Fight/Low-Rise rows already reached song end but failed strict
  compatibility on the explicit `bfwhit` character and icon diagnostic.
  Low-Rise HQ's three rows passed after a shared static stage-alpha fix.
  Six Overhead difficulties also reached natural endings with complete events
  but failed on the same absent character/icon. Underground's first nine-row
  pass masked the missing `bf-santa` Easy character by inheriting Normal's
  `bf`; the corrected loader now reports that absent source asset. The actual game-over
  override, source rendering/audio and interaction flows still need verification.
- The FNAS installation has one Codename song, `better-clone` Normal, with
  1,224 notes on three strumlines, stage `office`, three actor definitions and
  204 events. Its owner menu, global HUD and story-ending transition into
  `minigameyeaaaa` have private native evidence. The complete four-room route,
  final outcome, and return to the rendered owner menu passed on private Xvfb.
  Cutscene skipping, pause/game-over scripts, retry, seek and source
  frame/audio parity remain unverified. Its current chart manifest selects
  `assets/imported_mods/codename-engine-donor-3f9b2bff6b`; the provenance
  records the user-supplied `FNAS After Hours` label, and both audio stems
  are installed. The older `legacy-fnf-polymod-fnas-after-hours-11b4777f53`
  namespace is empty and is not the active owner. The September 24 inventory
  snapshot still reports that obsolete namespace and a `normal.json` chart
  path; the installed native chart is `better-clone.json`.
- D-Sides has mixed Codename and embedded Psych chart formats. Source charts
  for `blammed` easy and normal were missing from the initial installed song.
  An isolated production conversion yields the source counts (788/858/1,019),
  while the initial installed hard chart had base 400-row data under a D-Sides
  manifest. A scoped, backed-up owner refresh now installs all three source
  note sets and preserves their explicit section-chart titles.
  An older 20-song writer preview preserved seven other observed hard-chart
  row totals but predates the current GF-line converter and used a nested
  source root with a different owner key. The current mounted-donor converter
  test passes **22/22 source charts** with every source note represented by a
  unique native row and preserved origin; `dad-battle`, `monster`, and
  `tutorial` specifically cover 1, 49, and 126 GF-line notes. This proves
  current conversion, not rendered receptor behavior or parity for other
  stale installed charts. The old owner-matched writer preview predates the
  embedded-title fix and was not used for the live refresh.
  Two D-Sides song owners and three PERFEXION entries remain absent from the
  export. Bruce’s three songs are already installed under the exact owner for
  its `/mods` source root; the earlier inventory missed this parent-root
  provenance.
  A fresh exact-owner private import verified all 22 D-Sides rows against
  source note origins and event counts. Nine stale installed Hard charts were
  then backed up and refreshed from that current importer output, including
  source stage and chart fields; the owner and both settings files remained
  unchanged. Receipt: `tmp/dsides-current-chart-refresh/refresh-receipt.json`.
- PERFEXION has missing donor dependencies for the `bedroom` stage,
  `girl-mad`, `Night-PXT`, `Night-Girl`, and `Crazy-Girl` character art, and
  the `girl` health icon. The first three character JSONs are present but
  their referenced atlases are absent; `Crazy-Girl` has no donor definition.
  The source inventory also records unresolved gallery/menu assets and audio
  for its uninstalled entries. A private full-song sweep strictly passed
  Resonance Hard and Hardold, while Xfracture Hard reached its natural ending
  but failed on these source visuals and Lua script errors. The shared
  explicit-step loop translator is corrected. A fresh rebuilt 5× Xfracture
  Hard run still failed strict compatibility: the donor's
  `data/Xfracture/10scriptnote.lua` uses undefined `anglevar` in arithmetic,
  and the character/stage assets above remain absent. The shared callback
  diagnostic now prints the exact source file; receipts are
  `tmp/perfexion-xfracture-source-diagnostics.jsonl` and
  `tmp/perfexion-xfracture-dependencies.md`.
- The V-Slice `markov-lyrics` donor lacks two referenced split animation
  atlases. The `future-sound` stage `concert2` has a `teto` prop with no asset
  path or same-stage script construction. No substitute donor art is inferred.
  The build-10 full-song `future-sound` run reached its natural 205.333 s
  ending and dispatched all nine events. A shared HealthIcon fix now models
  V-Slice's missing-opponent fallback; its focused source test passes, but a
  rebuilt native full-song replay is pending. The separately authored
  `no-gfpixel.png` Freeplay icon remains absent from the selected owner and
  should not be used as the gameplay fallback. Evidence:
  `tmp/example-full-playthrough-future-sound-build10.jsonl` and
  `tools/tests/test_health_icon_no_character.py`.
  `rabbit-hole` likewise reaches its natural 159.566 s ending with all 592
  events dispatched, but its source `RabbitHoleOptions` menu preference and
  `onCountdownStart` shader callback are only partially represented by the
  bounded HXC shader adapter. The strict gate retains the unsupported callback
  diagnostic; evidence is in
  `tmp/example-full-playthrough-rabbit-hole-build10.jsonl`.
  `expurgation` Hard reaches its 193.073 s ending with all 126 events, but
  its source HXC `StaticTextHandler`, `StoryConfirmMouth`, vocal-volume module,
  and death/hell note-kind callbacks still carry six unsupported payload or
  callback diagnostics. The run is a failed compatibility gate despite the
  successful native exit; evidence is
  `tmp/example-full-playthrough-expurgation-build10.jsonl`.
  `ballistic` Hard reaches PlayState but its authored intro dialogue waits for
  a confirmation or skip input. The unattended build-10 full-song harness
  issued neither, so its 71 s song-end timeout is an input-automation gap,
  not evidence of a gameplay stall. It prompted a private Xvfb input-driven
  replay of the dialogue and skip paths. Baseline evidence:
  `tmp/example-full-playthrough-ballistic-hard-build10.jsonl`.
  That replay now passes for Hard: a private Xvfb `E` key skip hands off to
  gameplay, the 153.405 s song ends naturally, and 16/16 events dispatch
  without tagged interpreter errors. Evidence:
  `tmp/example-full-playthrough-ballistic-hard-skip-delayed-build10.jsonl`.
- DDTO++ has additional source-authored Story Mode dependencies outside its
  chart rows. `scripts/songs/bara-no-yume.hxc` requests conversations
  `bara-no-yume` and `bara-no-yume-end` and the `monika` video;
  `scripts/songs/libitina.hxc` requests `metaintro`. The supplied package's
  conversation directory contains only the three `epiphany` JSON files, and
  its video directory contains only `rain`, `testvm`, and `crackBG`. The
  selected owner has no missing source media to import. These story paths
  cannot pass source parity until the missing donor material is supplied;
  natural Freeplay endings do not exercise them. The `sadbf` definition also
  references absent `SadBFDies_Assets` and `MarkovGameOver` death atlases.
  Its `CustomTitleBar.hxc` requests `Paths.file('dokicon.png')` on selected
  stages and `icon16.png` on return; neither file exists anywhere in the
  supplied example root. The Baka alternate and Normal baseline runs reach
  their natural endings but correctly report the unresolved window icon.
- Wacky World Normal, Hard and Nightmare each reach natural ending with all
  106 chart events dispatched, but all three full-song gates fail on health
  icons and the donor `PVE_VideoModule`'s unsupported HXC callback bodies. The
  donor and installed icon PNGs are present; their mixed-case ids exposed a
  shared registry lookup defect that compiled in native build 18. The
  native video path has step resync and lifecycle cleanup. A private build-18
  Xvfb probe captured an actual frame of the authored `rough_vhs` chart video
  at the 0 ms event, exited successfully, and preserved default test settings
  (`tmp/wacky-video-build18/`). Replaying all three difficulties on build 18
  reached natural endings with 106/106 events each and no health-icon errors;
  all three strict gates still fail exclusively on the video-module warnings
  (`tmp/example-full-playthrough-wacky-build18.jsonl`). The donor module reports unsupported
  pause, resume, seek, focus, retry, and teardown callback bodies. Full HXC
  video-module behavior and source parity remain unverified. The earlier
  full-song process logs and results are under
  `tmp/example-full-playthrough-wacky-all-build10.jsonl`.
  **Later status:** the 24 September unsupported-body diagnostics above are
  superseded by the current shared HXC video-module adapter. Later Wacky
  offset and full-song logs show the adapter without those warnings, and
  4/4 focused adapter tests pass. Direct native invocation of
  `PVE_VideoModule.createVideo` through pause/resync/retry/teardown still needs
  a lifecycle run; the rendered chart-event video frame is a separate route.
- The ModdingPoop donor stage script has two independent code defects: line
  251 calls `cstaticthing()` although only `staticthing()` is defined at line
  444, and active `doStopSign*` calls at lines 627+ target definitions
  commented out at lines 583–620. The sound payload exists at
  `assets/images/custom_stages/cursedgation/staticSound.ogg` and in the
  selected owner namespace, but line 446 requests the absent
  `assets/sounds/staticSound.ogg` path; the current strict Hard replay fails on
  that lookup. This is a source path mismatch, not missing media.
  `gf-ex.hscript` supplies traces without animation setup. A generic
  owner-scoped sound alias is not implemented; see the path evidence in the
  [source dependency audit](../../tmp/example_mods_source_dependency_coverage_audit.json).
- The exact selected `psych/vswhitty` donor has no `bfwhit` or `bf-santa`
  character definition, sprite or matching health icon, although its charts
  request both IDs. All 28 donor character JSON files are present in the
  selected owner; the donor has no nested archive, symlink or case variant
  that would restore these actors. Other Whitty and BF variants are different
  authored identities and are not substitutes. The missing actor/icon
  diagnostics in Lo-Fight, Low-Rise, Overhead and Underground Easy are genuine
  source dependencies, even when a song reaches its natural ending. The
  exact-root evidence is `tmp/vswhitty-character-source-dependencies.json`.
- The corrected native read-only diagnostic fixture now invokes production
  Codename discovery: 49 raw Codename candidates across seven roots, 24 unique
  selected records, and 133 raw candidates across all 16 roots. It reports
  84 missing Codename character-atlas findings. The separate writer audit still
  reports three failed Codename imports and 25 chart comparison errors overall;
  discovery alone does not establish successful import.
- Bruce’s three Normal charts are present at their normalized runtime paths
  and retain their source note arrays exactly (570, 1,372 and 1,362 rows).
  Each runtime manifest selects `assets/imported_mods/psych-engine-mods-c300bd93c1`,
  the namespace calculated from the full mounted `/mods` path, not a basename
  match. All required `Inst.ogg` and `Voices.ogg` files exist and have the same
  byte sizes as their sources; the two event sidecars also match the source
  JSON. The [provenance audit](../../tmp/bruce_hotfix_owner_audit.json) is
  reproducible with [this verifier](../audit_bruce_hotfix_provenance.py), which
  requires selected-root, chart-payload, audio-metadata and event evidence.
  The owner’s `nullspace.json` and `nullspace.lua` match source and the stage
  has no media paths. This is file/config parity, not rendered visual parity:
  `nullspace.lua` still references unresolved `dadOpponent` and `fpSong` APIs.
  The static stage translator reports unsupported `setPosition()` and
  `fpSong()`, while LuaCompat preserves those runtime expressions. The standard
  Psych `noteTweenAlpha` call in the `Fade UI` event now has a shared bridge;
  Bruce still needs its offscreen full-song and visual comparison after the
  unresolved stage references are resolved.
- The Psych archive contains a complete source project (`Project.xml` version
  0.2.8), 1,276 files, 713 bundled `base_game` files, 28 songs, 78
  Psych-format charts, 11 stage definitions, 32 character
  definitions, and three videos. The charts reference eight stage IDs and 29
  character IDs and use 30 note types plus one event. The archive has no
  per-song script files, but includes 157 Haxe source files (44 relevant to
  stage/cutscene behavior); its charts rely on Psych Engine source behavior
  and the bundled base-game assets. **The following runtime counts are a
  historical 24 September snapshot, superseded by the 28 September owner
  promotion documented below:** the then-mounted runtime had paths for 71 of
  the 78 chart rows. Of those, 60 matched the
  archive's note-row counts, ten differ, and `smash` has a runtime JSON value
  whose `song` member is a string rather than a chart object. The seven missing
  chart paths are all `blazin` difficulties plus `dad-battle` Easy/Normal and
  `philly-nice` Easy/Normal. Thirty chart rows currently select the D-Sides
  imported owner; the other 48 have no `compatScripts.json`, and no row has
  archive owner provenance. Its 713 bundled base-game file paths have no
  archive owner in the live install; only 13 share an exact same-relative path
  under Psych's `Project.xml` asset-root mapping. The archive includes 148
  audio files across 27 audio directories (including a `darnell` audio
  sidecar); only 12 source audio basenames coincide under the 28 chart-song
  folders in the live runtime. `ridge` has no source audio despite
  `needsVoices=true`; `smash` also has no source audio, and its live chart is
  malformed. `blazin` has only an instrumental and `needsVoices=false`, so it
  has enough source audio for a one-stem run. `ridge` and `smash` cannot be
  full-song audio regressions from this archive alone; no replacement audio
  was inferred. The source-audio gap remains current; the unowned-chart and
  malformed-runtime-chart statements above are historical.
  At that time, these path and note-count checks did not verify audio, stage, character, event,
  cutscene, or gameplay parity. A safe
  import needs ZIP-aware private staging with `Project.xml`’s conditional
  `assets/base_game` to `assets` mapping applied only inside that staging root.
  The separate `assets/shared` tree and renamed `week_assets` and `secrets`
  trees require explicit collision review; `assets/shared` can overlap renamed
  `base_game/shared` paths. Keep charts, songs, character/stage assets and
  owner manifests in an isolated project until all 78 charts and their
  dependencies are reviewed. The owner must derive from the extracted archive
  root and must not claim the existing D-Sides-selected rows. No archive files
  had yet been extracted into or refreshed in the live install.
  A later private staging verifier checked all 78 valid chart rows, 16 event
  sidecars (254 event rows), eight stage IDs and 29 character IDs through the
  production scanner and owner manifest code. It confirmed one archive owner
  across 28 manifests, preserved a foreign `vcr.ttf` sentinel, copied no large
  media, and removed its disposable tree. The staged branch audit found 713
  `base_game` files, 263 `shared` files, three fonts, seven embed files and
  one `week_assets` readme. It still requires source Haxe stage/cutscene
  behavior, video support under the source build flag, and absent `ridge` and
  `smash` audio; no runtime parity is claimed. Evidence:
  `tmp/psych_archive_private_stage_verification.md` and `.json`.
- A read-only follow-up mapped the nine compiled Psych stage classes to all
  76 privately imported archive chart rows. Eight target HScript stages cover
  only part of the source class behavior; `PhillyBlazin` has no target stage
  script or registry entry. Missing source callbacks include stage events,
  story cutscenes, note handlers, rain shader behavior, and lifecycle hooks.
  The dependency matrix is in `tmp/psych-compiled-stage-audit.md` and `.json`.
  Stage-script presence is therefore not stage parity; a shared class runtime
  or mechanical importer path is required under this goal's implementation
  rules. A direct Haxe interpreter probe found that `StageWeek1` parses but its
  wildcard import is rejected by the owner class loader; `PhillyStreets` and
  several dependencies use currently unsupported `enum`, `final`, `using`,
  and aliased-import syntax. PlayState has no Psych `BaseStage` lifecycle host.
  The exact probe and dependency failures are recorded in
  `tmp/psych-class-runtime-feasibility.md`. A bounded owner-loader update now
  passes a focused wildcard/alias/final/StringTools fixture. On the actual
  archive, `StageWeek1` initially advanced beyond its wildcard import but
  stopped in `objects.Character` at nested `new Map<String, Array<Dynamic>>()`
  syntax; `PhillyStreets` stopped at its enum. These were historical failures
  subsequently addressed by the owner class bridge; selected source stages
  now execute in the strict native checks below. The importer retains Psych
  Haxe modules under the selected import owner;
  a disposable extracted-archive probe copied 157/157 `.hx` files with zero
  rejects and matching hashes for the two stages and `BaseStage`. That probe
  established source preservation; the later native stage checks establish
  execution for selected rows, with visual and audio parity still open.
- TAKEDOWN has no matching chart or asset in the current donor, Psych archive,
  or installed runtime. Its named regression remains unavailable for replay.

## Verification status

Source inventory and selected structural chart checks are complete. The
current consolidated matrix has 256 raw chart/difficulty rows, including one
undeclared empty DDTO++ Baka chart key. Of the 255 metadata-declared playable
rows, 173 pass selected-owner and source-note preflight in the live runtime;
82 remain structurally blocked, including 78 Psych archive reference rows not
installed in the live owner namespace. This preflight is not a gameplay pass.
The full source suite and offscreen native results are recorded in
[engine-discrepancies-verification.md](engine-discrepancies-verification.md).
They do not establish complete source behavior. Natural endings have been
verified for HL17's three Buck charts, 20/22 D-Sides rows through the strict
diagnostic gate, all nine VS Freddy rows, the six current V-Slice/Wacky rows,
and named subsets of other packages, but
the full package matrix still needs per-difficulty source visual/audio
comparison, repeat and cross-import loads, editor round trips, cutscene skip,
seeking, pause/resume, and failure recovery. An intermittent native heap abort was observed during
Future Sound HXC loading; the corrupting write is unknown. Loading/build/memory
optimization remains deferred until parity is verified. The configurable
480 FPS cap exists; sustained 480 FPS on this host and broad behavioral
equivalence remain inconclusive.

The current Codename scoring adapter accepts source rating presets and custom
ratings. An earlier full D-Sides sweep matched source notes and events
and reached gameplay on **22/22** difficulties, with **0/22** strict passes.
An installed-chart provenance audit now finds **19,174 of 34,798 D-Sides note
rows** across 52 chart files without the current Codename source-line tag;
those notes can still take the legacy actor route. The three HL17 Buck charts
had lacked this tag on all **1,923** rows; a reviewed, backed-up selected-owner
refresh now supplies it. The latest strict private sweep reaches natural ends
for all three with 0 runtime diagnostics and full event dispatch; the earlier
real-time Linkinteen replay shows the visible source player actor singing after
both early transitions. Bully Mod's 526 rows already had the tag. The D-Sides
gap still requires a separate scoped refresh and native verification.
Subsequent selected-owner changes added a real native Charter adapter,
transition script and sticker-sound import, and source HUD globals/utilities.
The latest private Darnell Hard and Spookeez Hard replay has no HUD or editor
import errors, but both still diagnosed the composer enum/type declaration and
missing transition runtime on that binary. Its protected installed files and
personal settings were unchanged. A newer private 22-chart startup sweep
reached all rows and passed 19 strictly; targeted rebuilt Bomb Bash,
Tutorial, and Ghastly replays increased the cumulative strict startup result
to 22/22.
The later selected-owner 22-row D-Sides natural-ending sweep passed 16 rows
strictly, then a backed-up generic importer/stage refresh raised the cumulative
strict result to 20/22. Blammed Easy and Normal still report three unresolved
source character IDs absent from that package. The current full serial suite
passed 1,279 tests with 61 skips, and recent Ghastly and Weiner replays passed
on the rebuilt binary. Source-behavior verification remains pending. Evidence:
`tmp/dsides-current-full-playthrough.jsonl`,
`tmp/dsides-six-post-refresh-playthrough.jsonl`,
`tmp/serial-full-tests-20260927-after-fixture-reconcile.log`, and
`tmp/recent-shared-fixes-two-row-playthrough.jsonl`.

The Psych source archive's Guns Easy row now has a strict offscreen natural
ending with its authored `Tank` compiled stage active and zero script errors.
The private receipt is
`tmp/psych-archive-real-import-v3/tank-guns-easy-current-v7.json`; this
does not establish visual/audio parity or coverage for the archive's other
rows.

The Wacky World V-Slice Normal player offset repro is now fixed in shared
character orientation: native LEFT/RIGHT hit traces changed from swapped
offsets to the donor's `[0, 5]`/`[-15, 72]` pair, with zero strict errors.
Receipts: `tmp/wacky-world-offset-before.json` and
`tmp/wacky-world-offset-after.json`. All three Wacky World difficulties then
reached natural endings with zero strict errors and unchanged protected
settings (`tmp/wacky-world-full-after-offset-fix.json`). The selected-owner
refresh later passed all three runtime rows with 106/106 due events and no
interpreter errors (`tmp/vslice-wacky-after-owner-refresh-20260929.jsonl`).
Source metadata (`data/songs/wacky-world/wacky-world-metadata.json`) lists
Normal and Hard; its chart's empty `notes.nightmare` key has 0 source and
runtime notes, so matrix row 221 is a structural placeholder, not an authored
third difficulty.

The source chart starts `rough_vhs` at 0 ms as an unmuted, HUD-hidden cutscene
with resync enabled. Its 20.84-second 1080p video, including AAC audio, and
the 153.767-second instrumental plus 145.837-second WackyCaine vocal are
present in the selected runtime and byte-match the donor. The chart also
switches stages `circo` → `pixel` (46.154 s) → `circo` (66.231 s) → `mc`
(108.261 s) → `circo` (124.957 s), with paired character swaps, 55 zooms,
28 camera focuses, flashes, lyrics, and a closing camera fade. A prior native
probe captured one frame from `rough_vhs`; full-clip video/audio sync and
audible mix, HUD restoration, and native hxvlc pause, resume, focus, seek,
retry, and teardown still need real native verification. The HXC adapter tests
cover the bridge with a fake host. Source visual/audio comparisons and editor
round trips remain open. A generic donor `StageData`
parser and a scoped, backed-up refresh corrected 30 owner-matched private
Psych archive chart stage fields. Spookeez Easy now executes the selected
`Spooky` source class and reaches a strict offscreen natural ending with
protected settings unchanged. The other refreshed difficulties remain to be
compared with source visual/audio behavior. The shared HScript class frame
fix now preserves the `PhillyTrain.sound` field when its constructor has a
same-named argument. Pico Easy, Normal and Hard each pass strict full-song
archive checks. Monster, South and Spookeez also pass all three difficulties
across the current refreshed-stage checks, with zero strict diagnostics and
unchanged settings; their Normal/Hard receipts are in the verification report.
The shared Int-backed `FlxColor` and owner-scoped class-value/recycle bridges
then cleared Blammed's source `Philly Glow` callback errors. Blammed Easy,
Normal and Hard now reach strict offscreen natural endings with unchanged
settings; each Blammed run dispatches all 119 due events. Together, the five
refreshed Psych stage songs have strict full-song passes for **15/15**
Easy/Normal/Hard rows. Receipts and historical failure evidence are in the
verification report. Source visual/audio parity, editor round trips,
pause/seek/skip behavior, and the archive's other chart rows remain open.
Thorns Easy now executes the selected archive's `SchoolEvil` compiled stage
through a strict offscreen natural ending with protected settings unchanged.
This still leaves source visual/audio and story dialogue parity unverified.
The latest automated suite passed 1,319 tests across 393 modules, with 61
skips and zero failures. A final-binary Ghastly Hard Xvfb frame samples its
up receptor, hold head, and tail at horizontal centroids within one pixel;
this is one rendered-frame alignment check, not all-note source parity.
The mounted Codename source also swaps every authored `singRIGHT` suffix pair
with its offset when player orientation requires it; the shared helper now
matches that rule for alt, dodge, loop and other suffixes. A D-Sides XML
character contains a distinct `-dodge` pair. The source helper tests pass,
while rendered pose comparison across imported characters remains open.
The private Psych archive `Satin Panties` Hard row now executes its selected
compiled `Limo` stage through a strict 96,079 ms natural ending, with 2/2
due events, zero diagnostics and unchanged settings. Indexed source-script
reads of Flixel group members use an owner-scoped bridge so the stage can
update its dancer sprites without replacing native group storage. The
remaining archive rows and visual/audio parity still require verification.
The latest full automated suite passes 1,320 tests across 393 modules, with
61 skipped and zero failures; the strict native Limo receipt above is on the
rebuilt release binary.

The isolated physical Psych archive import contains 26 songs and 76 chart
difficulties with source note-row/owner parity. The first complete offscreen
natural-ending sweep passed 67/76 strict rows; Cocoa and Eggnog
Easy/Normal/Hard failed on source `Hey!` argument and StringTools semantics,
and Stress Easy/Normal/Hard failed on a static source class field
(`tmp/psych-archive-isolated-import-v5/direct-all-76.jsonl`). Shared
compatibility fixes now pass all six Cocoa/Eggnog rows on the rebuilt binary
with zero diagnostics (`tmp/psych-archive-isolated-import-v5/replay-mall-after-hey.jsonl`).
Stress and rendered/audio/source-behavior comparisons remain open. Two
archive source rows, Ridge Normal and Smash Normal, lack packaged Inst audio.

The subsequent single-binary private Psych archive sweep passed all 76/76
imported difficulty rows through natural endings with zero strict script
diagnostics and unchanged private options
(`tmp/psych-archive-isolated-import-v5/direct-all-76-after-static-map.jsonl`).
Ridge Normal and Smash Normal remain unimported because their selected donor
has no instrumental media. Full source visual/audio parity, editor round
trips, skips, pause/seek behavior, menus and failure recovery are still open.
The separate DDTO++ Wilted Normal replay reaches its 151,088 ms ending with
34/34 events after shared sustain-swap and HXC actor lifecycle fixes. Its
initial Monika scale is 0.9 in the current native trace; strict status is
still blocked by the selected donor's missing `assets/dokicon.png` icon.

The Psych archive's 26 media-available songs and 76 difficulties are now
installed under a distinct owner-qualified namespace. The backed-up offscreen
import changed none of 517 existing chart JSON files and restored personal
options exactly (`tmp/psych-archive-live-promotion-backup/receipt.json`).
Its authored `Project.xml` title now labels 25 qualified Freeplay entries;
26 provenance records were refreshed with scoped backups and the existing
unqualified Blazin entry stayed in place
(`tmp/psych-archive-label-refresh-20260928/receipt.json`).
The refreshed matrix records 76 installed structural rows and two blocked
source rows (`tmp/example_mods_current_chart_matrix_after_psych_promotion.json`).
Live preflight finds all 76 available rows ready, and installed 2Hot Hard,
Monster Hard, and Stress Hard passed natural endings with zero diagnostics
(`tmp/psych-archive-live-sample.jsonl`). The isolated full 76-row sweep is
still the broadest gameplay receipt; complete source behavior and editor/menu
checks have not been established.

### Current combined owner snapshot (28 September 2026)

`tmp/example_mods_current_chart_matrix_after_fnas_install.json` inventories
**256 raw chart/difficulty rows** from the selected examples and archive.
The exact-owner preflight in
`tmp/example-mods-current-256-sweep-20260928/plan.txt` classifies **250
ready**, five blocked by missing donor instrumentals, and one undeclared
empty V-Slice Baka variant key. Readiness means that the installed route and
required media exist; it is not a gameplay or source-parity result.

The five missing instrumentals were checked against the mounted donors and
their source lookup rules. PERFEXION Demo1 has no song media for Extra Hard,
Extras Hard, or Gallery, and the Psych archive has no Inst media for Ridge
Normal or Smash Normal. PERFEXION's Extra and Extras scripts also reference
`music/extra_menu.ogg`, which is absent from that package. These rows remain
source-dependency gaps until those authored files are supplied.

A fresh, exact-root private import of HL17, D-Sides, and FNAS produced
three selected-owner refresh plans. The applied plans added 22 owner files,
replaced 37 verified generated files with individual backups, preserved one
unproven D-Sides Blammed camera sidecar conflict, and left the other 1,322
protected files byte-identical. Both repository and personal options retained
their SHA-256 values. The post-apply check is
`tmp/codename-base-overlay-refresh-20260928/protected-after.json`;
backup receipts are under `tmp/import-refresh-backups/`.

The release build after refresh passed 1,430 automated tests across 428
modules, with 61 skips and zero failures
(`tmp/full-suite-after-owner-refresh-20260928.log`). A refreshed FNAS Better
Clone Normal private story/practice **non-botplay** run reached natural audio
completion, dispatched 204/204 due events, and rendered the authored
post-song minigame in its captured frame. Its process had no strict script
diagnostics and neither settings file changed. The screenshot is
`tmp/codename-base-refresh-fnas-20260928/story-practice-no-botplay-after-song-end.png`;
the runner's `authoredMinigameStateObserved` field is false because its marker
parser did not identify the state name, so the frame and source script are the
evidence for that particular handoff. This does not establish all minigame
interaction or source presentation parity.

The refreshed HL17 Linkinteen Parks Buck run completed at 1× with 5/5
events and no strict diagnostics. Five transition screenshots show the
playable actor, background and HUD through the authored transitions; 83
motion snapshots include changing sing poses after the first transition.
The final black frame occurs at the source script's authored terminal hide.
Evidence is in `tmp/hl17-after-refresh-20260928/linkinteen-full-visual.*`
and the transition PNGs. This is a targeted regression check, not a
donor frame-by-frame comparison.

On the refreshed owner, Gordonteen Bucks and Huggyteen Dollars Buck also
passed 5× natural endings with 126/126 and 120/120 due events. A 5×
Linkinteen run exposed a post-song beat callback into an exiting script;
the shared PlayState lifecycle guard removed its two null-object
diagnostics. Its exact-rate replay then passed with 5/5 events and unchanged
settings (`tmp/hl17-after-refresh-20260928/linkinteen-post-end-guard.jsonl`).

The D-Sides Blammed camera sidecar is now refreshed from a uniquely matched
source package and exact owner-local fallback XML/atlas proof. The scoped
plan changed one generated sidecar, kept 1,321 other protected prior files
unchanged after all Codename refreshes, and retained both settings files.
Evidence is in
`tmp/codename-base-overlay-refresh-20260928/dsides-local-fallback-plan.json`
and `protected-after-dsides-fallback.json` beside it. Blammed's Easy,
Normal and Hard native presentation must still be checked after this change.
The latest complete automated suite passed 1,434 tests across 428 modules,
with 61 skips and zero failures.
Blammed Hard, Easy, and Normal then passed 5× natural endings with 257/257,
231/231, and 231/231 due events, zero script diagnostics, and unchanged
private options (`tmp/dsides-blammed-after-local-fallback-20260928.jsonl`).

### Strict natural-ending sweep and current failures

The first 256-row offscreen natural-ending sweep ran against release binary
`c802...` under default private settings at 20× song time. Its machine-readable
receipt is `tmp/example-mods-current-256-sweep-20260928/rows.jsonl` with
summary `receipt.json`: 164 strict passes, 86 failures, five absent-source-media
blockers, and one empty undeclared raw variant. Every inventory row was
classified. These are gameplay/runtime checks, not a source-visual parity
certificate. A test classifier counted three informational Wacky World video
adapter lines as errors; the matching native logs reached natural endings
without runtime diagnostics, and the newer focused replay passes Wacky World.

Release binary `b40ce107...` built after shared video, strumline and sidecar
adapter changes (`tmp/example-mods-post-sweep-build-20260928.log`). Its focused
eight-row offscreen replay is
`tmp/example-mods-postbuild-focus-20260928.jsonl`. Reactor Yuri Mix and Wacky
World pass; Catfight, Our Harmony and You and Me reach natural endings but
report a missing `dokicon.png` requested by donor title code. The donor package
has no such file. Our Harmony also reports a missing health icon, although
`images/icons/icon-our-harmony.png` exists in the donor and is being traced
through the generic import asset path. Your Demise VIP exits before song end
because the V-Slice pixel countdown image lookup resolves to a missing file.
Markov Lyrics still has unsupported HXC shader callback diagnostics. Libitina
crashes in OpenFL filter cloning when an opaque HXC shader token is handed to
`FlxCamera.filters`; the shared filter boundary now resolves owned tokens and
drops invalid entries, with a focused Haxe test passing, pending a rebuilt
native replay. None of these failures are counted as compatible.

The next release binary (`56ce32f4...`) built the shared filter, video,
Codename line, HScript context and countdown changes. A missing-only scoped
refresh added the donor `icon-our-harmony` PNG/XML to its selected DDTO owner;
461 prior owner files and both settings files retained their hashes
(`tmp/vslice-health-icon-refresh-20260928/applied.json`). The second focused
replay is `tmp/example-mods-postbuild-focus-v2-20260928.jsonl`: Your Demise VIP
and Wacky World pass strict natural endings. D-Sides Monster and Tutorial
reach their endings, with one shared missing `forEachAlive` method on the new
live source-line note group; that method is now implemented and interpreter
tested, awaiting another native build. The Tutorial `cancelAnimation` error is
gone. Markov Lyrics has one remaining unsupported shader pulse audio warning;
its countdown callback now runs. Our Harmony still needs owner-bound HUD icon
lookup at runtime. Libitina now reaches the shader render path, where its
donor GLSL requires a newer language version than OpenFL selects by default;
the generic shader loader is being corrected. The missing donor title icon
continues to be reported separately. This is progress evidence, not a pass.

Release binary `2939220559acc9312c622455c058bf290e9681659779d3683d6306662529c15d`
then replayed Libitina, Our Harmony, D-Sides Monster Hard, and D-Sides Tutorial
Hard offscreen at 20× with default private options
(`tmp/example-mods-postbuild-focus-v3-20260928.jsonl`). Both D-Sides rows now
pass strict natural endings. Our Harmony no longer reports its staged health
icon as missing; its only script diagnostic is the donor's absent
`assets/dokicon.png`. Libitina passed the GLSL setup and then reached a new
native crash in `Character.dance()` after a script-created actor had no
animation controller. Its donor contains `ghost-sketch.json` and the authored
`Libitina_tmp.png`/`.xml` pair; the selected owner has the PNG but lacks the
XML and a native character registry entry. The core trace is from PID 3597871
and shows `Character_obj::dance()` called by `PlayState_obj::beatHit()`. A
shared null-animation guard is now interpreter tested; the importer omission
still requires a scoped, backed-up refresh and native replay. Neither the
crash nor the missing icon is counted as compatible.

**29 September selected-owner visual refresh:** The shared V-Slice importer
now discovers safe character definitions across a selected package, including
actors created only by HXC scripts. It writes converted characters and paired
atlases into that owner's namespace and retains playable primary animations
when optional secondary sheets are absent, with explicit missing-sheet
diagnostics. A first live refresh exposed an older mixed-owner folder case:
49 qualified duplicate chart/audio folders were created. The disposable
folders were moved to a rollback area, Freeplay was restored from backup,
and all 610 pre-existing scoped files matched their SHA-256 values afterward
(`tmp/vslice-owner-refresh-20260929/`). A shared `visualOnly` ownership path
was added and tested, preserving base-song protection while allowing only the
selected root to repair its visuals. The rebuilt importer then skipped all
54 existing song entries, imported zero new charts, and copied 12 supported
assets with zero new qualified folders
(`tmp/vslice-ddto-native-visual-only-20260929/`). The final receipt proves
936 existing files byte-identical, all 62 old character registry rows
unchanged, one added `sadbf` row, and nine new files (four SadBF visual files
and five missing provenance files). Both options files and Freeplay stayed
unchanged (`tmp/vslice-owner-refresh-final-20260929/accepted-additive.json`).
The donor still lacks the `SadBFDies_Assets` and `MarkovGameOver` death sheets;
those animations remain explicitly unavailable.

Release binary `7a2c9ecaa3d8c6fd7b5bc6483937cd3335e506ac68b91ceea64d6d9cb8f340cb`
passed 1,473 automated tests across 439 modules (61 skips, zero failures).
Its private 20× natural-ending replay reached all due events for Libitina
Normal (1/1), Markov Lyrics Hard and Unfair (136/136 each), and Our Harmony
Normal (50/50), with unchanged private default settings
(`tmp/example-mods-post-owner-final-20260929.jsonl`). Both Markov difficulties
passed the strict runtime gate; the HXC shader pulse now handles numeric
sound arguments without interpreter type errors. Libitina and Our Harmony
each retain only the donor's missing `assets/dokicon.png` title-icon
diagnostic, so neither is counted as fully compatible. Source visual/audio
parity, editor/menu/cutscene interactions, switching and FPS equivalence
remain open; the package-wide rebuilt sweep is pending.

**29 September DDTO HXC dependency audit:** The last native Auto report's
48 static HXC diagnostics are partitioned by source reachability. One was a
shared resolver miss for `Paths.music(key)` when the donor keeps music at
`shared/music/<key>/<key>.ogg`; the importer now maps that layout to the
runtime's flat music alias, and the focused extracted Haxe test passes.
The 48 entries include 18 from unselected `hall` stage scripts, six from
note-script branches not selected by the audited charts/styles, nine from
countdown/death references in songs skipped as duplicates in that import
batch, two resolver/target false positives,
and 13 direct requests for absent donor files in conditional menu/module
paths. The `sadbf` death sheets and `dokicon.png` remain concrete blockers
on their reached paths. A generic selected-stage filter now restricts warning
eligibility without removing source references used for copying. The raw
warning count is not a count of active failures. No absent donor bytes were
synthesized.

The new strict 256-row sweep started on the same release binary. Its first
13 authoritative rows are saved in
`tmp/example-mods-final-256-sweep-20260929/rows.jsonl` (which also contains
a superseded no-input Ballistic Easy timeout); rows 13–59 used private
default-setting dialogue input and are saved in
`rows-from-13-with-dialogue.jsonl`. This run is in progress and the
results cannot establish source visual or audio parity by themselves.

The next release build (`b39e89c3...`) ran the selected DDTO Auto refresh
again under the runtime lock. It skipped all 54 existing songs, imported and
failed none, reduced static diagnostics from 48 to 29, retained the valid
overlay as `missing-merge-base`, and added the nested-source music's flat
runtime alias. A scoped backup proves every one of 797 existing owner and
protected files unchanged; no chart/audio duplicate was introduced
(`tmp/vslice-ddto-after-planner-backup-20260929/`,
`tmp/vslice-ddto-after-planner-native-20260929/`). Gameplay and menu
dependency gaps listed above remain open.

**29 September Nightmare Vision source and native receipt:** The separate
Nightmare Vision installation has 60 song folders across its new and old
content packs. Of 194 chart-shaped JSON envelopes, 180 are chart payloads and
14 are `events.json` sidecars. The source menu declares Easy, Normal and Hard;
four extra raw difficulty keys remain source files but are not menu choices.
An isolated native import installed all 60 songs with no failed imports or
final missing dependencies, preserving all 180 donor chart files and live
export data (`tmp/nmv-native-import-report-20260929/import-preparation.json`,
`tmp/nmv-mounted-import-audit-passing-20260929.log`). Four chart payloads
declare a third playfield, which the current native gameplay cannot yet run;
those selections are explicitly filtered and reported. Old-pack Fresh Normal
passed a 50× offscreen natural-ending check with 4/4 due events and zero
diagnostics (`tmp/nmv-private-fresh-native-20260929.json`). Package-wide
normal-speed visual, audio, scripting and editor parity is not yet verified.

**29 September declared-row completion sweep:** Matrix rows 180–241 were
preflighted and run offscreen at 50× with default test settings. All 62
reached natural audio end and dispatched every due event. The original strict
gate returned 51 passes and 11 failures; eight are DDTO++'s absent donor
`dokicon.png`, one is Cursed Expurgation's authored script errors, one was a
completion-observer false timeout on a direct Freeplay return, and one was an
intermittent native allocator abort after Try Harder completed. The generic
observer fix passed completion-only and strict handoff replays; Try Harder
passed a 5× and three subsequent 50× replays, but the original abort remains
unexplained. Receipts and limits are in
`tools/reports/engine-discrepancies-verification.md`. These completion runs
do not count as source visual/audio/script parity across every difficulty.
The subsequent full automated suite still has one failing mounted auto-import
scanner module: an intermittent native SIGSEGV while reading a previously
validated Psych chart row. Ordinary and GC-debug isolated scans each passed
once, but the original core does not identify a safe shared fix. The scanner
failure remains an open verification blocker.

### Focused ownership integration and evidence reuse — 2026-09-29

The reusable natural-ending ledger confirms 237/242 historical endings by
runtime chart path and difficulty, independent of shifting matrix indices.
This covers the declared matrix above, not the separate Nightmare Vision
inventory, and does not establish source parity. Missing endings remain Extra
Hard, Extras Hard, Gallery Normal, Ridge Normal and Smash Normal. Failed
diagnostics remain recorded even where a song reached its natural ending.

Shared note ownership changes preserve live script changes to `mustPress`
for ordinary charts while retaining normalized Nightmare Vision actor and
autoplay metadata. An offscreen Ugh Hard replay on the rebuilt engine passed
with the source's 256 player / 270 opponent head notes, all 11 events, natural
ending, results dismissal and Freeplay handoff. Third NMV playfields remain
explicitly unsupported. The 76 installed Psych archive charts now receive
the source ownership comparison using the supplied unpacked source tree.

The new integration suite passed 1,598 tests across 467 modules, with 65
skips and no failures. Its ordinary mounted scan passed; the earlier
intermittent scanner/allocator faults remain unresolved. See the current
sections of `engine-discrepancies-verification.md` for exact receipts,
provenance and limits. This supersedes the preceding suite's failed status
without treating an intermittent passing run as a defect fix.

### Nightmare Vision layout follow-up — 2026-09-29

The shared difficulty loader retains NMV playfield settings, and receptor
centering now follows the source ModManager. An isolated normal-speed Fresh
Normal probe checked eight initial hitbox/rendered receptor centers against
the source formula with no mismatches. This is narrow geometry evidence.
Source audit exposed missing NMV `.hx` script discovery/execution: previous
60-song imports and crash-free runs do not verify those scripts. NMV scripting,
extra playfields, custom skins and track-swap audio remain open compatibility
work. See the current verification report for build identity and receipts.

Direct Nightmare Vision gameplay-script discovery now emits unsupported-script
and incomplete-inventory diagnostics during import. Its saved audit contains
194 chart-shaped documents (including nonselectable helpers), with 46/27 unique
selected direct paths for the new/old packages including base fallbacks. This
is an inventory improvement; execution remains unimplemented. Six focused
discovery tests and the 1,607-test integration suite pass. See the verification
report for the exact scope and receipts.


### 2026-09-29 — default results regression: Codename Dusk Hard

Shared results/callback/Animate/transition fixes verified by a normal-speed,
private offscreen full-song run. All 386 player heads counted (380 Sick, 6 Good),
score 133250 and max combo 386 matched gameplay, all 372 events dispatched,
results rendered above the gameplay HUD, and Accept returned cleanly to Freeplay.
Evidence: `tmp/dusk-results-verified-1x-20260929.json` and its assertions and
6s/14s screenshots; binary `1289bb4ff9ce18c4a1af78d530eb8681b4759fc1ea71ec1b1cd3df853c8d1587`.
This closes the reported results case, not package-wide source parity. That
batch's final suite reproduced the previously recorded import-scanner exit 245;
later passing scanner runs have not resolved its intermittent cause.

### 2026-09-29 — shared native-property callback coverage

The HXC incoming-note ownership and character screen-position bridges now read
native properties correctly. Extracted-method regressions reproduce both old
failures. A private offscreen probe passed 21 checks against binary
`dbed0413e030d947fb5053986f90158b5a0eab74752ade54b020bdb52e4740d8`,
including actual native Notes, source ownership overrides, missing-GF fallback,
and a script-returned native point with a zero coordinate. Receipt:
`tmp/hxc-note-owner-native-20260929.json`. No donor content or personal settings
changed. These checks establish the shared callback contracts; existing song
rows retain their recorded builds and limitations, with no new full-song or
package parity claim.

### 2026-09-29 — Nightmare Vision execution core

Nine focused script-discovery/interpreter/group tests pass. The new core
matches the supplied dispatcher over 2,048 return-flow combinations in each
of the two HScript position modes. Public declarations, live state fields,
source scope precedence, lifecycle ordering, failure recovery and release are
tested independently. Gameplay integration, module imports/typedefs, API
bindings and source cancellation call sites remain pending, so no existing
NMV song/difficulty row is upgraded to script-compatible. Evidence:
`tmp/nmv-script-core-tests-20260929.log` and the verification report.
The unchanged mounted `new-dsides/scripts/Events.hx` additionally passed 22
assertions per interpreter mode using test actor/camera/tween bindings
(`tmp/nmv-events-core-20260929.json`). Its source hash was preserved. This is
real-script contract coverage, not native camera or tween-fidelity evidence.
The integration suite passed 1,620 tests, with 65 skips and no failures.

### 2026-09-30 — Nightmare Vision module grammar follow-up

The independent runtime now uses pinned Iris 1.1.3 with owner-local import and
using bindings, plus source adapters for string interpolation and key/value
loops. All 101 release Haxe scripts parse, including menus/plugins and the
73 inventoried direct gameplay scripts. Receipt:
`tmp/nmv-iris-all-scripts-parse-20260930.json` (paths and input hashes).
The unchanged Events script passes its 22 checks in both position modes, and
the unchanged Completion script passes import/callback/reload/owner-isolation
checks with test save/plugin bindings. These are interpreter contracts, not
native gameplay or plugin fidelity. The supplied source's newer ModPlugin API
has been audited against release PluginsManager calls; host integration and
source lifecycle differences remain open. No chart status is upgraded.

### 2026-09-30 — Nightmare Vision native main-group integration

The engine now hosts the selected NMV owner's stage/global/character/song
scripts through its separate Iris interpreter. Stage metadata lookup/import
repair and source easing aliases are implemented. A private missing-only
refresh added 20 stage JSON files with 330 protected files unchanged; the old
package's 21-file preview has not been applied. No live NMV refresh was made.

On binary `7e4499df18170d84438ad5023253dc1d7e8d07ed47ec6958424c80967c8a796f`,
the normal-speed offscreen check passes real Events camera/tween behavior,
main-group lifecycle dispatch and mod-ending precedence. Native testing also
found and fixed swallowed interpreter errors caused by enum catch handling.
Receipts: `tmp/nmv-gameplay-host-native-20260930/` and
`tmp/nmv-stage-metadata-private-refresh-20260930/`.

This is shared-system evidence, not a completed chart row. Missing preset APIs,
plugins, stage rendering/character groups, event and note-type script groups,
remaining hooks and multi-playfield behavior still prevent NMV compatibility.
The receipt retains unresolved diagnostics. Full-song endings, visual parity,
editor/switching checks and FPS parity remain unverified on this integration.


Integration evidence for that same build: 1,640 automated tests, 65 skips,
zero failed modules (`tmp/full-tests-nmv-gameplay-host-repaired-20260930.log`).
The normal-speed main-group camera/error/ending probe also passes at 60, 240
and 480 FPS caps with equal step/beat counts; see
`tmp/nmv-host-fps-summary-20260930.json`. These checks do not upgrade any
chart to full source parity. All 330 protected private files remain unchanged
following the refresh and native tests.


## 2026-09-30 — Nightmare Vision source APIs and asset retention

Shared importer/runtime changes retain the selected content tree plus its
explicit engine assets under an isolated `__nmv_core` subtree. Core-only
imports avoid duplicate script staging. Runtime lookup follows owner/core
precedence, including core-only calls and distinct core script identities.
Added source constants, color helpers, shader construction, camera-position
and snap helpers, and an owner-local ClientPrefs data view.

The canonical build completed (`tmp/nmv-source-apis-build-20260930.log`).
Focused NMV checks passed **43 tests in 20 modules**; the additional importer
integration checks passed **10 tests**. The first full suite exposed a stale destination-variable assertion and a
wrapper timeout. Their combined 20-test targeted rerun passed; aggregate
evidence and the newer render-batch checks are in the verification report.

The private-only refresh added **1,940 files / 1,059,146,438 bytes**, with
**350 existing files unchanged**, including chart metadata and personal
settings. Every added file was checked against its donor hash. Preview,
backups, protected hashes, and receipt are retained in
`tmp/nmv-assets-private-refresh-20260930/`. The importer itself uses
non-overwriting copies. No live import or donor content was edited.

The native source-API probe now passes after the shared zIndex bridge and a
corrected shader-uniform fixture. Four real stage sprites are created and the
attached shader uniform advances, with no shader compile errors. Twelve
source/import diagnostics remain, especially plugin/modifier/HUD APIs. No new
chart/difficulty is promoted to source-compatible by this implementation.
Known remaining Paths differences include GPU upload policy, sound cache
lifetime, and source missing-media fallback (the adapter currently diagnoses
and throws rather than returning the source logo/beep). HUD, plugin, automatic
camera/section hooks, event/note-type groups, and source sprite layering remain
open. Preference data support does not imply all native preference effects.

Integration run: **1,649 tests across 493 modules, 65 skips**, with two
failed modules (`tmp/full-tests-nmv-source-apis-20260930.log`). One was the
stale importer destination assertion, independently repaired and passed.
The other was the outer 300-second timeout in the mounted diagnostic test,
which includes both a separately bounded 300-second cold build and a
300-second scan. The wrapper now allows both phases plus startup/cleanup;
source count assertions remain unchanged. The targeted rerun passed all
20 tests (`tmp/nmv-source-apis-suite-recheck-20260930.log`).

Post-build integrity: 349 protected files remain byte-identical. During the
desktop build/play session, live options gained `normalizeSongAudio:false`
where it was previously absent; all existing personal option values remain intact.
The live settings file was not restored over the user's session. See
`tmp/nmv-assets-private-refresh-20260930/post-build-integrity.json`.


Final render-batch integration: **1,656 tests / 495 modules / 65 skips**.
The one mounted counts-scan timeout in the final run passed unchanged on an
isolated 205.618-second retry. See `engine-discrepancies-verification.md` for
the exact logs, separate native presentation/completion receipts, and limits;
this does not mark any package fully source-compatible.

2026-09-30 NMV follow-up: the shared plugin/save/callback/HUD integration has
focused interpreter checks, but its build and native probe are pending the
desktop runtime lock. No song/difficulty coverage status has been promoted.
The retained package still needs menu, utility, event/note-type, modifier and HUD
popup behavior; see the verification report's in-progress integration section.


NMV plugin/HUD follow-up verification: the 1,667-test integration run passed,
and the 1x native source-API assertions passed on binary `83f6058e…`.
The native receipt retains 15 distinct unresolved diagnostics, including a
repeated missing Mods-context callback. This is API evidence only; no package or
song/difficulty was promoted to full source parity. The alpha menu was separately
captured offscreen with zero diagnostics and the CammieEngine v0.0.1 label.


#### 2026-09-30 NMV source-context evidence

The shared Mods/Difficulty/Conductor/window/path adapters now pass the extended
normal-speed native API probe; per-frame missing-Mods errors are resolved. The
new evidence is `tmp/nmv-source-apis-native-20260930-release-facing/receipt.json`.
It retains six unresolved diagnostics (including the donor's missing click sound)
and does not establish song/difficulty parity. Inventory compatibility statuses
remain unchanged; see the verification report for scope and current build hash.
