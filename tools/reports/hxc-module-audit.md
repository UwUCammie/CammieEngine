# HXC module-body audit

This is a read-only audit of the mounted corpus at
`/run/media/cammie/External Storage/FNF-Example-Mods`. It does not edit donor
charts or scripts and does not require a build or game launch.

The selected auto-import diagnostic baseline recorded before the Round 17
overlay tranche was:

| diagnostic | before | after |
| --- | ---: | ---: |
| `hxc-unsupported-hxc-module-body` | 10 | 3 |
| `hxc-unsupported-hxc-callback-body` | 4 | 3 |
| `unsupported-hxc-script` | 51 | 0 |
| `hxc-hxc-module-adapter` | 40 | 41 |
| `hxc-hxc-lifecycle-adapter` | 156 | 157 |

The current post-Round 17 selected counts are recorded in the Round 17 section
below; the historical table above is retained for the earlier tranche audit.

The selected auto-import scan is the authoritative diagnostic set above. The
separate mounted 224-file inventory recorded before Round 17 covered every HXC
file and reported 3 unsafe callback bodies, 4 module-body findings, and 100/42 safe module
callbacks/files; its generated adapters remain 177/177 parseable. The full
inventory and selected discovery set differ because the latter counts only
records chosen by auto-import.

Round 14 starts from the post-DDTOModifiers selected 10/4/0 result and ends at
the following exact selected counts:

| diagnostic | tranche before | tranche after |
| --- | ---: | ---: |
| `hxc-unsupported-hxc-module-body` | 10 | 4 |
| `hxc-unsupported-hxc-callback-body` | 4 | 4 |
| `unsupported-hxc-script` | 0 | 0 |
| `hxc-hxc-module-adapter` | 40 | 40 |
| `hxc-hxc-lifecycle-adapter` | 156 | 156 |

The remaining character-gap diagnostics in the after scan are partitioned as:

| diagnostic | after |
| --- | ---: |
| `hxc-unsupported-hxc-character-base` (resolved inherited donor hook) | 0 |
| `hxc-unsupported-hxc-character-hook` (direct unsafe hook / unresolved base) | 0 |

The character reduction is limited to hooks whose semantics are represented by
the live native Character / PlayState bridge. The generic screen-position
adapter preserves the FlxObject base result and donor animation offsets; the
generic game-over adapter loads literal Sparrow animation records through
Character-owned frames and offsets. Safe wrapper/base callbacks remain emitted
and executable; generated-HScript parseability is not used as a substitute for
either gap. The mounted inventory now reports 3 unsafe callback bodies and 4
module-body findings, with 100/42 safe module callbacks/files and 177/177
generated adapters parseable.

The mounted `bf-pixelbar.hxc` suffix tranche lowered the selected
`unsupported-hxc-script` count before the current compatibility tranche. Its
`onCreate` callback is executable: assignments to the donor
`GameOverSubState.musicSuffix`, `GameOverSubState.blueBallSuffix`, and
`PauseSubState.musicSuffix` fields are lowered to the central
`HxcCompatRuntime` adapter. Native game-over loss/start/end audio and pause
music resolve those suffixes only when the corresponding asset exists, with
the existing pixel/default fallback retained. This is a bounded engine ABI,
not a song-specific bypass; other donor substate members remain diagnosed.
The current selected module-body/callback-body counts are 3/3, and the
character-base/direct-hook counts are now 0/0 after the generic death-overlay
tranche below.

The removed module-body diagnostics include TAKEOVER's `FullPause.hxc`,
HatsuneMiku's `Zoom2.hxc`, the newly rooted `yo.hxc`, and modules whose
construction now uses the isolated HXC save/current-chart adapters.
`FullPause`'s
`ddtoStages` array is a literal, its pause/resume callbacks only touch seeded
`FlxTimer`/`FlxTween` managers, and its retry callback is now dispatched by the
native restart path. `Zoom2` uses the live `currentSong`, camera zoom/follow,
camera-tween cancellation, and `curStep` aliases. Its two callbacks therefore
execute against the native PlayState rather than merely parsing. The `yo`
module is also now fully rooted: its named-property access is lowered to the
live `StageHelper.elements` map and its callbacks use seeded note/countdown
helpers. The character-registry tranche additionally lowers
`CharacterDataParser.listCharacterIds().contains(...)` to the native
`Character.characterExists` registry, constructs actors through the native
`Character` constructor, and routes the real `PlayState.boyfriend`/`dad`/`gf`
slot through canonical `PlayState.switchToChar` semantics. That native path
updates icons, control flags, HXC character scopes, health colours, and layer
order; reset actors inherit the existing slot position when their constructor
coordinates are still zero. Donor `set_characterType` calls become bounded
role hints and `initHealthIcon` updates the native icon when the role is known;
both avoid calling missing native Character methods. The fullscreen tranche also
routes TAKEOVER's `FullscreenOff.hxc` through a native window adapter: it clears
`FlxG.fullscreen`, restores the native `RatioScaleMode`, and dispatches the live
`gameResized` signal. No donor `FullScreenScaleMode` singleton is exposed. The
full inventory now reports 100/42 safe callbacks/files, up from 89/37. These
callback-level adapters are
reported separately even when the containing module still has an unsafe
constructor or hook. The other
module bodies remain diagnosed when they need donor-only roots or members such as
unsupported `Preferences` fields, `currentChart` metadata without a native
SwagSong field, highscore/tally lookups, or unrouted
state-change hooks. `Save.instance` key/value access,
`DokiPreferences.getDokiSave()`, direct `Preferences.downscroll`, and
`ModuleHandler.getModule(...).scriptCall/scriptGet` are translated only through
the namespaced store/module-scope adapters; nested donor option objects and
highscore lookups remain unsafe.

Freeplay capsule payloads now have a bounded shallow view: the nested
`freeplayData.levelId`, `songCharacter`, and `data.id` reads used by
`FreeplayFixes.hxc` are covered by the native payload adapter. CatFight popup
selection, icon changes, current variation, and default confirmation route
through native `FreeplayState` methods without exposing `grpCapsules` or the
donor state graph. The donor TAKEOVER `weekType` overlay atlas still has no
destination-native asset surface, so that visual-only helper is an explicit
safe no-op rather than a fabricated asset. Five callback bodies and twelve
aggregate module findings remain diagnosed elsewhere in the 224-file corpus.

The historical selected `unsupported-hxc-script` count moved from 51 to 49
after the character-registry and fullscreen adapters; the character/module
tranches lower it from 49 to 0 by composing mounted costume wrappers, generic
character hooks, and the bounded Freeplay views through native bridges. Parsing generated HScript is not treated as
proof of module semantics. The earlier inventory's increase from 40 to 51 was
intentional: the seeded-lifecycle gate retracts parse-only runtime claims for
files whose generated fragments still contain no safe lifecycle or event
adapter. The selected module-body count previously fell from 21 to 13 because the
character-registry, fullscreen, current-chart, isolated-store, direct
module-call, and native-field alias paths execute.
Round 11 then lowers that selected count from 13 to 11 through the bounded
CountdownGF, DDTO game-over, and costume-menu lifecycle adapters; Round 12
removes the final two unsupported-script findings while retaining unrelated
partial-body diagnostics.

The adapter also accepts the native zero-argument `FlxTypedGroup` container
initializer used by imported module state, and seeds the concrete
`FlxColor`/`FlxStringUtil` utility classes. These are deliberately narrow
initialization/data adapters. Generated HXC scripts receive one
`HxcCompatRuntime.openStore(...)` view per imported donor root; it is in-memory,
namespaced, and exposes only key/value operations plus a no-op `flush`.
The latest general PlayState-field adapter also roots native `needsReset`,
`timeTxt`, and `members` chains. This makes MikuScore's state-change setup and
GlassTimeBar's time-bar setup executable; donor-only chart metadata remains
diagnosed.
The runtime now also provides explicit fixed-rate, score-text/cutscene-camera,
per-song tally, rank, strum-opacity, window-title/icon, and named runtime-shader
aliases. Tally `totalNotesHit` is derived from native raw
`totalPlayed - misses` rather than weighted accuracy, while `maxCombo`
is observed and reset per song/retry. The rank adapter now uses the native
threshold implementation: null/zero notes returns null; an exact all-sick
tally returns `PERFECT_GOLD`; otherwise completion is clamped and classified
at 1.0/0.90/0.80/0.60 as `PERFECT`/`EXCELLENT`/`GREAT`/`GOOD`, with lower
results `SHIT`. Lowered `Scoring.calculateRank` calls emit the informational
`hxc-rank-adapter` diagnostic rather than the former unsupported warning. The
adapter does not expose donor persistent score tables. Unsupported chart
metadata and V-Slice menu/freeplay/costume graphs remain unsupported until
their live engine semantics are implemented.

The mounted pass also fixed a safety-gate alias boundary: a local such as
`var dadIcon = PlayState.instance.iconP2` is a field value, not another
PlayState root. Only assignments ending at the direct `PlayState.instance` or
`currentPlayState` object are now treated as PlayState aliases. This exact
native-field distinction makes TAKEOVER's `IconColoredHealthBar.hxc` and
HatsuneMiku's `yo.hxc` executable without widening object reflection; their
character/icon chains remain rooted in the live PlayState/Stage helpers.

Regression coverage:

* `test_module_literal_state_and_retry_lifecycle_are_executable` checks the
  safe and unsafe module fixtures and parses generated HScript.
* The mounted 224-file HXC inventory checks parseability and exact current
  counts for unsafe callback bodies (0), safe callback/file coverage (101/42),
  and module-body findings (1). The selected auto-import discovery set records
  current counts of 0 module-body, 0 callback-body, and 0 unsupported-script
  diagnostics; character-hook diagnostics remain empty (0 inherited-base, 0
  direct-hook). Its test asserts exact selected counts,
  including 41 module adapters, 156 lifecycle adapters, one pause-overlay
  adapter, and zero unsupported
  payload findings, while retaining the routed note-kind floor.
* Mounted and synthetic callback fixtures cover score/tally/rank reads, fixed
  icon playback rate, retry-stage opacity, window title/icon calls, fullscreen
  and resize dispatch, and the named runtime-shader constructor. Each generated
  adapter is parsed before it is considered usable.
* The mounted `Zoom2.hxc` fixture checks its two callbacks and generated HScript
  against the live camera/song aliases.
* Synthetic and mounted `ChangeCharacterHandler.hxc`/
  `CharacterResetHandlerCL.hxc` fixtures parse the generated registry/factory
  adapters, assert their lifecycle bodies are safe, verify unknown native ids
  remain false, and assert donor files are unchanged. Donor-only stage data,
  menu graphs, and chart variation metadata remain diagnostics.
* Synthetic three-level character inheritance asserts ancestor -> direct base
  -> wrapper lifecycle order exactly once and wrapper state-initializer
  precedence. Mounted costume wrappers assert literal constructor routing,
  inherited `defaultColor`/`missColor` state, and execution across
  `onCreate`/`playSingAnimation`/`playAnimation` using the native actor bridge.
  Rank fixtures cover null/zero-note, all-sick, perfect, and just-below each
  official threshold.
* The mounted `bf-pixelbar.hxc` regression executes its three suffix writes
  through `HxcCompatRuntime`, verifies the generated adapter parses and runs,
  and checks reset plus missing-asset fallback behavior.
* The auto-import harness checks the recorded current counts and rejects any
  regression beyond them while allowing future adapters to reduce the gaps.

Round 11 mounted-module evidence (2026-09-18): the selected auto-import
diagnostic pass was captured before and after the centralized lifecycle
adapters. `unsupported-hxc-script` moved 4 -> 2, unsupported module bodies
13 -> 11, and unsupported callback bodies 11 -> 9. The HXC module-adapter
count moved 40 -> 42 and the lifecycle-adapter count 156 -> 158. The three
requested files are covered: `CountdownGF.hxc` was already analyzer-safe and
now gets an isolated `gfCountdown=true` store default plus a runtime callback
regression; `DDTOGameOver.hxc` now routes its complete donor graph through the
native `GameOverSubstate` boundary; and `CostumeMenuButtonv2.hxc` now routes
its menu insertion through the native `MainMenuState` boundary. The donor
`images/mainmenu/PleaseKrillMe.png/.xml` atlas exists, but is not currently in
this destination's native asset scope, so the menu action uses a native
Freeplay-frame fallback and retains an explicit visual-fidelity gap. The two
genuine selected unsupported scripts remaining are
`CatFightFreeplayFix.hxc` (donor capsule/update graph) and `FreeplayFixes.hxc`
(donor capsule/difficulty graph). DDTO's donor actor graph and the costume
atlas/menu collection remain unexposed to imported HScript; missing native
assets or unknown lifecycle targets are no-ops. `tools/tests/test_hxc_round11_modules.py`
parses all three generated adapters, executes CountdownGF's THREE/cancel/GO
semantics, proves partial DDTO patterns remain blocked, and verifies donor
bytes are unchanged. No build or game launch was performed.

Round 12 mounted-Freeplay evidence (2026-09-18): the two remaining mounted
unsupported module scripts are now covered by namespace-safe native adapters.
The selected auto-import counts changed exactly as follows:

| diagnostic | before | after |
| --- | ---: | ---: |
| `unsupported-hxc-script` | 2 | 0 |
| `hxc-unsupported-hxc-module-body` | 11 | 11 |
| `hxc-unsupported-hxc-callback-body` | 9 | 5 |
| `hxc-hxc-module-adapter` | 42 | 44 |
| `hxc-hxc-lifecycle-adapter` | 158 | 160 |

The module-body total is an aggregate over the selected discovery set and is
unchanged because the remaining 11 findings belong to other donor-only module
graphs; both targeted modules now analyze as `moduleSafe` and
`moduleInitializationSafe`. `CatFightFreeplayFix.hxc` now routes its
CatfightPopup hand-off, namespaced `catfightIsYuri` write, and native song
selection through the bounded FreeplayState boundary. `FreeplayFixes.hxc`
retains its authored DDTO level-id list and routes lifecycle icon mappings
through shallow native capsule views. Its donor TAKEOVER week-type atlas
overlay has no destination-native surface, so that custom-display helper is a
safe no-op fallback rather than a fabricated asset or donor graph. The native
Freeplay state owns popup consumption, controls, and chart loading; imported
scripts never receive `grpCapsules`, variation objects, or donor state graphs.

The full mounted 224-file HXC inventory correspondingly moved from 9 to 5
unsafe callback bodies and from 98/43 to 102/45 safe module callbacks/files;
its aggregate module-body gate remains 12. `tools/tests/test_hxc_round12_freeplay.py`
parses both mounted generated adapters, verifies the strict unscoped-state
no-op boundaries, rejects partial CatFight/Doki graph patterns, and proves
both donor files are byte-for-byte unchanged. No donor chart/script/asset was
edited, and no build or game launch was performed.

Round 13 mounted/synthetic visual-asset evidence (2026-09-18): the two
documented HXC visual gaps now use one engine-level static-reference planner.
`HxcAssetPlanner` reads only HXC files below bounded `scripts`/`data` families,
collects literal `Paths.image`, `Paths.getSparrowAtlas`, and packer/media
lookups (including one-hop literal atlas arguments such as
`createMenuItem(..., 'mainmenu/PleaseKrillMe', ...)`), and feeds the existing
non-overwriting copy boundary. `ModuleFunctions` resolves those references
against the selected donor and writes only their PNG/XML/media companions below
the selected `assets/imported_mods/<namespace>` manifest root; it never walks or
edits donor media.

The native CostumeMenuButtonv2 bridge now asks that selected root for
`images/mainmenu/PleaseKrillMe.png/.xml`, uses the scoped atlas when complete,
and retains the native Freeplay-frame fallback plus `[hxc-asset-fallback]`
diagnostic for a missing/partial atlas. The native Freeplay view now owns a
small week-type visual slot; FreeplayFixes callbacks push their manifest root
for the duration of dispatch and resolve
`images/freeplay/freeplayCapsule/takeoverweektypes.png/.xml` through the same
scope. Missing media is hidden with one explicit diagnostic rather than falling
through to a sibling import or fabricated texture. Mounted TAKEOVER evidence
contains the `PleaseKrillMe` PNG/XML and the FreeplayFixes literal reference;
the week-type media is absent from the mounted donor, so the missing-asset
diagnostic path remains covered by synthetic fixtures.

Focused evidence command (no build/launch):
`TMPDIR=$PWD/tmp python3 -m unittest tools.tests.test_hxc_visual_assets_round13 tools.tests.test_hxc_round11_modules tools.tests.test_hxc_round12_freeplay tools.tests.test_foreign_script_runtime_integration`
completed 26 tests with `OK`. The synthetic planner fixture proves duplicate
literal references collapse, dynamic expressions are not guessed, one-hop
literal atlas aliases are found, and unrelated media is not part of the plan;
the mounted fixture proves both documented TAKEOVER reference spellings and
leaves donor bytes unchanged.

Round 14 mounted/synthetic module evidence (2026-09-18): six remaining
engine-level module bodies are now routed through generic native boundaries.
Wacky lyrics and vignette helpers use the PlayState-owned lyric/shader/tween
surfaces; TAKEOVER sound-tray customization is an allow-listed optional tray
hook with a native no-op fallback; Discord presence values use bounded metadata
and a native timestamp; Doki preferences use the namespaced option store; and
Doki menu update/state-change/redirect operations use optional native hooks
instead of donor menu collections. No donor class name or chart edit is used
to select these routes. The mounted generated adapters parse, the synthetic
lyric/vignette callbacks execute through fake native hosts, and all six donor
files remain byte-for-byte unchanged.

The selected scan now reports exact counts of 4 module-body findings, 4
callback-body findings, 40 module adapters, and 156 lifecycle adapters. There
are no `hxc-unsupported-hxc-payload` findings. The mounted inventory is
177/177 parseable with 4 unsafe callback bodies, 5 module-body findings, and
98/41 safe module callbacks/files. `test_hxc_round14_modules.py` covers both
the mounted adapters and the synthetic execution boundary; no build or game
launch was performed.

Round 15 mounted/synthetic death-overlay evidence (2026-09-18): the final
direct HXC character hook is now lowered through a generic engine boundary.
Literal `createSparrow` references (including one-hop string aliases) enter
the existing `HxcAssetPlanner` and selected manifest copy namespace. Runtime
character atlas loading accepts that manifest root and refuses to fall through
to global `Paths` when the scoped PNG/XML pair is incomplete. `GameOverSubstate`
owns opaque overlay handles, safe animation/alpha/position/camera operations,
and deterministic cleanup; temporary replacement characters rebind their
boyfriend HXC scope until the substate is destroyed. Imported window-close
requests are logged once and rejected. Variation reads use a generic runtime
alias whose default is the empty string. The synthetic and mounted
`bf-doki.hxc` fixtures are byte-for-byte read-only, and generated adapters
remain parseable; no build or game launch was performed.

Round 16 mounted/synthetic song-credit evidence (2026-09-18): the complete
TAKEOVER `Credits.hxc` `onSongStart` body is recognized structurally and lowered
to bounded native PlayState banner operations. The adapter accepts song name,
artist, pixel mode, and a validated literal icon key; it keeps pause/resume and
retry cleanup on the existing lifecycle path. `songCredits/*` references are
planned only from safe literals and resolved below the selected manifest root;
missing or incomplete icons fall back to text without probing donor or global
asset trees. The synthetic and mounted fixtures execute/parse the generated
adapter, reject a dynamic icon graph, plan the mounted five-icon set, and verify
the donor file remains byte-for-byte unchanged. The exact selected delta is
module bodies 4 -> 3, callback bodies 4 -> 3, module adapters 40 -> 40, and
lifecycle adapters 156 -> 156. The mounted inventory is 177/177 parseable with
unsafe callbacks 4 -> 3, module findings 5 -> 4, and safe module
callbacks/files 98/41 -> 99/41. No build or game launch was performed.

Post-Round 16 mounted HXC reconciliation (2026-09-18): the generic
literal-disabled `DDTOGameOver.hxc` boundary changes no module-body,
callback-body, or payload findings. The current selected baseline is 3
module-body, 3 callback-body, and 0 unsupported-script diagnostics, with 41
module adapters and 157 lifecycle adapters. The mounted inventory remains
177/177 parseable with 3 unsafe callback bodies, 4 module-body findings, and
100/42 safe module callbacks/files; no unsupported HXC payload diagnostics are
present. No build or game launch was performed.

## Exact remaining selected diagnostics (post-Round 16 baseline)

The post-Round 16 selected scan had zero `unsupported-hxc-script` findings, but it
does not treat that as proof that every body is executable. The three partial
module bodies at that historical baseline were:

* Hatsune Miku `scripts/ui/MikuMainMenu.hxc`;
* TAKEOVER `DokiMainMenu.hxc` and `DokiPause.hxc`.

The three partial callbacks at that historical baseline were MikuMainMenu
`onUpdate`, DokiMainMenu `onUpdate`, and DokiPause `onSubStateOpenEnd`.
Character-hook diagnostics are now empty; any future direct-hook warning
should be treated as a regression of the generic overlay bridge.

Round 17 bounded native main-menu overlay evidence (2026-09-18): the two
remaining mounted main-menu graphs are now recognized by a filename-independent
typed `HxcMenuSpecData` contract. Hatsune Miku's Module graph and TAKEOVER's
MusicBeatState graph contribute only literal labels, allow-listed routes,
manifest-relative background/atlas/font references, and a root-scoped imported
state target where one is authored. `MainMenuState` owns the overlay camera,
native Flixel objects, input, Story/Freeplay/Options/Credits/Costumes routing,
idempotent cleanup, and native fallback. `HxcCompatRuntime` exposes only the
mount/tick/clear boundary; `HxcStateFactory` materializes a recognized imported
menu state as `HxcImportedMenuState`. Donor object graphs, `FlxG.state`,
reflection, hardcoded chart launches, and window-close calls are never emitted
into the generated HScript. Unknown labels and unavailable imported targets are
informational no-ops, while missing or partial manifest assets leave the native
menu visible.

The exact selected auto-import delta from the post-Round 16 baseline is:

| diagnostic | before | after |
| --- | ---: | ---: |
| `hxc-unsupported-hxc-module-body` | 3 | 1 |
| `hxc-unsupported-hxc-callback-body` | 3 | 1 |
| `unsupported-hxc-script` | 0 | 0 |
| `hxc-hxc-module-adapter` | 41 | 41 |
| `hxc-hxc-lifecycle-adapter` | 157 | 156 |
| `hxc-hxc-menu-overlay-adapter` | 0 | 2 |
| `hxc-hxc-menu-state-materialized` | 0 | 1 |
| `hxc-hxc-menu-bounded-fallback` | 0 | 1 |

The mounted 224-file inventory remains 177/177 generated adapters parseable;
its exact safety totals are now 1 unsafe callback, 2 module-body findings, and
101/42 safe module callbacks/files. At the end of Round 17, the remaining
selected partial graph was the intentional DokiPause module; Round 18 below
closes that selected safety gap.
The common host preserves behaviorally important background, text/button
selection, native routing, scoped asset checks, fallback, and teardown. Donor
character splash/vignette choreography, custom tween easing, mouse/mobile
affordances, and pixel-perfect placement remain cosmetic parity gaps.

Focused evidence (no build or game launch):
`TMPDIR=$PWD/tmp python3 -m unittest tools.tests.test_hxc_menu_overlay_round17`
completed 3 tests with `OK`; the updated mounted transition, inventory, and
auto-import count tests also pass. Synthetic renamed fixtures, mounted donor
byte immutability, generated-HScript parsing, typed-route validation, runtime
no-owner no-op, and cleanup-boundary source assertions are covered.

Round 18 mounted/synthetic pause-overlay evidence (2026-09-18): the complete
TAKEOVER `DokiPause.hxc` helper plus `onSubStateOpenEnd`/close lifecycle is now
recognized structurally, independent of its donor filename or class name. The
analyzer emits only a typed `HxcPauseSpecData` literal containing manifest-scoped
art/atlas/font keys, title/death/practice labels, hidden labels, and colors.
`PauseSubState` owns the overlay objects, camera, stock menu actions, input,
selection colors, native practice/death/title mapping, idempotent cleanup, and
the native fallback. `HxcCompatRuntime` exposes only the owner-checked
`applyPauseOverlay`/`clearPauseOverlay` boundary; donor metadata, menu-entry
callbacks, character branches, reflection, `FlxG.state`, chart launches, and
window-close behavior are not emitted. Missing or partial scoped assets leave
the stock pause menu active with an informational diagnostic. Partial pause
shapes remain explicitly diagnosed rather than being treated as executable
ordinary modules.

The exact selected auto-import delta from the post-Round 17 baseline is:

| diagnostic | before | after |
| --- | ---: | ---: |
| `hxc-unsupported-hxc-module-body` | 1 | 0 |
| `hxc-unsupported-hxc-callback-body` | 1 | 0 |
| `unsupported-hxc-script` | 0 | 0 |
| `hxc-hxc-module-adapter` | 41 | 41 |
| `hxc-hxc-lifecycle-adapter` | 156 | 156 |
| `hxc-hxc-menu-overlay-adapter` | 2 | 2 |
| `hxc-hxc-menu-state-materialized` | 1 | 1 |
| `hxc-hxc-menu-bounded-fallback` | 1 | 1 |
| `hxc-hxc-pause-overlay-adapter` | 0 | 1 |

The mounted 224-file inventory remains 177/177 generated adapters parseable;
its exact safety totals are now 0 unsafe callbacks, 1 module-body finding, and
101/42 safe module callbacks/files. The remaining inventory module-body finding
is outside the selected DokiPause graph; it remains diagnosed by the existing
bounded gate. DokiPause's residual gap is cosmetic rather than a route/safety
gap: donor tween easing/mobile button affordances and pixel-perfect placement
are represented by the native stock-input host, while unavailable optional
opponent art falls back to the stock pause display. The focused four-test
Round 18 suite covers renamed structural extraction, partial-shape diagnosis,
mounted donor immutability/generated-HScript parsing, and runtime no-owner plus
native cleanup assertions. No build or game launch was performed.

## Counts-only scanner memory checkpoint (2026-09-24)

A single full mounted counts-only scan completed with exit 0 in 134.063 s. It
covered 16 roots and reported 137 candidates, 137 selected records, 112 unique
records, and 25 duplicates. Sampled peak RSS was 1,657,456 KiB (1.58 GiB),
below the 2.5 GiB stop threshold; no allocator error lines were observed. The
saved run metadata and output are `tmp/vslice-counts-only-full-20260924-01/run.json`
and `tmp/vslice-counts-only-full-20260924-01/scanner.out`. This is one successful
run and does not establish that the earlier intermittent heap abort is fixed.
