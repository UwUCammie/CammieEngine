# Engine discrepancy verification — 30 September 2026

This report records the shared engine/compatibility work and its verification.
Named content below is used as a regression fixture, not an executable special
case or authored chart rewrite. Missing imported assets are restored only through
receipted, missing-only compatibility repairs. Architecture is documented in
[ENGINE_ARCHITECTURE.md](../../ENGINE_ARCHITECTURE.md).

## Current offscreen evidence — 29 September 2026

### 30 September — Optional instrumental/vocal normalization

Added the shared `Normalize Song Audio` toggle (default off) to main settings
and imported Codename Gameplay settings. The same loader normalizes gameplay
and chart-editor stems. It uses a fixed gated RMS gain with a sample-peak
ceiling, preserving original PCM/assets, authored volume controls and timing.

Focused settings, PCM math, loader ownership/cache and split-vocal checks:
**16 tests passed**, `tmp/audio-normalization-focused-20260930.log`. Canonical
`./run.sh build` succeeded (`tmp/nmv-iris-owner-build-20260930.log`).

Three isolated Xvfb/null-audio native runs passed on binary SHA-256
`7772b99bea4d2424d2cb500e6e874bf6ad7c95f0fc5c73cc29d6a5254cffe52f`:
- Disabled: observed instrumental/vocal RMS 0.028297 / 0.282754.
- Enabled and repeated load: 0.125968 / 0.125853 (target 0.125893).
- Script volume/mute setters, successful gameplay entry/playback, unchanged
  test options and personal settings; no script errors.

Receipt: `tmp/audio-normalization-native-20260930/receipt.json`. Disposable
synthetic chart/audio were removed and the private runtime options restored.
This verifies PCM scaling and controls, not subjective listening or final
mix clipping. Unsupported streaming PCM/bit depths diagnose and preserve
original playback. Native editor interaction and a current-build integration
suite remain pending alongside the custom-note work.

### 30 September — NMV module parser and source syntax

The independent NMV core now uses namespaced `hscript-iris` 1.1.3, installed
by the canonical build scripts and declared in `Project.xml`. Existing engine
interpreters keep their original packages. Imports and custom using handlers
are scoped to each interpreter; no owner closure is registered in Iris's
global import/using tables. Release clears those references.

The stable dependency differs from the supplied NMV source extension. Its
single-quoted strings stayed literal and its parser rejected key/value loops.
The shared `HaxeStringInterpolation` lowering now serves Codename and NMV,
including `$$` escapes. NMV's parser marks key/value iterator bindings inside
ordinary `EFor` nodes, retaining Iris comprehension lowering. Its interpreter
uses source iterator binding, loop control and null key/value checks. Missing
object methods log the source diagnostic and return before a null native call.
An executed loop test also exposed Iris's null local-slot restoration hiding
an outer preset. The NMV adapter removes absent slots when restoring scope;
callback exceptions now restore interpreter frame bookkeeping before reporting
the error, so later calls can recover.

All **101** Haxe script files under the mounted release, including the **73**
direct gameplay scripts, parse (`tmp/nmv-iris-all-scripts-parse-20260930.json`).
The receipt records input paths and hashes. This is grammar coverage only.
The unchanged `scripts/Events.hx` again passes 22 assertions in each position
mode (`tmp/nmv-events-iris-core-20260930.json`) with test actor/tween bindings.
The unchanged `scripts/Completion.hx` executes its real import, onLoad and
onEndSong flow against isolated save/plugin doubles, including reload and
separate-owner cases. It does not test the real plugin or save backend.

The new source audit maps the release's `PluginsManager.callPluginFunc` surface
to the supplied source's newer `ModPlugin.callOnPlugin` API, and records
duplicate-name ordering and owner-switch lifecycle differences
(`tmp/nmv-plugin-api-contract-20260930.md`). The local `PluginManager` is not
that service. Native gameplay host/API integration is still pending, and no
NMV song/difficulty is upgraded to source-compatible by these core checks.
Wildcard imports, source dependency revisions and compiled-class APIs still
require verification. The build and broader integration checks for this batch
are recorded separately below when completed.

Native owner-retention refresh now passed on binary
`7772b99bea4d2424d2cb500e6e874bf6ad7c95f0fc5c73cc29d6a5254cffe52f`.
The isolated importer found/imported 60 charts, copied 96 missing script files
into their selected content-pack namespaces, and reported zero errors. All 96
retained files match donor hashes; all 269 protected existing files remained
byte-identical. Evidence: `tmp/nmv-script-retention-native-20260930/retention.json`.
This closes the owner-retention check only; source API host/load phases, base
asset fallback and NMV gameplay script execution are still unverified.

The earlier integration suite ran 1,624 tests across 478 modules (65 skips)
and failed three fixture modules after production helper signatures changed.
Those fixtures were corrected without weakening assertions; all 18 tests in
the three modules now pass, including both mounted donor scans. A final suite
run follows the in-progress audio/custom-note integration.

### Default results layering and Codename judgement regression

The user reported Dusk Hard showing gameplay HUD over the default results pack,
UNKNOWN difficulty, and zero judgement counts. Shared fixes now promote the
claimed fallback overlay above gameplay cameras, expose the selected difficulty,
forward committed Codename hit/miss callbacks while notes are live, and map
additional source judgement tiers into the Psych observer's four categories.
The fallback provider cannot overwrite source scoring through its root scoring
`setProperty` calls. Psych Animate defaults preserve authored atlas origins.
A one-shot owner/chart lease carries source song metadata through the incoming
transition without retaining the destroyed gameplay state.

Final normal-speed native evidence (`tmp/dusk-results-verified-1x-20260929.json`,
assertions in the adjacent `-assertions.json`, binary SHA-256
`1289bb4ff9ce18c4a1af78d530eb8681b4759fc1ea71ec1b1cd3df853c8d1587`):

- Dusk Hard completed naturally at 160858 ms; all 372 authored events dispatched.
- All 386 player heads were counted: 380 Sicks, 6 Goods, no Bads/Shits/misses.
  Max combo 386 and score 133250 match committed gameplay values.
- All 386 per-head observer snapshots matched cumulative judgement totals,
  including notes at nonzero group indices.
- The results overlay was camera 4 of 5, above gameplay. Six- and fourteen-second
  screenshots show the authored animated character, score digits, and clean
  layering. The earlier capture also shows Dusk/HARD.
- The supplied pack's V-Slice clear percentage is `(Sicks + Goods) / total`,
  hence 100%; native weighted accuracy was 99.6113989637306%. These intentionally
  different measures retain the pack's authored formula and source scoring.
- Accept returned through the paired Codename transitions to Freeplay, with no
  runtime diagnostics. Private options were unchanged; six protected live files
  match pre-test hashes (`tmp/dusk-results-protected-files-20260929.json`).

The intermediate `tmp/dusk-results-final-1x-20260929.json` run reported only 370
judgements against 386 hits. Diagnostic probes isolated the loss to nonzero live
note indices. `Reflect.hasField` did not recognize compiled native Note members,
so the callback adapter defaulted every ID to zero. Shared note detection now
uses public property reads, preserving false/zero values. An accessor-backed
class fixture exercises the field-presence difference and a live index of two.
The temporary per-property read trace was removed; opt-in per-head observer
snapshots remain available for future native counter checks.

`./run.sh build` passed (`tmp/dusk-results-native-field-build-20260929.log`).
The preceding full suite passed 1,612 tests across 471 modules, with 65 skips and
zero failures (`tmp/full-tests-dusk-results-final-20260929.log`). The final suite ran 1,613 tests across 471 modules in 285.8 seconds, with 65
skips and one failure (`tmp/full-tests-dusk-results-native-fields-20260929.log`).
It reproduced the known intermittent native import-scanner exit 245 in the mounted
HXC auto-import count test. This remains an open compatibility/stability gap,
not a passing gate. Earlier accelerated runs are crash/handoff evidence only;
normal-speed screenshots are used for results presentation. No donor content
was edited, no mod/chart-specific runtime branch was introduced, and broader
Example Mods compatibility remains incomplete.

### Native scanner header corruption and private row-mark probe

The failed final-suite scanner core (PID 461178) faults in
`hx::Anon_obj::__Mark`, unlike the earlier Psych row-array dereference. Its
10-field anonymous object starts at block offset `0x104`; the header at
`0x100` records only four allocation bytes and one row, although its fields
require 424 bytes. Newer allocations overlap its tail. This establishes header
damage and overlapping data, not the write that caused them. The earlier core's
first-block object also contained repeated `0x01` bytes. Evidence:
`tmp/scanner-461178-object.log`, `tmp/scanner-461178-anon.log`, and
`tmp/auto-import-scanner-461178-receipt.txt`.

The private `--recycle-diagnostics` scanner now checks both GC row-mark spans
before writing the row table, retaining the normal marking policy. A bad span
could overwrite the first allocation; this remains a hypothesis. The pinned
production toolchain is unchanged. Twenty-five focused diagnostic-tool tests
pass, including compiled boundary/overflow checks and both writer call sites
(`tmp/scanner-row-probe-tests-20260929.log`).

One native probe reached the V-Slice root before its 180-second bound and exited
124 without a row-mark/recycler violation. It did not complete and cannot clear
the intermittent defect. Receipt and output are retained under
`tmp/auto-import-diagnostic-recycle-cache/31b43c8703658e212805ae3975b4780a7d6b0aa57962891a9555ff60ba3a6d84/run-471867-8998dcf75134426ca4d4945fae573a46/`;
the compact parent log is `tmp/scanner-row-probe-native-20260929.log`.
The upstream audit found no confirmed matching fix
(`tmp/hxcpp-upstream-gc-audit-20260929.md`). No game build, donor refresh, or
personal-setting change was needed for this diagnostic batch.

A second run reused that instrumented binary with a 300-second allowance so it
could reach the late high-memory phase. It completed with exit zero: 265
candidates, 241 unique entries, and 24 duplicates, with no row-mark or recycler
violation. The receipt is
`tmp/auto-import-diagnostic-recycle-cache/31b43c8703658e212805ae3975b4780a7d6b0aa57962891a9555ff60ba3a6d84/run-490169-070cd2a8cc9c47ca8054997aecd876eb/run.json`;
the parent log is `tmp/scanner-row-probe-full-window-20260929.log`.
One live-process sample recorded 2,584,924 KiB RSS and the same high-water mark
at that instant (`tmp/scanner-row-probe-full-window-memory-20260929.json`).
This completed diagnostic run does not resolve the intermittent ordinary-build
crash or establish its cause.

### Psych receptor RGB toggle and remaining native-property audit

The same hxcpp field-presence mismatch also affected `useRGBShader`. The shared
toggle now reads native properties and invokes their setters, preserving false
values when re-enabling. Native verification exposed a second cause: its old
combined receptor group stays empty. The helper now visits the live opponent
and player groups, matching the existing Psych group-access adapter.

The accessor regression failed on the old implementation, then passed with the
fix. Two focused palette/toggle tests and 29 Lua routing tests pass
(`tmp/psych-rgb-toggle-after-20260929.log`,
`tmp/psych-rgb-lua-routing-tests-20260929.log`). The test includes unequal group
sizes, null members, a missing opponent group, unrelated objects, and a legacy
group that must remain untouched.

`./run.sh build` passed. A five-second offscreen native probe checks exactly
eight live receptors: all eight return false from `Reflect.hasField`, yet all
eight disable and re-enable through the shared helper. The process exits zero,
emits smoke success, and reports no script diagnostics. Its receipt is
`tmp/psych-rgb-toggle-native-20260929.json`, with binary SHA-256
`15ad168c678c08c42864aba4bb5c54ac3db8c71dc8ab2d61cc53b432c5cbb0b8`.
The generated chart/audio links were removed; private default settings and live
personal options retained their hashes. This checks native property routing,
not a new full-song shader-fidelity claim. An initial synthetic fixture lacked
audio; the next revealed the empty legacy group. Both failed observations remain
labelled separately beside the passing receipt.

Final canonical build: `tmp/psych-rgb-final-build-20260929.log`. The integration
suite passed **1,615 tests across 472 modules in 277.6 seconds, 65 skipped,
zero failures** (`tmp/full-tests-rgb-row-probe-20260929.log`). This includes the
ordinary mounted scanner; its intermittent fault remains open despite this
successful run. One process sample observed 2,726,352 KiB RSS at elapsed 3:18
(`tmp/scanner-integration-memory-20260929.json`); it is not a peak measurement.

A bounded audit identified the HXC native-property defects fixed below.
The subsequent source audit distinguishes bare-scalar `startTween` from a Psych
contract defect: the supplied Psych callback expects an object target and a
property map. PERFEXION's `ZoomedStart.lua` supplies a scalar target and endpoint;
the fork has an extra branch for that call shape, which native `hasField` can
bypass. The extension remains unfixed, but this call shape does not establish a
regression of upstream Psych behavior. Evidence:
`tmp/psych-start-tween-contract-audit-20260929.md`, with supplied source and donor
call-site references. See also `tmp/native-field-presence-audit-20260929.md`.
The next NMV scripting slice also
has a source call-site plan in `tmp/nmv-next-script-gap-20260929.md`; execution
remains unsupported.

### HXC native note ownership and character screen positions

`hxcCharacterScopeOwnsNote` now reads native note properties instead of relying
on `Reflect.hasField`. Incoming opponent notes previously fell through to the
player scope. Explicit hit/miss side arguments retain precedence, followed by
source playfield ownership and then `mustPress`. Forced-GF notes use the live
GF when available and the normal opponent singer when absent, matching the
native singing path. `dispatchHxcCharacterScreenPosition` likewise accepts
native point properties, including zero coordinates; replacement points were
previously discarded by the field-presence guard. Both changes apply to the
shared HXC bridge, with no song or package checks.

Both extracted-method regressions failed before the fixes. Focused coverage
passes **19 tests, one skipped, zero failures**
(`tmp/hxc-character-native-properties-tests-20260929.log`). The skip is an
unavailable mounted Whitty fixture. The tests cover actor ownership, callback
argument precedence, absent actors, point replacement, recursion, and recovery
after a throwing visual callback.

`./run.sh build` passed
(`tmp/hxc-character-native-properties-build-20260929.log`), producing SHA-256
`dbed0413e030d947fb5053986f90158b5a0eab74752ade54b020bdb52e4740d8`.
An isolated offscreen native probe passed **21 checks** on that binary,
including two actual Notes for which `hasField(strumTime)` is false, both source
ownership overrides, explicit side arguments, forced-GF and missing-GF routing,
and a returned native point `(0, -2.5)` through the live Character hook.
Receipt: `tmp/hxc-note-owner-native-20260929.json`; output: the matching `.log`
and `.jsonl`. The process exited zero with smoke success and no script errors.
The first fixture attempt had an incorrect interpreter scope key; correcting
the test fixture made the screen-position assertions exercise the intended
live callback. Personal options, private default settings, and the source chart
retained their hashes, and temporary chart/audio/save files were restored or
removed. This is native callback-contract evidence, not a new full-song parity
claim.

The integration suite passed **1,617 tests across 474 modules in 271.9 seconds,
65 skipped, zero failures**
(`tmp/full-tests-hxc-native-properties-20260929.log`). The ordinary mounted
scanner also passed in this run; its intermittent crash remains unresolved.

### Nightmare Vision layout and newly identified scripting gap

The dedicated NMV execution core now implements public declaration parsing,
live parent/import/preset/shared lookup, source assignment semantics, group
registration before execution, immediate `onLoad`, ordered callback returns,
and cleanup. It is not wired into gameplay or counted as script support.
Nine focused tests pass (`tmp/nmv-script-core-tests-20260929.log`). The new
interpreter/group tests run both with and without `hscriptPos`, and the group
dispatcher is compared with the supplied source method across 2,048 return-flow
cases per mode. Additional executed-script assertions cover public functions
and values, zero/false/null fields, duplicate loads, parse and callback errors,
recovery, context reassignment, exclusions, clear/reuse, and release.

The mounted release's unchanged `scripts/Events.hx` also executed against test
actor/camera/tween bindings: **22 assertions in each position mode**, with no
diagnostics and its source hash preserved
(`tmp/nmv-events-core-20260929.json`). This exercises real authored middle-camera,
camera-unlock and angle-event logic through live parent fields; the tween API is
a recording double, so this does not establish rendering, tween timing or native
gameplay parity. Temporary interpreter fixture directories were removed.

The supplied source does not pin its Iris git dependency. Current upstream
[`Iris.call` at commit `8867c9a801a051e2bc5f9c03f06e8f88e6c574f9`](https://github.com/pisayesiwsi/hscript-iris/blob/8867c9a801a051e2bc5f9c03f06e8f88e6c574f9/crowplexus/iris/Iris.hx#L344) explicitly checks
that callbacks are functions, catches callback errors, and returns null without
disabling the scope. The new module follows that recovery contract, including
the native-call guard. Source snapshot/URL receipt:
`tmp/nmv-iris-upstream-call-20260929.hx` and the adjacent `.json`. This is upstream
reference evidence; the exact revision bundled into the release remains unknown.

The source review confirms why ordinary HScript loading cannot stand in for
NMV: its globals run before character creation, song scopes load later, and
STOP-returning note-spawn callbacks can suppress native note generation. Real
scripts also contain module imports and typedefs beyond the new public-field
parser adapter. Those parser/API/staging and gameplay-dispatch steps remain
required before any native NMV script-fidelity claim. No game launch, donor
refresh, or personal-setting change was needed for the independent core tests.
The bounded real-script integration audit is
`tmp/nmv-global-runtime-contract-20260929.md`.
The integration suite passed **1,620 tests across 476 modules in 278.5 seconds,
65 skipped, zero failures** (`tmp/full-tests-nmv-script-core-20260929.log`).
The nine focused tests were also rerun after adding the non-function callback
guard. This independent core is not linked into the gameplay loader, so this
batch does not change the previously recorded native binary or chart receipts.

The chart adapter now preserves `keys`, `lanes`, `arrowSkins`, and `trackSwap`
per selected difficulty and materializes the source defaults. The shared
Strumline centered-layout policy follows the supplied NMV ModManager formulas
without legacy mania spacing. Thirteen focused layout, chart, ownership, and
visual-probe tests pass (`tmp/nmv-centered-layout-tests-20260929.log`).

`./run.sh build` passed with the layout probes
(`tmp/nmv-layout-probe-build-final-20260929.log`), binary SHA-256
`40774e10db76cf479cc0d7123264480b89f515b0aa9aff88c28b7b35cd1cd436`.
The existing private runtime was reused for an isolated full-root NMV import:
60 detected songs imported, with no importer errors
(`tmp/nmv-centered-layout-import-20260929/import-preparation.json`). A 12-second
normal-speed Fresh Normal probe then verified all eight initial hitbox and
rendered receptor centers against source coordinates; no native diagnostics
were emitted and private options were unchanged
(`tmp/nmv-source-receptor-layout-20260929.json`). It establishes initial geometry,
not authored skin, script, input, audio, or full-song parity. An intermediate
probe build failed on private-field access; the final build corrected access
inside the opt-in test harness.

Source audit found that NMV `.hx` stage, character, global, song, event, and
note-type scripts are not selected by the current Psych runtime discovery.
NMV uses a separate script API and source load order. Existing successful NMV
imports and zero-diagnostic playthroughs therefore do not establish scripting
compatibility; silent omission must not be counted as success. Additional
playfields and custom skin/audio behavior also remain incomplete.

### Nightmare Vision direct-script diagnostics

`NightmareVisionScriptDiscovery` now inventories the source stage, immediate
global/song scripts, characters, referenced note types and events (including
legacy embedded event rows and Change Character references). It follows the
selected owner and same-package overlays, source extension priority, TJSON
stage parsing and GF visibility. The importer reports selected `.hx` scripts
as unsupported instead of silently treating a Psych-only launch as complete.
Dynamic script loads, runtime global-pack activation and non-gameplay entry
points remain explicitly outside this direct discovery inventory.

Six focused discovery tests pass, including 1,030 direct scripts without
truncation (`tmp/nmv-script-discovery-final-tests-20260929.log`). The saved
direct-script audit covers 194 chart-shaped documents, including helper files
that are not selectable difficulties: 83 new-pack and 111 old-pack documents.
Their plans identify 46 and 27 unique direct script paths respectively;
these counts include base fallbacks and are not a claim of executable support
(`tmp/nmv-direct-script-inventory-summary-20260929.json`). The legacy embedded
event-row test was added after that audit snapshot.

The integration suite passed **1,607 tests across 470 modules**, with 65 skips
and no failures (`tmp/full-tests-nmv-layout-discovery-final-20260929.log`).
The earlier six failures were extraction fixtures missing the new helper or
probe stub; those fixtures were corrected. Intermittent native allocator and
scanner failures recorded elsewhere in this report remain unresolved.

### Shared note ownership and focused replay

Normalized Nightmare Vision charts retain authored field, direction, actor,
and autoplay metadata on heads, sustains, and lifts. Ordinary charts and
`psych_v1_convert` keep the actor override unset so incoming script callbacks
continue to follow a script-mutated `mustPress`. Native opponent hit dispatch
now uses the same autoplay policy as note timing, allowing NMV's automatic
opponent field to dispatch in duo mode. Third-field rendering, scoring,
callbacks and input remain unimplemented and explicitly unsupported; this
metadata change does not enable those charts.

The final `./run.sh build` passed
(`tmp/field-routing-final-build-20260929.log`), producing binary SHA-256
`4a2b85c70af5a277dee09c1624f31a070dc3922d903cc6b1585a08f25274133e`.
The focused ownership/autoplay suite passed five tests, including comparison
of all 76 installed Psych archive charts against the supplied unpacked source
tree. This source fallback removes a stale ZIP-path skip. Psych Ugh Hard then
passed an offscreen 50× replay with 256 player and 270 opponent head notes,
natural ending at 86,616 ms, all 11 due events, Accept dismissal of results,
return to Freeplay, and zero strict diagnostics
(`tmp/psych-ugh-field-routing-native-20260929.jsonl`). This is completion and
ownership evidence, not normal-speed visual/audio or human-input parity.

Completion receipts now capture the actual binary/chart hashes, compatibility
manifest/default-settings hashes, owner and playback conditions. The runner
also creates its private scratch/cache folders on first use; an initial
targeted launch exposed the missing scratch directory before starting the
game. Its 17 focused tests pass. The reusable private runtime was retained
for subsequent targeted checks, avoiding another full asset copy. Six live
protected files, including personal options, Freeplay and difficulty registries,
and the checked base charts, retained their baseline hashes
(`tmp/field-routing-protected-files-20260929.json`).

The integration suite passed **1,598 tests across 467 modules in 274 seconds,
65 skipped, zero failures** (`tmp/full-tests-field-routing-ledger-20260929.log`).
This includes the ordinary mounted scanner, which completed in its existing
300-second run allowance; the shorter instrumented observations below are
separate diagnostic runs. This successful scan does not resolve the retained
intermittent SIGSEGV or the earlier native allocator aborts. `git diff --check`
also passed. Full compatibility remains unverified.

### Native scanner diagnostics remain inconclusive

The opt-in Psych discovery trace now records one source identity header and
compact section/row coordinates before dereferencing chart rows. The earlier
per-access trace emitted 942 MB; the compact trace emitted 40 MB over the same
180-second observation limit. Both runs timed out without reproducing the
native fault, so neither is a passing scan or evidence that the crash is fixed.
The verbose log is retained compressed at
`tmp/psych-discovery-native-trace-20260929.log.gz`; the compact log is
`tmp/psych-discovery-native-compact-trace-20260929.log`. The 57 focused
discovery/cache/import-workflow tests pass. Ordinary scans retain their
uninstrumented row traversal.

### Historical natural-ending ledger

The reusable ledger at `tools/audit_natural_ending_coverage.py` joins receipts
to the 242-row declared matrix by exact `runtimeChart` plus `difficulty`; it
keeps each matrix row's existing `matrixIndex` as reference only. Replaying the
available Example Mods JSONL receipt globs reproduced **237/242 historical
natural endings** in `tmp/example-natural-ending-coverage-ledger-20260929.json`.
The five rows without a valid ending marker are Extra Hard, Extras Hard,
Gallery Normal, Ridge Normal and Smash Normal. The last two have no
`runtimeChart`, so they cannot match receipt evidence by the ledger's key.
Skipped rows are not counted as ended.

Ending coverage and diagnostic outcome are separate: some historically ended
rows still have failed or mixed diagnostic outcomes. The receipts supplied to
this rerun do not validate natural endings on the current build: no
`--current-build-sha256` was provided, 240 keyed rows have unknown build
provenance, and the two unkeyed rows have no matching receipt. Even matched
binary and chart hashes would validate only that ending pair, not all runtime
dependencies. The ledger makes no full source, visual, audio, menu, UI, editor
or cutscene parity claim. The earlier snapshot
`tmp/example-natural-ending-coverage-audit-20260929.json` recorded the same
237/242 coverage, but its `receiptFilesExamined: 236` count is not reproduced:
the regenerated ledger examined 26 JSONL files and 1,392 records, deduplicated
seven duplicate matched records, and retained 806 unique chart-keyed attempts.
The earlier snapshot did not record its receipt input manifest, so only its
coverage result is independently confirmed here.

Adding today's Ugh receipt with the explicit current binary hash yields one
matched binary/chart natural ending and 241 unknown rows in
`tmp/example-ending-current-build-ledger-20260929.json`. Historical coverage
stays 237/242. The ledger's eight focused tests cover reordered matrix rows,
failed-but-ended runs, duplicate receipts, invalid markers and conflicting or
missing provenance. None of these counters measures full source parity.

Reproduce the ledger with:

```bash
python3 tools/audit_natural_ending_coverage.py \
  --matrix tmp/example_mods_chart_matrix_runtime_declared_20260929.json \
  --receipt-glob 'tmp/example-mods-*.jsonl' \
  --receipt-glob 'tmp/example-mods-*/*.jsonl' \
  --receipt-glob 'tmp/example-mods-*/**/*.jsonl' \
  --output tmp/example-natural-ending-coverage-ledger-20260929.json
```

### Earlier 256-row sweep

The earlier installed matrix had 256 song/difficulty rows. The first 157 distinct rows
(indices 0–156) have an initial strict natural-ending sweep receipt under
`tmp/example-mods-final-256-sweep-20260929/`; it recorded 104 passes,
47 failures and six blocked rows. Several failures came from installed assets
that predated later shared importer fixes. The continuation at indices 157–255
saved all 99 distinct rows: 48 strict passes and 51 failures. The combined
pre-rebuild snapshot is 152 passes, 98 failures and six blocked rows. These
are not final compatibility results; source-backed importer and harness fixes
still require scoped refreshes, rebuilds and replays.
Natural endings do not establish visual, audio, menu, editor or cutscene parity.
The 29 September source catalog reconciles all 14 mounted package roots plus
the Psych ZIP to the same 256 raw chart/difficulty keys (255 playable rows and
one undeclared empty DDTO placeholder). Its non-chart catalog lists 5,909
mounted-package files and 1,276 archive entries. The default matrix artifact
is dated 27 September and still has pre-install FNAS status; the current-state
refresh described below supersedes those stale installed fields. Neither matrix
establishes stage, character, script, cutscene, menu, or required-asset parity.
The base catalog's `assets/` file list omitted the enabled Modding Plus
`mods/introMod/_append/data/introText.txt`. The bounded supplemental audit in
`tmp/example_mods_nonchart_entity_inventory_20260929.json` now records that
20-byte overlay, confirms `mods/modList.txt` enables `introMod`, and indexes
DDTO's already-cataloged 70-byte `_merge/data/players/pico.json`. The same
audit resolves the relocated FNAS root to
`/run/media/cammie/External Storage/FNF-Example-Mods/codename/fnas_after_hours`
and surfaces the new `nightmare-vision` mount entry and its `source_code`
child; neither shallow candidate had an operation-folder file. The audit
enumerates mount candidates only through depth two, alongside deeper roots
already named by the source inventory, and does not traverse package assets.

A read-only current-state refresh of those 256 reviewed chart keys is now in
`tmp/example_mods_chart_matrix_runtime_20260929.json`. It verifies all 233
previously recorded source chart hashes, records the other 23 source hashes,
and rechecks installed chart bytes, selected owners and playable note counts.
The moved FNAS installation resolves at its current `codename/fnas_after_hours`
location with the same chart hash. The result is 250 structurally covered
playable rows, five rows with no installed chart candidate because their source
audio is absent, and Baka's undeclared empty Normal placeholder. Focused
dry-run preflights accepted the refreshed Madness difficulties and the D-Sides
Tutorial/Weiner tail rows. This is structural evidence only; source behavior
still needs direct comparisons and interaction checks.
The full current-matrix native preflight without launch reports 250 ready, six
blocked and zero failed (`tmp/current-matrix-full-preflight-20260929.jsonl`):
the five source-media rows have no installed chart candidate, and the sixth is
Baka's undeclared empty placeholder. The command's exit status is 1 because
it correctly treats those blocked rows as unfinished work.
The first 120 private offscreen editor round trips have a separate receipt at
`tmp/example-editor-matrix-20260929.json`: 112 pass, five skip for missing
source media, and three native failures. Each pass checked the selected owner
and difficulty, edited/deleted an event, Quick Saved and reloaded, and kept
the installed chart, event sidecar and options byte-identical. The initial
five-second smoke deadline falsely failed Underground Easy while its large
grid reloaded; a 20-second replay passed, and the editor-matrix default
deadline was raised accordingly. The previous Hopeless-Bastard pre-load
`Invalid field:null` failure passed on the rebuilt binary, but the later
Eggnog and South editor reloads exited with the same diagnostic and Senpai
aborted with native heap corruption. The Quick Save smoke had been resetting
Flixel recursively from `ChartingState.create()`, unlike a real user action;
it is now deferred to the next update and still needs a rebuilt native replay.
Native heap stability and the remaining editor rows remain open.

The editor runner now has an optional two-worker mode with separate Xvfb
displays, private overlays and logs under one parent runtime build lock. A
four-row pilot took 24.0 seconds serially and 11.0 seconds with two workers;
three rows passed in each mode, while the same fourth row aborted in native
shader/bitmap setup in both. This is a bounded throughput measurement, not a
compatibility pass. Strict failures will be replayed serially.
The broad natural-ending sweeps use demo botplay at 20×. A focused 50×
crash/completion gate for Linkinteen Parks Buck also reached the authored
186,666 ms ending and dispatched all five due events, with zero native
diagnostics (`tmp/linkinteen-50x-crash-gate-20260929.jsonl`), matching the
20× event/ending receipt. The 50× gate is suitable for fast completion and
crash coverage where display timing is immaterial; animation, camera,
cutscene, sound synchronization and source appearance still need real-time
checks. Startup and asset loading remain fixed costs, so wall-time speedup
will be less than the playback-rate multiplier.
The current mounted-source offscreen sweep has completed rows 0–59 on the
preceding release (34 strict passes, 23 failures, three missing-source-audio
blocks) and rows 60–119 on the rebuilt release (56 strict passes, two native
heap aborts, two missing-source-audio blocks). Linkinteen's previously failing
row passed a focused rebuilt 20× replay and a separate 1× post-transition
actor-animation check. The rebuilt archive aborts occurred in Monster Easy and
Pico Easy during note setup; each passed one later fresh replay with glibc
allocator checks enabled. Their saved coredumps detect heap damage in
ordinary path allocation but do not identify the corrupting write. Valgrind
itself failed in the host loader before game code, so the native heap issue
remains open. Receipts are
`tmp/example-mods-current-build-rows-0-59-20260929.jsonl` and
`tmp/example-mods-rebuilt-rows-60-119-20260929.jsonl`. The editor matrix
preflight accepts 250 selected-owner rows and diagnoses six skips; native
round trips are still pending. The current automated suite passes 1,539 tests
across 453 modules, 64 skipped, none failed
(`tmp/full-tests-20260929-after-editor-matrix.log`).
The next rebuilt range, rows 120–179, finished with 37 strict passes, 22
icon-only strict failures and one blocked empty Baka Normal source placeholder
(`tmp/example-mods-rebuilt-rows-120-179-20260929.jsonl`). Every icon-only
case reached a natural ending with zero native diagnostics. DDTO's authored
`CustomTitleBar.hxc` checks `Assets.exists` before changing the window icon,
so the shared adapter's current-icon fallback matches that source behavior;
both donor and selected import lack `dokicon.png`. The diagnostic remains
visible as an unresolved source dependency.
Rebuilt rows 180–239 then completed with 39 strict passes, 20 further DDTO
icon-only failures, and one Cursed Expurgation failure containing 62 native
stage/script diagnostics (`tmp/example-mods-rebuilt-rows-180-239-20260929.jsonl`).
The Cursed stage's undefined helpers and requested sound path are absent from
the selected donor. Its byte-identical modchart writes `gramlan.x` before
`beatHit(5)` first creates that sprite, so the separate null-object diagnostic
is also source-backed rather than a missing shared API.
Wacky World Normal/Hard and its empty, metadata-unlisted Nightmare key all
reached natural endings with the current classifier correctly ignoring an
informational video adapter trace. Native endings alone do not verify video
sync, sound mix, stage visuals, or editor behavior.
Rebuilt rows 240–255 all passed strictly, including D-Sides Monster, Soretro
and Tutorial (`tmp/example-mods-rebuilt-rows-240-255-20260929.jsonl`). The
first 60 rows were then replayed on this exact release, with 34 strict passes,
23 failures and three source-media blocks
(`tmp/example-mods-rebuilt-rows-0-59-20260929.jsonl`). The complete
consistent-release 256-row gate is 182 strict passes, 68 failures and six
blocks. The failures group as 42 DDTO source window-icon dependencies, 15
Vs. Whitty source character/icon dependencies, three PERFEXION Lua/asset
diagnostics, three Bruce missing-fork API diagnostics, one Cursed donor script
failure, two native heap aborts and two `PsychRGBShader` constructor aborts.
The blocked rows are five source-missing instrumentals and one empty undeclared
Baka Normal placeholder. Linkinteen now passes; two long Psych charts fail
before gameplay with `Invalid field:null` during shader construction. This
is a completeness/accounting receipt for offscreen endings and diagnostics,
not a source-presentation or editor parity verdict.
A source-shaped Psych RGB palette cache with per-note copy-on-write now avoids
constructing a shader for every note and exposes the donor `rgbShader`
reference. Focused interpreter tests and `./run.sh build` pass. On that new
binary, Low-Rise HQ Normal reached a natural ending without diagnostics.
Overhead Normal advanced past its former shader-construction abort and, with
authored dialogue input, reached a natural ending; it remains a strict failure
because the selected Vs. Whitty source lacks `bfwhit` character/icon assets.
Receipts: `tmp/psych-rgb-row44-rebuilt-20260929.jsonl` and
`tmp/psych-rgb-row47-advance-20260929.jsonl`. These two replays do not resolve
the intermittent native heap corruption seen elsewhere in the corpus.
The newly present `nightmare-vision/source_code` directory is an engine source
checkout, not a populated mod package. Its `content/NMV-Base-Game` submodule is
uninitialized; the only chart is an embedded `Test` smoke fixture with its own
audio but an undefined `bf-pixel-opponent` character dependency. It is tracked
as a source-format reference, not silently counted as an imported song.

The rebuilt release binary `0615fa3d490de584e0e1097522fb274647677be71efb4490cf7a2a5f52f41bef`
passed a focused Soretro Hard native replay after binding Codename's script
`gf` to the live actor on authored strumline 2: its two-line donor script no
longer enters the nonexistent GF-line branch, and 343/343 due events reached
a natural ending with zero diagnostics and unchanged private settings
(`tmp/soretro-after-codename-gf-binding-20260929.jsonl`). The mounted donor
callback and absent/present third-line fixture passed its focused interpreter
test. This is a shared Codename facade change, not a Soretro chart exception.

On the same binary, Glitcher Monika Mix Normal completed 110/110 due events
with no HXC shader callback errors; its strict row still fails only on the
mounted DDTO package's missing `dokicon.png` window icon
(`tmp/glitcher-after-hxc-filter-20260929.jsonl`). Markov Lyrics Hard passed
136/136 due events after the native gameplay deadline and outer process
timeout were made readiness-relative (`tmp/markov-after-ready-deadline-20260929.jsonl`).
Ballistic HQ Easy stopped its countdown for the source intro when no input
was supplied; a bounded private Accept-input replay passed its natural ending,
82/82 due events and zero diagnostics without changing settings
(`tmp/ballistic-hq-easy-dialogue-after-note-phase-marker-20260929.jsonl`).
These targeted replays do not replace the package-wide sweep or source visual
and cutscene checks.

A private Soretro Hard pause/resume probe initially delivered Escape and
Return but hung because the pause outro ran `data/stickerTransition.hx` while
the resume selector had changed to a different transition script. The shared
Codename lifecycle now pairs the incoming pause transition with the actual
outgoing script path and retains its static state; real state handoffs still
follow their live selector. On the rebuilt release binary, the same offscreen
probe passed: both inputs were delivered, music stopped and restarted with no
pause-clock advance, the incoming script was `data/stickerTransition.hx`, its
25-second gameplay window completed, and there were zero diagnostics or
settings changes (`tmp/soretro-pause-resume-after-transition-pair-20260929.json`).
The input driver now streams complete game lines and input receipts during
execution so a future timeout retains its diagnostic tail. Its temporary
process termination fixture and the transition scope fixture pass.

On the same release build, the private default-settings Tutorial baseline
reached its natural 67,250 ms ending at configured 60, 240 and 480 FPS with
matching ending positions, 0/0 due events, zero script diagnostics and
unchanged installed settings. Median measured rates were 60, 240 and 340 FPS.
The offscreen renderer did not attain the 480 FPS cap, so rate attainment is
inconclusive even though timing and ending parity passed
(`tmp/fps-cap-parity-after-transition-build-20260929.json`). Imported chart
parity across those rates remains to be checked.

The imported D-Sides Tutorial Hard replay now supplies one chart-level
60/240/480 comparison. All three private runs reached the natural 100,650 ms
ending, dispatched 214/214 due events, reported zero native diagnostics and
left installed settings unchanged. The 60 FPS run measured 60 FPS, while the
software-rendered 240 and 480 settings each measured about 100 FPS median.
Behavioral timing and event parity passed; higher-rate attainment remains
inconclusive on this display (`tmp/dsides-tutorial-fps-parity-20260929.json`).
This one chart does not establish parity for every imported package or stage.

The latest parallel repository suite passed 1,531 tests across 452 modules,
with 64 skipped and zero failures
(`tmp/full-tests-20260929-after-linkinteen-and-fnfassets.log`). The preceding
serial suite passed 1,524 tests across 450 modules, with
64 skipped and zero failures (`tmp/full-tests-20260929-after-texture-fixture.log`).
Its first run found one outdated Vs Tricky test fixture that treated source
`permanentCacheTexture(Paths.sound(...))` as a sound cache. The shared HXC
adapter correctly treats the operation as a texture request; the fixture now
asserts those image keys and separate sound behavior stays under its own
tests. The focused HXC suites passed 99 tests (one skipped) plus the
constructor-cache test before the clean serial rerun.

After a source-form V-Slice importer preview matched the installed Madness
gameplay charts, a selected-owner, three-file chart refresh retained the
donor's otherwise unrouted note rows as editor metadata: 4 Easy, 8 Normal and
8 Hard. An independent byte audit found that deleting only the new
`vSliceUnroutedNotes` member from each refreshed chart exactly reproduces its
backed-up chart; owner and options were preserved
(`tmp/vslice-madness-unrouted-chart-refresh-20260929.receipt.json`). A shared
native editor check now compares authored raw metadata by JSON value across
load, Quick Save and reload. Madness Hard passed the private editor round trip
with all eight rows, zero diagnostics and unchanged installed chart, event
sidecar and options (`tmp/madness-hard-editor-semantic-20260929.json`). Its
post-refresh native gameplay reached the natural 151,698 ms ending with 37/37
due events, zero interpreter errors and unchanged private settings
(`tmp/madness-hard-after-metadata-refresh-20260929.jsonl`). These checks
establish metadata preservation and this difficulty's gameplay regression;
they do not establish source visual parity for the package.

At the first tail checkpoint, distinct rows 157–197 had 12 strict passes and
29 failures on the pre-rebuild binary. Twenty-four failures reached a natural
ending with only the package's missing `dokicon.png` title icon diagnostic;
the source package and installed owner also lack the title-return `icon16.png`
requested by the same source module. One row has additional HXC countdown
shader callback warnings, one intermittently aborted in native atlas setup,
and four reached readiness but hit the runner's launch-based ending deadline
before natural completion. A generic readiness-relative deadline correction
and rebuilt native replays remain pending. The mounted package has neither
requested title icon, so no substitute or importer rewrite is justified.
The allocator abort on matrix row 170 has a retained system core (PID 3998082):
glibc detected heap corruption while the main thread was constructing a
V-Slice character atlas through `DynamicAtlasFrames.combineSparrow` and
`FlxAtlasFrames.fromSparrow`. That stack shows where the allocator noticed
corruption, not where memory was first damaged; no atlas-specific fix is
claimed without a reproducible rebuilt run. One immediate old-binary repeat
passed the row's natural ending with 186/186 due events, zero diagnostics and
unchanged private settings (`tmp/ddto-row170-repeat-old-binary-20260929.jsonl`),
confirming that the original allocator abort is intermittent, not resolved.
One replay on the rebuilt binary with `MALLOC_CHECK_=3` and
`MALLOC_PERTURB_=173` also reached 186/186 due events and a clean ending
(`tmp/ddto-row170-allocator-check-new-binary-20260929.jsonl`). The retained
Natsuki loader uses one atlas pair on this path, so the helper's multi-atlas
append is not involved in that core. Two successful repeats cannot rule out
the earlier native corruption; no speculative atlas change was made.

A shared Codename note-presentation correction now leaves notes owned by an
authored input line out of the later legacy two-bank snap pass. Its focused
geometry fixture covers angled head and narrow-sustain placement, including
travel and center alignment (seven focused tests passed, one optional fixture
skipped). It has not yet been built or checked in the native game. A bounded
HXC adapter for source-backed boolean camera-filter choices also passes four
focused shader tests and the 228-file mounted static corpus; native visual
replay on the rebuilt binary remains pending.

The generic seek smoke now distinguishes charts that request vocals from
instrumental-only charts through a source `needsVoices` marker. Runtime
object existence alone is insufficient because PlayState owns a silent vocal
placeholder even when no vocal track is authored. The instrumental mode checks
music, Conductor, event and note clocks without inventing a vocal clock; the
vocal mode still requires synchronized vocal timing. Eight focused seek tests
pass. Native matrix replays are pending the current sweep and rebuild. The
rebuilt binary's private Blazin Normal seek passes this instrumental-only path
(`tmp/blazin-instrumental-only-seek-20260929.json`): its source chart sets
`needsVoices=false`, music/Conductor/song clocks landed at 20,000 ms, 55 stale
notes were discarded, zero stale notes remained, and private default settings
were unchanged. The runtime still owns a silent vocal placeholder
(`hasVocals=true` in the marker), so source intent selects validation.

The tail sweep has also reached Vs Tricky rows 209–218 and Wacky World rows
219–221. All naturally ended but failed strict checks for owner-scoped
character visuals: both selected owners lack an `images/custom_chars` registry
and converted actors, while their mounted sources have character JSON and
atlases and the old shared global registry contains legacy conversions. The
shared resolver correctly refuses to borrow another owner's global row.
Current importer code writes V-Slice conversions to the selected owner, and
its ownership/mixed-visual focused suites pass 15 tests. Selected-owner
additive refreshes with backups and rebuilt native replays are required before
these rows can count as passes. Wacky World's informational HXC video-adapter
description also triggers an overly broad strict-log regex because it mentions
`playback-error` as a behavior name; the generic classifier is being corrected
while retaining real playback error detection.

The first native Vs Tricky refresh transaction was refused and fully rolled
back (`tmp/vslice-visual-owner-apply-v2.stdout.json`). The importer finished
and generated 42 new selected-owner visual files, but a one-owner legacy chart
also gained a provenance file and the wrapper's source recheck treated that
partial runtime provenance as a donor change. All 283 protected files matched
their preflight hashes after rollback, with no remaining watched-tree
additions. The wrapper now rechecks source chart/audio bytes independently of
runtime provenance, restores all protected bytes, removes transaction-created
chart/audio additions, and accepts only selected-owner additions. Seven
focused transaction tests passed at that point. The revised wrapper now has
seven focused transaction tests, including a fault-injection rollback and
preservation of unrelated new directories.

The rebuilt binary `12c2f7ea80400890f065cb70d201668b7881238973701050a8769b99a6a1235f`
and reviewed Vs Tricky plan completed the second selected-owner refresh
(`tmp/vslice-visual-owner-apply-after-hxc-build-20260929.stdout.json`). It
added 42 missing owner visual files, restored all 283 protected files, removed
only the new legacy-chart provenance file, and left both options locations
unchanged. Native import reported zero errors. The three former HXC diagnostics
were false sound-asset lookups: `permanentCacheTexture(Paths.sound(key))`
requests a texture, and its PNG/XML files were already present under the
selected owner's `shared/images` mapping. The shared HXC planner and runtime
now use the operation's texture type; focused tests retain a separate true
sound reference when one is authored.

All ten Vs Tricky matrix rows (indices 209–218) passed strict private native
natural-ending replays after that refresh, with every due event dispatched,
zero interpreter diagnostics and unchanged private default settings
(`tmp/vslice-vs-tricky-expurgation-after-refresh-20260929.jsonl`,
`tmp/vslice-vs-tricky-remaining-after-refresh-20260929.jsonl`). This covers
Expurgation Hard and all three difficulties each for Hellclown, Improbable
Outset and Madness. It does not yet establish source visual/cutscene parity
or editor and interaction round trips.

The same wrapper applied an owner-only Wacky World visual refresh, adding 36
selected-owner files while restoring all 185 protected files and options,
removing only the generated legacy-chart provenance file, and reporting zero
native import errors (`tmp/vslice-wacky-visual-owner-apply-20260929.stdout.json`).
All three Wacky World rows (Normal, Hard and Nightmare; indices 219–221)
then passed strict offscreen natural endings with 106/106 due events, zero
interpreter diagnostics and unchanged private default settings
(`tmp/vslice-wacky-after-owner-refresh-20260929.jsonl`). Source visual,
video, editor and menu parity remain separate checks.

The Vs Tricky Madness source has 4/8/8 extra raw rows on unrouted V-Slice
strumlines, while all three playable note counts match. The shared V-Slice
converter now retains integer lanes outside the two gameplay strumlines as
per-difficulty `vSliceUnroutedNotes` editor metadata, including negative and
later source lines, without adding them to gameplay notes. Difficulty loading
keeps that metadata local to the selected chart; the existing editor save path
preserves it. The focused importer/editor fixture passed. Existing installed
charts still need a separately backed-up refresh and native editor replay.

A backed-up, selected-owner V-Slice refresh of the Hatsune Miku package added
41 missing owner files, including package character definitions, atlases and
the owner registry. All 142 preexisting files in the scoped backup retained
their SHA-256 values after one logically unchanged Freeplay serialization was
restored byte for byte. A shared `importSong` guard now avoids that redundant
write when the song is already registered. Fantasy Girl 01, Future Sound and
Rabbit Hole Normal then passed strict offscreen natural-ending replays with
no interpreter diagnostics, respectively dispatching 70/70, 9/9 and 592/592
due events (`tmp/miku-after-owner-character-refresh-20260929.jsonl`). This
checks the refreshed import and gameplay paths, not their complete source
presentation.

The release binary SHA-256
`6d5a9d2fe5c1c72714426204dc8485d3fc625a56007edc442ee872d20bdd09c9`
includes a generic Codename `final` local-declaration parser adapter and the
live Codename `splashHandler` binding. Hopkins Hard passed its strict offscreen
replay with 38/38 due events, zero script diagnostics, a natural ending and
unchanged private settings (`tmp/hopkins-after-splash-binding-20260929.jsonl`).
The Codename parser suite passed nine tests, and the importer preservation
suites passed 25. The full automated suite has not yet been rerun on this
binary.

Ballistic HQ Easy still emitted thousands of `lua arithmetic on nil (/, left
operand)` diagnostics on the same binary despite a focused Lua call adapter;
its strict replay failed (`tmp/ballistic-hq-easy-after-direct-lua-call-20260929.jsonl`).
The exact expression boundary is being instrumented before another behavior
change. V-Slice DDTO rows using a missing package-root `dokicon.png` currently
end naturally but fail strict diagnostics; source package absence and selected
owner resolution are being classified explicitly. Carol Roll Sayori Mix
Normal also aborted after chart generation with glibc allocator corruption,
so native stability remains unresolved across formats.

The source inventories are package-scoped: `tmp/codename_psych_inventory.json`
records six Codename/Psych packages plus the separate Psych archive;
`tmp/inventory_mplus_poop.json` records both Modding Plus families; and
`tmp/inventory_vslice_fnas.json` records four V-Slice packages and the FNAS
installation. These files enumerate source chart difficulties, stages,
characters, scripts, cutscenes/video and referenced assets. The installed
cross-package non-chart catalog is
`tmp/example_mods_nonchart_entity_inventory_20260929.json`: all 14 package
roots and the Psych archive, 5,909 mounted source paths and 1,276 ZIP entries,
with explicit dependency gaps and stale-runtime caveats. The installed
chart matrix is `tmp/example_mods_current_chart_matrix_after_fnas_install.json`
(256 raw rows). A fresh read-only preflight on the latest binary found 250
ready rows, five source-media blockers, and one undeclared empty raw key
(`tmp/example-mods-current-256-plan-20260928.log`). Chart/owner/audio
readiness does not establish gameplay or source presentation parity.

## Latest build and package-wide replay — 29 September 2026

The pre-seek release binary was SHA-256
`7a2c9ecaa3d8c6fd7b5bc6483937cd3335e506ac68b91ceea64d6d9cb8f340cb`.
The latest complete automated run passed 1,473 tests across 439 modules, with 61
skips and zero failures (`tmp/full-suite-final-20260929.log`). `git diff
--check` passed. This verifies engine behavior covered by those tests, not
source presentation parity for every imported package.

The DDTO static HXC import report has 48 diagnostics. One nested-music
resolver miss is fixed in the shared importer and passes its focused test.
The warning set mixes unselected stage/note scripts, song-specific assets,
conditional menu/module references, and an asset already supplied by the
target. A generic selected-stage warning filter is focused-test passing;
the full planner still supplies every source reference to asset copying.
The raw warning count must not be treated as 48 active gameplay failures.
The detailed audit is recorded in the DDTO source dependency section of the
compatibility inventory.

The selected DDTO V-Slice owner was refreshed with the shared mixed-owner
visual-only path. It preserved all 936 preexisting scoped files byte for
byte, left all 62 existing character registry keys unchanged, added only
missing SadBF visual files and one registry key, and made no duplicate chart
or audio folder (`tmp/vslice-owner-refresh-final-20260929/accepted-additive.json`).
The earlier duplicate output from the first refresh attempt was moved to a
repository `tmp` rollback directory; its 610 backed-up preexisting files
were verified identical after restoration. User options and the Freeplay
registry stayed unchanged. Missing secondary death atlases are diagnosed
and excluded from generated animation references; the usable primary atlas
can still load.

On the current binary, strict private offscreen replays ended Libitina
Normal with 1/1 due events, Markov Lyrics Hard and Unfair with 136/136 each,
and Our Harmony Normal with 50/50
(`tmp/example-mods-post-owner-final-20260929.jsonl`). Markov's two rows
passed with zero diagnostics. Libitina and Our Harmony failed strict
diagnostics only for `assets/dokicon.png`, absent from the mounted donor.
The package-wide 256-row strict sweep has its first 13 authoritative rows at
`tmp/example-mods-final-256-sweep-20260929/rows.jsonl`; that file also
records a superseded no-input Ballistic Easy dialogue timeout. Rows 13–59
are recorded at `rows-from-13-with-dialogue.jsonl`. The runner advances
default-setting intro dialogue in its private Xvfb when needed to reach
gameplay. At the pause point, the 60 distinct rows have 27 strict passes,
30 failures, and three blocked source-media rows. All three HL17 rows pass;
the failures include source dependencies, script diagnostics, and native
chart-generation aborts under investigation. This is not a package-wide
pass. Repeated loads,
cross-owner switches, editor round
trips, cutscene paths, seeking, pause/resume, and 60/240/480 FPS parity still
require complete native evidence.

Release binary `b39e89c3c3b291430d42d968e57764da40d729555bf549e5d69c69f5d2c9fd91`
built after the shared overlay path, nested V-Slice music, selected-stage
warning, and smoke-only seek/phase instrumentation changes. A scoped DDTO
Auto refresh on that binary found 54 songs, skipped 54, imported none, and
failed none. Static warnings fell from 48 to 29: the 18 unselected stage
warnings and nested-music false positive are gone. The valid `_merge` patch
now reports `overlay-retained: missing-merge-base`, not target escape.
The refresh added `music/breakfast-doki.ogg` to the selected owner; all 797
preexisting owner/protected files in the backup manifest retained their hashes,
including settings and Freeplay (`tmp/vslice-ddto-after-planner-backup-20260929/`,
`tmp/vslice-ddto-after-planner-native-20260929/`). This is an importer check,
not a DDTO gameplay parity pass.

The new binary's focused replay passed Ballistic (Beta Mix) Easy and Low Rise
HQ Hard, which had native allocator aborts in the earlier sweep; those failures
are intermittent, not resolved. Ballistic HQ Easy again exited with
`Invalid field:null` after the first note was constructed but before the
256-note marker (`tmp/psych-native-crash-phase-replay-20260929/rows.jsonl`).
The new forward seek smoke on Gordonteen Bucks synchronized instrument,
vocals, Conductor and song clocks at 20,000 ms, replayed 20 crossed events,
and discarded 207 stale notes, then SIGSEGV'd on the next active-note update
(`tmp/seek-gordonteen-native-20260929.json`, coredump PID 3695964). This
first post-seek check exposed a destroyed predecessor retained by a sustain.
The shared seek path now kills retired notes before destroying them and
re-roots surviving sustain chains. The rebuilt release binary SHA-256 is
`903df272f45b21e0e8e57135502a3648c5f830d716f0b23d8bd5541728687324`.
Its Gordonteen 20,000 ms offscreen seek passed: clocks synchronized, 20
events crossed, 207 stale notes discarded, zero process diagnostics, clean
exit, and unchanged private options
(`tmp/seek-gordonteen-native-after-harness-fix-20260929.json`). The first
rerun reached the natural song ending without crashing but exposed a harness
unit conversion error; `run_seek_smoke.py` now uses millisecond units
consistently, and the passing rerun validates the repair. The new extracted
seek regression and video cutscene suites passed 11 tests.

The same new binary finished note generation for Ballistic HQ Easy and
entered gameplay on a focused replay, but its imported Psych Lua script
then emitted repeated `lua arithmetic on nil (/)` diagnostics during
`updatePost`, and the strict run timed out before a natural ending
(`tmp/psych-hq-easy-context-replay-20260929/rows.jsonl`). This is a current
shared Lua compatibility issue under investigation. The Psych archive sweep
has passed rows 60–90 (31/31); row 91 Lit Up Hard failed in the shared
head-note compatibility callback with an exact smoke context marker for
section 16, authored row 1. Subsequent rows are still being checked.

A further release build (`eb20cfa0dc824961555e8d2a32165428aef292388901c6787ba8afb81d07e02b`)
adds smoke-only subphase labels for note compatibility and an operand label
to Lua's existing nil-arithmetic error. The focused suites passed 49 tests.
Lit Up Hard and Monster Normal each passed a strict focused natural-ending
replay on this build after earlier native failures; their intermittent
failures remain unresolved. Ballistic HQ Easy again entered gameplay but
its `updatePost` division failed because its left operand,
`getSongPosition()`, evaluated to nil before song start. The live Lua bridge
is being traced; this is not yet a compatibility pass. Receipts are in
`tmp/archive-lit-up-phase-replay-20260929/`,
`tmp/archive-monster-phase-replay-20260929/`, and
`tmp/psych-hq-easy-nil-operand-20260929/`.

## Latest status — 28 September 2026

An FNAS source menu action entered native Freeplay directly and initially
SIGSEGV'd because `FreeplayState::create` assumed CategoryState had populated
`currentSongList` (`coredumpctl info 3081902`). Shared `FreeplayDirectEntry`
now resolves rows only from the selected owner; an empty owner returns safely
to its captured imported menu. A one-shot, owner-scoped caller route retains
that menu through Freeplay and ModifierState. The shared Freeplay renderer
recovers a missing source subtitle from same-folder `importProvenance.json`
while respecting explicit labels and owner identity. Focused entry, caller,
source-display, ordering, ownership, and registry tests pass.

The private offscreen FNAS route passed Continue → Freeplay → authored menu,
Options → menu, Credits → menu, and New Game → `PlayState` creation (`ui done`).
Freeplay visibly rendered `Better Clone` with the smaller
`(FNAS After Hours · Codename Engine)` subtitle. Credits Accept on the source
link logged `[codename-open-url-test-suppressed]` under the private no-browser
flag, with no host browser action or URL error. The receipt reports zero
runtime diagnostics, clean teardown, and unchanged repo/live options:
`tmp/fnas-live-owner-import-20260928/ui-routes-fnas-menu-return-fix-20260928/menu-routes-result.json`.
The latest combined-binary replay, including the legacy pending-state bridge,
passed the same four routes and Credits Accept under the no-browser gate with
zero strict diagnostics and unchanged protected settings:
`tmp/fnas-live-owner-import-20260928/ui-routes-final-recheck-20260928/menu-routes-result.json`.
Its global pre-switch trace reports concrete `legacyRequestedState` targets,
including `MainMenuState` before the authored redirect and
`CodenameImportedState` afterward; the trace now uses the same alias as
HScript. This verifies that route's native pending-state view, not every
unknown lazy factory.
An earlier runner accidentally left Shift pressed after `shift+i` and invoked
Shift+Escape `resetGame()`; a private Xvfb keymap probe identified that input
error, and the corrected runner explicitly releases Shift. Full source
visual/audio/editor parity remains open.

The D-Sides XML Options route now passes two private offscreen native sessions.
It rendered the selected owner's checkbox rows, visibly toggled Mechanics
On→Off without changing Modcharts On, and serialized `mechanics=false` in
the private owner-scoped Flixel save. The second session displayed the saved
Off value; Back returned to the authored main menu both times. Repo/live
options and the personal save hash stayed unchanged. The earlier return
failures exposed two shared gaps: `openfl.display.BitmapData` was missing from
Codename bindings, and the callback-driven outgoing sticker transition saw
`newState=null`, so it chose an empty sticker asset key. The binding and
concrete same-owner script target are now built; the imported-state runtime
uses that target path instead of bypassing it. The final trace reports
`scriptTarget=CodenameOptionsMenuCompat` on entry and
`scriptTarget=CodenameImportedState` on return, with no transition script or
asset-key error. Five focused state-trace/transition tests pass, and the
combined `./run.sh build` passed
(`tmp/build-menu-route-browser-test-gate-20260928.log`). Receipt and frames:
`tmp/dsides-options-native-transition-target-replay2-20260928/receipt.json`.
Its status is `passed_with_known_compatibility_gaps`, not a full Options
parity pass: at the time of that replay, source-only `naughtyness`, music/SFX
volume, `colorHealthBar`, `week6PixelPerfect`, quality, and developer/config
preferences were unmapped and explicitly diagnosed. Pause callbacks were outside this
menu route. The `LoadingState` lazy factory overload also has no concrete
FlxState before its callback and remains unverified.

The subsequent shared Options adapter build maps `naughtyness` with the
source default of true, music/SFX volumes with defaults of 1.0 and [0,1]
clamping into Flixel's default groups, and `colorHealthBar` to the existing
`useCharColor` behavior with a true default. These are global user preferences;
the facade preserves unrelated saved fields. A later shared adapter adds
source LOW/HIGH/CUSTOM preset values, preserves older non-HIGH graphics tuples
as CUSTOM, and exposes/persists `week6PixelPerfect` for imported scripts.
Native value/persistence checks are recorded below; pixel-camera, shader,
and low-memory effects still require source-parity checks. Developer/config
controls remain diagnosed as unsupported. Eight focused interpreter tests cover read/save, live audio
application, defaults, clamping, and preservation. The combined `./run.sh
build` passed (`tmp/build-freeplay-options-fnas-20260928.log`); the previous
D-Sides route receipt predates these direct mappings. A subsequent private
two-session replay on this binary rendered the supported Gameplay/Appearance
rows and persisted `naughtyness=false`, `volumeMusic=0.9`, `volumeSFX=0.9`,
and `useCharColor=false` in the private options overlay. The selected owner's
XML save kept `mechanics=false` and `modCharts=true`; Back returned to its
authored menu in both sessions. Repository/live options and personal save
hashes stayed unchanged. Its receipt status is
`passed_with_known_compatibility_gaps`, with strict compatibility false for
the explicit remaining options and an untested pause callback:
`tmp/dsides-options-native-preference-mappings-20260928/receipt.json`.

On the later combined binary, the private D-Sides Options route visibly
cycled HIGH → LOW → HIGH → CUSTOM, kept advanced rows locked in HIGH, allowed
a CUSTOM antialiasing edit, and toggled Pixel Perfect Effect. A second
private process reloaded `quality=2`, `week6PixelPerfect=false`,
`antialiasing=false`, `lowMemoryMode=false`, and `gameplayShaders=true`, showed
Mechanics Off / Modcharts On in the same owner's XML page, and returned to its
authored menu. The first end-to-end runner failed an antialiasing-sensitive
image-template gate despite the visible values. A session-2 resume completed
the native route, but its wrapper exited 1 on a post-run bookkeeping KeyError.
An independent offline receipt verifies the captured native traces, frames,
save fields, and unchanged private/repository/live/personal hashes without
claiming the wrapper passed:
`tmp/dsides-options-native-quality-week6-final-20260928/validated-native-evidence.json`.
These checks establish menu value and persistence behavior only; pixel-camera,
shader, low-memory effects, developer/config controls, and pause callbacks
remain open.

The splash warning audit found all eight selected Ourple animation prefixes
and four frames per prefix in the donor atlas. The cached atlas graphic was
released when the first transient splash died, invalidating later frame
lookups. The shared splash handler now retains one graphic reference for each
cached style and releases it on eviction and teardown. Its focused lifetime
tests pass 4/4. A private Xvfb/dummy-audio real-hit replay on the combined
binary emitted 122 renderable selected-owner splash markers across 115
distinct successful player hit times, with zero strict diagnostics, exit 0,
and unchanged repository/live options. Its markers cover all eight source
prefixes (four colors × two variants), and its process log has zero
`could not find animation prefix` traces. This exercises atlas reuse after the
first transient splash; it does not compare every source frame or hit-judgment
distribution. Receipt:
`tmp/runtime-smoke/logs/dsides-dguy-splash-multihit.receipt.json`.

The isolated mounted HXC Auto-import scanner passed in 91.824 seconds after
its extracted test fixture included the new per-search deduplication helper
(`tmp/hxc-mounted-auto-import-isolated-retry-20260928.log`). Its earlier
parallel-suite SIGSEGV has not recurred in isolation; concurrent full-suite
stress and native memory behavior remain open checks.

A new combined release build passes after two shared Codename corrections
(`tmp/build-transition-selector-menu-sfx-20260928.log`). Transition selectors
may omit `.hx`; the transition runtime now resolves the installed script using
the same extension convention as the importer. `CoolUtil.playMenuSFX` selects
one of six shared sound keys by ID, so the importer now stages the available
same-owner sound dependencies even when a script contains no literal
`Paths.sound` key. The D-Sides menu had selected an extensionless transition
and called the default scroll sound: its transition script was already present,
but the runtime had looked up an extensionless filename; its source
`sounds/menu/scroll.ogg` was absent from the installed owner. A backed-up,
missing-only refresh added that one sound with its source hash while 82
protected chart, provenance, and settings files and every preexisting owner
file retained their hashes
(`tmp/codename-menu-sfx-owner-refresh-20260928/apply-receipt.json`). Focused
importer, transition-scope, engine-router, camera, and event-drain tests pass.
Native transition and menu-option return checks are pending on this build.

The D-Sides selected-owner options XML rendered its two authored checkbox
rows offscreen on the preceding build (`tmp/dsides-options-native-post-binding-20260928/session-1-xml-options.png`). That session stopped at an OCR gate
for the pixel font before toggling, persistence, or return could be judged.
The shared Options host still reports source-only preference types as
unsupported, so the rendered rows do not establish full Codename Options
parity. The FNAS Switch Mod route likewise opened the grouped owner chooser
and returned to its authored main menu; a subsequent OCR spelling error
stopped its test before Options and Credits. These are incomplete test gates,
not proof of those later interactions.

An offscreen D-Sides `dguy` hard real-hit smoke recorded one visible,
renderable, owner-scoped `ourple` splash on the player receptor at 5454.545 ms
with zero strict diagnostics and unchanged settings
(`tmp/runtime-smoke/logs/dsides-dguy-splash.receipt.json`). Six other
selected Ourple variant prefixes logged missing-frame warnings in the same
run. Those warnings are being checked against the source atlas before the
splash family can be counted as source-compatible.

The user-selected `FNAS After Hours` label was used in a backed-up live
Codename import. Better Clone Normal is installed in its own owner with exact
source chart row/event counts, matching Inst/Voices hashes, and unchanged
personal settings. Its direct offscreen gameplay reached PlayState readiness.
The first imported-menu launch exposed a generic pending-state lifetime bug:
Codename HScript constructed `new PlayState()`, the outgoing interpreter
owned it as an unclaimed FlxBasic, and menu teardown destroyed it before
Flixel completed the state switch. The shared facade/interpreter now transfers
an accepted state target out of the outgoing script's cleanup list. A focused
real-interpreter regression proves rejected targets are destroyed and accepted
targets survive teardown. The installed-owner offscreen menu replay then
rendered all four authored FNAS menu choices and reached Better Clone gameplay
through New Game with zero runtime diagnostics. Both repo and live options
remained byte-identical. This closes the reproducible menu crash, while full
source presentation, audio, ending and editor parity remain unverified. The
successful receipt, screenshots, original crash and scoped import backups are
in `tmp/fnas-live-owner-import-20260928/`.

An isolated FNAS Better Clone Normal story-mode 5× **botplay** run exited 0 at
the audio boundary, with all 204 due events dispatched and no strict script
diagnostics. It transitioned to the native victory state. Source inspection
showed that botplay enables demo mode; its completion path deliberately skips
the `inst.onComplete` callback that donor `songs/hud.hx` uses to launch its
minigame. That run cannot judge source ending parity. A story/practice run
without botplay subsequently dispatched all 204 events, captured the
authored checkerboard minigame after the state switch, and exited 0 after
the smoke harness emitted `success` five seconds later
(`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-result.json`,
`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-after-song-end.png`).
The shared imported-state smoke tick passes 25 focused runtime-smoke tests.
On the combined creation/menu build, the private non-botplay story/practice
replay passed again: 204/204 due events, native exit 0, no timeout or strict
diagnostics, unchanged repo/live/private options, and a screenshot of the
authored checkerboard minigame after the song. The source `hud/oppNOTE` atlas
was applied to opponent notes and all four opponent receptors; the first
opponent tap reports `frameOffset=25,0`. The during-song frame visibly shows
the custom opponent arrows. The aggregate creation markers record 1,343 note
atlas applications and four receptor applications. This verifies the selected
creation callbacks and ending handoff for this song; full frame/audio parity,
pause, editor and remaining menu interactions remain open. Receipt and frames:
`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-result.json`,
`tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-mid-song.png`,
and `tmp/fnas-live-owner-import-20260928/story-practice-no-botplay-after-song-end.png`.

A read-only audit of the FNAS menu paths found three additional shared-layer
gaps. Its Credits state calls `FlxG.openURL`; a validated selected-owner URL
bridge is now staged in source. Its main menu requests Codename
`ModSwitchMenu`; a grouped owner switcher is also staged in source.
The donor provides `AdventPro-Medium.ttf`, `851MkPOP.ttf`, and
`Technology.ttf`, referenced by literal text-format font paths. The first
owner import missed them; a scoped missing-only refresh has now copied all
three with donor hashes matching and existing owner files, charts, registries,
and settings unchanged (`tmp/fnas-live-owner-import-20260928/font-refresh.json`).
The combined-build private menu screenshot now visibly renders the authored
menu text with the registered owner fonts
(`tmp/fnas-live-owner-import-20260928/ui-routes/fnas-main-menu.png`);
exact donor font/layout parity and the URL action remain unverified. The
mod-switch action fails the first
native Tab check, as described below.
Continue selects Freeplay, and the combined build visibly opens the new
shared Options category screen. The first private multi-route run's OCR gate
did not recognize that pixel font, so it did not establish Options return or
subsequent Credits routes; Tab also left the source menu unchanged because
`controls.SWITCHMOD` was not bound. Both gaps remain under shared-layer repair.
The installed state catalog had included `MusicBeatTransition.hx`, a helper that
needs dedicated transition context, as a standalone launch row. Six stale
missing donor roots were filtered by the chooser but still produced
missing-namespace diagnostics. A scoped, backed-up catalog reconciliation
removed those six stale rows and the transition-only launch rows while
retaining all three valid owners. The receipt proves the selected-owner trees,
charts, audio, other registries, and both options files were unchanged
(`tmp/fnas-live-owner-import-20260928/catalog-refresh.json`). The refreshed
chooser still needs native interaction checks. The previous private minigame
proof traversed all four rooms and returned to the authored menu; repeated
entry and frame/audio parity remain open.

The post-FNAS 256-row installed-runtime preflight reports 250 structurally
ready rows and six blocked raw keys
(`tmp/all-example-preflight-after-fnas-install.jsonl`). Five blocked playable
difficulties have instrumentals absent from their source packages; the sixth
is an empty, undeclared Baka key. This read-only preflight launches no game
and does not count as source presentation or interaction parity.

The combined binary also passed the isolated native `ChartingState` companion
event round trip for imported Psych `2Hot` Hard. The editor loaded two private
fixture events, edited one, deleted the other, Quick Saved, reloaded, and
collected the edited event once while suppressing the deleted event at
runtime. The source chart and sidecar and repo/live options remained unchanged;
the process exited 0 with no strict diagnostics
(`tmp/runtime-smoke/logs/chart-editor.process.log`, run token `0.21`). This
tests one owner/difficulty editor path, not every imported chart format.

Codename's selected-owner options XML is now staged by a bounded importer
planner. A scoped missing-only refresh installed D-Sides' authored
`data/config/options.xml` in its existing owner. The target hash matches the
mounted selected-mod source; 928 preexisting owner files, 78 owner-chart JSON
files, and repo/runtime options retained their hashes
(`tmp/dsides-options-refresh-20260928/apply-receipt.json`). Focused importer
and menu tests pass 37/37. Native checkbox interaction and persistence are
still under verification.

The shared Codename importer now stages selected-owner OBJ `mtllib` sidecars
and their `map_Kd` diffuse textures when those source files exist. Focused
dependency and discovery tests pass 3/3 and 10/10. The mounted HL17 package
has no MTL to stage, so its runtime warning remains a source dependency
finding. Other MTL texture directives are outside the current runtime loader's
supported subset and must be diagnosed if encountered. The FNAS owner also
received a missing-only two-file `hud/oppNOTE` atlas refresh, with donor hash
parity and unchanged old owner files, catalogs and settings
(`tmp/fnas-live-owner-import-20260928/missing-hud-refresh.json`). Importer
collection of literal note/receptor sprite keys passed focused tests. The
combined native replay above confirms atlas use in gameplay, while the
complete rendered source comparison remains open. Shared Codename creation
callbacks now support mutable pre/post note and receptor events, cancellation,
atlas metadata, and writable note frame offsets; a focused Haxe interpreter
test passes. Custom note-splash rendering and unnamed pixel receptor prefix
changes remain explicitly diagnosed unsupported paths.

A shared Away3D direct-readback candidate built and passed standalone Haxe
byte-path tests, but its native same-frame comparison against OpenFL's snapshot
reported 14,745,600 mismatches across 14,745,600 bytes. An active-scene
screenshot still rendered the desk, actors and floor, which makes the native
pixel mismatch the decisive failure. The candidate was rejected, the
existing full-resolution snapshot renderer was restored and rebuilt through
`./run.sh build`; no internal
resolution or draw-frequency cap is accepted. The mismatch receipt is
`tmp/hl17-menu-native/gordonteen-3d-fast-readback-480.process.log` and its
screenshot is `tmp/hl17-menu-native/gordonteen-3d-fast-readback-480.png`.
The Gordonteen FPS/RSS issue remains open; a 60/240/480 run of this rejected
candidate would not establish an improvement.

The pre-FNAS raw matrix had 256 chart keys; one DDTO++ Baka key is empty and
undeclared, leaving 255 playable source song/difficulty rows. Of those, 249
had owner-matched installed charts and required instrumentals; six were
structurally blocked (`tmp/example_mods_current_chart_matrix_after_psych_promotion.json`,
`tmp/all-example-preflight-after-psych-promotion.jsonl`). The 76 playable
Psych archive rows passed one isolated offscreen natural-ending sweep, and
three installed samples passed separately. One archive row passed the native
Imported Freeplay → ModifierState → PlayState route. These are distinct gates;
none establishes source-rendered, audio-mix, all-editor, cutscene, pause, or
seeking parity across every row. The Freeplay source subtitle and generated
All-category title ordering build succeeded. A native offscreen Freeplay route
selected the D-Sides Tutorial from the generated All list, where the base
Tutorial preceded it and Psych Tutorial followed it. The selected row reported
`Tutorial` as its title and `D-Sides REDUX · Codename Engine` as its separate
source label; it entered ModifierState and PlayState with zero diagnostics
(`tmp/freeplay-tutorial-native-final.json`,
`tmp/freeplay-tutorial-native-final.markers.jsonl`). The offscreen
driver retried one missed ModifierState Enter press and reached PlayState on
its second bounded send. A registry/provenance
audit recovered source labels for all 35 installed owner-qualified entries,
including one older record without a stored mod name. The native editor
round-trip for an owner-qualified Psych chart passed edit, delete, Quick Save,
reload and runtime event collection with zero diagnostics
(`tmp/chart-editor-after-marker-fix.json`). This exposed and drove shared fixes
for missing editor section lengths and split-vocal previews. The smoke uses a
private runtime overlay; source chart, event sidecar and options were unchanged.
The automated suite passed 1,366 tests across 409 modules, 61 skipped and
zero failed (`tmp/full-suite-freeplay-editor-final.log`). A later generic
receipt-based title-sort edge case and offscreen input retry passed focused
tests and a native menu rerun; another exact snapshot suite is due after the
ongoing importer work.

The Psych archive's `psych_v1_convert` charts use absolute note sides in
their source runtime, while the old native section-relative rule had assigned
most Ugh notes from both singers to the player. `ChartNoteOwnership` now reads
that authored format, and `Song.loadFromJson` retains it through difficulty
merging. All three Ugh difficulties passed isolated offscreen native startup
with zero diagnostics and player/opponent head counts matching their source
charts: Easy 141/155, Normal 227/241, Hard 256/270
(`tmp/psych-ugh-all-difficulties-note-sides.jsonl`). Hard also reached an
accelerated 20× natural ending with zero diagnostics
(`tmp/psych-ugh-hard-ending-native.json`). On the rebuilt engine, Normal
reached its natural 86,616 ms ending at 1× rate, dispatched 11/11 due events,
reported zero diagnostics, and left installed options unchanged
(`tmp/psych-ugh-normal-rate-final.jsonl`).
An archive-wide static audit matched the source format and player/opponent
head counts to all 76 installed Psych archive charts; Ridge and Smash remain
unimported because their source instrumentals are missing
(`tools/tests/test_chart_note_ownership.py`).
The check covers note ownership and ending; rendered lane geometry and the
source audio mix remain outside this gate. No chart, donor asset, or options
file was changed.

The pasted D-Sides Try Harder scene-array, shader scalar, actor-access and
transition warnings are covered by existing shared fixes. Nine focused checks
passed, and its installed snowfall shader compiled through the OpenFL GLSL
normalizer. A current-binary normal-rate offscreen replay exited with SIGBUS
in OpenFL/Mesa texture upload after a desktop game instance started five
seconds earlier, so this overlapping run was inconclusive. A subsequent
isolated current-binary 1× replay reached its natural 262,022 ms ending,
dispatched 657/657 due events, reported zero diagnostics, and left options
unchanged (`tmp/dsides-try-harder-current-binary.jsonl`). This establishes a
clean playthrough on this build; visual parity still needs source comparison.

For the reported Gordonteen Bucks layering defect, the donor stage calls
`insert` on the same 3D view before GF, Dad and BF. Flixel's group `insert`
leaves an existing member where it is. The Codename script bridge instead
removed and reinserted the view on each call; its before capture showed the
floor over GF's desk atlas. The shared bridge now follows Flixel's existing
member behavior; later duplicate insertions leave the first index unchanged.
The latest original-resolution offscreen capture shows the desk and characters
in front of the floor
(`tmp/hl17-menu-native/gordonteen-3d-final-original-resolution.png`). Live
scene telemetry held the 3D view at index 27, GF at 29, BF at 31 and Dad at
48 across draw frames 2, 60, 300, 360 and 420. The renderer retained its
authored 2560×1440 bitmap. A temporary resolution budget was removed; its
earlier 480-FPS setting comparison is diagnostic history, not an accepted
compatibility change (`tmp/hl17-menu-native/gordonteen-perf-before-480.json`,
`tmp/hl17-menu-native/gordonteen-perf-after-480.json`).
The capture and indices verify the sampled Flixel composition order; they do
not establish donor parity for the Away3D floor-versus-desk depth appearance.
That visual parity question remains separate from the shared renderer's
allocation work.

The same native run reached the complete GameOver death-character construction
path and exited 0. The crash was a shared Codename character case: an owner
had character metadata, but the death replacement had no live XML definition;
orientation code dereferenced that absent definition. The orientation helper
now uses available live animation names, and a focused interpreter test covers
the null-definition case. The sole runtime diagnostic was a missing
`testStage.mtl` named by the package's `plane.obj`. A read-only audit found no
`.mtl` file anywhere in the mounted HL17 source package, and source/imported
`plane.obj` match SHA-256
`3c1a1c89c01718e0f639e73bf9254a8cd351a03991ff51356044da506112fed0`.
The stage passes `textures/gradient` explicitly as the model texture, and
Away3D continues without MTL data. No source asset was
changed. This run left repo defaults, private defaults and installed personal
settings byte-identical (`tmp/hl17-menu-native/gordonteen-final-3d-death.json`,
`tmp/build-gordonteen-death-and-layer-live.log`). The 16-second smoke reached
40–120 FPS in sampled windows and 1,140.2 MiB peak RSS with default test
settings. It does not resolve the reported 480-FPS setting slowdown or RAM
oscillation. The earlier isolated 60-cap baseline peaked at 1,148.6 MiB RSS
and mostly ran 62–66 FPS (`tmp/hl17-menu-native/gordonteen-perf-baseline.json`).
Source inspection identifies the current full-resolution 3D compositor
bottleneck. `FlxView3D` retains one 2560×1440 `BitmapData` and, while
`dirty3D` is true (the default), asks Away3D for a snapshot on each view draw.
The pinned Away3D renderer calls OpenFL `Context3D.drawToBitmapData`; its
separate-backbuffer-texture path allocates a fresh 14,745,600-byte pixel array
and reads the full frame, then copies the image into the destination bitmap.
Flixel uploads the changed bitmap as a texture when drawing it. The sprite's
camera loop completes before `FlxView3D` performs one snapshot, so cameras do
not multiply the readback within a view draw. This GPU-to-CPU readback/copy
followed by a CPU-to-GPU upload is a plausible source of FPS loss and memory
churn, but the short receipts do not record which OpenFL context branch ran or
per-sample RSS. They do not establish the user's reported 1.3 GB oscillation.
No zero-copy replacement has passed visual verification yet. An experimental
GPU texture path avoided the readback but rendered a blank stage in an
offscreen screenshot, so it was removed from source and is not accepted as a compatibility fix
(`tmp/hl17-menu-native/gordonteen-3d-gpu-current-480.png`,
`tmp/hl17-menu-native/gordonteen-gpu-current-capture.json`). The restored
snapshot source rebuilt through `./run.sh build` and passed an offscreen
480-cap capture. Its first nine-second screenshot fell earlier in stage setup
and showed only the plane; a ten-second capture showed the desk and all visible
characters in front of the plane, with 25-point snapshot samples containing
nontransparent pixels and unchanged settings
(`tmp/build-restored-3d-snapshot.log`,
`tmp/hl17-menu-native/gordonteen-snapshot-restored-late-480.json`,
`tmp/hl17-menu-native/gordonteen-3d-snapshot-restored-late-480.png`). A
120-cap nine-second capture also showed the desk and characters, but these
wall-time screenshots were taken at different song positions because 3D
startup took about one second longer in the 480 run. They do not establish
frame-matched 60/240/480 equivalence. The full authored resolution remains in
use; no bitmap size or render-frequency cap is active.
The corrected smoke-only probe reads the render target before restoring the
backbuffer. It found a complete FBO with transparent sampled pixels at draw
frames 2 and 60, while Flixel's bitmap shader requested and matched the
borrowed texture on all 58 intervening requests. A second bounded 16-by-9
grid found zero nontransparent samples at both frames with scissor disabled;
the accompanying screenshot still omits the 3D floor. This confirms that the
experimental GPU target is not visually usable and does not establish source
visual parity (`tmp/hl17-menu-native/gordonteen-3d-gpu-current-480.process.log`,
`tmp/hl17-menu-native/gordonteen-3d-gpu-current-480.png`).
An isolated current-binary baseline at saved caps 60, 240 and 480, changing
only each run's private test options, reached active-scene median sampled FPS
of 60, 80.5 and 80 respectively. All runs exited 0 and left installed and
repository settings unchanged. Peak sampled RSS was 1,207.6, 1,188.3 and
1,183.8 MiB; median RSS was 1,097.9, 1,081.5 and 1,072.1 MiB. The separate
FlxG bitmap census had median/max estimated sizes of 188.5/229 MiB and does not
account for most process RSS. Post-death windows without the 3D view reached
their requested 240/480 FPS, isolating the live scene as the pacing limit in
these runs. These bounded smokes do not show that the reported 1.3 GB
oscillation is eliminated; no RSS time series was retained. The only
diagnostic in each run was the package's missing `testStage.mtl`
(`tmp/hl17-menu-native/gordonteen-perf-gpu-before-60.json`,
`tmp/hl17-menu-native/gordonteen-perf-gpu-before-240.json`,
`tmp/hl17-menu-native/gordonteen-perf-gpu-before-480.json`).
The shared OpenFL 9.5.2 patch now retains one readback byte array and one source
`Image` per `Context3D`, rebuilding them only when the backbuffer dimensions
change and clearing their references when that context is disposed. The full
readback, bitmap copy and Flixel texture upload are unchanged. The exact-source
patcher and build-hook checks passed with
`python3 -m unittest tools.tests.test_openfl_context3d_readback_patch tools.tests.test_build_scripts`
(20 tests); a coordinated build and native visual/memory check are still
pending. This bounds repeated staging allocations in source but does not claim
to resolve the measured FPS bottleneck or reported RSS oscillation.

The importer now records an authored package ID or a bounded selected-chart
and audio-manifest fingerprint with its destination-only provenance. A moved
root can reuse a known owner when the ID matches, or when its label and
fingerprint both match. A private second-package fixture with the same title
received a distinct destination and left the first chart and compatibility
manifest byte-identical. Ownership, script-manifest, package-name prompt and
import-workflow suites passed 49 focused tests. The native release build then
passed with these importer changes (`tmp/build-after-owner-and-psych-sides.log`).
Four standalone Haxe test fixtures were updated to include the new shared
ownership helper; their 13 targeted tests pass. An interactive scoped refresh
is still pending. Existing receipts lacking an
identity/fingerprint fail closed on moved roots; they are not rewritten.

D-Sides Blammed Easy and Normal were present as installed charts but the older
generated Codename resolved-metadata sidecar listed Hard alone. A scoped
refresh copied only that sidecar from a private full donor import after
checking song identity, all three chart difficulties, and unchanged existing
Hard metadata. The previous bytes and hashes are in
`tmp/dsides-blammed-meta-refresh/receipt.json`. Easy then reached its natural
128,704 ms ending with 231/231 due events, and all prior `SONG.meta` null
diagnostics disappeared. The shared Codename fallback now resolves missing
source character definitions through the owner's declared fallback. After
rebuilding, both Easy and Normal
reached their natural 128,704 ms endings at 20× with 231/231 due events,
zero strict compatibility diagnostics and unchanged settings
(`tmp/dsides-blammed-easy-normal-identity-native.jsonl`). The earlier failed
Easy run remains diagnostic evidence
(`tmp/dsides-blammed-easy-after-metadata-refresh.jsonl`). A normal-rate
playthrough at 1× also reached the natural ending with zero logged diagnostics
and unchanged settings (`tmp/dsides-blammed-easy-1x-native.json`). Its
mid-song screenshot is a **failed visual gate**: the gameplay scene is flat
gray while the HUD remains visible
(`tmp/dsides-blammed-easy-1x-mid.png`). A disposable diagnostic that removed
only the camera shader attachment from a copied owner stage script rendered
the full stage and characters at the same point
(`tmp/dsides-blammed-easy-no-camera-shader.png`). The shared camera shader
bridge was isolated and repaired in the shared interpreter; no donor or
installed chart was edited.
The visual check also exposed an importer/runtime identity mismatch: generated
metadata already maps missing IDs to the fallback host, but the live primary
actor plan previously marked fallbacks only when that map entry was null. A
shared plan fix and production-shaped interpreter test pass; native visual
verification awaits the next build (`tools/tests/test_codename_actor_plan.py`).
A bounded private camera-filter probe isolated the gray output to the shader
uniform bridge. The stage assigns authored `contrast=1.0` and
`saturation=1.0`; on the native prepared-script path both reach
`CodenameScriptInterp.setShaderParameter` as `TInt` values of 1, although the
GLSL declarations are FLOAT. The old bridge calls `setInt`, leaving both
OpenFL float parameter values null. Decimal values such as brightness use
`setFloat` and retain their values. A passthrough camera filter rendered the
scene, while the original numeric filter rendered gray. The shared bridge now
dispatches by declared uniform type and the canonical build passes. Two
isolated offscreen replays on that build exited 0 with zero runtime
diagnostics: the original owner script rendered its full stage and actors
through the authored color-correction filter, and a private copy with only
the filter attachment removed rendered the same stage without that color
correction. Their screenshots differ in 106,595 pixels. Donor, installed and
pre-run overlay stage hashes matched, and the installed personal options were
unchanged. This closes the reported flat-gray D-Sides visual failure at the
sampled scene; full source color parity remains unmeasured
(`tmp/codename-shader-fixed-20260928/original.png`,
`tmp/codename-shader-fixed-20260928/no-shader-control.png`,
`tmp/codename-shader-fixed-20260928/preflight.json`,
`tmp/codename-shader-fixed-20260928/original.process.log`)
(`tmp/dsides-camera-uniform-values-instrumented.process.log`,
`tmp/dsides-camera-uniform-values-instrumented.png`).
A read-only cross-check of the inventoried Codename rows against all 24
installed resolved-metadata sidecars found no other missing selected
difficulty after this scoped refresh.

The shared Codename importer now stages a compiled installation's declared
base-character XML and exact atlas under its selected mod owner when that
owner lacks its DEFAULT_CHARACTER definition. The dependency is allowlisted
and SHA-256 receipted; runtime resolution still selects character scripts
from the mod owner and uses only the receipted visual files. The actual HL17
installation plan selected `data/characters/bf.xml` and
`images/characters/bf.png`/`bf.xml`. A staged private materialization resolved
those bytes, and a scoped missing-only refresh added four files (three assets
plus receipt) to the installed HL17 owner. A pre/post hash audit found all
212 existing owner files and both settings files unchanged. The combined
native build and 35 focused Codename tests pass
(`tmp/hl17-base-character-refresh-20260928/apply-receipt.json`,
`tmp/hl17-base-character-refresh-20260928/backup-manifest.json`,
`tmp/build-codename-shader-base-fallback.log`,
`tmp/codename-base-fallback-focused-final.log`). A read-only check of the
three installed Buck chart camera entries found `missingCharacters: []`, and
their actor IDs resolve to owner-local XML. Those songs therefore do not
exercise the receipted default-character fallback during ordinary gameplay;
the scoped materialization and runtime resolver have focused tests, while a
native fallback rendering check remains pending. This file refresh is not
itself a gameplay pass.
The first combined full-suite run exercised 1,387 tests and failed three
extracted fixture modules because their standalone `SongImport` typedefs and
Codename discovery method list lagged behind the new shared importer fields.
Those fixture surfaces were updated, and all seven affected focused tests
passed against the mounted donor roots in 301.6 seconds
(`tmp/full-suite-20260928-after-codename-fixes.log`,
`tmp/focused-fixture-after-codename-base.log`). A complete rerun on the final
source is still required.
The Wacky World `PVE_VideoModule` unsupported callback warnings cited in
older 24 September goal logs are stale: later offset and full-song logs use
the shared `hxc-hxc-video-module-adapter` without those body warnings. A
read-only donor/runtime audit found matching video resync timing, pause,
resume, focus and teardown logic; four focused adapter tests pass. A direct
native `PVE_VideoModule.createVideo` lifecycle run remains unverified. Prior
native video checks exercised the separate chart-event cutscene route.

Known source/dependency gaps include the two archive songs without source
instrumentals, three PERFEXION Extra/Extras/Gallery entries without package
audio or playable declaration, FNAS pending live import with the user's
selected `FNAS After Hours` label, the
DDTO++ `dokicon.png` icon absent from the mounted package, and the ModdingPoop
Cursed Expurgation stage's missing sound/function references.
Later chronological sections record each diagnosis and any superseding fix;
these remain open compatibility gaps, not passing rows.

A read-only HL17 donor execution probe found its Windows executable and set
up a private Wine/Xvfb sandbox, but bounded Wine initialization produced no
positive completion marker. The donor game was not launched and no source
Linkinteen pose/video capture was obtained. The disposable prefix/cache was
removed; `tmp/hl17-source-wine/attempt-receipt.json` retains the failed
probe. Source-versus-native rendered character placement remains unverified.

## 28 September diagnostic correction and archive audit (in progress)

The offscreen runtime and full-playthrough gates now count
`[hscript-null-operand]`, `[hscript-null-iterator]`, and missing HXC window
icons as diagnostics. Earlier
"strict" passes that omitted these lines must be rechecked. A read-only scan
of saved process logs found null arithmetic in 37 logs (98 lines) and a
missing HXC window icon in 99 logs (139 lines); logs include repeated and
older builds, so these are diagnostic counts, not unique chart failures.
The DDTO++ owner requests `dokicon.png`, but the mounted package has no such
file. That is a source dependency gap, not a verified visual pass. The HXC
`Constants` facade now includes source-backed V-Slice strumline and timing
values, including X/Y offsets 48/24; focused interpreter and gate tests pass.
Current native replays and source visual comparison remain pending.
A corrected scan of eleven previously cited DDTO++ song receipts found newly
counted diagnostics in all eleven, chiefly the absent icon and, in two songs,
null arithmetic. Their earlier "passed" labels are superseded by
`tmp/ddto-reclassification-after-null-diagnostics.json` until rebuilt native
replays clear engine faults or an explicit source dependency is recorded.

The Psych archive was imported into a physical private copy of the release
runtime under the canonical runtime lock. The importer reported 26 songs
imported and zero failures. The route audit matched **76/78** source chart
rows to selected-owner charts with equal source note-row counts; Ridge and
Smash have no source instrumental and were not imported. The live options,
Freeplay registry and protected base Monster Hard chart hashes were unchanged.
Fontconfig created three symlinks within the private runtime cache; all
resolve inside the private copy. Receipt:
`tmp/psych-archive-isolated-import-v5/result.json`. This is structural import
evidence, not a 76-chart gameplay, audio, editor or menu pass.
All 76 owner-matched rows passed private preflight for chart, ownership and
instrumental (`tmp/psych-archive-isolated-import-v5/private-preflight.jsonl`).
The first offscreen natural-ending replay passed 2Hot Easy, Hard and Normal
with one ending each, no interpreter diagnostics and unchanged live options
(`tmp/psych-archive-isolated-import-v5/2hot-three.jsonl`). The other 73
playable archive difficulties have not passed this native gate yet.
The second private replay passed Satin Panties Easy, Hard and Normal on the
same gate (`tmp/psych-archive-isolated-import-v5/satin-three.jsonl`), leaving
70 playable archive difficulties without a full-song native check.
The combined `./run.sh build` succeeded and preserved the live options hash.
The first parallel full suite on this source snapshot ran 1,346 tests across
402 modules with 61 skips and one failing mounted HXC diagnostic-count
assertion (five expected, one observed). The executable mounted safety
inventory itself passed with three remaining unsafe callbacks. The aggregate
scanner count is being reconciled before a clean suite is claimed. Receipt:
`tmp/full-suite-after-character-stage-diagnostics.log`.
On that build, Rabbit Hole Normal reached its natural ending at 159,566 ms with
all 592 due events dispatched and zero newly counted script diagnostics,
including no indexed-offset null arithmetic
(`tmp/rabbit-hole-after-global-offset-bridge.jsonl`). This verifies the
runtime bridge along the played path; ghost-image visual comparison remains
open.
The rebuilt DDTO++ Cheerful Vision Normal replay reached its natural ending
with 8/8 events and zero counted diagnostics, clearing the previous Evil
Clubroom Sayo callback failure. Catfight Normal reached its ending with 38/38
events; its only diagnostic was the source package's absent `dokicon.png`.
The remaining two rows of `tmp/ddto-target-after-shader.jsonl` were still
running when this report section was written.

## Complete Example Mods goal audit (24 September, in progress)

The mounted package inventory has been rebuilt before coverage is claimed.
The completed package index is
[example-mods-compatibility-inventory.md](example-mods-compatibility-inventory.md).
At the first audit snapshot, its per-chart matrix mapped 161 of 177 package
difficulty entries to installed chart files with matching owner and
source-variant provenance, but only 143 of those 161 also matched the source
note-row count. The later normalized matrix in the inventory maps 168 of 177
entries, with 150 matching source note-row counts. The 18 mismatches
include D-Sides `blammed` hard (1,019 source notes, 400 installed rows),
`hopkins` (526 versus 436), and six Vs Tricky difficulty rows. They require
importer investigation or an owner-scoped refresh before their runtime starts
count as source-chart checks. The first snapshot had 16 explicit import gaps;
the normalized matrix has nine.
The previous 96-song Auto winner count in `port-assets.md` describes a selected
subset, not every song and difficulty in the current mounted donor. Current
per-package path inventories are retained under `tmp/`; they distinguish
declared difficulties, valid chart files, script and media dependencies, and
installed runtime owners. The Psych source archive is inventoried separately
from playable package roots. No donor content was changed for this audit.
The corrected read-only diagnostic scan invokes production discovery for all
16 roots. It sees 133 raw candidates, including 49 Codename candidates across
seven roots; 24 Codename records remain after owner/duplicate selection. The
scanner reports 84 missing character-atlas findings in Codename packages and
three missing PERFEXION donor dependencies. The separate writer audit still
reports three failed Codename imports and 25 chart comparison errors overall,
including a `hopkins` comparison; the discovery-only pass is therefore a
coverage inventory, not an import success claim. The earlier zero-Codename
result in `tmp/goal-20260924-mounted-scan.log` came from a stale fixture.

The first exhaustive owner-matched **startup** gate launched all 161 mapped
song/difficulty entries offscreen with private default options. It reached
startup markers in 153 and aborted in eight DDTO++ entries with native heap
corruption. Passing markers do not imply gameplay compatibility: the logs
include missing Codename atlases, 41,787 missing-default-Psych-skin lines,
stage API gaps, HScript exceptions, and 39 zero-frame actor snapshots. The
machine-readable results and diagnostic counts are in
`tmp/example_mods_startup_gate.jsonl` and
`tmp/example_mods_startup_summary.json`; process logs are under
`tmp/runtime-smoke/logs/example-matrix-*.process.log`.

Subsequent shared fixes resolve the selected-owner default Psych note-skin
lookup, allow exact native base-character art when a Codename owner has only
an incomplete local character folder, expose Psych's `addCharacterToList`,
and stage Codename `.pack` event scripts. The V-Slice importer now discovers
declared alternate song variations and keeps their selected audio and vocal
stems distinct. The canonical `./run.sh build` succeeds
(`tmp/example-mods-native-build.log`). Five selected post-build native starts
passed (`tmp/example-mods-postbuild-selected.jsonl`); the skin warning is absent
there, while stage `front`, XML parse, and HXC `save` exceptions remain in the
logs. A further generic stage-constructor preference translation passed its
focused source test and a second canonical build. On the same DDTO++ case,
`EUnknownVariable(save)` disappeared from the post-build process log
(`tmp/example-mods-hxc-save-postbuild.json` and its process log). This remains
an opening check, not a full stage-behavior comparison.
The ten installed named regression rows also reached startup markers on the
second build (`tmp/example-mods-native-named-postbuild.jsonl`), including two
Wacky World difficulties. They are 1.2 s isolated runs; they do not cover
song endings, source audio/visual parity, or the intermittent heap abort.
Two private recycler-instrumented Auto scanner runs completed without an
invariant violation (`tmp/example-recycler-diagnostic-run.log` and `-2.log`).
A full private AddressSanitizer scanner also completed within a 900 s bound
without a sanitizer finding (`tmp/example-asan-diagnostic-run-900.log`); the
first 300 s ASan attempt hit its timeout after discovery output. These passing
diagnostics do not clear the eight saved native heap aborts; the first
corrupting transition remains unidentified. On the latest build, a replay of
the eight formerly aborting DDTO++ startups passed six and aborted two again
with glibc heap corruption (`god-eater-monika-mix` and `knives`, exit 134;
`tmp/example-mods-eight-aborts-postbuild.jsonl`). New matching-build cores
are retained for allocator inspection.

The post-build parallel source suite ran 1,033 tests across 279 modules in
86.4 s with 61 skips and **seven failing modules**. The failures are source
fixture dependency and stale assertion issues introduced by the new importer
paths; the run is not a passing gate. Details:
`tmp/example-mods-full-suite-postbuild.log`. The earlier 1,024-test pass below
is the pre-change baseline only.

After fixture repairs, the next suite ran **1,040 tests across 279 modules in
253.4 s, with 61 skips and one failure**
(`tmp/example-mods-full-suite-after-fixtures.log`). The remaining failure is
the mounted Auto scanner's `missing-health-icon` count: 86 actual findings
against an older expected zero. The scanner emits these from Codename character
conversion when non-native icon references cannot resolve under that candidate
root's `images/icons/`. Its aggregate includes duplicate pre-selection roots;
selected-owner dependency counts are still being separated. The assertion has
not been relaxed. A focused Haxe runtime test now
binds source Codename GF lines to projected CPU notes and checks the selected
singer, but the corresponding importer projection and native D-Sides run are
still pending. The latest `knives` core confirms the same recycler pointer
appearing at two indices immediately before the second free; the insertion
that caused the duplication has not yet been located
(`tmp/example-allocator-audit.md`).

FNAS script support now includes owner-scoped `Paths.video` and
`Assets.getPath`, a scoped `CustomShader` constructor, and a native
`FlxVideoSprite` binding whose constructed bitmap is released even if a
script fails before adding the video to the scene. The native `FlxTypedGroup`
binding and bounded GLSL float-literal bridge fixed initial PlayState and
shader compile errors. `CodenameScriptInterp` provides the source
`lerp(from, to, ratio)` helper to song, stage and event scripts. Chart-event
dispatch advances its cursor before callbacks and drains through `songLength`
at native audio completion, preventing missed tail rows and re-entrant
duplicates. Focused tests cover these shared paths. Smoke-only
`--smoke-require-song-end` and `--smoke-codename-visuals` flags verify natural
completion and emit bounded owner-relative visual state without changing normal
launch behavior.

The build-7 private Xvfb replay used repository-seed options in an isolated
runtime overlay. It imported the real FNAS `better-clone` normal chart with
1,224 notes (479 on opponent, 745 on player, and an empty third/GF line) and
all 204 authored events; office, clone, bffnas and guardgf resolved. Instrumental
and vocal bytes, three event `.pack` payloads, both videos and the shader matched
their donor hashes. Natural audio completion was observed at 206,896 ms with
`dispatchedEvents=204/204`. The terminal source Camera Flash at 200,689.655 ms
was delivered and routed to native `Camera Fade @ 200690ms` with `v1=false`
and `v2=50`. Smoke telemetry recorded the owner-scoped ConfettiHUD video as
loaded/playing with `CoolRuntimeShader`; the delayed screenshot visibly shows
its green particles over the office and actors. The event-time screenshot also
shows the stage and all three actors. No Codename script, HScript, asset or
event errors were logged. The eight protected installed paths, including live
options and selected owner files, retained their hashes; repository seed
options were unchanged. Receipt and marker stream: `tmp/fnas-native-preview/result.json`
and `normal-play.markers.jsonl`; screenshots: `confetti-event.png` and
`confetti-playing.png`. The initial timed-window run did not prove natural
completion; the corrected build-7 replay does.

This validates the single real-media FNAS song's chart, event, stage, actor,
video and shader paths. FNAS cutscene skipping, custom menu/state callbacks,
pause/resume through an opened menu, restart/song-switch cleanup, editor
round-trip and failure recovery still need source-matched native checks before
the package can be marked fully compatible.

The stricter full-song offscreen gate also reached the natural ending for VS
Freddy's `slaughter-easy` on build 10: its 203.100 s instrumental completed at
5x playback, the native process exited normally, there were no tagged
interpreter errors, and the private default options were unchanged. The chart
has no authored events, so its `0/0` event marker does not exercise event
dispatch. Evidence: `tmp/example-full-playthrough-slaughter-easy-build10.jsonl`
and the linked process log. This is one of nine VS Freddy difficulties; it does
not yet establish rendered source parity or the remaining playthroughs.

The Psych v0.2.8 source archive was extracted only under
`tmp/psych-archive-source` and passed the current production writer audit
against that directory. Auto discovery selected 26 song candidates with
source audio; the writer imported all 26 with no duplicate or failure, checked
all 76 difficulty chart payloads and 16 event sidecars, and left donor chart
bytes unchanged. The retained preview in `tmp/psych-archive-current-preview`
contains bounded audio markers, so it cannot be used for native playthroughs.
The archive's other two chart songs, `ridge` and `smash`, have no source
instrumentals and remain explicit source-audio blockers. The current
255-row full-playthrough preflight reports 156 structurally ready rows and
99 blocked rows, including all 78 Psych archive rows because none has a
private real-media runtime owner yet. Evidence:
`tmp/psych-archive-current-preview.log` and
`tmp/example-full-playthrough-current-preflight.jsonl`.

The same gate played `future-sound` to its 205.333 s natural ending on build 10
with all nine events delivered and no native abort. It failed on one explicit
visual dependency: the donor metadata selects `no-gf` as the opponent, while
neither donor gameplay icons nor the installed icon registry defines that id.
The donor has a separate `no-gfpixel.png` freeplay icon; its use in gameplay is
not established. The native fallback draws the neutral icon grid. Evidence:
`tmp/example-full-playthrough-future-sound-build10.jsonl` and its process log.

Source review resolved the expected gameplay presentation. V-Slice v0.3.2
instantiates the opponent health icon only if `CharacterDataParser.fetchCharacter`
returns a character; with this package's undefined opponent `no-gf`, the source
shows no opponent icon. Its generic missing-icon fallback uses the base `face`
icon, so `no-gfpixel.png` is unrelated to this gameplay slot. The shared native
`HealthIcon` now keeps a hidden `face` backing sprite for `no-gf` in the
gameplay HUD and restores visibility when a real character replaces it;
Freeplay's separate icon identity remains untouched. The isolated interpreter test
`tools/tests/test_health_icon_no_character.py` passes. A new native full-song
replay is pending. The Freeplay menu still needs the separately authored
`images/freeplay/icons/no-gfpixel.png`: V-Slice 0.3.2 resolves this through its
pixel-icon path, while the current imported owner lacks that asset and native
Freeplay shows its fallback. Source: [V-Slice 0.3.2 PlayState character setup](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/play/PlayState.hx),
[health-icon fallback](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/play/components/HealthIcon.hx),
 [default icon constant](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/util/Constants.hx),
and [pixel-icon path](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/play/character/CharacterData.hx).

Two more build-10 full-song runs reached their natural endings: `rabbit-hole`
at 159.566 s with 592/592 events, and `expurgation` Hard at 193.073 s with
126/126. Both failed the strict compatibility gate. Rabbit Hole still has an
unsupported HXC shader/options callback body, and Expurgation logs six HXC
module and note-kind payload/callback gaps. Their native exits and event totals
are useful stability evidence, but neither is a source-parity pass. Results:
`tmp/example-full-playthrough-rabbit-hole-build10.jsonl` and
`tmp/example-full-playthrough-expurgation-build10.jsonl`.

The unattended build-10 `ballistic` Hard full-song attempt timed out before
`song_end`, with no interpreter error. Its PlayState reached the authored intro
dialogue and remained there because the offscreen runner sent no confirm or
skip input. This case needs an input-driven replay in the same private Xvfb
environment before its gameplay can be judged. Evidence:
`tmp/example-full-playthrough-ballistic-hard-build10.jsonl` and its process log.
An isolated follow-up focused the game's own Xvfb window and held Return four
seconds after `playstate_ready`; the visible dialogue advanced from “ENOUGH.”
to its second authored line. The prior 1.5-second input attempts preceded the
dialogue-ready frame. This verifies ordinary input delivery but still does not
reach Ballistic gameplay or test the secondary-key skip. Screenshot:
`tmp/ballistic-intro-return-delayed-build10.png`; input log:
`tmp/runtime-smoke/logs/ballistic-intro-return-delayed.process.log`.
The same private driver held the default secondary key (`E`) after dialogue
was active. Ballistic then left the intro, dispatched its chart event at 0 ms,
and reached song position 4,600 ms before the short window ended. This verifies
the native skip handoff, not its full-song ending. Evidence:
`tmp/runtime-smoke/logs/ballistic-intro-e-delayed.log` and its process log.
The complete input-driven build-10 replay of `ballistic` Hard then reached its
153.405 s natural ending at 5x, delivered all 16 chart events, exited normally,
logged no interpreter diagnostics, and preserved the private default options.
The private gameplay screenshot shows the post-dialogue actors and live notes.
Evidence: `tmp/example-full-playthrough-ballistic-hard-skip-delayed-build10.jsonl`
and `tmp/ballistic-hard-skip-gameplay-build10.png`. This clears the previously
unattended intro timeout for this one difficulty; audio/visual source matching
and other Whitty difficulties remain to verify.

The offscreen source suite passed **1,024 tests across 277 modules in 168.7 s;
61 skipped, zero failed** (`tmp/goal-20260924-suite.log`). The focused
Expurgation timer/drain fixture passed nine tests after adding 480 FPS to the
existing 60/240 FPS comparisons (`tmp/goal-20260924-fps-fixture.log`). This
checks those elapsed-time contracts, not all gameplay at 480 FPS; the runtime
FPS cap is still 240 while package parity remains open.

The existing native smoke matrix started all six installed engine-family
representatives with default seed options in private Xvfb sessions. Seven
legacy regression rows failed before gameplay because their chart files
(`chaos`, `inquiry`, `locked`, `cycles-wrath`,
`cycles-encore-springless`, `popipo`, `fnia-ugh`) are absent from the tested
runtime; they are missing fixtures, not observed engine failures. Raw result:
`tmp/goal-20260924-native-matrix.log`.

A separate installed-chart startup pass reached the success marker without
script errors for Expurgation hard, Wacky World hard/nightmare, Rabbit Hole,
Fantasy Girl 01, VS Freddy's Slaughter, Ballistic, Resonance hard, and Cursed
Expurgation hard. Future Sound aborted during HXC script loading with native
`corrupted size vs. prev_size while consolidating`; two immediate isolated
repeats passed. This is an unresolved intermittent native stability failure,
not a clean Future Sound result. Evidence:
`tmp/goal-20260924-named-smoke.jsonl`,
`tmp/runtime-smoke/logs/goal-future-sound.process.log`, and
`tmp/goal-future-sound-repeat.jsonl`. These short startups do not verify
playthrough, endings, script timing, editor round trips, visual or audio parity.
The retained core for the abort detects corruption in HXCPP's allocator while
`HxcCompat.lowerHxcApiAliases` allocates a string during script translation;
the earlier corrupting write is unknown. The two selected V-Slice owner roots
contain byte-identical copies of the candidate scripts and both load in passing
runs. A further private rerun with glibc allocator checks also passed, so no
shared fix has been inferred from the detection stack. See
`tmp/future_sound_abort_audit.md`.

The ModdingPoop donor itself has active stage calls to three commented-out
stop-sign functions, a static-sound path absent from its package, and a
trace-only GF script. They are recorded as source/dependency blockers in
`tmp/inventory_mplus_poop.json`; no chart-specific workaround has been added.
The installed release has all ten Modding Plus/ModdingPoop chart files under
their correct owner manifests. Each chart retains its source note-row count
and lane-value set, including Cursed Expurgation's lanes 0–15
(`tmp/inventory_mplus_runtime_crosscheck.json`). This is structural evidence;
the donor's broken script references and playthrough parity remain open.
The reusable smoke matrix now includes the installed named regressions with
source chart evidence. TAKEDOWN has no chart or matching file in the current
mounted donor, archive, or runtime, and cannot be replayed from this source set.

## Psych cutscene sound and countdown handoff (24 September)

A user report after enabling Freeplay cutscenes exposed an incomplete Psych Lua
bridge. A 35 s default-settings Xvfb replay showed missing `playSound` cues,
unknown `cameraFade`/`cameraFlash` callbacks, then `inCutscene=true` while the
song clock advanced. The visible intro stayed in its cutscene pose and blocked
input. Baseline log and screenshot are preserved under
`tmp/freeplay-cutscene-native/baseline/`.

The shared runtime now resolves sound names within the selected import owner,
exposes both camera effects and maps `startDialogue` to the prepared native
dialogue box. The generic Psych importer copies donor `sounds/` into that owner
on import. A guarded missing-only receipt restored 17 existing selected-owner
sounds (2,307,827 bytes); the donor's chart script matched the installed script
byte-for-byte, and options/chart/script hashes stayed unchanged. Receipt:
`tmp/psych-sound-repair/receipt.json`.

On the integrated build, the private replay logged the timed sound callbacks,
Whitty's overlay hiding by 12 s, and after private dialogue input at 22 s:
`inCutscene=false`, `startedCountdown=true`, song position 2,177 ms. No missing
sound, audio decode, or unknown-variable error appeared. The game process exited
normally and protected files retained their hashes. The 35 s smoke window ended
before the observer's optional 30 s song-time marker; the saved run was validated
against its 22 s checkpoint in `tmp/freeplay-cutscene-native/validated-result.json`
without repeating gameplay. This establishes the handoff and audio path
resolution; the entire song and ending cutscene have not been replayed.

## Codename import and runtime follow-up (24 September)

Script-owned `FlxTween.num`, `angle`, and `color` now participate in pause,
resume and cleanup. Interpreter tests cover the source API and lifecycle.
Codename chart discovery validates chart shape before registering a JSON
file as a difficulty. Section-based `song.notes` charts beside native
strumline charts now convert through a shared adapter, retaining note rows,
BPM changes, events, girlfriend and difficulty visuals. Shared events are
merged with chart-owned groups. Events/metadata sidecars are diagnosed rather
than becoming empty playable entries. The mounted mixed-format D-Sides folder
and a synthetic import verify the contract (13 focused tests passed).
Other foreign chart shapes remain explicitly unsupported.

Codename nullable strumline slots now keep array indices stable through actor
plans, camera references and input line initialization; four focused tests
cover null holes before live lines. Stage `startCamPosX/Y` now apply per present
axis on initial load and stage swap; 10 stage interpreter tests pass. These
source checks await the next native build.

Codename chart metadata now resolves selected-owner `[Flags]` defaults from
`data/config/modpack.ini` or `data/config/flags.ini` before authored metadata,
recording provenance. Fourteen targeted tests pass. Other configuration flags
and variant chart selection remain unsupported.

Per-line Codename `ghostTapping` now inherits a live engine default or accepts
a script override. Focused tests exercise two simultaneous lines and valid
notes beside an empty-lane press; the canonical build remains pending while
the user has the game open. Source/tests are in `CodenameImporter.hx`,
`CodenameInputLine.hx`, `ModuleFunctions.hx`, `PlayState.hx` and `tools/tests/`.

## Psych effect animation and character metadata follow-up (24 September)

The source afterimage event registers its current BF frame as an animation
without an explicit play call. Shared Psych registration now starts the first
registered animation, matching the source API; native snapshot registration
selected `BF idle dance0006` exactly, instead of the atlas's raw death frame.
This is an API-level native check, not a full replay of the late-song effect.

The selected Psych owner lacked its character JSON. A generic missing-only
receipt repair restored 15 JSON files (20,907 bytes), with protected chart/script/
settings hashes unchanged and a backup under
`tmp/resonance-character-metadata-repair/`. The shared importer already preserves
this metadata for new imports. Source position now resolves to dad (-1250,-400)
and BF (749,450), including safe unique case resolution for `Bf.json`.

The first native position check passed numerically but FAILED visual review:
restored camera metadata exposed a stale 720px hitbox on a character scaled to
4320px. The shared constructor now repairs stale dimensions only when the
selected owner's JSON and exact standard-generated legacy HScript agree.
New generated Psych scripts update their hitbox after scaling. Custom scripts
are excluded from this legacy repair.

Native verification on binary `bd2f252d...` passed: the opponent reports a
4320×4320 hitbox, source position (-1250,-400), and BF position (749,450).
Visual review now shows the phone on the left and BF on his rock separately
on the right. The first registered animation matches `BF idle dance0006`.
Evidence: `tmp/psych-animation-position-native/`; previous failed screenshots
are archived there. Personal settings and six protected installed files retain
their hashes. This is opening-scene/API verification, not a full-song replay.
The unrelated existing Loading Screen.lua null comparison remains recorded.
A separate later character-swap draw-order inversion remains to be addressed.

The final ownership-guard suite ran 1,016 tests across 275 modules in 125.7 s
(61 skipped). One failed: the mounted HXC/importer audit reproduced the known
native scanner `double free or corruption (!prev)` (exit 250). This is an
unresolved failure, not a green gate. Log: `tmp/psych-owned-hitbox-suite.log`.
Canonical build succeeded; log: `tmp/psych-owned-hitbox-build.log`.

## V-Slice zoom and lane follow-up (24 September)

The shared `currentCameraZoom` now exposes resting zoom, and translated custom
SongEvent bodies execute authored behavior. Empty textual HXC float payloads
become NaN so donor default branches work in the native interpreter. Rabbit
Hole's authored 4161 ms event changes resting zoom from 1.3 to 0.55; the native
probe measured rendered zoom 0.572 at 5 s and 0.559 at 10 s, without runaway
pulse accumulation. The default-settings screenshot shows the wider stage.
Evidence: `tmp/vslice-zoom-lanes-native/`, binary `7c70df0c...`.

Ordinary V-Slice taps now center their own frame canvas using their own style
offsets, while receptor offsets use the source's 104px lane convention. Static
note/receptor centers align to approximately 0.1px in this native fixture.
The user's subsequent hit-animation screenshots exposed a remaining anchor error:
upstream retains its setup hitbox through static/press/confirm frame changes.
The shared receptor now preserves that anchor and uses the authored scale
without per-direction integer-size rounding. The native observer on binary
`a2f4611a...` captured all four opponent lanes, including confirm/confirmHold,
with the same local rendered center (56.2,48.6) across observed frames. Player
static lanes match. This is real hit-animation coverage, not a static-only pass.

The character constructor now refreshes V-Slice hitbox dimensions after its
opening idle selection, matching source creation/reset before stage placement.
It repairs stale generated adapters that sized an unrelated first atlas frame.
The native opponent now reports 581×918 instead of 935×943 and starts at
(509.5,-573); visual review shows Miku's feet on the platform. Source animation
and global offset formulas already match Bopper and remain unchanged.
The shared stage background scale was not overridden.

Canonical combined build passed. The suite ran 1,018 tests across 275 modules
in 187.7 s (61 skipped, zero failed). This later pass does not resolve the
scanner crash reproduced by the preceding suite. Logs:
`tmp/vslice-animation-countdown-build.log`,
`tmp/vslice-animation-countdown-suite.log` and `tmp/vslice-animation-native.log`.
Installed chart/settings hashes remained unchanged; the private display and
runtime overlay were removed by the test runner.

## Freeplay cutscene policy (24 September)

The user confirmed Ballistic was opened in Freeplay. Its source guards both
intro and ending on story mode. At the user's request, the shared Always Do
Cutscenes policy now projects story context into translated Lua scopes while
native PlayState remains in Freeplay. Both default and personal options already
enable this setting; no personal options were changed. Script-local countdown
gates also survive callback re-entry. Synthetic mode/isolation tests and the
actual donor's translated intro/ending callbacks pass. Native verification on
binary `26f8ac02...` also passed: Ballistic launched from Freeplay reports
script story context true, actual engine story mode false, countdown blocked,
and its visible `crazy` intro animation running. The default-settings screenshot
was reviewed; this verifies intro startup, not the full dialogue/ending sequence.
Evidence: `tmp/freeplay-cutscene-native/`. The probe exited normally and protected
installed chart/script/options hashes remained unchanged. Existing static stage
translator diagnostics for setGraphicSize/updateHitbox/setBlendMode are retained
in the log and are not covered by this cutscene gate check.

Final canonical build succeeded. The full suite ran 1,019 tests across 275
modules in 226.7 s: 61 skipped, zero failed. Logs:
`tmp/freeplay-cutscene-build.log` and `tmp/freeplay-cutscene-suite.log`.
This successful run does not resolve the earlier intermittent scanner failure.
All native probes used private displays, default options and disposable saves;
no native probe process remains. Evidence and rollback receipts are retained
under repository `tmp/`, with disposable runtime overlays cleaned.

## Original-binary scanner release probe (24 September)

One bounded headless scan used the exact saved normal binary (`f0181b05...`),
without recompiling or changing the toolchain. A symbol-relative debugger
breakpoint, guarded by original instruction bytes, inspected the live-list
removal result before explicit recycler insertion. All 79,409 observed releases
found their allocation in the live list; the scan exited normally in 135.3 s.
Evidence and reusable probe: `tmp/scanner-original-release-probe/`.
This does not fix or rule out the intermittent duplicate-free defect. It avoids
another sanitizer rebuild and establishes that this exact run did not follow
the hypothesized failed-removal path. Debugger stops can still alter timing.
Disassembly also shows that `InternalRealloc` retains the old pointer in rbp
and `AllocLarge` spills rbp before collecting, weakening the specific hypothesis
that this call chain omits the old buffer from the conservative stack roots.
No game process, donor files, settings or production sources were changed.

## V-Slice initial camera targeting follow-up (24 September)

User reports Rabbit Hole remains centered on BF with Miku nearly offscreen;
Fantasy Girl 01 starts similarly but corrects after an authored camera move.
The shared cause is confirmed: host section-follow logic targets BF from
converted mustHitSection flags, whereas V-Slice holds the opponent's initial
focus until an authored camera event. The implementation now activates only
for the selected V-Slice source, initializes from the opponent after stage and
character setup, respects a construction-time script camera claim, and blocks
legacy section-follow overrides. Existing FocusCamera events remain in control.
Two new interpreter tests and adjacent camera tests pass (eight total).
Three offscreen native cases passed on binary `d8413394...`, with default
settings and unchanged installed hashes (`tmp/vslice-camera-native/result.json`):
Rabbit Hole starts/holds at opponent focus (970,-136.5), then respects authored
stage movement to (1000,-150). Fantasy Girl 01 starts at opponent (500,728),
moves to BF (639,773.25) at the 12 s event, and returns to opponent at 21.6 s.
Expurgation retains its initial opponent (1450,716.5) and subsequent BF
(2059,844) focus. Private screenshots confirm improved opening framing and
Fantasy's second event. These are bounded samples, not a full-song parity claim.
The first short-duration fixture stopped before late assertions and is retained
under `tmp/vslice-camera-native/previous/`; corrected durations passed.
No chart data, offsets or donor files were edited. All overlays were removed.
Audit: `tmp/vslice-initial-camera-audit.md`.

## Psych skin repair and hazard pixels (24 September)

The final bounded Hurt-palette test passes on `d349a9a7...`: the same source-red
Hurt frame renders (16,16,16) with RGB enabled and (255,0,0) when disabled,
with 484 matching pixel pairs. SourceKind is generated from the authored chart
without a noteInfo sidecar or a manual type write. Receipt/screenshots:
`tmp/psych-skin-native/hurt-result.json`. Private processes/overlays were removed;
personal settings remained unchanged.

After these gates, the generic receipt-based missing-only repair added six
owner-scoped PNG/XML files for the selected existing Psych import. All 96
protected charts/scripts/settings/owner files retain their hashes; independent
post-apply verification confirms all six added hashes. Source/donor files were
not edited. Backup, preview and applied receipt are under
`tmp/psych-note-texture/repair-preview-resonance-ready/`; reusable invocation is
in `tmp/psych-note-texture/repair-procedure.md`. A short actual imported-song check now passes on `d349a9a7...`: all 11 authored
Hurt rows yield runtime Hurt notes using the selected owner's
NOTE_assets-Symmetrical atlas, with Scroll animations, at least 48 atlas frames,
positive frame sizes, and RGB disabled as the chart specifies. The final
bounded gameplay capture at 5,000 ms confirms an on-screen note at (316,547)
uses that authored atlas. Protected hashes remain unchanged; receipt:
`tmp/resonance-skin-check/result.json`, screenshot `gameplay.png` beside it.
The final run has no observer errors and retains one known Loading Screen.lua
`>` nil diagnostic. Its process and private overlay were cleaned up; the earlier
loading-only capture is archived. Missing dynamic references in other donor scripts remain diagnosed;
this is not full package compatibility or a claim of distinct bomb artwork.

## Psych skin centering gate (24 September, synthetic native pass)

Final `d349a9a7...` full suite passes: **1010 tests across 274 modules,
61 skipped, zero failures in 190.4 s** (`tmp/psych-skin-centering-suite.log`).
Seven native cases pass two visits each, including an A-to-B owner switch in
one process. Tap-to-receptor center error is +0.2px for atlas sheets (rounding)
and 0.0px for pixel sheets. Rendered normal-note pixels match the source palettes
exactly with RGB enabled, and retain red source pixels with RGB disabled.
Receipt: `tmp/psych-skin-native/result.json`, including screenshot hashes and
paired pixel evidence. The separate bounded Hurt-palette pixel check and existing
import verification also pass as recorded above; this is not full-song/mod visual parity.

### Intermediate defect and correction

Intermediate binary `f271b570...` produced verified RGB pixels: atlas source red
(255,0,0) becomes (194,75,153), pixel source red becomes (226,118,255), while
RGB-disabled cases retain source red. Seven property cases also pass, including
owner switching, script RGB overrides and rejected texture swaps. However, the
unscripted Hurt tap's center differed from its receptor by -19px (atlas) or
+2.5px (pixel). The reload wrongly restored the previous native atlas's offset.
Those receipts/screenshots are retained as intermediate evidence, not a final
visual pass.

The shared reload now recalculates offset and origin from the new frame, as
Psych does. Timing, source kind, x/y and sustain vertical scale remain intact;
focused production-method tests cover changed frame sizes and sustain alignment.
Build `d349a9a7412f0fb6ba95ae4866618f2c4b961b9876ede374a8ca8bac0b7942da`
passed (`tmp/psych-skin-centering-build.log`). Native rerun requires <=1px tap/
receptor center error for atlas and pixel sheets, plus the rendered-color gate.
No installed skin repair has been applied yet.

## Psych skin native follow-up (24 September, final visual gate pending)

Binary `10f89063...` passed five native property cases, two visits each,
including A-to-B owner selection in one process. Checks include owner-qualified
image keys, Hurt identity without noteInfo.json, sustain ENDS selection, pixel
frame dimensions/filtering, valid texture swaps and failed-swap preservation.
This is property evidence, not a rendered-color parity claim.

Review then found two additional source differences: texture reload reset an
explicit receptor RGB enable, and confirm retained the native -13 offset.
Focused tests reproduced both; the shared receptor adapter now preserves live
RGB flags and uses Psych centering/origin behavior. Rebuild passed on binary
`f271b570d9f7b040b6337a650ec7f07304e91740100994003e0fbdf88d96f124`
(`tmp/psych-skin-runtime-final-build.log`). Final suite: **1010 tests across
274 modules, 61 skipped, zero failures in 175.6 s**
(`tmp/psych-skin-runtime-final-suite.log`). The final native probe adds actual
rendered-color checks; installed imports remain unchanged pending that gate.

## Psych skin runtime integration (24 September, native verification pending)

The selected Psych manifest now gates note/receptor configuration. Both banks
and generated notes use current chart skin/RGB settings, and real texture
setters support later source-script writes. No shared static active skin state
is used. Missing initial skin keeps its source configuration so a later valid
script texture can recover. Rejected loads preserve the prior visual; sustain
scale, timing, type and animation are covered by an interpreter test executing
the production adapter and extracted sprite methods. Generated sourceNoteType
is retained as sourceKind, allowing the authored Hurt Note palette to apply.

Importer copying is owner-scoped and missing-only, with complete ordinary and
pixel pairs handled independently. Dynamic skin keys, incomplete sheets and
missing source defaults are diagnosed. Source pixel postfix ordering is tested.
The build passed on binary `bae65a6b7ad5b5cd698d7a4f03948fb431e2ec28d6884bf3d45190a44583d9cc`
(`tmp/psych-skin-runtime-build.log`); personal options retain SHA `0cee51b8...`.
The first native fixture exposed missing Hurt identity when no generated
noteInfo.json existed. The authored row was intact, but null native definitions
prevented NoteTypeCompat from creating its shared Hurt definition. The engine
now initializes that list only for selected Psych sources, preserving existing
definitions. The fixture deliberately remains sidecar-free; its failed receipt
is retained under `tmp/psych-skin-native/previous/`. A focused production-method
test covers generation and native isolation. Rebuild and rerun are underway.

Pre-sidecar-fix full suite passes: 1010 tests across 274 modules in 181.1 s, 61 skipped, zero
failures (`tmp/psych-skin-runtime-suite.log`). Synthetic native rendering checks
are running. Installed imports
have not been refreshed, and the reported Resonance appearance is not yet
verified. Splash selection and the complete script-facing rgbShader object API
remain unsupported.

## Psych skin pipeline continuation (24 September, incomplete)

The previous turn made verified progress: shared camera fixes and native ending/
pause checks completed. The next unresolved visual contract is Psych skins.
Typed skin metadata now survives difficulty resolution, including explicit empty
skin resets and `disableNoteRGB: false`. A production-method interpreter test
covers selected/default/fallback precedence and absent/invalid values; adjacent
five difficulty tests pass. The new owner-scoped resolver passes an interpreter
fixture covering two colliding owner keys, complete/missing pairs, shared roots,
pixel ENDS, postfix selection, case collisions, unsafe paths and deep valid keys.
It returns a descriptor and diagnostic reason without mutating sprite state.
Canonical build passed (`tmp/psych-skin-foundation-build.log`), binary SHA
`7e1e3bdaad057569df476ee4636233dbe7f81b8ac332ce90cc77657239a0ccf2`.
Full suite: 1006 tests across 270 modules, 61 skipped, zero failures in 180.6 s
(`tmp/psych-skin-foundation-suite.log`). The resolver module was added after
suite discovery and passed separately (one interpreter test). Live settings
retained SHA `0cee51b854f2673d753c0ff1edfc9f2bc2597e30d2c34604a14ddea5755387ee`.
No native visual parity claim is made for this unfinished rendering pipeline.
The resolver is not yet wired into rendering; neither change fixes note or
receptor appearance by itself. No donor or installed content was modified.

## Psych hazard notes, outro and custom pause follow-up (24 September)

- User reports ordinary-looking bomb notes, missing ending and nonfunctional
  pause controls in Resonance. Hazard rendering remains open; ending verification
  now passes, as does actual donor pause/resume interaction.
- Read-only donor/installed audit is in `tmp/psych-bomb-outro-audit.md`.
  Hurt Note identity survives import. Shared `Note.texture` reload is missing;
  the donor explicitly writes a texture to every note. Local Psych's reload
  also disables RGB on a nonempty texture, but that local source is Psych 1.0.4.
  Official [Psych 0.7.3 Note.hx](https://github.com/ShadowMario/FNF-PsychEngine/blob/0.7.3/source/objects/Note.hx)
  preserves RGB on texture reload, so the donor's declared version matters.
  The user's screenshot supplies a red note/receptor appearance reference.
  Exact rendered parity remains unverified. Do not claim a unique bomb atlas or
  force a hazard skin without reference evidence.
- Full-song offscreen baseline probe completed on binary `d3e814fa...` with
  clean default settings and the practice modifier (survival only). Nine
  observations confirm the ending sprite is created at step 2960, fades to
  alpha 1, remains visible on an opaque overlay camera, and survives until
  onEndSong. Its scale stays at 10 throughout: authored nested `sprite.scale`
  tweens are ineffective. Shared nested-target handling now resolves exact object tags first and then
  the existing property-path bridge. Extracted production tween tests cover
  nested scale, direct tags, plain nested objects and missing targets. Rebuilt
  binary `d8413394...` completed the full-song offscreen run (exit 0): eleven
  observations through endSong show scale moving from 10 to the authored 0.67.
  Screenshots at steps 3015 and 3065 visibly confirm the large phone contracts
  to its centered ending pose. Receipt: `tmp/resonance-outro-observer/result.json`;
  screenshots are in that directory. This verifies the reported missing ending,
  not complete visual parity for the whole song. Baseline evidence is archived
  under `previous/`. Default and personal settings hashes stayed unchanged.
- The first probe failed during stage creation because canonical script paths
  escaped the disposable runtime overlay. That failure is retained under
  `tmp/resonance-outro-observer/previous/`. Tooling now materializes selected
  script metadata for old binaries; production discovery preserves mounted
  read paths while retaining canonical deduplication (six tests, one skipped).
  The successful probe's default and live options hashes were unchanged, and
  its disposable overlay was removed.
- Corrected shared mouse-camera coordinates. Production-method interpreter test
  `test_psych_mouse_coordinates.py` passes (one test). Native click verification
  passes in the synthetic native pause fixture. The donor pause controls intentionally open
  after five pause attempts; host cancellation/custom-substate ownership now uses a real Flixel substate.
  Four focused tests cover class lifecycle, pending cancellation/replacement,
  callback ownership and timer/tween pause restoration. Three native synthetic
  runs verify resume, restart and exit, including mouse input at (600,350),
  callback teardown and paused parent ownership (receipt
  `tmp/codename-pause-lifecycle/result.json`). Actual donor interaction also passes: five P presses open the authored menu,
  the song clock holds while paused, and Escape destroys the substate and
  resumes playback (2139 to 2343 ms). Receipt:
  `tmp/resonance-pause-check/result.json`; screenshot in that directory. The
  source script intentionally rejects the first four pause requests. No browser
  button was used. One previously observed Loading Screen onUpdate null-operand
  warning remains; this pass does not claim it fixed. Processes and disposable
  overlays were removed, and personal options stayed unchanged.
  `insertToCustomSubstate` is still unsupported.
- Native test tooling now copies clean repository seed settings into disposable
  runtime overlays and isolates save paths. Personal options must never be used
  as a visual baseline or overwritten. Earlier visual receipts using personal
  options are not sufficient evidence for the newly reported appearance issues.

## Codename accuracy and rating model (24 September, bounded native probe passed)

- Source `accuracy` and `game.accuracy` now expose the donor ratio and -1
  no-notes sentinel while native score/HUD code retains percentages. The donor
  setter and mutable accumulated/pressed counters are covered by extracted
  production-method tests.
- Added ComboRating/RatingUpdateEvent with explicit source import bindings,
  per-state default/custom rating lists, maxMisses filtering, stable ties and
  mutable/cancellable scene/character rating callbacks. Hit/miss accuracy
  updates enter this same path. No chart or mod-specific branches were added.
- Accuracy HUD formatting follows the pinned donor English template and
  quantization, with only the rating substring colored. Tests cover N/A,
  custom labels, rounding and preservation of unrelated text formats.
  Donor localization and full HUD layout/replacement remain unsupported.
- The rebuilt binary `d8413394...` passed the default-settings offscreen
  two-visit native probe (PID 3569056): ratio 0.8 and three mutable rating
  callbacks per visit, zero script warnings, unchanged installed critical
  bytes. Receipt: `tmp/codename-ratings/native-probe.result.json`. Temporary
  donor/runtime overlay removed. The probe exits during visit two and does
  not assert that visit's final teardown.

### Integration verification follow-up

Final combined suite: **1,005 tests across 269 modules in 208.3 seconds;
61 skipped, zero failures** (`tmp/compat-camera-pause-suite-final.log`).

The combined source suite ran 1,005 tests across 269 modules (61 skipped) in
181.2 seconds, with one fixture compile failure: the ownership-reset fixture
lacked the new V-Slice camera flag. The fixture now initializes and asserts
cleanup of that flag and the new custom-substate fields; all nine tests in the
module pass (`tmp/compat-camera-pause-reset-fixture.log`). Other modules passed.
An earlier full run similarly exposed the custom-substate fixture fields.

The first canonical build caught a prior rating HUD API mismatch hidden by an
overpermissive stub: FlxTextFormat has no writable `color`. Production now
replaces its owned format only when the color changes, and the fixture exposes
an immutable color. The focused test passed, followed by canonical build exit 0
(`tmp/compat-camera-pause-build-retry.log`). Live settings retained SHA
`0cee51b854f2673d753c0ff1edfc9f2bc2597e30d2c34604a14ddea5755387ee`.

## Codename note events (24 September)

- Added shared source hit/miss payloads, real Flixel line signals, directional
  animation callbacks, and judgement presentation separated from scoring.
  Scoped live globals expose note display defaults and accuracy counters.
- Directional tests exercise hook mutation/cancellation, suffix fallback,
  nullable-force defaults and cross-scope aliases. Source stun tests cover
  elapsed-time expiry/reassignment at 60, 240 and 480 FPS; this is not full-game
  FPS equivalence verification.
- Presentation tests cover world coordinates, scoped custom assets/default base
  resources, recycled sprites, pause/resume and tween cleanup. First focused
  Codename run exposed seven fixture compilation failures from newly required
  presentation/signal dependencies; those fixture boundaries were updated while
  retaining their assertions (`tmp/codename-note-events-focused.log`).
- First canonical build passed (`tmp/codename-note-events-build.log`), binary
  `b1d896abd888ceeef1eb47601f96ca79ae7e0d9421c7619f03f6631e1c44c155`.
  Review then caught invented once-only missed-note semantics; the pinned
  donor repeats misses when cancellation or preventDeletion retains a late
  note. This correction and explicit detached presentation cleanup were included
  in the later builds below. The first build is not final evidence.
- Two full suite runs passed: **991 tests across 262 modules, 61 skipped,
  zero failures**, in 179.7 and 176.3 seconds. Logs are
  `tmp/codename-note-events-suite.log` and `tmp/codename-note-events-final-suite.log`.
- The expanded native probe initially appeared to pass on binary
  `ffa60ad6b3c67c6cc3ffb219dd144f598dcd19a007f720ed6bd95df3feb7fcb8`,
  but review caught one null-operand warning per visit: source `game.misses`
  read the host's static field through an instance and returned null. A null
  arithmetic fallback weakened the fixture assertion. That receipt is now
  **partial**, archived under `tmp/codename-note-events/previous/`.
  Added a typed instance accessor and explicit live global; the stricter probe
  rejects null counts and null-access/arithmetic warnings. The partial receipt
  does not prove miss-count correctness.
- The stricter two-visit native rerun **passed** on canonical binary
  `d3e814fa5b02b0c7335d1f53a4411367699568d9d6051cc4ebef8add7d553adb`,
  PID 3534138. Both visits verified numeric miss delta +2, mutable score/health,
  scene/line/character callback order, hit cancellation and post callbacks,
  five judgement sprites, typed event imports, and directional animation
  mutation/cancellation. No null-access/arithmetic warnings or script errors
  were logged. First-visit teardown had owned=1, destroyCalls=1, remaining=0,
  no cleanup errors; actor tokens differed between visits. The harness exits
  during visit two before its teardown, so that final teardown is unverified.
  Evidence: `tmp/codename-note-events/native-probe.result.json`, process/marker
  logs, and `tmp/codename-note-events-accessor-build.log` (build exit 0).
  Installed critical hashes/settings were unchanged; private donor/runtime
  overlays were removed. Native runs used isolated Xvfb and dummy audio.
- Final full suite after the instance-accessor fix passed: **991 tests across
  262 modules in 182.2 seconds; 61 skipped, zero failures**. Evidence:
  `tmp/codename-note-events-accessor-suite.log`. No regression was detected by
  this suite or the scoped native probe; this does not verify every installed
  chart visually or close the remaining compatibility/performance goal.
- No installed charts, mod assets or donor scripts were patched. Native
  judgement-window sizing, independent receptor banks, per-line vocals and the
  donor combo-rating model remain separate compatibility work.

## Codename camera/input identity and indexed movement (24 September)

- Camera callbacks now receive the same stable live line model as input.
  Averaging reads script-edited actor slots, including empty/null slots, without
  recreating them from metadata. Changes to CPU/control ownership through the
  camera event persist in the input path.
- The production-method camera test first failed with `camera and input expose
  different line objects` (`tmp/codename-camera-input-before.log`), then passed
  after the shared fix. It also verifies mutated arrays across frames, empty and
  released views, and live focus updates while scroll interpolation is active.
- Structured Camera Movement now selects an authored index instead of converting
  it to a native character role. Extra/empty lines, invalid indices, snap,
  CLASSIC, step-based easing, replacement/completion and post-callback target
  invalidation have focused coverage. Missing selected-owner actor plans/runtime
  produce a once-only diagnostic; no chart-specific fallback is introduced.
- Camera scroll tweening disables follow without suppressing camFollow updates
  or onCameraMove. Absolute Camera Position retains its fixed-target semantics.
- Full suite passed: **986 tests across 257 modules in 185.6 seconds,
  61 skipped, zero failures** (`tmp/codename-camera-input-suite.log`).
- Canonical build passed: `tmp/codename-camera-input-build.log`, binary SHA256
  `5159192f4d7db1406cf93ddb9909d627a3745238704e60cde7dfa30937211f5a`.
  Offscreen native verification passed on that binary, PID 3508846, across two
  PlayState visits. Each visit confirmed camera/input object identity, persistent
  actor-array edits and camera averages, CPU suppression/restoration of input,
  restored actor focus, and imported Camera Movement selecting source index 1.
  Evidence: `tmp/codename-camera-input/native-probe.result.json` and its process
  and marker logs. First-visit teardown passed; the harness exits before the
  second teardown. Installed critical hashes/settings were unchanged, and
  disposable donor/runtime-overlay trees were removed.
- Independent source note/receptor groups and signals remain incomplete; sharing
  the model does not implement the full donor StrumLine class. No installed
  charts, donor scripts or mod-specific branches were changed.

## Codename authored-line input ownership (24 September)

- Follow-up: each Codename input line now exposes the donor's nullable
  `ghostTapping` override. With no override, it reads the live game default;
  a script can set or clear its own value without changing another line.
  The shared input path uses that resolved value for source ghost misses.
  Extracted interpreter tests cover two simultaneous lines with opposite
  overrides, a global default change, and clearing an override. This remains
  a four-key projected line; independent receptor groups and extra-line
  projection are separate work. The canonical native build was deferred while
  the user's game process held the runtime lock.
- Input/CPU ownership now uses stable source strumline models, including empty
  lines. Notes retain their origin through heads, sustains and lifts. Local
  duplicate removal uses the source <=2 ms threshold within one line; notes on
  another line no longer share that duplicate bucket.
- Mutable/cancellable `onInputUpdate` arrays drive actual judgement, and accepted
  frames dispatch `onPostInputUpdate` to scene and character scopes. Held input
  grants the animation lock only to attached actors outside DANCE; animation
  playback alone no longer locks the character. Source ghost misses do not
  suppress valid hits on other pressed lanes.
- Manual hits, misses and autoplay animate attached actors. Review caught and
  corrected remaining writes to native singleton alt/hold state. Primary swaps
  replace matching references while preserving script-edited actor arrays.
  Solo, opponent and co-op controls are selected and configured explicitly.
- Extracted production-method tests cover cross-line same-time notes, local
  duplicate tolerance, cancellation, null arrays, hold/lift routes, ghost input,
  native fallback, mode banks, binding guards, swaps and event propagation.
- The first full suite ran 984 tests across 255 modules (179.0 seconds, 61 skipped)
  with two fixture compilation failures: demo-speed and dynamic-scroll tests
  extracted the spawn loop without the new input binding/model setup. Their
  stubs were extended without changing the original assertions; focused tests
  pass. Evidence: `tmp/codename-input-full-suite.log`.
- Final full suite passed: **985 tests across 256 modules in 174.9 seconds,
  61 skipped, zero failures** (`tmp/codename-input-final-suite.log`).
- Final canonical build passed: `tmp/codename-input-controls-build.log`, binary
  SHA256 `c74f793b8508ada214d8c1e64b243462d07422d37e6f909a7d8b73baa90737e4`.
  Earlier build logs are retained because review found further routing and
  control-bank corrections before native verification.
- Native probe evidence is under `tmp/codename-input-lines/`. Its first run
  exposed fixture assumptions: injected presses ignored the user's +251 ms
  timing offset, and a lock check used a non-dancing beat. The probe's phase
  assertions also needed finite windows. These require fixture corrections;
  this failed run is not evidence of successful engine behavior.
- Corrected offscreen native verification passed on that binary, PID 3502417,
  with two PlayState visits: separate simultaneous same-lane hits, a cancelled
  line without a held-input lock, primary alt/hold isolation, CPU mutation, and
  scene/character callbacks all emitted their required markers twice. No source
  script errors were logged. First-visit actor teardown had no remaining bindings
  or cleanup errors; the harness exits before second-visit teardown. Result:
  `tmp/codename-input-lines/native-probe.result.json`. Earlier failed fixture
  runs remain archived under `previous/`; subsequent fixture corrections also
  distinguish MISS fallback animations from SING and allow intentional CPU
  changes in ownership assertions. Engine source was unchanged during these
  fixture corrections.
- Installed critical hashes stayed unchanged, including options SHA256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  Disposable donor and runtime-overlay trees were removed, and no probe game
  process remains. Reusable runners, tests, logs and results are retained locally.
- Remaining scope: independent source receptor/cover groups, note signals,
  unprojected GF/extra-line notes, arbitrary key counts, and a unified camera
  line view remain incomplete. The two native receptor banks are still shared;
  only the first controlled line per side performs raw visual input updates.
  No installed charts, donor scripts or mod-specific branches were changed.

## Codename XML animation initialization and recycler diagnostics (24 September)

- Character XML loop-type animations now play immediately after registration,
  before raw force metadata storage and node callbacks. Initial force defaults,
  cancellation/mutation, case/whitespace normalization, duplicate-name lookup
  and the separate frame-loop flag follow the donor contract. Construction
  callbacks use private state until the completed definition is available.
- Accepted generic sprite animation calls now replace the context even when
  it is omitted/NONE; missing/null animation names preserve previous state.
  The focused test first failed with `default NONE retained prior context`:
  `tmp/codename-sprite-context-before.log`, then passed after the shared fix.
- The old-binary native probe reproduced missing XML playback at node 0 in all
  ten actors across two visits, and separately emitted GENERIC_NONE_FAIL twice.
  Evidence is retained under `tmp/codename-character-xml-loop/`.
- Canonical build passed (exit 0): `tmp/codename-xml-loop-build.log`; binary
  SHA256 `8641632d0f9c545484f1121ecb3b831689ead4829142c362482610f6b201e1c8`.
  Native verification passed, PID 3477795:
  `tmp/codename-character-xml-loop/native-probe.result.json`. Ten actor
  initializations across two PlayStates matched play-before-node callback
  order, type/loop separation, force, mutation/cancellation and instance
  isolation. Generic NONE reset passed in both visits. First-visit cleanup
  markers passed; the harness exits before the second teardown. Disposable
  donor/overlay trees were removed and installed critical hashes/settings
  remained unchanged.
- The first full suite found one test-fixture compilation failure: the isolated
  V-Slice character geometry stub lacked the new private construction fields
  referenced by the extracted production method. Added those fields without
  changing its assertions; the focused test passes. Original suite evidence:
  `tmp/codename-xml-loop-suite.log` (979 tests, 61 skipped, one failed module).
  Final complete suite passed (exit 0): **979 tests across 251 modules in
  173.2 seconds, 61 skipped, zero failures**:
  `tmp/codename-xml-loop-final-suite.log`. No engine source changed after the
  native passing build; the correction was confined to the test stub.
- Private recycler diagnostic v2 adds post-push and reuse checks, exact
  duplicate detection before GC frees, and a bounded transition history.
  Equal-size candidate substitution is recorded without treating it alone as
  corruption. Fingerprint matches are probabilistic evidence; ring truncation
  is explicit. Pinned source guards/cache separation remain, and compiled C++
  tests exercise valid transitions and deliberate invariant failures. The
  intermittent scanner defect is not claimed fixed by this instrumentation.
- One reviewed private v2 build and scan completed successfully, exit 0,
  without timeout or stderr. It found 16 roots and selected 84 unique songs
  (4 Modding Plus, 58 V-Slice, 22 Psych); this historical reproducer's selected
  workload does not exercise Codename song conversion. The normal hxcpp source
  hashes remained unchanged. Evidence: `tmp/auto-import-recycler-v2-wrapper.log`
  and `tmp/auto-import-diagnostic-recycle-cache/d814ec95d63f764e56b8f539d661380ada521a476a21cee0594154cc7e013329/`.
  The sub-agent's reporting turn was interrupted by a content filter; root
  verified the still-running process, then its terminal run.json and outputs
  directly, without restarting the scan. No additional scan was run.
- Synthetic diagnostic abort tests now disable core dumps. Fifteen small
  systemd-owned dumps from earlier synthetic runs could not be removed because
  noninteractive sudo requires a password. Exact, verified filenames are listed
  in `tmp/cleanup-synthetic-cores.sh` for administrator cleanup; genuine scanner
  crash evidence is excluded. Local disposable test directories were removed.

## Codename shared sprite offsets and cross-scope actor calls (24 September)

- Generic source sprites now subtract frameOffset before scale/rotation and
  support frameOffsetAngle. Culling applies the transformed offset before
  camera factors and conservatively accounts for pixel rounding. Production
  draw-method interpreter tests compare matrix corners with bounds.
- Song/stage scripts and character scripts addressing another actor now use
  the source five-argument playAnim, tryDance and authored curCharacter view.
  Dispatch is based on a shared character interface and authored identity,
  with native characters and unrelated objects retaining their own APIs.
  Interpreter coverage includes nullable force, context, reverse, starting
  frame, method references, duplicate actor IDs and source-identity writes.
- Canonical build passed (exit 0): `tmp/codename-sprite-offset-build.log`.
  Binary SHA256:
  `3057a0d8e1027b613f5acd17507e6503b037540427f9ed929f29258fbfc7b01b`.
  Initial full suite passed: **977 tests across 251 modules in 185.4 seconds,
  61 skipped, zero failures** (`tmp/codename-sprite-offset-suite.log`).
- Initial offscreen native verification passed ten sprite phases (PID 3462904)
  and ten character geometry phases including the cross-scope five-argument
  call (PID 3463528). Installed critical hashes/settings were unchanged.
- Review then found the isolated test's fake base bounds were more correct
  than Flixel's real negative-scale bounds, hiding a remaining culling error.
  The native probe reproduced it on that binary: NEG_BASE pixels spanned
  [534,296,630,336], but reported bounds spanned [630,296,726,336]. All four
  negative-scale/flip cases had the same 96-pixel displacement. Evidence:
  `tmp/codename-sprite-offset/negative-bounds-red.result.json` and
  `tmp/codename-sprite-offset/previous/pre-negative-fix/`.
- Shared bounds now correct reflected frame spans before rotation and preserve
  fractional camera scroll. The revised test base follows the real Flixel
  calculation, including signed origin and absolute frame dimensions. Focused
  tests pass. Final canonical build passed (exit 0):
  `tmp/codename-sprite-offset-negative-build.log`, binary SHA256
  `fa1e1c957956c33827bbd17549f26c688ac8ca3fef3161f2048d270ad37c1698`.
- The same native probe then passed all **14 phases**, PID 3468290:
  `tmp/codename-sprite-offset/native-probe.result.json`. Negative-scale bounds
  now exactly match pixels: baseline [534,296,630,336], shifted
  [552,306,648,346], with the same rectangles for flip variants. Rotation,
  offset-angle and camera-factor phases remain passing. Private overlays were
  removed and installed critical file hashes/settings remained unchanged.
  The character-call/geometry probe above used the preceding binary; only
  generic sprite bounds changed in this final rebuild.
- Final full suite passed (exit 0): **977 tests across 251 modules in 180.4
  seconds, 61 skipped, zero failures**:
  `tmp/codename-sprite-offset-negative-suite.log`. No new regression was found
  by this batch's checks; they do not establish full imported gameplay parity.
- The scanner memory-corruption investigation remains unresolved. The bounded
  read-only audit in `tmp/auto-import-recycler-next.md` identifies diagnostic
  gaps around recycler reuse, vector mutation and pre-free state. No additional
  scan or claimed scanner fix is part of this batch.

## Codename live character world/draw geometry (24 September)

- Separated source character world placement, global offset and animation
  frameOffset. Stage camera composition uses source cameraOffset baselines;
  legacy metadata-only actors keep their generated placement fallback.
- Rendering source review disproved the earlier positive-screen-space plan.
  Historical cne-flixel/cne-flixel-addons snapshots preceding v1.0.1 and current
  sources both subtract frameOffset before scale/rotation/skew. The character
  adapter now uses that matrix order with temporary flip/extraOffset restoration.
  The separate generic CodenameFunkinSprite adapter was corrected in the later
  batch documented above.
- First canonical build passed (`tmp/codename-character-geometry-build.log`).
  First integrated suite passed: **975 tests across 249 modules in 198.6
  seconds, 61 skipped, zero failures** (`tmp/codename-character-geometry-suite.log`).
- The first native geometry probe **failed**: normal camera follow selected
  the native section's player instead of Codename's default strumline 0. Source
  inspection also requires averaging that line's visible character instances.
  This is a genuine engine gap being corrected, not a passing rendering result.
  Evidence is preserved under
  `tmp/codename-character-geometry/previous/pre-line-camera/`. Disposable fixtures
  were removed and installed critical hashes/settings remained unchanged.
- The camera correction's build and suite passed: **976 tests across 250
  modules in 187.5 seconds, 61 skipped, zero failures**
  (`tmp/codename-character-geometry-line-camera-suite.log`). The second native
  attempt passed selected-line averaging and A_IDLE pixel bounds exactly, then
  found the legacy countdown's direct dance reset a source-selected pose.
  Evidence: `tmp/codename-character-geometry/previous/pre-countdown-gate/`.
  Countdown now excludes live Codename actors from those duplicate legacy
  calls; a production-block interpreter test covers source/native mixed scenes.
- The final canonical build passed (exit 0):
  `tmp/codename-character-geometry-countdown-build.log`. The offscreen native
  probe then passed all ten pixel phases, PID 3455368: unit/nonuniform scaling,
  animation offsets, dynamic flip, rotation, skew and A/B/A restoration. Native
  onCameraMove payload/dispatch and the duplicate-actor camera average passed.
  Example pixel bounds: A idle [134,162,198,194], shifted [122,170,186,202],
  A return identical to idle. Camera average A [416,88], B [717,141].
  Result, screenshots and logs:
  `tmp/codename-character-geometry/native-probe.result.json`.
- Final full suite passed (exit 0): **977 tests across 251 modules in 181.8
  seconds, 61 skipped, zero failures**:
  `tmp/codename-character-geometry-countdown-suite.log`.
- Disposable native donor/runtime trees were removed; installed critical file
  hashes and live settings remained unchanged. These tests establish the
  exercised static-atlas transforms, not complete Animate/3D/StrumLine support.
  Full indexed Camera Movement events remain open. Cross-scope five-argument
  actor animation aliases and generic sprite offsets were addressed in the
  later batch documented above.

## Codename missing-animation requests and loop transitions (24 September)

- Shared Codename dispatch now validates the callback's final animation name
  before changing animation/context. Null always rejects; missing names reject
  outside debug mode. SING/MISS timestamps still follow the donor's separate
  post-call behavior, while cancellation prevents that update. Legacy animation
  handling is unchanged.
- Finished animations follow an available authored `-loop` successor after
  native animation update and before script update, preserving nullable force
  and context. Debug mode skips automatic transitions. Focused interpreted
  production-method tests include mutation, missing/null names, cancellation,
  debug behavior, absent successors and the source's null-current-animation
  successor lookup.
- Canonical build passed (exit 0):
  `tmp/codename-animation-transitions-build.log`.
- Full suite passed (exit 0): **974 tests across 248 modules in 176.6 seconds,
  61 skipped, zero failures**:
  `tmp/codename-animation-transitions-suite.log`.
- A new offscreen native probe **failed on the preceding binary**, reproducing
  the missing-name state mutation across five actors in two visits. Evidence:
  `tmp/codename-character-animation/previous/before-animation-fix/`.
  The same probe **passed on the rebuilt binary**, PID 3434514, including
  missing/null state preservation, sing timestamps, loop callback arguments and
  loop transition visibility in script update. Evidence:
  `tmp/codename-character-animation/native-probe.result.json` and its runner.
  Five first-visit script destroys were observed; the harness exits before the
  second teardown. Installed critical hashes/settings remained unchanged and
  disposable donor/runtime trees were removed.
- Geometry, XML loop-mode initialization and input-lock timing remain separate
  incomplete work; this verification does not establish full character fidelity.
  The shared world/draw/camera implementation and pixel-probe plan is recorded
  in `tmp/codename-character-geometry-next.md`; it explicitly preserves the older
  metadata-only import fallback while correcting live source actor semantics.

## Codename animation callback restart defaults (24 September)

- Shared character dispatch now preserves nullable force through `onPlayAnim`
  and resolves its default using the callback's final animation name. Explicit
  true/false, callback null resets, cancellation, nested dispatch and exception
  restoration are covered by the extracted/interpreted production methods in
  `test_codename_character_force_order.py`. Legacy Bool calls are unchanged.
- Canonical build passed with exit 0:
  `tmp/codename-animation-force-build.log`.
- Full suite passed with exit 0: **974 tests across 248 modules in 175.5
  seconds, 61 skipped, zero failures**:
  `tmp/codename-animation-force-suite.log`. The separately rerun focused test
  also passes with nested dispatch and exception-restoration assertions.
- The offscreen native lifecycle regression passed on the rebuilt binary,
  PID 3428541, both gameplay visits, five first-visit script destroys, unchanged
  installed hashes/settings and removed disposable fixtures. Current evidence:
  `tmp/codename-character-lifecycle/native-probe.result.json`. Earlier lifecycle
  evidence is archived in `previous/pre-force-order-fix/` under that directory.
  This native probe covers lifecycle regression; the focused interpreter test
  establishes nullable-force callback semantics. Second-visit destruction is
  still outside the smoke harness's observed lifetime.
- The source audit in `tmp/codename-character-animation-audit.md` records
  remaining animation-name validation, loop transitions, input lock timing and
  global/frame draw-offset discrepancies. These are not claimed fixed.

## Codename actor-local character lifecycle (24 September)

- Connected selected-owner character XML/scripts to actual Character construction.
  Each repeated occurrence gets a separate interpreter. Mutable XML and ordered
  post-node callbacks precede orientation/dance/postCreate; live presentation
  metadata feeds stage baselines. Supported actor callbacks, cancellation,
  source-facing animation signatures, pause ownership and guarded destruction
  are integrated. XML extension packs and full routing/draw modes remain open.
- Canonical current build passed (exit 0):
  `tmp/codename-character-lifecycle-build-preserve-create.log`. Earlier builds
  are retained as intermediate evidence only.
- The strengthened private native lifecycle probe passed once, PID 3421781, two gameplay
  visits in one process. It asserted five distinct scopes per visit (including
  three instances of one authored ID), mutable XML, ordered node application,
  create/postCreate/update/beat/step, dance/play cancellation, exactly five
  first-visit script destroys, fresh second-visit actor identities and native
  owned/borrowed cleanup. No character/script diagnostics occurred. Result:
  `tmp/codename-character-lifecycle/native-probe.result.json`.
- Script-created nonuniform scale (1.25, 1.5) and antialiasing=false survive
  omitted XML attributes through postCreate and stage placement for all five
  actors in both visits. Explicit XML attributes still override script values;
  existing animation offsets survive unless XML replaces their named entries.
  The previous native result is archived under
  `tmp/codename-character-lifecycle/previous/pre-omitted-attributes-fix/`.
- The preceding native stage regression probe also passed: two gameplay visits,
  each with stage A/B/A transitions preserving live actor identities and
  restoring presentation. Evidence:
  `tmp/codename-character-stage-reload/native-probe.result.json`.
- Source XML/scripts/atlases matched the selected donor. Eight checked installed
  files, including settings, remained unchanged; disposable donor and overlay
  were removed. The smoke harness exits during visit two, so its final teardown
  is not observed. Full draw/camera/note compatibility is not inferred from this
  lifecycle probe.
- Initial integrated suite: 968 tests/246 modules/186.1 seconds, 61 skipped,
  six failed modules, all missing updated extracted fixture declarations.
  Corrected fixture coverage also checks gamePostCreate once and actor pause;
  a recursive runtime destroy test and Character guard prevent duplicate cleanup.
  Fourteen focused tests passed after corrections. The final integrated rerun
  passed (exit 0): **973 tests across 247 modules in 177.2 seconds, 61 skipped,
  zero failures**, recorded in
  `tmp/codename-character-lifecycle-suite-preserve-create.log`.
- Live settings SHA-256 remains
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  No installed imports were refreshed for this lifecycle batch. XML extensions,
  dynamic character dependencies, full draw/camera/note routing and the
  intermittent native scanner allocator defect remain incomplete.

## Codename character script preparation (earlier 24 September batch)

- Canonical release build passed (`tmp/codename-character-preservation-build.log`).
  Full suite: **965 tests across 244 modules in 179 seconds; 61 skipped, one
  failed module**, the synthetic sprite fixture described below. The corrected
  focused import/actor/discovery rerun passes 18 tests
  (`tmp/codename-character-preservation-focused.log`). Full-suite evidence:
  `tmp/codename-character-preservation-suite.log`. The normal scanner passed in
  this run; the known intermittent allocator defect remains unresolved.
  Live options SHA-256 remains
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.

- The shared importer now preserves selected character XML, `.hx`, static
  source atlases and literal script dependencies within the owning namespace.
  Nested IDs remain intact through camera/actor metadata. Rejected identity,
  case-ambiguity and path-escape diagnostics are explicit; a missing optional
  `.hx` is not an error. Missing-only repair retains edited files.
- XML without `sprite` now resolves using its authored character ID, including
  nested IDs, instead of the renamed native key. An existing synthetic fixture
  supplied a `camera-extra` atlas for the authored ID `camera extra` without an
  explicit sprite; it now declares that sprite, matching source semantics.
  The corrected import/discovery/actor-plan group passes 18 tests. Dynamic
  character selection, computed asset references and XML extensions remain
  unfinished; no installed import refresh has been performed for this batch.

- Added optional actor-parent binding to the actual compatibility interpreter.
  Tests execute real HScript against two independent actor instances and check
  field/method access, property accessors, lexical/global shadowing, closure
  writes, parent replacement, unknown-name errors and release. The focused
  interpreter/lifecycle/reload group passed 10 tests:
  `tmp/codename-character-parent-focused.log`.
- This does not yet execute original character scripts in native gameplay.
  Source XML preservation, construction-phase callbacks, actor events and
  native verification remain required before character script support can be
  claimed. No installed imports have been refreshed for this work yet.

## Same-process actor teardown and reload (24 September)

- Added opt-in `--smoke-playstate-visits 2`, per-visit gameplay deadlines and
  a watchdog that also covers queued transitions. Missing/duplicate/mismatched
  cleanup evidence fails before a second visit can be accepted. The default
  single-visit path is preserved. Focused harness/identity/integration tests:
  21 passed (`tmp/codename-actor-reload-focused.log`).
- Canonical build passed (`tmp/codename-actor-reload-build.log`). The native
  offscreen probe passed in one runner-recorded process (PID 3385464), one
  runToken, visits 1 and 2. First teardown and full state destruction preceded
  second start: two owned actors, two destroy calls, zero remaining bindings,
  no cleanup errors. Tokens 1–5 and 6–10 were disjoint. Both visits passed
  A/B/A stage replacement and presentation restoration; settings and checked
  import files remained unchanged. Result:
  `tmp/codename-actor-reload/native-probe.result.json`.
- An earlier native attempt also succeeded, but its result parser expected a
  PID marker instead of runToken and had not persisted the runner PID. That
  evidence is retained separately. The final runner records its Popen PID and
  validates runToken; no native fix or failure was involved.
- Full suite: **960 tests across 244 modules in 122.7 seconds; 61 skipped,
  two failures** (`tmp/codename-actor-reload-suite.log`). The demo-speed fixture
  still declared the smoke tick as Void; its Bool stub is fixed and its focused
  test passes (`tmp/codename-actor-reload-demo-wrapper.log`). The other failure
  is the unresolved native scanner heap abort, described below. No green
  whole-suite claim is made for this batch.
- Forty-six compact evidence files were hash-verified before removing the
  private donor/overlay. Same-process verification now covers the shared actor
  registry teardown/reconstruction; original character scripts and full note,
  event, camera and strumline behavior remain separate compatibility work.

## Scanner memory investigation update (24 September)

- A bounded follow-up series of three runs with the same reviewed cached
  recycler diagnostic binary completed (125.6/126.8/126.3 seconds), all exit
  zero, identical counts, no invariant violation or stderr. No fourth run was
  made. Evidence is under `tmp/auto-import-recycler-series/`. This still does
  not explain the duplicate insertion seen in the saved normal core.

- Added an opt-in private normal-GC `--recycle-diagnostics` build. It checks
  failed live-list removal and duplicate explicit/sweep insertion, reporting a
  bounded native stack before abort. The compiled binary contains the probe;
  21 focused diagnostic tests pass. One bounded scan completed 16 roots and
  84 unique candidates with no violation (three missing dependencies, 46
  scripts); normal toolchain hashes were unchanged. This does **not** resolve
  the intermittent defect. Evidence:
  `tmp/auto-import-diagnostic-recycle-cache/dc294ce9006ac4289df7f7db0d656dfbfd0865ec75888e69ffd297e4a2d47f41/`.

- The fresh core now identifies the exact allocator failure: the free loop for
  `largeObjectRecycle` contains the same allocation at indices 987 and 988.
  The 2,294-entry list has exactly one duplicate, and that pointer is absent
  from the remaining live large-object list. Prior cores stop at the same
  recycler free call. This proves a duplicate free; it does not identify the
  code that inserted the duplicate. Next instrumentation targets both recycler
  insertion paths, including a failed live-list removal in `FreeLarge`.
  Evidence: `tmp/auto-import-current-3382766-free-site-summary.md` and its
  referenced disassembly/list audits. No production allocator fix is claimed.

- The full normal scan again aborted with `double free or corruption (!prev)`,
  now after the three-candidate Hatsune Miku root and before Wacky World/DDTO.
  The different failure point reinforces that content names are reproduction
  context, not an appropriate fix boundary.
- Added explicit `--scan-timeout-seconds` (default 300, finite positive value),
  preserving the cached binary key and separate build bound. Nineteen focused
  diagnostic tests pass. One cached v2 ASan scan with a 600-second limit completed
  all 16 roots: 84 candidates/selected/unique, no duplicates, three missing
  dependencies, 46 inspected scripts. Exit zero, no ASan report, pinned normal
  hxcpp source hashes unchanged. Evidence:
  `tmp/auto-import-diagnostic-asan-cache/327cb1e7268b3bc1959d262aff13521379891f940ae8d276440c989c2de6fb0d/run-3378892-8c7fb302b5664eac8964e9fb6e48a6c5`.
  This instrumented pass does not resolve the reproducible normal allocator
  abort; root-cause investigation continues. The fresh normal core (PID3382766)
  was recovered read-only into `tmp/auto-import-current-3382766.core`; thread
  stacks are in `tmp/auto-import-current-3382766-gdb.log`. Detection occurred
  during hxcpp GC while dependency inspection allocated a normalized path;
  four GC workers were waiting. This identifies the detection/free path,
  not a corrupting write or a content-specific cause.

## DDTO/Future Sound native heap aborts (24 September)

- The retained runtime logs record allocator aborts during chart setup: DDTO++
  `god-eater-monika-mix` (`example-matrix-095.process.log:75`) reports
  `corrupted size vs. prev_size while consolidating`; DDTO++ `knives`
  (`example-matrix-106.process.log:704`) reports `double free or corruption
  (!prev)`; Future Sound (`goal-future-sound.process.log:119`) reports the
  same corrupted-size message. The runs reach character/stage/HXC setup but do
  not emit `playstate_ready`. The same allocator errors appear in unrelated
  matrix songs, so the chart names are reproduction context, not a safe fix
  boundary. Successful later DDTO++ runs exist, including the retained
  20-process repeat series in `tmp/example-game-recycler-probe/repeat20/`;
  these successes show intermittency and do not disprove the aborts.
- No matching game core is retained for 23–26 September (`coredumpctl` query
  returned no `Funkin`/`Main` entries in that interval). The captured DDTO++
  and Future Sound logs therefore provide the exact allocator messages and
  load phases, but no application backtrace. The unrelated scanner core
  `tmp/auto-import-current-3382766.core` must not be represented as a game
  crash: its stack is `free -> GlobalAllocator::Collect -> GetFreeBlock ->
  hx::NewString -> Path.normalize -> DependencyInspector...` while scanning
  import candidates.
- The scanner core proves that the shared hxcpp large-object recycler can
  contain the same pointer twice before its free loop: the 2,294-entry
  `largeObjectRecycle` had its only duplicate at indices 987 and 988, and the
  pointer was absent from the 746-entry live list. The repository pins hxcpp
  4.3.2 (`run.sh:196`, `.haxelib/hxcpp/.current`). In that source,
  `GlobalAllocator::FreeLarge` (`Immix.cpp:3176-3197`) ignores the boolean from
  `mLargeList.qerase_val(blob)` and pushes the pointer into the recycle vector
  anyway; `Collect` later frees each vector entry (`Immix.cpp:5064-5067`).
  This is a concrete shared allocator hazard, but the scanner core does not
  prove that the game aborts took this path.
- Static call-site inspection found `InternalReleaseMem` reached from
  `ArrayBase::__SetSizeExact(0)` and from mutually exclusive branches in
  `InternalRealloc`; the former nulls `mBase` immediately, while the latter
  replaces it with the returned allocation. No normal in-tree duplicate delete
  route was established. A duplicate `FreeLarge` call would make the unchecked
  failed removal enqueue the same blob again, but reaching that path through
  valid array ownership remains unproven.
- The existing private `--recycle-diagnostics` hxcpp overlay checks failed
  live-list removal before the explicit recycle push and checks duplicates at
  explicit/sweep insertion and before the free loop. Its standalone QuickVec
  harness includes an injected duplicate transition. Four retained scanner
  runs with this diagnostic completed without a `HXCPP_RECYCLE_*` violation;
  this is useful negative evidence for those scanner runs, not for gameplay.
  No production or haxelib source was changed. A focused gameplay build with
  this probe or a matching game core is still needed to attribute the DDTO++ /
  Future Sound aborts before proposing an allocator patch.

## Codename live actor occurrences (24 September)

- Added a shared occurrence runtime keyed by source line/character index.
  Duplicate IDs construct separate instances; exact primary aliases are borrowed;
  unresolved slots retain null positions. Owned-only cleanup is idempotent.
- Generated XML stages publish the full validated placement model. Runtime
  presentation uses constructor baselines and the current stage model for
  position, spacing, scroll, scale, alpha, angle and skew. Stage replacement
  retains actors and rebinds ordering. Unsupported placement or edited primary
  identities are diagnosed before creating additional actors.
- Three focused actor tests pass, including extracted real PlayState methods
  for current-stage selection and nonaccumulating presentation. Stage publication
  and importer focused tests also pass. Canonical native builds pass. Two fresh
  offscreen processes each verified distinct actors/primary aliases, occurrence
  spacing and A/B/A stage replacement with stable identities and restored
  scale/alpha/angle/skew. Settings and checked registries stayed unchanged.
  Evidence: `tmp/codename-live-actors/native-probe.result.json`. These are fresh
  process loads, not two PlayStates in one process; native teardown verification
  remains open. The first full suite ran 956 tests across 242 modules in
  186.4 seconds (61 skipped), failing two extracted fixtures missing the new
  `reapplyCodenameActors` stub and `codenamePlacement` field. Both fixtures are
  updated, including a placement-reset assertion; their three focused tests
  pass. The follow-up suite passed **956 tests across 242 modules in 183.0
  seconds; 61 skipped, zero failures** (`tmp/codename-live-actors-suite-fixed.log`).
  The final canonical build passed (`tmp/codename-live-actors-build-verified.log`).
  Earlier logs: `tmp/codename-live-actors-suite.log` and
  `tmp/codename-live-actors-wrapper-tests.log`. Disposable native donor/overlay
  fixtures were removed after hashing 45 compact evidence files; the runner and
  reproduction summary remain under `tmp/codename-live-actors`.
- Original Codename character scripts, source-indexed note/event/camera routing,
  extra playable strumlines, per-character zoom and full draw-offset semantics
  remain open. Older generated scripts without placement publication retain
  their existing behavior and require a reviewed migration to adopt this path.

## Codename song metadata verification resumed (24 September)

- Shared import discovery preserves raw metadata and writes a separate resolved
  per-difficulty record with file and inline provenance. Runtime script views
  forward native chart properties while keeping mutable metadata per PlayState.
  Variant metadata selection and flags.ini overrides remain unsupported and
  explicitly diagnosed.
- The resumed focused loader, interpreter, metadata and camera-plan run passed
  five tests (`tmp/codename-meta-resumed-focused.log`). The canonical build
  reported up to date (`tmp/codename-meta-resumed-build.log`). The revised
  native probe passed two isolated owners at normal/hard plus raw-only fallback.
  All six loads verified create/postCreate/update, live chart fields and expected
  metadata; selected BPMs were 120/134 and 145/159. Checked installed bytes were
  unchanged. Evidence: `tmp/codename-song-meta/native-probe.result.json`. This
  verifies the metadata contract, not complete scene compatibility. The full
  suite reported **950 tests across 240 modules in 184.0 seconds; 61 skipped,
  one failure** (`tmp/codename-meta-resumed-suite.log`). The normal scanner
  completed its counts, then diagnostic cleanup raised `UnboundLocalError` for
  `root_dir_fd` on the cached path. This is a new diagnostic-tool regression;
  initialization now occurs before the cache branch. A new test executes the
  cached main/cleanup path. The follow-up full suite passed **951 tests across
  240 modules in 181.2 seconds; 61 skipped, zero failures**
  (`tmp/codename-meta-resumed-suite-fixed.log`). The later private conservative
  stack-read diagnostic guard has 16 focused passing tests. This passing normal
  scan does not establish that the intermittent corruption is fixed.
- Reviewed shared missing-file plans added eight metadata sidecars across the
  two installed owners. Receipts: `tmp/import-refresh-backups/20260924T004211418732Z`
  and `20260924T004218488253Z`. All candidate hashes match; all 46/150 recorded
  existing inputs and critical snapshots remain unchanged. Repeat plans have
  zero additions; the existing differing camera file remains preserved.
  Fresh offscreen installed Hopkins gameplay passed with owned opponent/GF
  atlases and no script errors (`tmp/codename-bully-installed-play/result.json`).
  That check does not directly assert metadata name; the synthetic probe does.
  Compact preview evidence is retained under `tmp/codename-bully-meta-preview`
  and `tmp/codename-hl17-meta-preview`; disposable overlays were removed.
- Live settings still hash to
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
- The previous ASan attempt stopped before scanner execution because haxelib
  selected the checkout repository instead of the private copy. The diagnostic
  now uses `--global` with its private HAXELIB_PATH and refuses compilation when
  the path preflight escapes that copy. Fourteen focused diagnostic tests pass.
  The isolated ASan build subsequently succeeded (178 compiler invocations).
  Its scan aborted before the first root count at the conservative GC stack
  read in `Immix.cpp:5638`, over the collector's intentional stack marker.
  This is a diagnostic false positive, not evidence of the importer overwrite.
  Symbols and output are preserved in
  `tmp/auto-import-diagnostic-asan-cache/09b33b35cf71295fe57d1c5b809c8294f039de41c37f5109d140d9198be3051d`.
  A narrowly scoped private stack-read exemption is prepared and tested; the normal
  toolchain is unchanged. A subsequent cached v2 scan ran for 300 seconds and
  timed out (exit 124), with no ASan report and partial counts through the
  50-candidate DDTO root. It did not finish the final roots/aggregate. Timeout
  handling now preserves partial stdout/stderr and records `timed_out` in the
  run artifact; 18 focused diagnostic tests pass. Evidence:
  `tmp/auto-import-diagnostic-asan-cache/327cb1e7268b3bc1959d262aff13521379891f940ae8d276440c989c2de6fb0d/run-3371875-4ce70d10be1849c1982ef459e5fa7837`.
  The intermittent scanner corruption remains unresolved; absence of a report
  before timeout is not proof of a fix.

## Installed Codename namespace repair (23 September)

- Added `repair_codename_owned_bundles.py`: derive the owner through the real
  manifest helper, validate matching selected songs, inventory the bounded
  preview owner, and add only missing files. Both runtime locks, exact plan
  revalidation, atomic no-clobber writes and rollback protect existing content.
  Twelve focused tests pass, including source-folder case differences,
  conflicting registries, concurrent file creation, changed inputs, rollback,
  symlink rejection, disjoint donor/runtime paths and idempotence.
- Fresh native offscreen previews generated missing owned files for the two
  selected donor roots. Reviewed plans added 16 Bully files and 64 HL17 files.
  All 21 pre-existing preservation hashes stayed unchanged at this point.
  Receipts: `tmp/import-refresh-backups/20260923T154918627855Z` and
  `20260923T154919512292Z`. Replanning found zero missing files for both owners.
- The separate actor metadata tool initially refused its unchanged plan because
  Python set iteration changed serialized field order between processes.
  Sorted additive keys now produce stable after-images; nine focused tests
  pass, including four independent hash-seeded Python processes. The reviewed
  second plan upgraded only the old Hopkins camera sidecar, preserving every
  pre-existing metadata value. Backup:
  `tmp/import-refresh-backups/20260923T155102625712Z`. Its repeat plan is empty.
  Charts, selected manifests, existing scripts, global registries and settings
  remained unchanged (`tmp/codename-owned-repair-installed-result.json`).
- A private snapshot of the updated installed Hopkins chart/owner loaded
  successfully offscreen. Live visual records resolve the opponent and GF
  atlases within the selected owner. The old chart's `bf` identity still uses
  native fallback instead of the newly mapped `boyfriend`; this repair did
  not rewrite its chart. Evidence: `tmp/codename-bully-installed-play/result.json`.
- A short HL17 preview gameplay probe reached PlayState and loaded its three
  owned characters without crashing. Unsupported Flx3D/Away3D and other
  imports prevent faithful stage behavior; the stage script also disables
  initial slot-orientation metadata. Imported event metadata and legacy note
  provenance remain separate migration work. This is basic load evidence,
  not complete Codename gameplay compatibility. Evidence:
  `tmp/codename-hl17-preview/gameplay.analysis.json`.
- The full suite before the deterministic-serialization fix reported
  **936 tests across 238 modules in 102.2 seconds; 61 skipped, one failure**
  (`tmp/codename-owned-bundles-suite.log`). The normal native scanner again
  aborted with `corrupted size vs. prev_size while consolidating`; no engine
  source changed in this repair batch. The later nine-test actor refresh run
  passed (`tmp/codename-actor-refresh-determinism-tests.log`). The heap failure
  remains unresolved and this batch does not claim a green full suite.
- The three private runtime overlays were removed after verification. Compact
  JSON/script evidence, file inventories, logs, snapshots and cleanup ledgers
  remain under `tmp/codename-bully-preview`, `tmp/codename-hl17-preview` and
  `tmp/codename-bully-installed-play`. Backups and repair receipts are retained.

## Complete-song import repair (23 September)

- Reproduced a shared importer bug with an isolated synthetic Codename donor:
  after deleting only the owner's converted character/stage bundles while
  retaining its song scripts and manifest, re-import skipped the complete
  chart and copied nothing. The missing visuals remained missing.
- Complete same-owner Codename and V-Slice songs now enter the existing
  missing-only visual/runtime merges without re-entering chart import or
  rewriting their manifest. Foreign-owner rejection still precedes repair.
  Focused executable tests cover both engine branches, edited chart/script
  preservation, idempotence and ownership refusal (15 tests passed).
- Canonical release build passed: `tmp/codename-owner-repair-build.log`.
  The same native offscreen fixture then restored 14 missing items with
  imported=0, skipped=1, failed=0. A second import copied zero items and kept
  an appended user script edit. Both runs retained the exact edited chart
  hash. Evidence: `tmp/codename-owner-repair/pre-fix.result.json` and
  `post-fix.result.json`. The native repair probe covers Codename; V-Slice
  scheduling is covered by the executable branch test.
- Installed critical files and settings remained unchanged. This verification
  repaired a private fixture, not the installed older namespaces. Disposable
  donor/runtime overlays were removed; compact evidence and logs remain.
- The full suite passed **924 tests across 237 modules in 172.3 seconds;
  61 skipped, zero failures** (`tmp/codename-owner-repair-suite.log`). Its
  normal native scanner passed on this run; the previously reproduced
  intermittent heap failure remains open. The diagnostic cache test also
  passed separately after making its temporary directory explicitly local.

## Existing Codename actor metadata refresh (23 September)

- Added shared plan/apply tooling for additive actor metadata upgrades from
  current-engine isolated import previews. Runtime locks, exact plan/input
  revalidation, verified backups and rollback protect existing content. Eight
  focused tests pass, including an interrupted second replacement restoring
  the first, edited values/implementations, stale inputs and missing bundles.
  Evidence: `tmp/codename-actor-refresh-tests-final.log`.
- Installed metadata inventory found four selected songs: three HL17 songs
  have no selected namespace; Hopkins has an old camera sidecar. A fresh native
  offscreen import preview for the exact donor root generated current Hopkins
  metadata with no installed mutations. Existing metadata values agree, but
  review found its matching owned character/stage bundles are absent; older
  playable files live globally. The applicability gate now rejects this
  sidecar-only upgrade until shared namespace repair supplies matching bundles.
  No installed sidecar, chart, script, asset or settings file was changed.
- Inventory: `tmp/codename-actor-refresh-inventory.json`. Rejected final plan:
  `tmp/codename-actor-refresh-plan-v2.json`. Native preview result and compact
  source evidence remain under `tmp/codename-bully-preview/`; preview/gameplay
  overlays were removed. No installed gameplay probe was launched.
- The broad suite run before the final applicability-gate tests reported
  **919 tests across 236 modules; 61 skipped, one failure**. Its native mounted
  importer scanner aborted with `double free or corruption (!prev)` during
  V-Slice discovery. This reproduces an unresolved native heap problem; it is
  not dismissed as a passing run. Evidence: `tmp/codename-actor-refresh-suite.log`.
  One bounded GDB rerun completed normally across all 16 roots (84 selected
  records), without a crash stack: `tmp/auto-import-current-gdb-repro.log`.
  Earlier saved cores detect corruption during hxcpp GC allocation while
  resolving V-Slice assets; those allocation stacks do not identify the write
  responsible. The intermittent heap issue remains unresolved.
  The scanner now accepts `--gc-debug-level-1`, compiling with pinned hxcpp's
  `HXCPP_GC_DEBUG_LEVEL=1` under a distinct diagnostic cache key. Normal builds
  and scans keep their existing flags. Three focused tests verify opt-in
  parsing, compiler flags and cache separation. Level 1 adds GC checks and
  changes marking concurrency, so a successful diagnostic run alone would
  not establish that ordinary native scans are fixed.
  One level-1 diagnostic run completed with exit 0: 16 roots, 84 selected
  candidates, zero duplicates and three missing dependencies. It emitted no
  GC errors. Evidence: `tmp/auto-import-gc-debug-level-1-counts.log`; the
  instrumented cache key is distinct from the normal scanner. The tool
  suppressed successful compiler output, so this log records the command
  and scan result rather than a compiler transcript.

## Codename initial actor identity and orientation (23 September)

- New camera sidecars preserve exact native registry names for authored actors
  and the selected difficulty's native stage. Explicit null actor entries mark
  unresolved definitions without discarding other known mappings. Older
  sidecars retain unknown mappings and are not overwritten.
- `CodenameActorPlan` keeps separate records for every line/occurrence, including
  repeated IDs. Initial runtime selection validates owner containment, song,
  difficulty, authored stage, native stage and exact primary actor identity.
  Resolved stage slots select constructor orientation before actor creation.
  This is still primary-actor construction, not live additional actors or
  indexed camera/note routing.
- The executable actor-plan test passes repeated-ID spacing, empty-line skipping,
  unresolved-first-role handling, slot flips, edited-chart refusal, malformed
  and old metadata, ambiguous difficulty names and unresolved stage dependencies.
  Focused importer tests passed 10/10 after retaining XML `flipX` metadata.
- The selected Codename character constructor uses XML `playerOffsets` to
  decide sing/miss frame and named-offset swaps, then applies the stage slot
  flip even for dance-pair characters. Other engine constructors retain their
  existing path. Full draw-time offset transforms and per-instance Codename
  character scripting remain unfinished.
- The canonical build passed (`tmp/codename-actor-orientation-build.log`).
  The private native import/PlayState probe passed with transformed registry
  names, repeated authored IDs and live frame/offset assertions for all three
  primary actors. It includes a player slot with no flip but reversed offset
  convention, an opponent with matching flipped convention, and a flipped
  dance-pair GF whose generated native script has `noFlip=true`.
  Result: `tmp/codename-actor-orientation/native-probe.result.json`; marker:
  `ORIENTATION_OK|player=false|opponent=true|gf=true|LR-frames-offsets|safeStem`.
  This checks live construction and animation data, not full drawing/camera
  equivalence. Installed settings/registries remained byte-identical; disposable
  donor and overlay files were removed. Existing imports were not refreshed.
- Final full suite passed: **913 tests across 235 modules in 171.8 seconds;
  61 skipped, zero failures** (`tmp/codename-actor-orientation-suite.log`).
  Additional actors, indexed camera/note routing, complete character drawing
  and script lifecycle, and backed-up upgrades of existing sidecars remain open.

## Codename XML stage ordering (23 September)

- Shared stage placement metadata retains ordered prop/anchor records, including
  duplicate anchors and appended default GF/dad/BF slots. Old sidecars without
  order stay readable with unknown order. Empty named slots remain valid; a
  missing name is distinct. Unsupported XML/script effects retain diagnostics.
- Live StageHelper anchors preserve prop/actor interleaving. Actor bindings
  remain separate from stage ownership and rebind before character-added
  callbacks during native swaps. The generated path currently binds primary
  actors; creating all authored strumline actors remains unfinished.
- Removed XML nodes remain in an ownership ledger so stage teardown releases
  detached props/anchors too. The focused executable runtime test verifies
  duplicate-key selection, repeated actor instances, replacement/self-rebinding,
  unknown slots, one-time node destruction and actor/HUD survival.
- Initial focused metadata/camera-plan tests passed, as did the runtime ordering
  test (`tmp/codename-stage-order-runtime.log`). The canonical build passed,
  followed by an incremental build for the primary-actor selection correction
  (`tmp/codename-stage-order-build-final.log`). Receptor-only lines are skipped
  when selecting the first line that actually owns the native primary actor.
- The private native probe passed real import and live PlayState checks:
  normal difficulty's default anchors, an interleaved alternate stage, duplicate
  dad slots selecting the last anchor, a native player self-swap and repeated
  `OrderB -> OrderA -> OrderB -> OrderA` swaps. Actor identities survived; old
  props/anchors released their sprite resources, including a detached anchor.
  Result: `tmp/codename-stage-order/native-probe.result.json`; live marker
  `STAGE_ORDER_OK|interleaved|duplicate-last|defaults|reload`. This is repeated
  stage replacement in one PlayState, not a claim of complete song-reload parity.
  Private fixtures were removed and installed settings/registries were unchanged.
- Existing imports were not rewritten. New stage generation uses these APIs;
  old generated scripts require a shared, backed-up refresh to gain this order
  representation. Full additional-actor creation and camera/note routing remain
  open.
- The initial full suite exposed one outdated extraction fixture in
  `test_stage_group_forwarding.py`: it lacked the new stage ownership fields.
  The corrected fixture passed, then the final full suite passed: **910 tests
  across 233 modules in 169.9 seconds; 61 skipped, zero failures**
  (`tmp/codename-stage-order-suite-final.log`). This does not establish full
  engine parity or resolve the previously recorded intermittent heap issue.
- Follow-up actor integration audit: `tmp/codename-actor-next-audit.md`.
  Authored-to-native character identity mapping, constructor-time orientation,
  per-occurrence ownership and replacement-stage placement remain required.
  The live settings hash remained unchanged after verification.

## Codename note identity and complete editor row copies (23 September)

- Imported playable notes retain original strumline/note ordinals in versioned
  row column 13, including duplicate-role lines and custom note types. Native
  head, sustain and generated lift objects receive independent metadata.
  Legacy rows remain untagged; stale side/schema/key-count metadata is rejected.
- Unsupported GF/extra line note records are retained per difficulty. Song
  loading clears sibling records when the selected difficulty has no list.
  Additional Codename actors/receptors and note routing remain unfinished;
  retaining identity does not make those lines playable yet.
- Editor section copies now preserve the entire row with independent nested
  data, replacing only the timestamp. Existing optional note parameters and
  compatibility metadata are no longer truncated to three fields.
- The first native probe caught a real issue missed by interpreter tests:
  inferred section-sort callback parameters became `Array<Int>` on hxcpp,
  coercing every row's null/object values to zero. The same generated callback
  type existed in V-Slice. Both importers now explicitly sort mixed dynamic
  rows, preserving fractional times and optional fields. Pre-fix evidence:
  `tmp/codename-note-origin/pre-fix-failure.result.json` and
  `pre-fix-imported-chart.json`.
- Focused importer tests passed (10), editor row-copy tests (1), nearby editor
  tests (2), selected-difficulty loader tests (5) and runtime propagation test
  (1). The first broad run passed 905 tests across 230 modules with 61 skips;
  that run preceded the native sorter correction.

- The corrected canonical build passed:
  `tmp/codename-note-origin-build-final-typed-rows.log`. The private native
  import/gameplay probe passed with five exact source identities and a
  5000.25 ms timestamp; live PlayState checked five heads, two sustain segments
  and one generated lift. An untagged legacy head, two sustains and its lift
  all remained null. Results: `tmp/codename-note-origin/native-probe.result.json`.
  This validates construction/identity, not completed per-line actor routing.
  The donor/runtime overlay was removed and installed settings/registries
  remained byte-identical.
- `test_importer_note_sort_cpp_codegen.py` generates C++ from both real
  comparator expressions and verifies dynamic row arguments. Its untyped
  negative control reproduces the integer-array inference; interpreter checks
  retain fractional timestamps/sustains, nulls and structured fields. It does
  not link a standalone executable (hxcpp's tiny-target include parsing failed
  on this checkout's spaced path). The canonical game build and Codename native
  import probe provide the actual native execution evidence.
- An intermediate full run saw the new propagation test before its Python
  f-string edit was finished, producing a test-construction NameError. The
  corrected focused test passed. Final frozen-source verification passed:
  **907 tests across 232 modules in 171.4 seconds; 61 skipped, zero failures**,
  recorded in `tmp/codename-note-origin-suite-verified.log`.
- No installed imports were refreshed for this batch. Existing imports without
  source tags remain untagged; any future refresh must use shared tooling and
  recoverable backups. The live settings SHA256 remains
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.

## Codename difficulty stages and empty chart loading (23 September)

- Each Codename difficulty now resolves its own authored stage. Every distinct
  stage converts in the selected owner using the first chart that references
  that stage and its character offsets. Case-distinct keys remain distinct.
  Missing/failed source stages produce owned registry declarations without a
  script, retaining identity through Song's difficulty merge and preventing
  sibling/global stage substitution. Native-only aliases retain their fallback.
- Runtime swaps compare canonical stage identities exactly. `Room` and `room`
  can replace each other; a unique case alias resolving to the current stage
  stays a no-op. Declared unavailable swaps preserve the current stage.
- Ambiguous converted character/stage identities reject their song candidate
  before materialization, including a converted-owned character versus a
  separate unresolved/native fallback identity. Native-only aliases remain
  allowed. This prevents wrong content selection; general identity encoding
  for arbitrary source IDs remains unfinished.
- Focused importer tests passed (nine), along with the executable stage resolver/
  swap tests (two) and Song owner/merge tests (five). Logs:
  `tmp/codename-difficulty-stage-swap.log` and
  `tmp/codename-difficulty-stage-loader.log`.
- Native testing discovered an existing shared crash on zero-note charts:
  `generateSong` dereferenced `unspawnNotes[0].width`. The failure was reproduced
  on the pre-fix binary with exit -11 after `before generate`; evidence is
  `tmp/codename-difficulty-stages/empty-notes-pre-fix-failure.result.json` and
  its named failure process log. The initial attempt's log had been overwritten;
  the preserved reproduction is the authoritative failure evidence.
- The shared fix retains first-note width for populated charts and uses loaded
  receptor width for empty charts, with an engine lane-width fallback. The
  executable regression verifies empty packs, invalid receptor entries,
  player/opponent fallback and unchanged populated-chart behavior:
  `tmp/empty-chart-note-alignment.log`.
- The first canonical build and 902-test suite passed before the final
  converted-vs-fallback collision guard and empty-chart fix. The final build
  also passed (`tmp/codename-difficulty-stages-build-final.log`); final suite and
  empty-chart runtime results are recorded below.
- The native one-note fixture passed real import plus three difficulty loads,
  verifying distinct `Room`/`room` props and graphics, `Room -> room -> Room`
  swaps in one process, missing-stage identity and blocked global/sibling
  substitutions. Unavailable swaps preserved the live stage. Evidence:
  `tmp/codename-difficulty-stages/one-note-native-probe.result.json` and retained
  one-note logs. These checks exercise stage swaps, not full song-state transitions.
- Final full suite passed 903 tests across 229 modules in 179.5 seconds,
  61 skipped, zero failures (`tmp/codename-difficulty-stages-suite-final.log`).
  The final built binary passed the same three difficulty loads with zero notes,
  including exact prop paths and stage swaps; the former native crash is gone.
  Evidence: `tmp/codename-difficulty-stages/empty-notes-native-probe.result.json`
  and its process/marker logs. The preserved pre-fix result records the old
  binary hash and exit -11, with separate `pre-fix-empty-notes-*` logs.
- All native runs used private Xvfb/runtime roots. Installed settings and global
  registry bytes stayed unchanged, and private donor/runtime/cache fixtures were
  removed while keeping the runner, results and evidence logs.
- Remaining: one shared stage used with different actor placements across
  difficulties is diagnosed and still uses its first authored occurrence;
  indexed actor runtime, note provenance and exact stage display order remain
  incomplete. Installed imports have not been rewritten.

## Codename complete character discovery and placement metadata (23 September)

- Shared Codename discovery now collects all exact character IDs across every
  converted difficulty and ordered strumline, including repeated occurrences
  and extra lines without native notes. Each definition is materialized once
  in the selected owner, while occurrence lists retain their original order.
  Scoped case-distinct IDs remain separate; exact XML/registry matches take
  precedence, and ambiguous casefold XML lookup stays unresolved.
- Each generated difficulty retains its own primary character choices instead
  of inheriting the first chart's choices. Missing definitions and actual
  converted-name collisions are diagnosed. Missing-only repair still preserves
  existing scoped edits and global assets.
- Camera sidecars now carry optional full `stagePlacement` data: named and role
  slots, spacing, flip, presentation, camera offsets and unresolved dependencies.
  The pure codec validates field types, finite numbers and required slots;
  older metadata remains explicitly without a placement model. Stage script
  dependencies remain marked instead of presenting XML as the whole live scene.
- Focused coverage passed: three placement model/codec tests, two camera plan
  tests, five shared script-import tests, one generated-stage test and nine
  Codename import tests. Logs: `tmp/codename-actor-placement-codec.log`,
  `tmp/codename-actor-camera-plan.log`, `tmp/codename-actor-script-import.log`,
  `tmp/codename-actor-placement-script.log`; the import module is also included
  in the full-suite evidence below.
- Canonical build passed (`tmp/codename-all-actors-build.log`). Full suite:
  902 tests across 228 modules in 217.5 seconds, 61 skipped, zero failures
  (`tmp/codename-all-actors-suite.log`). Build and tests overlapped in this run.
- Two isolated offscreen native import runs passed through the real importer.
  The first copied 31 assets, including secondary/extra/later-difficulty actors,
  case-distinct atlases/registries, distinct hard/normal primary characters,
  repeated camera occurrence IDs and the full placement sidecar. After deleting
  one private PNG and the camera sidecar, same-owner repair copied two files,
  skipped 29, and preserved an edited scoped character script. Neither run
  failed or merely skipped the selected song. Evidence:
  `tmp/codename-all-actors/native-probe.result.json` and per-run process/marker
  logs. This verifies import/repair, not live additional actor rendering.
- Installed global registry and settings hashes remained unchanged; native
  processes exited zero, and the private overlay/donor fixtures were removed.
- Remaining: PlayState does not yet consume the complete sidecar to create
  indexed actor instances. Generated stage initialization still selects the
  first difficulty's primary placement; per-difficulty stage selection,
  additional actor lifecycle, character script hooks and live Camera Movement
  remain incomplete. Existing installed imports were not rewritten.

## Codename stage ownership (23 September)

- Codename primary and event-only stage conversions now materialize scripts,
  registry rows and prop assets in the selected import namespace. Donor XML
  takes precedence over native aliases. Missing-only repair preserves existing
  scoped edits and leaves colliding global assets unchanged.
- `ImportedStageRegistry` supplies shared Song validation/normalization and
  PlayState load/swap resolution for selected Modding Plus/Codename owners.
  Missing or unsafe owned scripts, malformed registries and ambiguous casefold
  keys prevent foreign fallback. Unavailable swaps return before teardown;
  an absent owned row retains existing native fallback.
- Canonical build passed (`tmp/codename-stage-owner-build.log`). Twenty focused
  importer/loader/difficulty tests passed (`tmp/codename-stage-owner-focused.log`).
  Two resolver tests additionally execute the production helper and extracted
  PlayState resolver/swap functions (`tmp/codename-stage-owner-resolver.log`).
- Full suite ran 901 tests across 228 modules in 172.5 seconds, with 61
  skipped and one failing module (`tmp/codename-stage-owner-suite.log`). That
  failure was the new extraction fixture missing `using StringTools`, not a
  production failure. After correcting the fixture, both tests in that module
  passed separately on the same production sources. All other modules passed
  during the full run; the entire suite was not rerun after the fixture-only fix.
- Three isolated offscreen native launches passed: both owners coexist with the
  same logical stage ID and a colliding global registry. Each selected owner
  loaded its generated Codename stage, authored prop coordinates and owned prop
  graphic. A declared unavailable stage swap preserved the current StageHelper.
  Removing the initial owner's script produced the missing-stage diagnostic and
  never executed the colliding global stage. Evidence:
  `tmp/codename-stage-owner/native-probe.result.json` and per-variant logs.
- Live settings hash remained unchanged; all native probes exited successfully
  and the private runtime overlay was removed. These were separate launches;
  they do not prove same-process owner transitions or full stage-script parity.
- Installed imports were not rewritten. Older generated charts that lost donor
  identities, full stage display-list ordering, additional actor instances and
  nested identifiers still need shared compatibility work. The character-owner
  section below predates this stage-ownership implementation.

## Codename character ownership (23 September)

- Converted character assets, scripts and registry entries now use the selected
  Codename import namespace. Donor XML definitions take precedence over built-in
  name aliases. Missing-only repair preserves scoped edits and leaves the global
  registry/assets unchanged; missing ownership fails the materialization step.
- Runtime character and icon resolution share selected Psych/Codename ownership.
  Psych camera metadata remains Psych-only. Owned character identities survive
  chart validity and GF fallback, so a missing owned dependency can be diagnosed
  without replacing its authored ID. Freeplay icons receive their row's song
  explicitly; same-named rows no longer depend on a gameplay owner's registry.
- The importer’s nine focused tests passed, including native-name override,
  non-overwrite, global sentinel preservation and missing-owner rejection. Eleven
  runtime/loader checks passed (`tmp/codename-character-owner-focused.log`), plus
  `test_health_icon_owner.py`, which executes explicit row-owner, alias and
  active-state isolation using the production icon lookup method.
- Canonical build passed (`tmp/codename-character-owner-build.log`). Full suite
  passed 899 tests across 227 modules in 177.6 seconds, 61 skipped, zero failures
  (`tmp/codename-character-owner-suite.log`); the new icon-owner module was added
  after that run started and passed separately on the same production sources.
- A 15-second offscreen Psych Ballistic Hard guard passed with exit code zero
  after the shared owner lookup changed. The captured frame retains the selected
  stage, Whitty/BF/GF, notes and HUD; no script-error/exception marker was found.
  Evidence: `tmp/codename-owner-psych-guard.log` and
  `tmp/runtime-smoke/codename-owner-psych-guard-reopened-11.0.png`/`.process.log`.
  This guards the changed owner path, not full Psych gameplay parity.
- Two sequential isolated native launches passed with both Codename namespaces
  present and identical logical character IDs. Each selected root supplied its
  own initializer, atlas path and both health icon graphics; no foreign
  initializer ran. A GF definition absent from the global registry survived
  chart loading and resolved from the selected root. Both processes exited zero
  in about nine seconds, settings were unchanged, and the overlay was removed.
  Evidence: `tmp/codename-character-owner/native-probe.result.json` and the
  per-owner process/marker logs. These were separate launches, not a same-process
  transition test; Freeplay owner isolation is covered by the executable icon
  lookup test rather than a native menu capture.
- Existing generated charts that lost authored IDs to native aliases still
  require provenance-safe refresh. Converted stage ownership, additional actor
  instances and nested character IDs remain incomplete. No installed imports
  were rewritten by this implementation batch.

## Codename stage placement model (23 September)

- Added a pure shared model of upstream stage placeholders: role tag aliases,
  named character precedence, last definition winning, chart position selection,
  default role coordinates/scroll, per-occurrence spacing, flip and presentation
  metadata. Named placeholders use neutral defaults even when named after a role;
  missing explicit slots do not invent spacing or role fallback. Dynamic stage
  dependencies are reported as unresolved.
- Stage conversion uses that model for the existing primary actors' positions
  and live/stored scroll factors. BF's omitted Y now matches Codename's 100,
  rather than the native engine's 450. Missing chart position remains null;
  explicit empty position stays empty through camera metadata serialization.
  Role camera metadata no longer treats every named character as dad.
- Character XML `isPlayer` is preserved as `playerOffsets`. The converted visual
  placement reverses global X when that flag differs from the selected stage
  flip; global Y retains its sign. A repeated definition supplies offsets to
  every primary role using it. Animation orientation and runtime offset mutation
  remain unfinished; world-coordinate translation is not a complete substitute
  for upstream sprite-offset behavior.
- Fourteen focused checks passed, including executing actual generated HScript
  against actor and stored-stage boundaries. They cover named-versus-position
  selection, omitted defaults, absent/empty position, scroll, and both global-X
  signs. Evidence: `tmp/codename-stage-placement-focused-final.log`.
- Canonical build `tmp/codename-stage-placement-build-final.log` passed. Three
  isolated native stage loads passed via the real generated HScript: matching
  offset convention, mismatched convention, and omitted role placeholders.
  Each asserted live actor coordinates, scroll factors and stored stage offsets.
  Evidence: `tmp/codename-stage-placement/result.json` and its per-variant logs.
  The fixture overlay was removed; installed imports and settings were unchanged.
- Final full suite passed after offset-sign composition: 899 tests across 227
  modules in 171.8 seconds, 61 skipped, zero failures
  (`tmp/codename-stage-placement-suite-final.log`). Live options retained SHA256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
- Remaining: per-occurrence actor creation, complete stage document draw order,
  presentation/lifecycle parity, character hooks and live Camera Movement.
  Discovery still starts from the first converted difficulty's primary actors;
  donor definitions using native-reserved IDs and nested IDs need a complete
  ownership/resolution path. Existing generated imports are not overwritten by
  these changes; no donor files were modified.

## Codename camera position and identity (23 September)

- Typed Camera Position now preserves relative offsets, immediate snaps,
  CLASSIC following, step-duration easing and cancellation/restoration of an
  interrupted scroll tween. Fixed ownership prevents the native section camera
  from overwriting the authored follow point. Legacy FocusCamera handoffs release
  that ownership.
- `CompatCamera` preserves the script-visible target while `followEnabled` gates
  automatic following. Explicit snaps retain the prior flag. Executable tests
  cover the production adapter, position controller, interruption, stale
  completion, prior-disabled following, pause and teardown.
- Build `tmp/codename-camera-position-build.log` passed. The isolated offscreen
  probe `tmp/codename-camera-position/run_probe.py` passed seven callbacks through
  actual conversion and gameplay: absolute/relative snap, CLASSIC, interrupted
  easing, restored following and the held position after completion. Its
  `native.log`, `markers.jsonl` and `result.json` retain evidence. The runtime
  overlay was removed and settings were unchanged.
- A separate 15-second offscreen Psych Ballistic Hard run verified that the new
  default-enabled gameplay camera still renders the selected Psych stage,
  characters, HUD and notes and exits successfully, without script-error logs.
  Evidence: `tmp/compat-camera-psych-driver.log` and
  `tmp/runtime-smoke/compat-camera-psych-reopened.process.log`/`-11.0.png`.
  This is a cross-engine camera guard, not a new claim of full Psych parity.
- A missing-only camera metadata companion preserves ordered strumline character
  identities, role/type/position, exact difficulty, XML global/camera offsets,
  nullable `centercam` and XML `isPlayer` (`playerOffsets`) overrides, stage camera offsets and optional
  initial camera coordinates. Existing stage plans and camera companions remain
  unchanged during repair. Live multi-actor following, camera hooks and initial
  movement-event seeding are still incomplete.
- Final canonical build `tmp/codename-camera-position-build-final.log` passed.
  The full suite in `tmp/codename-camera-position-suite-final.log` passed:
  896 tests across 225 modules, 61 skipped, zero failures, 163.1 seconds.
  The preceding run exposed three stale fixtures: two asserted the previous
  camera constructor and one omitted the new camera companion. Those fixtures
  now verify the adapter and missing-only metadata repair; production behavior
  was not weakened to satisfy them. Skipped checks are not evidence of coverage.
- The subsequent native pause probe exposed a real adapter defect despite that
  passing suite: Flixel calls `updateLerp` separately from `updateFollow`, so
  scroll continued toward a stale target while following was suspended. The
  adapter now gates both phases. The strengthened executable boundary reproduces
  the failure before the fix and passes afterward, including 120 suspended
  frames with script-owned scroll. Canonical rebuild
  `tmp/codename-camera-pause-build.log` passed. The repeated native probe passed
  in 22.14 seconds: 43 samples held follow point and scroll stable through a
  two-second pause, then easing resumed to its destination and restored the
  original follow flag and attached target. Settings were unchanged and the
  temporary overlay/processes were removed. Evidence:
  `tmp/codename-camera-position-pause/result.json`, `native.log` and retained
  `native-first-failure.log`. The earlier suite result predates this correction.
- The shared native non-overwriting importer repaired an existing Codename
  namespace with exactly one copied asset: its missing camera companion.
  The original chart, compatibility manifest and stage script plan retained
  their recorded SHA256 values. The resulting exact difficulty, ordered
  strumlines, stage and character XML offsets were compared with the read-only
  donor, including XML `isPlayer` stored as `playerOffsets` (not camera role).
  User settings retained their original hash. Before-file backups and results
  are in `tmp/codename-camera-repair/`; native import markers are in
  `tmp/runtime-smoke/codename-camera-repair-import.markers.log`.
- Final full-suite rerun after the interpolation gate and `playerOffsets`
  correction passed: 896 tests across 225 modules in 172.8 seconds, 61 skipped,
  zero failures (`tmp/codename-camera-pause-suite.log`). The live settings hash
  still matches `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  Live Camera Movement, additional actor instances, character camera hooks,
  stage placeholder/flip fidelity and nested definition IDs remain open;
  source-backed implementation notes are retained in
  `tmp/codename-camera-movement-plan.md`.

## Codename structured event runtime (23 September)

The typed native bridge now consumes exact `Camera Zoom` and `Scroll Speed
Change` names after structured callbacks, with current-value multiplication,
step durations, direction easing, false-before-CLASSIC precedence, separate
camera defaults and state-owned tween channels. Replacement, pause and teardown
are covered by `test_codename_native_events.py`, which extracts the production
handler and lifecycle methods and uses a deterministic tween boundary.

Canonical build `tmp/codename-native-events-build.log` passed. The private-Xvfb
probe `tmp/codename-native-events/run_probe.py` passed twelve callbacks through
the real importer, script mutation and compiled runtime. It verifies immediate
actions, CLASSIC, interrupted tweens, concurrent camera/speed channels, live
scroll-speed access, HUD default updates and recovery. The runtime fixture was
removed and user options stayed unchanged. Evidence is in that directory's
`native.log`, `markers.jsonl` and `result.json`.

The first probe correctly rejected its own inaccurate assumption that the HUD
default and camera zoom would be identical inside every frame. Pinned Flixel
calls `onUpdate` before VarTween writes the next value; the boundary double and
native assertion now reflect that ordering, including no final onUpdate.
Initial evidence is retained under `initial-callback-order/`; the ten-callback
pass before adding recovery coverage is under `before-recovery-check/`.

Initial complete suite: **892 tests across 222 modules, 61 skipped, one failed**,
185.5 seconds (`tmp/codename-native-events-suite.log`). The failure was an
extracted lifecycle fixture missing the new tween-map fields. After adding the
fixture fields, all six lifecycle tests passed. Final complete suite:
**892 tests across 222 modules, 61 skipped, zero failed**, 178.1 seconds
(`tmp/codename-native-events-suite-final.log`). Skipped cases remain unverified.

Seven converter/refresh tests and three executable
transaction tests in `test_codename_refresh_transaction.py` passed: a second
replacement failure restores the first file and leaves verified backups;
an occupied debug runtime lock prevents writes and releases the release lock;
a modified reviewed output is rejected before backup or replacement. These
tests use real files and isolated locks, with regeneration mocked at the
transaction boundary; converter correctness is covered separately.

The read-only HL17 metadata refresh inspection found three selected manifests
whose `codename-engine-hl17-v3-b2d7aa552d` asset namespace is absent from the
release runtime. Those entries have no source-song provenance and are skipped.
This is an unresolved import-state gap, not evidence of working HL17 scripts.
The other reviewed plan applied to one unchanged generated difficulty, adding
provenance to 38 rows in 32 groups with no timestamp changes. Only the event
field changed; backup: `tmp/import-refresh-backups/20260923T120804302480Z`.
Plans and apply output are in `tmp/codename-refresh-review/`. This refresh does
not establish parity for the still-incomplete camera movement/position and
character animation event contracts.
The refreshed import also completed an isolated offscreen native run with pause
and resume: eight frame-stat samples held song position at 2096 ms, then resumed
to 15111 ms before successful exit. No Codename script/event error was logged;
the authored stage, characters and HUD remained rendered after resume. Evidence:
`tmp/codename-refresh-review/native-result.json`, `native-driver.log`, and
`tmp/runtime-smoke/codename-event-refresh-reopened.process.log` with corresponding
screenshots. Options retained SHA256
`923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
This verifies the migration and tested transition, not full content parity.

- Selected-owner event scripts and their registration schemas/literal dependencies
  now share the Codename import and repair planner. Selection requires an exact
  chart-authored name and either an upstream built-in registration or a nonempty
  same-owner `.json`/`.pack` schema. Uncharted scripts, schema-less custom scripts
  and escaping symlinks are excluded; edited destination files remain preserved.
- The runtime sends one mutable wrapper through `onEvent`, one recognized native
  action and `onPostEvent`. Cancellation skips default/post, with upstream's
  different propagation defaults for `preventDefault()` and `cancel()`. Script
  mutation is routed after callbacks. Custom events receive post callbacks but
  cannot invoke an unrelated engine's same-name default action. In-place runtime
  changes survive replay without modifying serialized import provenance.
- Eight focused interpreter/integration tests passed in 1.226 seconds:
  `tmp/codename-event-dispatch-focused.log`. They execute actual HScript methods,
  PlayState owner gating and scope changes, including cancellation, replacement,
  post order, invalid replacement and stale metadata. Fourteen import/discovery
  tests also passed during the agent's bounded implementation check.
- Initial canonical build passed (`tmp/codename-event-runtime-build.log`). Full
  suite `tmp/codename-event-runtime-suite.log`: **881 tests across 219 modules,
  61 skipped, zero failures**, 177.3 seconds. A later exact built-in-name guard
  prevents legacy importer aliases such as custom `Change Character` and
  `Change Scroll Speed` from receiving unintended native defaults. Its focused
  tests pass and final canonical build `tmp/codename-event-runtime-build-final.log`
  passed. The initial private native probe passed with exact callback trace and
  one native-action assertion; original logs are retained under
  `tmp/codename-event-dispatch/pre-stdlib/`.
- Probe preparation exposed a missing standard `Std` global. The shared Codename
  import/global map now binds it. Build `tmp/codename-event-runtime-build-stdlib.log`
  passed. A final native probe uses `Std.string` and explicitly compares the
  pre/post wrapper reference, in addition to exact callback order and native-action
  counts. It passed in 15.09 seconds with exit code 0. Evidence:
  `tmp/codename-event-dispatch/native-probe.result.json`, `native-probe.process.log`,
  `native-probe.markers.jsonl`, `native-probe.png`, and `driver.log`. There were six
  song pre-callbacks, four post-callbacks, exactly one native animation action,
  and no unintended native character switch. The schema-less script stayed
  undiscovered; registered event scripts still saw the unknown event. The
  temporary overlay was removed, no native probe process remains, and options
  retained SHA256 `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  The complete suite above precedes the final exact-name guard/Std binding;
  focused interpreter checks and this final native probe cover those additions.
- Read-only comparison with upstream found remaining native action mismatches:
  `Camera Movement`
  loses live strumline following and offsets; `Play Animation` drops force/context
  and additional actors. Camera Position, zoom and scroll-speed semantics are addressed by the
  follow-up above. The remaining actions require a shared typed native bridge using the post-callback
  payload, not additional chart conversions or content-specific overrides.
  Reference: [upstream executeEvent](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/PlayState.hx).
- Character event callback packs and initial camera event seeding also remain
  incomplete. Existing imported charts require the provenance-safe metadata
  refresh to use this ABI; the reviewed application above covers one eligible
  generated difficulty only.

## Codename event metadata preservation (23 September)

- Imported Codename rows retain exact times, typed source parameters, source
  ordinals and global status in validated optional metadata. Distinct source
  events sharing a native action remain distinct; identical companion copies
  still deduplicate. Other engines retain the existing collection behavior.
- Editor JSON roundtrips and companion merges preserve metadata. Timestamp-only
  edits synchronize it; native event name/value edits clear stale metadata while
  preserving any unrelated extension column indexes.
- `tmp/codename-event-metadata-focused.log`: **16 tests, four skipped, zero
  failures**, 19.627 seconds. Tests execute conversion, collection and editor
  helpers, including near-equal timestamps, colliding routes and companion rows.
- Canonical release build `tmp/codename-stage-events-build.log` passed. A private
  Xvfb native probe converted two authored rows with identical native actions
  and verified both dispatched exactly once. Evidence:
  `tmp/codename-event-probe/driver.log`, `native.log`, `events.json`, `result.json`.
  The run exited 0, preserved settings and removed its temporary runtime overlay.
- Initial full suite `tmp/codename-stage-events-suite.log`: **878 tests across
  218 modules, 61 skipped, one failure**, 177.5 seconds. The failure was a source
  test demanding adjacent stage publication and HXC callback-drain calls. It now
  checks their actual ordering on both successful and failed stage replacement;
  both tests in that module pass (`tmp/codename-stage-events-lifecycle-recheck.log`).
  Final suite `tmp/codename-stage-events-suite-final.log`: **878 tests across
  218 modules, 61 skipped, zero failures**, 165.2 seconds. Skipped cases remain
  unverified.
- Structured Codename event callback execution and event-script loading remain
  unfinished; existing imports have not been rewritten by this pass.

## Codename XML prop bindings (23 September)

- `CodenameStageBindings` exposes authored named stage objects before callbacks.
  It refreshes aliases across stage replacement without replacing engine globals
  or variables reassigned by scripts. Missing/null props clear stale aliases.
- Nine focused executable tests passed in 0.393 seconds:
  `tmp/codename-stage-bindings-focused.log`. They cover actual HScript property
  writes, stage replacement, disappearing/null props, name collisions, immediate refresh for timer-only scopes, resource
  lifecycle and interpreter behavior.
- The initial private-Xvfb probe verified an atlas-backed named prop resolved to
  the exact stage element and a conflicting `camHUD` element could not replace
  the camera global. Evidence: `tmp/codename-stage-bindings/native-probe.result.json`,
  `native-probe.png` and `native-probe.process.log`. It exited 0, preserved settings
  and cleaned its runtime overlay.
- The combined build `tmp/codename-stage-events-build.log` includes the subsequent
  null-prop guard and immediate timer-only scope refresh. Native follow-up
  `tmp/codename-stage-bindings/native-timer.result.json` passed: a song scope
  with only `create()` retained two timers across a stage swap; both observed the
  new stage and the old named prop was unavailable. A stage scope also verified
  a null prop alias was removed before its next callback. The 15.1-second run
  exited 0, cleaned its fixture and preserved options. Logs and screenshot are
  in `native-timer.process.log`, `native-timer.markers.jsonl`, `native-timer.png`.
  Broader stage APIs and structured event dispatch remain incomplete.

## Codename native HUD membership verification (23 September)

- HUD add/remove/insert now uses one reversible membership coordinator shared
  by Codename scopes. Borrowed native HUD objects never become script-owned;
  removed script-created objects remain owned for cleanup. Per-owner reorder
  history is bounded to the latest action. The live `members` array and native
  HUD globals are available during callbacks.
- Build `tmp/codename-hud-build.log` passed. Suite
  `tmp/codename-hud-suite.log`: **875 tests run across 216 modules, 61 skipped,
  zero failures**, 173.0 seconds. Executable tests cover the actual script
  bindings, both scope release orders and 10,000 repeated placements.
- Private-Xvfb synthetic runtime fixture `tmp/codename-hud-probe/run_probe.py`
  passed against the release binary. A stage-created camera raised the count
  to four; its deliberately failing postCreate removed the health bar, then
  engine cleanup restored the bar to index 22 and the camera count to three.
  The following song scope verified native remove/insert/add behavior with
  the live member list. Its only script error was the expected rollback marker.
  Evidence: `tmp/codename-hud-probe/native.log` and `driver.log`.
- The eight-second native run exited 0; the disposable runtime overlay was
  removed. Settings remained unchanged with SHA256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
- A subsequent corrected sprite probe passed on private Xvfb against this
  release: zoom/rotation pixel bounds matched independently composed screen
  coordinates within 0.47 pixels; a separate raw-culled/transformed-visible
  sprite rendered at the exact expected bounds. Evidence:
  `tmp/codename-render/result-corrected.json`, `native-corrected.png` and
  `native-corrected.process.log`. The 18.23-second run exited 0, removed its
  fixture and preserved settings. These two cases establish bounded rendering
  behavior, not complete Codename rendering parity.
- The first probe omitted final camera composition and used a host HUD camera
  whose zoom changes during gameplay. Its evidence remains as
  `tmp/codename-render/native-first-failure.*`; the corrected probe uses dedicated
  fixed cameras. The later XML binding pass is recorded above; broader event/API
  coverage and cross-engine completion remain open.

## Codename camera ownership pass (23 September)

- Codename scripts now receive a per-interpreter FlxG camera facade. The
  constructor bridge adopts newly created cameras before they are added, so
  failed initialization can release them. Host cameras are restored without
  destruction; another scope's owned cameras remain intact. Overlapping host
  mutations still diagnose an unsupported operation rather than silently
  replacing another scope's state.
- `tmp/codename-camera-build.log` passed. Focused executable camera, membership
  and interpreter tests passed (`tmp/codename-camera-scene-focused.log`). The
  complete suite `tmp/codename-camera-suite.log` passed: **874 tests run,
  216 modules, 61 skipped, zero failures**, 167.6 seconds. This precedes the
  in-progress HUD binding integration.
- `CodenameSceneMembership` has executable tests for both scope release orders
  and preservation of unrelated nodes. HUD binding integration is in progress;
  the helper alone does not establish native HUD compatibility.
- The first native sprite-transform probe exited 0 but found no test-color
  pixels. Its expected coordinates omitted the camera's final canvas transform,
  so that initial attempt was inconclusive. The corrected probe subsequently
  passed both bounded cases, as recorded in the latest HUD section above.

## Codename pause and difficulty verification (23 September)

- Shared Codename resource ownership now suspends timers/tweens on actual pause
  and restores their prior active states on resume. Cancelled/finished handles
  remain inactive. Throwing hooks report once and stop retrying that hook;
  unrelated callbacks remain available. Difficulty selection preserves exact
  authored case, with only an unambiguous case-insensitive fallback.
- Release build `tmp/codename-pause-build.log` passed. Full suite
  `tmp/codename-pause-suite.log`: **872 tests run across 214 modules, 61 skipped,
  zero failures**, 176.7 seconds. Focused executable tests cover resource state,
  failed-hook isolation, lifecycle order, cleanup and difficulty selection.
- `codename-pause-active-title` ran 35 seconds under private Xvfb and exited 0.
  Pause was triggered from the logged song clock at 11.059 seconds, while the
  authored title tween was active. The title remained visible six seconds into
  pause; the title region was pixel-identical in captures four seconds apart.
  Return resumed gameplay and the effect finished afterward. Evidence:
  `tmp/codename-pause-active-title-driver.log`, its runtime log/screenshots and
  `tmp/codename-pause-title-pixels.json`.
- The initial fixed-wall-clock attempt paused at 9.360 seconds, before the effect
  began at approximately 9.796 seconds. It verified the song clock held but was
  inconclusive for active tweens. Its log remains; redundant screenshots were
  removed. The corrected driver uses song time rather than assuming load speed.
- User settings retain SHA256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
- Camera ownership, native HUD reordering, XML prop bindings, event objects and
  broader Codename APIs remain open. Camera-transform rendering checks are in
  preparation; title-card rendering on a unit-zoom HUD alone does not prove them.

## Codename runtime integration in progress (23 September)

- Strict per-owner paths and interpreter-owned timer/tween cleanup now have
  executable Haxe tests. Missing assets cannot borrow another namespace;
  escaping symlinks and traversal are rejected. Atlas selection covers
  Sparrow, Packer and plain images; Animate remains explicitly unsupported.
- Literal font and JSON/XML/text dependencies now use the same non-overwriting
  Codename copy/repair plan. The import fixture executes the real dependency
  planner and verifies scoped font/data copies.
- `tmp/codename-runtime-foundation-tests.log`: 15 focused tests passed in
  0.992 seconds. These cover parser, scope boundaries, importer metadata,
  dependency repair and interpreter resource cleanup; they do not prove native
  sprite rendering or complete gameplay lifecycle compatibility.
- Initial suite during integration: 870 tests across 214 modules, 61 skipped,
  four failed modules in 169.4 seconds (`tmp/codename-runtime-suite.log`).
  Failures were in the in-progress sprite/lifecycle tests and two extracted
  fixtures requiring new dependencies. The import fixture has been corrected
  and its five tests pass; final settled-source verification remains pending.
- Settled-source suite `tmp/codename-runtime-suite-final.log`: **871 tests,
  214 modules, 61 skipped, zero failures**, 169.0 seconds. Lifecycle tests now
  execute extracted Haxe methods to check callback order, cleanup and failed
  postCreate rollback. Skips remain unverified.
- Initial canonical build caught a pinned Flixel API mismatch (`isAtEnd` is
  absent). The adapter now checks the directional terminal frame separately
  from animation completion; forward/reverse/middle-frame probes pass. The
  corrected release build passed (`tmp/codename-runtime-build-retry.log`).
- Native `codename-runtime-metadata-refresh` passed: one same-owner import
  repaired, one metadata file copied, 17 assets preserved, no failures/errors.
- Native `codename-runtime-title-restart` ran 43 seconds on private Xvfb and
  exited 0. The 16-second capture shows the authored title card rendered over
  gameplay. Pause/Down/Return restarted the song; both state loads reported
  three cameras. No Codename script errors were logged. This verifies initial
  lifecycle/title/tween execution and restart, not complete scene parity.
- Review identified further gaps: global-manager timers/tweens need pause
  suspension; camera ownership, native HUD removal, XML prop bindings and broader
  event APIs remain incomplete. The subsequent pause pass above verifies timer
  and tween suspension; the other gaps remain open.
- Current settings hash is
  still `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.

## Latest continuation evidence (23 September, Psych dance/camera and Codename import)

- Shared Psych character generation now chooses paired dances or idle from the
  live suffix. Reviewed refresh replaced 28 exact legacy generated scripts;
  customized scripts are excluded. Backup:
  `tmp/import-refresh-backups/20260923T093615664784Z`. All 28 outputs match the
  renderer and donor definitions remain unchanged, including after the build.
- Release build `tmp/psych-dance-camera-codename-build.log` passed.
- Final suite `tmp/psych-dance-camera-codename-suite-final.log`: **858 tests,
  207 modules, 61 skipped, zero failures**, 200.8 seconds while the release build
  ran concurrently. Skipped scenarios remain unverified.
- `psych-dance-camera-restart` completed 35 seconds on private Xvfb, exit 0.
  Escape/Down/Return opened pause and restarted the song: two PlayState loads,
  both with three cameras and initial target `(819.5,319)`. Effective offsets
  were BF `[-100,-100]`, opponent `[60,-500]`, GF `[0,0]` on both loads, matching
  Psych baselines plus the selected character metadata. Subsequent donor camera
  overrides still take effect. Periodic native samples show both GF danceLeft
  and danceRight, with advancing frames; paused samples retain the same frame.
  No HScript/unknown-variable/null-operand errors were logged. The 25-second
  capture verifies the visible scene after restart; this is not full-song parity.
- `wacky-camera-isolation-resume` completed 45 seconds on private Xvfb, exit 0,
  reaching song time 53.720 seconds after video skip and two pause/resume cycles.
  Psych camera mode remained false. Initial target `(642,461.5)`, zoom `0.65`
  and BF position `(652,224)` match the previous verified build. The 39-second
  capture shows pixel actors in front of the pixel background. No HScript,
  unknown-variable or null-operand errors were logged.
- Codename imports now preserve selected song/difficulty/stage scripts and
  supported literal dependencies in their owning namespace, using one copy and
  repair plan with non-overwriting writes and source containment. Behavioral
  fixtures cover differing owners, difficulty selection, escaping symlinks,
  custom destination preservation and missing-file repair. Runtime execution
  remains unsupported; copied files alone are not scene compatibility.
- Native offscreen `codename-scoped-script-refresh` succeeded: one same-owner
  song repaired, two missing files copied, 15 assets preserved, zero failures.
  The scoped song script and its title-card image are byte-identical to the
  donor. Settings remained unchanged. This validates importer wiring in the
  release binary, without claiming the still-unsupported callbacks execute.
- Parser audit: 17/17 sampled song scripts parse with types/JSON objects enabled
  after diagnostic declaration removal; 9/13 stage sidecars parse. Runtime
  import bindings, lifecycle and sprite rendering remain separate gaps. See
  `tmp/codename-parser-audit-summary.json` and the architecture notes.
- The first complete test attempt had three stale camera fixtures; they were
  updated to exercise actual role-target composition, repeated setup, live
  changes, swaps and preserved native/V-Slice behavior. Review also caught an
  empty-string/non-Psych mode check and native event-focus turn-nudge difference
  before the release build. The initial Wacky native regression driver used
  Escape to resume, which the pause menu does not accept; it stayed paused and
  hit the wrapper deadline. The corrected Return-key run passed above; its
  redundant failed-run screenshots were removed while logs were retained.
- Latest settings hash remains
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  Redundant parser output was removed; probe, evidence and recovery backups remain.
- Remaining: Codename runtime Haxe parsing/lifecycle/API/rendering integration,
  complete cross-engine scene and lifecycle verification, the earlier intermittent
  native heap corruption, and the performance/60–240–480 FPS phase. No full
  compatibility or regression-free claim is made from these bounded checks.

## Latest continuation evidence (23 September, pause/import pass)

### Final verified state of this pass

- Release build `psych-character-metadata-api-build.log` passed. Full suite
  `psych-character-metadata-api-suite.log`: **851 tests, 205 modules, 61 skipped,
  zero failures**, 186.9 seconds. Skips are not verification of their scenarios.
- `psych-whitty-character-metadata` refreshed through the shared Auto importer,
  exit 0, zero failed imports. Character JSON now exists at the scoped original
  paths and is byte-identical to the donor; existing charts were skipped.
- `psych-ballistic-metadata-api` ran 45 seconds on private Xvfb, exit 0, reaching
  song position **39.300 seconds**, with zero HScript errors or unknown-variable
  errors. Runtime diagnostics verify opponent `(370,500)` and GF `(680,310)`,
  matching stage coordinates plus authored character offsets. The 35-second
  capture verifies corrected placement; the opponent atlas remains scoped.
  This verifies the ownership, metadata, version-gate and legacy callback fixes,
  not full-song visual parity.
- `wacky-pause-camera-isolated` verifies visible pause UI during the event video,
  resume, song seek from Space, and a second pause/resume. Earlier 52-second
  native evidence also covers the pixel-stage actor/background ordering.
- User options remained at SHA-256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  Disposable duplicate captures were removed; before/after evidence and backups
  remain under repository `tmp/`.
- Still open: Psych paired-dance conversion/old generated scripts, authored
  character camera offsets, Codename runtime Haxe lifecycle support, remaining
  original cross-engine checks, and the earlier intermittent heap corruption.
  Performance and 60/240/480 FPS equivalence are not yet complete.

### Earlier evidence and intermediate failures from this pass

**Follow-up:** `compatibility-owner-pause-full-suite-final.log` passed 847 tests
across 204 modules (61 skipped, zero failures), and the release build passed.
`wacky-pause-camera-isolated` completed 22 seconds offscreen, exit 0: its
7-second capture shows a visible menu while the video/HUD is hidden; subsequent
resume, Space skip and another pause/resume complete, and song position reaches
29.959 seconds. This closes the previously observed invisible-menu regression.
Settings remained unchanged at the recorded hash.

`psych-whitty-owner-scoped` import completed with 17 imported, 17 skipped and
zero failures. Scoped opponent atlas bytes match the donor and scoped icons/Lua
dependencies exist. Its 30-second gameplay check exposed an earlier actor-name
normalization boundary still choosing the global spelling, breaking the later
owner-specific position lookup (the diagnostic confirms the scoped atlas loads), and countdown remained
blocked by the compatibility version's shortened representation. These are
being corrected; a clean exit here is not gameplay success. The shared version
now uses the equivalent full `0.7.0` baseline; three focused tests pass, including
an executed Lua version gate accepting this baseline and rejecting `0.5.0`.
Follow-up `psych-ballistic-owner-normalized` completed 35 seconds, exit 0,
and reached song position 27.839 seconds. The ID spelling and version gate are
corrected. Position remains wrong because the namespace is missing the donor
character JSON consumed by `PsychCharacterPosition`; preserving this metadata is
in progress. The run also reached beat callbacks and exposed the missing legacy
`characterPlayAnim` API. Its shared implementation now follows the local Psych
reference, with a passing role/force/missing-animation interpreter test; native
verification of these final metadata/API corrections remains pending.
A separate remaining Psych dance issue is confirmed: standard character
conversion emits `idle` even for JSON containing only `danceLeft`/`danceRight`.
The native GF diagnostic has no active animation. Upstream selects paired dance
from available animations; native beat cadence already matches. Repair must
preserve authored custom dance scripts and safely handle existing generated
imports, rather than changing one character file.



- `wacky-pause-lifecycle-final` completed a 52-second private-Xvfb run, exit 0.
  Held-key input opened a visible pause menu after the video (39-second capture),
  and the pixel actors remained in front of their background. During the event
  video, the menu was invisible because the authored HUD camera had alpha zero.
  A shared owned-camera fix is implemented and interpreter-tested; native
  verification of that final change is still pending.
- The clean Psych import now selects the correct Ballistic Hard chart and stage.
  Its subsequent native run exposed a case-colliding global character lookup;
  owner-scoped character/icon conversion is being implemented. This run does
  not establish Psych visual parity. Lua dependency/API changes also await
  native verification after a normal shared importer refresh.
- Read-only follow-up confirmed that the partial ModdingPoop stage script is
  byte-identical to the full reference: its `cstaticthing()` call has no shared
  definition. The full reference supplies the requested global sound path,
  while the partial package supplies only a stage-local copy. Neither finding
  justifies a basename alias or a chart-specific function substitution.
- Partial ModdingPoop import and 25-second gameplay completed, exit 0. Missing
  character registry metadata was recovered through the shared exact-file
  validator. The supplied stage script still references an absent logical sound
  path and calls an undefined function also present in the reference install;
  these donor defects have not been hidden with content-specific aliases.
- Full-suite evidence: 839 tests across 199 modules, 61 skipped, one fixture
  failure. The duplicate `sourceRoot` diagnostic-fixture field was then fixed,
  and that failing test passed independently. A final complete run is pending.
- Latest import settings check preserved SHA-256
  `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`.
  This is evidence of preservation, not a baseline to overwrite newer settings.
- Codename song/stage Haxe callbacks remain unsupported. Selected stage sidecars
  now receive an explicit omission diagnostic, with nine importer tests passing.
  Static XML import is not evidence of complete runtime compatibility.
- Intermittent native heap corruption from earlier runs remains unresolved.

## Acceptance status at the latest continuation

Older sections below are chronological evidence, including superseded settings
hashes and test counts. The goal remains active; a successful startup is not a
claim of full chart or engine parity.

| Requirement | Current evidence and remaining scope |
| --- | --- |
| Engine-only fixes | Shared importer/runtime changes; named content is used for regression checks. Reviewed regeneration uses the common converter, without donor/chart edits. |
| Editor event column/navigation | Native Previous/Next seeks verified; format/timing tests pass. Latest offscreen editor capture verifies checkerboard alignment. |
| Imported backgrounds | Scoped resolver restores the reported stages. V-Slice scaled geometry and actor-relative depth corrected; reviewed regeneration retains numeric depths. Stage replacement reapplies native presentation and depth to replacement actors; the latest Wacky pixel-stage capture verifies foreground actors. |
| Danger-note appearance/alignment | Native live note uses its scoped danger atlas and has zero error against the nominal lane center after movement. The current native botplay run also retains the incoming Y offset through hitbox updates and excludes the hazard from automatic hits. |
| GF animation | Shared non-looping default corrected and live flags verified. User subsequently accepted Expurgation as correct; earlier donor-frame investigations below are historical, not a newly reproduced regression. |
| Expurgation effects/sign frequency | Current no-input run triggers text/static from autonomous hits. Source comparison preserves manual sick versus automatic perfect, one hit per note head, 24 FPS overlay and authored step cooldown. Earlier sign census matched all 47 events. |
| Resonance visuals | Earlier full native run and red-phone reference checks cover the listed scene/HUD fixes. Re-audit is in progress; residual script warnings and complete parity remain open. |
| Future Sound load crash | Current release completed an 18-second private-Xvfb startup/gameplay run, exit 0, no script errors (`future-sound-current`). |
| Fantasy Girl player animation | Current release completed a 26-second private run: 77 normal hit callbacks, all routed to current BF; all four sing animations observed (`fantasy-current`). This does not resolve ambiguity about the original strumline report. |
| Cross-selection popup leak | Prior independent-selection and owned-popup native checks passed; no content-name routing. |
| Settings | Latest verified import-preservation hash is `923f29314775f23e45fde8b354f025fda00e78dee2cdd69049c0ec1b06720348`; retain later user changes over this historical baseline. |
| Tests/build/performance | See latest continuation above for current suite/follow-up status; the older 810-test all-green result below predates these changes. Skips and intermittent scanner allocator fault remain explicit. Prior Freeplay measurements show improvement; worst-case scene-switch pauses remain unproven. |
| Temporary files | Runner and native diagnostic use project `tmp/`; obsolete fixtures/aliases/captures removed, verification and rollback records retained. |

## Reopened user reports — 23 September 2026

The user resumed the goal after live testing. Earlier bounded smokes do not
override these reports. All fixes remain engine/compatibility-level, all game
tests must be offscreen, and current subagents use GPT-6 Sol at medium reasoning.

- Editor: add an event column to the left of the note grid; Previous/Next must
  seek the grid/playhead to the selected event; support differing import formats.
- Vs Freddy: background still absent.
- V-Slice Expurgation: default background regression; missing ground spikes,
  flashing text, and full-screen static in the user's launch.
- Psych Resonance: partial-screen flashes and excessive late flashing; broken
  player/opponent strum movements; placeholder background textures; incorrect
  BF placement and missing rock; missing intro/outro; incorrect red-effect
  layering (the user clarified this is not a fade timing issue); missing
  health bar and misplaced health icon.

These are open acceptance checks. Verify the actual launch/import/difficulty
path and compare runtime semantics with the donor before declaring them fixed.

## Hit-routing and geometry native verification

- Release build `tmp/cammie-engine-plus-hit-geometry-build.log` passed. Settings
  remained byte-identical to `tmp/cammie-settings-hit-geometry-pass.json`.
- `expurgation-autonomous-effects`: 45-second private-Xvfb run, no input, exit 0,
  no script errors. Observed 44 text/static cues. Minimum cue separation was
  four chart steps, matching the authored strict `startStep + 3 < currentStep`
  boundary. Capture at 25 seconds shows text and screen-covering static.
- `expurgation-actual-botplay`: actual demo mode, practice disabled, 45 seconds,
  exit 0. Live danger note has `avoidAutoHit=true`, `autoControlled=true`,
  `autoHitAllowed=false`, `wasGoodHit=false`, `offsetY=90`, zero nominal lane-center
  error. Capture at 38 seconds shows full health and zero misses. Botplay yields
  more eligible `perfect` hits on both sides, as upstream does: 90 cues in this
  sample, also no closer than four chart steps.
- Opt-in timing in those two runs: 38 one-second gameplay windows each; 206–240
  and 222–240 FPS respectively, maximum per-window 95th-percentile measured frame
  cost 1 ms, and no intervals over 33.4 ms. These are bounded offscreen CPU/render
  observations, not a guarantee for the user's GPU or the entire chart.
- The subsequent `expurgation-botplay-full` run completed the entire chart and
  reached Victory, exit 0, practice disabled, no script errors. It observed 453
  text/static cues, never closer than four chart steps. The full sample reveals
  a performance issue absent from the short windows: 106 frame intervals over
  33.4 ms and 37–241 FPS, with slow windows around 98–113 seconds and later.
  Peak measured per-window p95 frame cost was 15 ms; one early frame cost 573 ms.
  Peak process RSS was 2,579,400 KiB. Cue cadence now matches the authored rules,
  but late performance needs a controlled render/effect comparison.
- Wacky World normal run aborted while loading HXC scripts with glibc heap
  corruption. The actual core backtrace places detection in hxcpp GC allocation
  during `HxcCompat.lowerHxcApiAliases`, reached through the companion-module
  registration pass; this does not identify the corrupting operation. The
  extracted 1.2 GB core was removed after saving the system core info and
  backtrace; the system-managed original remains available. Evidence: `tmp/wacky-hit-geometry-core-backtrace.log`.
- The same binary completed a 40-second GDB run without script errors: 45 player
  hit callbacks covered all four directions at actor scale 1.05; 20 receptor
  snapshots all have zero X/Y lane-center error. The 34-second capture shows the
  aligned receptors. This verifies that execution path but does not erase the
  normal-run crash; stability remains open.

## Latest input, timing and geometry reports

- Botplay must avoid danger notes. Horizontal danger-note placement and authored
  incoming offsets need checks after receptor movement and hitbox updates.
- V-Slice text/static must follow upstream autonomous note hits, not manually
  scored player input. Compare chance, cooldown, sustain handling and animation
  rate; measure frame cost without changing authored frequency to hide defects.
- Wacky World and other imports expose receptor animation misalignment and
  character sing-offset drift. Verify the shared V-Slice source-frame and actor
  scale conventions across directions, retaining other engines' conventions.

The current source addresses these through common note policy, HXC dispatch,
receptor geometry and character geometry. Native verification is pending below.
A full-suite pass during integration also discovered newly added donor Lua
scripts (174 total, 169 supported at that point), stale helper stubs, and fixed
corpus-count assertions. These failures are being addressed explicitly.

## Current reopened-goal evidence

- Event lane: native offscreen screenshots show Previous seeking to 4173.913 ms
  (section 3) and Next to 6260.870 ms (section 5), with the selected event at the
  playhead. Extracted timing tests cover differing section lengths/BPM and
  normalized imported event formats, plus save/reload event equivalence.
- Stage resolution: validating authored casing before normalization restores the
  selected V-Slice stage. Manifest-scoped Modding Plus registry/script resolution
  restores the imported background. The normal importer repair completed with
  3 imports, 3 duplicates skipped, 0 failures; no donor files were changed.
- The release build in `tmp/cammie-engine-plus-reopened-build.log` passed.
  A 42-second Expurgation smoke completed with 45 static cue activations and no
  script null-access warnings. `expurgation-reopened-anchor-7.png` visibly shows
  ground spikes, red text, and screen-covering static on the authored stage.
  This verifies the effects in the bounded segment; it is not a whole-song claim.
- Resonance: the next release build (`cammie-engine-plus-camera-text-build.log`)
  passed. A 255-second offscreen run confirms BF on the restored rock, moving
  strums, the heart/HP display at the authored HUD position, readable scripted
  text, and the late red scene followed by the authored black ending. Native
  camera snapshot records BF at `[749,450]`, matching the stage point plus
  Psych's base-character position. The donor intentionally drops the normal
  health bar at step 255 and replaces it with this custom display.
- A 75-second recording of the late section shows the two large brightness
  changes at authored Flash events, covering over 99.8% of the sampled frame.
  There is no repeated large brightness jump in that sample after per-channel
  tweening. This is a coarse rendering check, not complete visual parity.
  The user's later reference confirms the phone and its displayed content must
  retain their original colors above the red background. Our captured phone is
  incorrectly red: the added camera-color tween route affects the whole canvas.
  A native hxcpp probe proves upstream Psych's dynamic camera target becomes
  null at the typed sprite tween boundary. The adapter now preserves that
  null-sprite tween and its callback lifetime, without tinting the canvas.
  Focused tests and the next offscreen native run pass. The new captures show
  the phone and its contents in full color against the red background. No fade
  timing or content-specific layering rule was changed.
- That longer Resonance run still logs three guarded null-operand diagnostics
  (`>`, `+`, `-`). Their remaining causes are not yet verified. A subsequent offscreen startup capture (`resonance-intro-reopened-7.0.png`)
  confirms the loading artwork fills the overlay camera and its CD animates.
- Current live settings still match the saved baseline hash below.

Evidence files are under ignored `tmp/runtime-smoke/`: `editor-next-verified.png`,
`editor-previous-verified.png`, `freddy-stage-restored.png`,
`expurgation-reopened.process.log`, and `resonance-reopened-*.png`.

## Implemented shared paths

- Cammie Engine + app, HUD, presence, and launcher branding; stable save IDs.
- Live options backup before asset sync; public seed remains separate.
- Parallel tests with desktop display variables removed; native tests use a
  private Xvfb display and dummy audio.
- Metadata build cache, compilation-server retry, runtime asset reuse, cached
  diagnostic compilation, and deferred/limited Freeplay object creation.
- Bounded parsed-character and bitmap reuse for repeated scene changes.
- Imported category mapping and guarded legacy stage-registry recovery.
- Difficulty-specific stage resolution and chart editor Events tab.
- Psych stage/root resolution, opening actor/camera placement, timed zoom
  ownership, independent overlay camera, single Flash handler ownership,
  optional Lua arguments, and safe native HScript exception handling.
- V-Slice note styles, draw ordering, current actor bindings, deferred character
  initialization, native note reflection, graphic offsets, and vertical flips.
- Structural HXC sprite-event and hit-cue descriptors, pre-callback judgement,
  bounded root-scoped constructor media warmups, and normal hit-route testing.
- Bounded literal miss-text rules with separate probabilities/text and the
  same active cue owner; interpreted owner tests exercise both routes.
- Selection-bound Freeplay prompts and manifest-scoped popup factories.

## Native observations

- Imported Freeplay startup decreased from 7,451 ms to 1,470 ms in the same
  isolated local fixture. This is a local diagnostic measurement.
- Future Sound completed its startup/gameplay smoke after the shared native
  exception fix. Resonance camera snapshots are described in the architecture
  document; automated startup alone does not establish whole-song parity.
- Fantasy Girl 01 player UP input reached the current BF and played singUP.
- The latest 45-second Expurgation smoke recorded 195 player-hit callbacks,
  56 static-overlay activations, three sign-event dispatches, zero script
  null-access warnings, and a success marker. Separate event-anchored captures
  show the sign rendered at the first authored event; text/static were also
  inspected visually. These bounded runs do not cover the complete chart.
- A subsequent 190-second smoke completed successfully and matched all 47
  sign-event timestamps, including simultaneous entries, with no missing or
  extra dispatches. It exposed four later custom-splash null-access warnings
  that are not covered by the earlier zero-warning observation.
- A Freeplay cross-selection smoke accepted Resonance with confirmArmed=false.
  A separate Catfight selection armed and opened its own popup, confirmed it,
  and closed it successfully.
- A native miss-text smoke completed successfully with 18 miss-cue activations
  and zero script null-access warnings.
- Local settings retained SHA-256
  `22c8ffe0a179053dabbcc378ac0a7bf0ff0ad185cf5bd5077b56472010ee68ea`
  through these builds and tests. This is the user's latest settings baseline.

The native evidence is under ignored `tmp/runtime-smoke/`, including
`expurgation-note-offset-final.process.log`,
`expurgation-sign-anchored.process.log`,
`expurgation-sign-census-complete.process.log`, and `sign-native-*.png`.
Freeplay logs are `tmp/vfree-sol-cross-selection.process.log` and
`tmp/vfree-sol-owned-popup.process.log`.

## Latest build and tests

The camera/text/position build passed. Its full suite ran 777 tests across 174
modules in 153.3 seconds (61 skips), with one native diagnostic-scanner heap
abort. The older cached executable reproduces that abort on the full donor
corpus but succeeds on the final root alone. A new source fingerprint built a
scanner that passed twice, including allocator checks. This does not establish
that the underlying heap fault is fixed. Isolated AddressSanitizer builds
conflicted with hxcpp's conservative stack-scanning collector (first its
register-capture sentinel, then early null dereferences when collector objects
were left uninstrumented), so that attempt did not localize the corruption.
No retry, count adjustment, or donor edit was used to mask it.

The next splash-bridge release build passed, and its complete suite passed:
782 tests across 175 modules in 181.5 seconds, 61 skipped, 0 failed. A later
idempotent effect-attachment guard passed its focused test. A manual offscreen
note-input smoke exposed overly broad HXC NoteKind dispatch: unrelated ordinary
notes could trigger custom-kind damage/effects. The ownership correction now
matches authored note kinds, separates ghost misses, and provides the strumline
offset alias. A second dispatch correction tests the HXC scope map's Boolean
value rather than its membership, preserving ordinary Psych callback arguments.
The subsequent 785-test run exposed two outdated extraction fixtures, which
were repaired and passed their focused checks; its native diagnostic scan passed.
The latest release build passed. A 50-second offscreen manual-input Expurgation
run then passed with 114 sick judgements, 47 static-effect log entries, zero
script errors, and zero unrelated custom-splash attachments. The old broadcast
had attached many unrelated splashes during the same ordinary-note segment.
The stable-source full suite passed: 786 tests across 176 modules in 195.2
seconds, 61 skipped, 0 failed (`cammie-engine-plus-dispatch-suite.log`). This
includes the native diagnostic scanner, but does not erase its older heap-fault
reproduction. The next 255-second Resonance run also completed without a crash and reproduced
the same three guarded null-operand diagnostics. Its intro, HUD, authored
silhouette section, late red scene, and ending were captured offscreen. The
user reference confirms the phone must stay in full color; the whole-camera
tint was incorrect; the shared correction now passes native visual checking.
A separate upstream comparison found a shared `setObjectOrder` forward-move
off-by-one: the requested index is the final insertion index after removal.
That correction passes its focused interpreter test and the subsequent release build.

The normal V-Slice importer repair copied 30 missing files (including scoped
style JSON): 4 imported, 0 failed, 3 nonfatal diagnostic errors. It did not edit
the donor. The custom-splash rendering observation from that smoke is not
accepted as correct gameplay until note ownership is fixed.

## Limits and remaining checks

- The tied-girlfriend donor definition requests frame indices 0–30 but the
  donor atlas has only 20 matching frames. A compatibility adapter cannot
  reconstruct missing artwork; no replacement frames or donor edits were made.
- The donor and imported chart each contain 47 sign entries in 33 timestamp
  groups; the full runtime census matches them. Reducing this frequency would
  alter authored chart behavior.
- The shared note-style/splash bridge is implemented and interpreter-tested.
  Scoped metadata repair and native constructor/attachment work. Dispatch
  ownership now filters authored kinds. The ordinary-note native recheck passed;
  this does not verify every custom style's rendering in every imported chart.
  The earlier four null warnings were exposed by that incorrect broad dispatch;
  they were not proof that every reported chart authored that splash behavior.
- The reported notes being below the strumline is ambiguous between draw order
  and travel direction. Draw ordering is fixed. With the current upscroll
  setting, notes travelling toward top receptors from below is expected;
  a different intended vertical behavior still needs clarification.
- Scene/character cache changes remove repeated work but do not establish a
  maximum first-load pause for every asset in the library.
- Passing focused and full tests does not establish exhaustive parity for
  arbitrary donor scripts. Unsupported or missing donor content retains
  diagnostics; this report does not claim the entire discrepancy goal complete.

### Atlas and ordering follow-up

The release build with character atlas identity, extensionless sprite paths,
and final-index object ordering passed. Its full suite passed 789 tests across
179 modules in 160.3 seconds, 61 skipped and 0 failed. This run predates the
camera-target tween correction; that next build must be verified separately.

### User-reference camera parity check

`cammie-engine-plus-camera-parity-build.log` records a successful release build.
The next isolated native run (`resonance-camera-parity-reopened.process.log`)
completed at 4× song rate over an 80-second wall-time smoke window. This is a
mechanical/visual regression check, not a fresh real-time flash-frequency census.

- `resonance-camera-parity-reopened-59.0.png` shows the yellow figure, purple
  phone screen and green arrow above a red background, matching the user's
  clarified layering/color requirement.
- The 57-second capture shows the other phone pose in full color and correctly
  resolved angular lyric text. The 54-second capture shows actual BF atlas
  silhouettes in the authored trail; camera-snapshot property reads confirm
  `boyfriend.imageFile` and `dad.imageFile` expose their selected native atlases.
- Font keys resolve through selected-import then native font folders. Native
  OpenFL TextEngine loads unregistered font paths from disk, so no duplicate
  font-registration or invented font-family alias is necessary.
- The three guarded null-operand warnings remain. Source/timing points to the
  removed loading sprite for `>` and an uncancelled donor trail timer for `-`;
  these are inferences because the warning lacks callback context. The `+`
  warning remains unattributed. No donor script was changed to suppress them.
- Live settings retain the same SHA-256 baseline. All native windows used a
  private Xvfb display with desktop display variables removed.

Final stable-source suite for this pass: **790 tests across 180 modules in
168.4 seconds; 61 skipped, 0 failed**
(`tmp/cammie-engine-plus-camera-parity-suite.log`). `git diff --check` passes.
The goal remains active: the guarded script warnings, earlier native diagnostic
heap corruption, source-art limitations and broader first-load performance
acceptance remain explicitly open.

## Warning attribution and load profiling follow-up

Null-operand diagnostics now include the script path and callback and deduplicate
per operator/context. A focused test covers repeated warnings, separate scripts,
and separate callbacks; a callback test verifies context restoration after a
nested callback throws. The operator guards themselves are unchanged.

A new full offscreen 4× run attributes the warnings directly:

- `Loading Screen.lua#onUpdate`: `>` after its loading sprite was removed.
- `Muns.lua#onUpdate`: `+`. Executing the translated source in an isolated
  interpreter exposes an earlier invalid string-key write to an HScript array.
  Raw Lua sequence indexing and value-returning `or` also differ from HScript;
  this is a shared Lua compatibility gap, not a reason to edit that script.
- `THEGOUSET.lua#onTimerCompleted`: `-` after its trail timer continues with
  missing frame tags. No donor timer or chart was edited.

Smoke-only load counters now measure bitmap cache hits/misses, cumulative decode
milliseconds, maximum decode duration and creation phases. Two isolated native
Resonance starts took 4,184 and 3,768 ms, with 75 bitmap misses and 91 cache hits
each; bitmap decoding took 2,146 and 1,956 ms respectively. Initial character
work took 723/674 ms; future-character preloading added 859/760 ms. These are local
samples, not a percentile benchmark. The 45-second 4× baseline observed peak
RSS of 1,770,624 KiB. Per-song bounded warm-atlas retention is being implemented
because FlxGraphic's default last-user cleanup discards a warmed character's
atlas when its temporary character is destroyed.

The scanner heap audit did not find a smaller reproducer: even the old cached
binary passed two fresh full-input runs. Smaller subsets passing cannot prove
minimization of an intermittent failure. The earlier core remains evidence of
an unresolved allocator abort; no speculative GC patch, retry, or changed
scanner count was introduced (`tmp/heap-reduction-report.md`).

## Lua semantics verification and atlas experiment outcome

The Lua-only interpreter passed five focused tests covering a LuaJIT oracle,
sequence and mixed-key access, object-key identity, sparse indices, truth values,
short circuit, iterator/helper boundaries and source-language selection. The
unaltered regression script replay creates all nine authored items and produces
finite movement values. Native HScript and unmarked mixed stage wrappers keep
the normal interpreter; the latter's embedded callbacks still have their prior
table semantics. This is not a claim of complete Lua VM support.

The first combined release build passed. The full suite at that snapshot passed
**801 tests across 183 modules in 188.6 seconds; 61 skipped, 0 failed**
(`tmp/cammie-engine-plus-lua-atlas-suite.log`). The offscreen native 80-second
4× run (`resonance-lua-atlas-reopened.process.log`) traversed the entire song
and reached VictoryLoopState. The earlier `Muns.lua#onUpdate` `+` warning is
absent; the removed-loading-sprite `>` and uncancelled-trail-timer `-` guards
remain. Its 59-second capture preserves the yellow figure, purple screen and
green arrow above the red background. No donor scripts were edited.

That run's experimental teardown assertion failed because its 80-second deadline
occurred after gameplay had already ended. A 45-second rerun requested a real
state switch while PlayState was active and passed: the holder reported
266,324,892 bytes before release and zero afterward. This validates release,
not a performance improvement.

A same-binary comparison then showed **no meaningful atlas-retention benefit**:

| Retention | First opponent swap | Player swap | Return to player | Peak RSS (KiB) |
| --- | ---: | ---: | ---: | ---: |
| Disabled | 4 ms | 20 ms | 4 ms | 1,775,636 |
| Enabled | 2 ms | 18 ms | 4 ms | 1,772,792 |

Logs: `resonance-atlas-disabled-reopened.process.log` and
`resonance-atlas-enabled-reopened.process.log`. The difference is ordinary
single-run timing variation, not evidence of faster switching. These scripts
pass string keys to `FlxAtlasFrames.fromSparrow`, which can reuse OpenFL's own
bitmap cache. `FNFAssets` decode counters only measured incidental loads here.
The extra holder and its experimental flags/tests were therefore removed;
load-phase and swap elapsed-time diagnostics remain. Performance work must
measure the actual image-loading path before changing ownership or retention.

An additional 40-second 4× Expurgation gameplay check with normal player-hit
callbacks completed successfully (`expurgation-lua-atlas-regression-reopened.process.log`),
with its authored stage and effects still present. The earlier intermittent
native scanner allocator abort remains unresolved; passing full-suite scans do
not demonstrate a fix for it.

After removing the atlas experiment, the next release build passed and the
stable-source suite passed **799 tests across 182 modules in 162.9 seconds;
61 skipped, 0 failed** (`tmp/cammie-engine-plus-lua-final-suite.log`).

## Shared V-Slice background-offset follow-up

The user also reproduced the background offset in Wackyworld. Upstream
`Stage.hx` applies scale, calls `updateHitbox`, then assigns authored position;
our stage importer omitted the hitbox update for props. This matters because
Flixel's draw transform uses both origin and offset. A 1920×1080 background
scaled by 1.9 was drawn 864 pixels left and 486 pixels above its authored
coordinates. Expurgation's non-unit prop scales exercise the same missing step.

The importer now emits the donor order. Existing generated stage blocks receive
the same correction in memory only when selected V-Slice manifest provenance and
the generator's prop structure match. No donor, chart or generated stage file is
rewritten. A native Wackyworld baseline was captured after its 20.84-second intro
video (`wacky-offset-stage-before-reopened-26.0.png` and `31.0.png`); the earlier
14-second run was still in that video and is not stage-framing evidence.

During this follow-up the game was reopened and the saved offset changed
from 0 to approximately 251 ms while that session was running. The current settings baseline is now
`025d1a4921bf2913343bb5ae6b808db82ebf9b9ab04e5455b8feed2daea73db4`
(`tmp/cammie-settings-stage-offset-pass.json`); do not restore the older baseline.
The game was closed before the next build, as required by the runtime lock.

The geometry build passed, with **801 tests across 183 modules; 61 skipped,
0 failed**. Private-Xvfb Wackyworld captures at 26 and 31 seconds now show the
stage after the intro with corrected scaled prop placement. The unrelated
`countdownStart: EUnknownVariable(loadStage)` warning occurs before and after
this change and remains open.

## V-Slice layering, note visuals and animation follow-up

The user's subsequent gameplay screenshot exposed issues that the earlier
stage-presence checks did not prove fixed. New imports now retain each prop's
numeric depth. Eligible older generated stage scripts recover actor-relative
depth before the stable scene sort. A release build passed; the private-Xvfb
18-second `expurgation-visual-before-refresh` run exited 0 and its 14-second
capture shows the foreground masking the lower opponent body at the hole.
This run used old scripts with the in-memory layer repair.

Native `custom_note_visual` diagnostics verify that the lethal authored kind
now actually binds the selected namespace's `NOTE_death.png` (44 atlas frames,
7 Scroll frames), rather than only showing corrected metadata. Dedicated
NoteKind constructor identities can differ from filenames. Existing authored
visual overrides remain authoritative. Another special kind without an authored
style still uses its normal atlas; it is not assigned the lethal note's skin.

The importer also incorrectly defaulted dance animations to looping. It now
matches V-Slice's non-looping default and preserves explicit flags. Before
refresh, native GF diagnostics confirm 15 left frames and 5 right frames with
both halves looping. The supplied atlas has only 20 frames although its JSON
references frames through 30. Correcting the engine default does not create
those absent frames; full animation equivalence remains unproven.

The editor event lane now uses the note grid's checkerboard cell size and
colors, aligned separately to previous/current/next sections. Verified by
opening the actual editor with key 7 on a private Xvfb display and inspecting
`tmp/runtime-smoke/editor-checkerboard.png`. Input mapping was unchanged.

The source-suite snapshot before the final diagnostic/tool additions passed
**803 tests across 183 modules in 162.7 seconds; 61 skipped, 0 failed**.
Current settings retain the user's changed import path and showFPS preference;
the visual-refresh baseline is
`86840ab92642ff50087320840602530d9b59efe039772190a0642394d08588d3`
(`tmp/cammie-settings-visual-refresh-pass.json`).

The test runner now exports TMPDIR/TMP/TEMP under repository `tmp/` and strips
desktop display variables. Removed 670 obsolete isolated fixture directories
and 22 verified obsolete system-temp aliases; preserved verification records
and settings/import rollback backups.

The authorized refresh was applied after reviewing fresh plans generated with
the real compatibility helpers: four Tricky scripts and three Wackyworld scripts.
The changes are outputs of shared importer fixes: animation loop defaults,
stage depth/geometry, and existing camera/character anchoring metadata. Shared
base IDs and missing donor definitions were skipped. The existing native-base
character output was unchanged. Rollback copies are under
`tmp/import-refresh-backups/20260923T065721968162Z` and
`20260923T065736122185Z`; no donor/chart/media/settings file was replaced.

The user subsequently reported horizontal placement of the now-visible danger
notes. Correct atlas binding alone did not establish correct lane alignment;
that shared renderer path is being checked separately.

Shared horizontal alignment now centers the full rendered frame canvas on the
lane after every hitbox update, while preserving authored style offsets and
scale. A 33-second private-Xvfb run exited 0; the actual custom note canvas was
444 pixels wide and its constructor render-center error was approximately
`-5.7e-14` pixels. The source suite passed **810 tests across 186 modules in
121.3 seconds; 61 skipped, 0 failed**. A final bounded smoke marker checks the
live position after receptor snapping as well.

The final live check passed in `danger-alignment-live`: after gameplay snapping,
the danger atlas remained selected, rendered width was 444.5 pixels, and both
render center and nominal lane center were x=1124 (error 0). Its receptor's
109-pixel graphic centers at x=1122.5 inside the 112-pixel lane. The run exited
0 with no script errors. Release build passed; six focused smoke/alignment/temp
runner tests also passed after the final diagnostic addition.

After refresh, native GF diagnostics report both dance halves as non-looping;
Expurgation's 22-second and Wackyworld's 34-second private runs exited 0.
The Wackyworld `loadStage` warning remains. A separate note-script compatibility
gap remains: direct `offset.y` writes made during incoming-note callbacks can
be reset by subsequent hitbox updates. This pass does not replace those writes
with chart-specific constants.

The native import diagnostic now also keeps its short compiler aliases under
project `tmp/`. Haxe and hxcpp use the local C++ output directory as cwd, avoiding
spaces without system-temp aliases. A narrow native compile/run and its focused
path test passed; the temporary harness cleaned itself up. Twenty redundant
screenshots from this pass were removed after retaining the final evidence.

## Codename script tween facade follow-up (24 September)

Mounted Codename scripts call `FlxTween.color` (for example HL17 Freeplay),
while the scope-local facade exposed only `tween` and `cancelTweensOf`.
The facade now exposes Flixel's `num`, `angle` and `color` constructors through
the same owned-tween path. This preserves callback parameters and applies pause,
resume and teardown to tweens created by all four methods, including creation
during a pause. The extracted Haxe interpreter fixture executes the calls and
verifies callback delivery, pause/resume, scope isolation and cancellation;
`test_codename_script_interp`, `test_codename_character_runtime`,
`test_codename_stun_timing`, and `test_codename_character_visual` passed
(7 tests). A full native game build
and visual check are deferred to the integration pass.

## Psych cutscene and Codename integration (24 September)

The shared Psych Lua bridge now resolves sound effects from the selected import
owner, exposes camera fade/flash, and hands scripted dialogue completion back to
the native countdown. Future Psych imports copy missing shared donor sounds into
their selected owner without overwriting existing files. A guarded missing-only
repair restored 17 sounds (2,307,827 bytes) to the installed Psych owner; donor
chart and script bytes and the user's live options were preserved. In an
isolated 35-second native Freeplay run with default settings, the dialogue
advanced, the overlay disappeared, `inCutscene` became false, countdown started,
and the song position advanced. No missing sound, decode, or unknown Lua global
errors appeared. Audio output was not recorded or listened to, and the entire
song was not replayed. Evidence: `tmp/freeplay-cutscene-native/validated-result.json`.

Codename discovery now accepts both native strumline and section-based charts,
ignores non-chart JSON sidecars, preserves nullable line identities, and reads
selected-owner chart defaults from supported INI configuration. Per-line
nullable ghost-tapping overrides follow the live engine option. Stage starting
camera coordinates are applied by axis after creation and stage changes. The
release build passed. A private Xvfb import of a mounted mixed-format Codename
song passed for all three difficulties: 788, 858, and 1,019 note rows; shared
events and difficulty-specific stage/GF fields were retained; each chart
entered PlayState successfully with default options. Installed asset hashes were
unchanged and the private donor/runtime overlay was removed. Evidence:
`tmp/codename-dsides-blammed-preview/result.json` and
`tmp/codename-final-build.log`.

The final suite recheck passed **1,024 tests across 277 modules in 175.3
seconds, with 61 skipped and zero failures**
(`tmp/codename-final-suite-recheck.log`). Its first run had one isolated stage
test fixture missing the new camera helper; that fixture was corrected and its
two focused tests and the full recheck passed. The previously observed
intermittent native diagnostic-scanner allocator failure remains unresolved;
this passing run does not establish that it cannot recur.

## DDTO++ V-Slice variation import and scoped refresh (24 September)

The sibling chart/metadata pairs in the mounted DDTO++ V10 root now import as
separate native songs. The native importer scanned the exact owner source root
and found 54 candidates with zero duplicates, missing dependencies, or scan
errors. Its aggregate batch did not pass: the copied live export already had
base-song `compatScripts.json` files with both the selected
`v-slice-ddto-v10-release-2dbdf01f44` root and an older
`v-slice-ddto-v10-release-c10f3d7e1c` root. The shared ownership guard rejects
those 49 existing mixed-owner destinations before writing them. The four
variation output directories were absent before this run, so those conflicts
could not affect their charts or media.

| Source variation / difficulty | Native song / difficulty | Note rows | Source events | Native event groups | Actors (player / opponent / GF) | Stage / UI |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `baka` / `alt` | `baka-alt` / `normal` | 790 | 45 | 42 | `tankman-doki` / `natsuki` / `nogf` | `clubroom` / `normal` |
| `epiphany` / `lyrics` | `epiphany-lyrics` / `normal` | 1,650 | 7 | 7 | `bf-doki` / `bigmonika-dress` / `gf` | `evilClubroom` / `normal` |
| `love-n-funkin` / `pico` | `love-n-funkin-pico` / `normal` | 666 | 49 | 49 | `pico-doki` / `sayori` / `nogf` | `musicroom` / `normal` |
| `shrinking-violet` / `alt` | `shrinking-violet-alt` / `normal` | 719 | 33 | 30 | `spooky-doki` / `yuri` / `nogf` | `musicroom` / `normal` |

Every flattened source event (timestamp, authored event name, and parameters)
matches the converted chart. Baka and Shrinking Violet have fewer native event
rows because same-timestamp events are grouped into one row; none are lost.
All 11 copied instrumental/vocal OGGs have byte-identical SHA-256 hashes to
their donor files, including the alternate/pico instrumental selections and
the character-specific vocal stems. The four `compatScripts.json` files select
the exact DDTO++ owner namespace. Their imported Freeplay records and all
required custom character registry entries are present. Stage and `normal` UI
definitions were already available and were exercised by the chart startups.
The `Imported` Freeplay category gained four records with source display names
and opponent icons: Baka (Tankman Mix)/`natsuki`, Epiphany with Lyrics/
`bigmonika-dress`, Love n' Funkin' (Pico Mix)/`sayori`, and Shrinking Violet
(Spooky Kids Mix)/`yuri`. The character registry gained only the missing
`pico-doki`, `spooky-doki`, `tankman-doki`, and `bigmonika-dress` entries.

All four charts passed serial offscreen native PlayState startup smokes with
default options and dummy audio. Each reached `playstate_ready` and `success`
with no timeout or options change; each smoke ran for 2 seconds, so this is a
startup gate, not a complete playthrough or listening comparison. Evidence:
`tmp/vslice-native-preview/variation-source-parity.json`,
`tmp/vslice-native-preview/startup-report.json`, and
`tmp/vslice-native-preview/import-report/import-preparation.json`.

The scoped live refresh added exactly 42 files: 11 chart/manifest/note-info
files under the four new song data directories, 11 OGGs under their song
directories, and 20 script/atlas/icon files for the four missing character
definitions. It merged only four Freeplay records and four character-registry
keys, preserving every pre-existing record/value. The whole-root preview's
unrelated `event-sprites.json` and `notestyles/libitina.json` changes were
excluded. SHA-256 comparison saw exactly the 44 planned changed paths (42 new
files plus two registry updates) among 5,154 pre-existing files/links; all 453
files in the selected owner namespace and the user's `options.json` remained
unchanged. Rollback copies and the absent-target manifest are in
`tmp/vslice-native-preview/live-refresh-backup/`; the post-refresh audit is
`tmp/vslice-native-preview/post-refresh-audit.json`. The run.sh build path
preserves runtime-only registries across Lime asset sync, so no repo seed or
user settings were edited. The registry rollback copies are
`live-refresh-backup/assets/data/freeplaySongJson.jsonc` and
`live-refresh-backup/assets/images/custom_chars/custom_chars.jsonc`.

## Cross-owner native reload and full-song gate (24 September)

Canonical `./run.sh build` passed after the storage-key editor route, Psych
`close()`/`noteTweenAlpha` bridge, Codename owner-catalog checkpoint, and
two-song smoke harness were added (`tmp/example-mods-native-build-10.log`).
The focused harness, storage-key, Psych Lua, and full-playthrough runner suite
passed 31 tests.

The two-visit native gate now accepts a second chart and prepares script
metadata for both selected owners. Wacky World Hard then Expurgation Hard
passed under Xvfb with the repository default options, dummy audio, and an
exclusive release runtime lock. Four more offscreen processes alternated the
direction; all five had two distinct `playstate_ready` markers, a first-state
teardown, exit code 0, no script errors, and unchanged disposable options.
Evidence: `tmp/example-cross-owner-build10.jsonl`,
`tmp/example-cross-owner-repeat-build10.jsonl`, and the matching
`tmp/runtime-smoke/logs/example-cross-*.process.log` files. These bounded
visits do not cover song endings or source visual/audio parity.

The new full-song runner requires the source chart and selected runtime owner
to pass its preflight before launching. Wacky World Hard played through its
153.767-second donor instrumental at 5x rate and reached natural `song_end`
with 106/106 source events dispatched, no interpreter errors, and unchanged
options (`tmp/example-full-playthrough-wacky-hard.jsonl`). This verifies one
difficulty's event and ending path; its rendered scene and sound have not been
compared frame by frame or by listening.

An expanded build10 full-song run covered Wacky World Normal, Hard and
Nightmare. All three reached natural `song_end` and dispatched 106/106 events,
but the stricter gate correctly failed all three on four health-icon dependency
diagnostics. Their logs also contain unsupported HXC module/callback-body
diagnostics for the donor video module; the initial gate did not classify those
as errors, and this has now been corrected. The donor and installed icon PNGs
exist under lowercase character registry keys while the authored health-icon
ids use mixed case. The shared
`HealthIcon` registry lookup now resolves the matching key and disk folder;
its synthetic and mounted-asset Haxe tests pass. SHA-256 comparison confirms
the installed Pomni/WackyPomni and Caine/WackyCaine icon PNGs match the two
source `icon-Wacky*.png` files byte for byte; source and installed hashes are
in `tmp/wacky-icon-source-hashes.json`. A rebuilt native replay is still
required. The native chart-video route covers part of the donor module's
behavior, but its pause/resume/resync/cleanup parity is unverified, so even a
clean icon replay cannot close Wacky World compatibility yet. Evidence:
`tmp/example-full-playthrough-wacky-all-build10.jsonl` and its per-case
process logs.

Build 18 compiled and linked through `./run.sh build`
(`tmp/example-mods-native-build-18.log`). A private Xvfb/default-options
probe captured a frame from the real `rough_vhs` chart-event clip at Wacky
World's 0 ms event (`tmp/wacky-video-build18/event-video.png`). The process
exited 0 and its disposable options were byte-identical. All three Wacky
World difficulties were then replayed to natural endings on build 18, each
with 106/106 events and no health-icon dependency error. The strict gate
still failed all three on ten donor `PVE_VideoModule` body/callback warnings
per run. Native video rendering is demonstrated; source-equivalent pause,
focus, seek, retry, and teardown behavior remains open. Evidence:
`tmp/wacky-video-build18/result.json` and
`tmp/example-full-playthrough-wacky-build18.jsonl`.

The full `tools/run_tests.py` run after build 18 completed with six failing
test modules caused by extraction fixture dependencies on new Codename and
Lua runtime classes (`tmp/example-mods-full-suite-build18.log`). Owners
updated those fixtures without loosening assertions; focused modules pass.
The HXC analyzer also had three false payload warnings across the mounted
Tricky note/text donors: the native note proxy already copies `offset.x`,
`offset.y`, and `flipY`, and the bounded text-cue adapter owns the extracted
callbacks. `HxcCompat` now recognizes only those already implemented fields
and a fully safe text-cue spec. Synthetic and mounted-source regression tests
pass. Build 19 with these changes and the shared imported-mod chooser routing
passed `./run.sh build` (`tmp/example-mods-native-build-19.log`). A complete
post-build suite and FNAS native menu replay are still pending.

Build 20 also passed `./run.sh build` after a shared role-aware vocal bus
bridge and the Codename state host's map binding were added
(`tmp/example-mods-native-build-20.log`). The vocal adapter keeps source
`player` and `opponent` stem roles: the donor `set_playerVolume` call now
addresses only player stems, while a direct legacy write to the primary
FlxSound still propagates to all stems. Synthetic, mounted Tricky-module,
and split-vocal tests pass. Build 21 passed with a native video focus-gain
guard; its focused lifecycle test confirms a clip cannot restart behind an
open pause menu after focus returns (`tmp/example-mods-native-build-21.log`).

The FNAS private owner import staged one chart with 1,224 notes, 204 events,
the expected audio, scripts, actor atlases, event packs and videos without
changing eight protected export paths or default options. One build19 UI
probe reached the Imported Mods chooser, proving the shared hotkey route;
its driver chose a different row from the globally sorted launch plan. The
corrected build20 driver then stopped on the title screen because it sent its
second Enter before the title transition. Neither probe verifies
`FnasMainState` or its song/menu behavior. Evidence is under
`tmp/fnas-owner-ui-preview/`; the driver is being changed to wait for an
observable transition.

The mounted full auto-import diagnostic scanner returned successfully once
after the payload analyzer correction (`tmp/hxc-payload-scanner-build19.log`,
no `unsupported-hxc-payload` count). A later test-driven invocation aborted
with glibc `double free or corruption (!prev)` while enumerating V-Slice roots
(`tmp/hxc-vocal-focused-build19.log`). This reproduces the previously known
intermittent native heap defect; its corrupting operation is still unknown.
The strict mounted scanner test is failing on that abort, not a diagnostic
count assertion. No run is counted as clean by retrying past this failure.

Build 22 passed `./run.sh build` after the role-aware vocal bridge was wired
through `PlayState`, `HxcCompatRuntime`, and the HXC lowering pass
(`tmp/example-mods-native-build-22.log`). The mounted Tricky vocal module now
lowers its `vocals.set_playerVolume(...)` call to the player-stem bus in the
focused Haxe tests. The build-22 D-Sides private preview retained 22 source
charts, while its 22-row native startup sweep found two concrete script
errors (`EUnknownVariable(currentState)` in Darnell Hard and
`EUnknownVariable(camFollow)` in Spookeez Hard); the remaining 20 rows reached
the smoke success marker. This is a private owner preview, not a live refresh.
The forward class variable declaration and missing live camera alias are
being corrected in the shared Codename interpreter bindings.

Build 23 passed `./run.sh build` after an explicit event-video skip smoke
marker was added (`tmp/example-mods-native-build-23.log`). A private Xvfb
Wacky World Hard run at normal speed rendered frames from the donor chart
video, accepted Escape to pause and Return to resume, then accepted Space to
skip. The native marker records a seek from 2,220 ms to the authored
20,840 ms video boundary and four chart events crossed. Four visual captures
show the video before pause, the pause menu, video after resume, and gameplay
after the skip. The process exited 0 and its default test options were
byte-identical. Evidence: `tmp/wacky-video-interaction/result.json`, its
`markers.jsonl`, process log, and four PNGs. The donor video module's complete
HXC lifecycle remains under review, so this interaction pass does not close
the remaining module warnings or establish all-difficulty source parity.

A fresh, isolated Vs Tricky writer audit imported all four songs and ten
difficulties with zero writer or semantic errors
(`tmp/vs-tricky-current-converter-preview.log`). It did not copy gameplay
media into the live export. Its current Hellclown charts match all source raw
note counts (1,822/2,070/2,254), whereas the installed owner charts have
1,725/2,065/2,255 rows. The current Madness preview has 652/832/1,064
gameplay rows versus 669/852/1,084 installed. The mounted source charts
contain 4/8/8 further rows on lanes 12–15. In the authored V-Slice 0.3.2
engine, `SongNoteData.getStrumlineIndex()` divides `d` by four, and
`PlayState.regenNoteData()` routes only strumline indices 0 and 1 into the
two gameplay strumlines; those source rows are present in the raw inventory
but do not play. The [upstream note schema](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/data/song/SongData.hx)
and [upstream PlayState](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/play/PlayState.hx)
are the source-behavior evidence. `tools/audit_vslice_playable_rows.py`
reproduces this distinction for all 84 V-Slice difficulty keys; its build-23
report records 20 unrouted raw rows, 77 live gameplay-row count matches, and
all ten current Vs Tricky preview counts matching source gameplay rows
(`tmp/vslice-playable-row-audit-build23.json`). Count agreement alone does
not establish note timing, note kind, animation, or audio parity. A backed-up
owner-scoped live refresh is still required for Hellclown and Madness; no
installed file was changed by this audit.

The build-23 FNAS private owner preview imported its one chart with 1,224
notes, 204 events, source audio, event packs, character atlases and video
files. Its offscreen menu probe reached the native MainMenuState, opened the
Imported Mods chooser, selected the staged `FnasMainState`, and captured the
destination screen (`tmp/fnas-owner-ui-preview/`). The destination was black
apart from the host's F10 hint because source `create` stopped on a missing
scoped `music/freakyMenu` asset; subsequent lifecycle calls reported
`Invalid field:iTime` and `EUnknownVariable(so)`. These are shared Codename
host/path gaps to fix before any FNAS menu or song compatibility claim. The
third private probe exited with a failed UI assertion, and protected
repository/export options and eight checked paths retained their pre-run
hashes. No FNAS files were installed into the live export.

On the next canonical build, the shared Codename top-level declaration and
live `camFollow` fixes cleared the two D-Sides startup exceptions. Darnell
Hard and Spookeez Hard both reached PlayState success in their private owner
overlay, with protected live files and options unchanged. The strict rows
remain failed: Darnell still reports unresolved `darnell-tunnel` and
`pico-tunnel` actor IDs, `phillyTruck.hx` `Invalid field:uRainColor`, and a
`Change Character.hx` parse error; Spookeez still reports a
`spookyMansion.hx` parse error. Evidence:
`tmp/dsides-refresh-preview-build19/targeted-native-build-current/result.json`
and its two process logs. The remaining diagnostics are being traced to
shared actor, stage, and Codename parser support.

The same native binary replayed Vs Tricky Expurgation Hard to its natural
193.073-second ending at 5x, dispatched all 126 chart events, exited 0, and
left disposable options unchanged
(`tmp/example-full-playthrough-expurgation-post-vocal.jsonl`). The vocal
module and note/text payload warnings present in the earlier build-10 run
are absent. Its strict gate now fails on exactly one unsupported module:
`StoryConfirmMouth.hxc`, which owns a donor Story Menu presentation and
confirmation transition that the native story host does not yet execute.

Six current-converter Hellclown and Madness charts were then overlaid one at
a time on private copies of their installed data folders; the live charts
were never written. All six reached native startup smoke success with exit 0
and unchanged default test options
(`tmp/vs-tricky-preview-startup.json`). Their strict logs still retain three
`bfhell.hxc` `onCreate` hook warnings across Hellclown and two
`StoryConfirmMouth.hxc` module warnings per case. The latter is present in
both the selected Vs Tricky owner and an older overlay root for these charts;
duplicate module discovery needs an owner-aware review. The result supports
a future scoped, backed-up chart refresh but is not evidence of full-song,
rendered, audio, editor, or Story Menu parity for those six difficulties.

The six Hellclown/Madness charts were subsequently refreshed in the live
export from the current isolated converter preview under the selected
`v-slice-vs-tricky-5cb4ba5ba3` owner. The scoped refresh tool required the
same selected owner in source and target manifests, pinned every before/source
chart hash and both settings hashes, backed up the six replaced chart files,
and verified each installed result and backup hash. No manifest, media, donor,
or settings file was in its write set. Evidence:
`tmp/vs-tricky-owned-chart-refresh.plan.json` and
`tmp/vs-tricky-owned-chart-refresh.receipt.json`; backups are in the receipt's
`tmp/owned-chart-backups/` directory. The reproducible V-Slice audit now
finds 83/84 live difficulty keys matching source gameplay row counts; the
remaining mismatch is an unpopulated DDTO++ alternate-normal placeholder
which the source variation metadata does not declare. The updated matrix
retains raw source counts and stores separate gameplay counts; the full-song
preflight reports all ten Vs Tricky difficulties ready
(`tmp/vs-tricky-post-refresh-preflight.jsonl`). This is a structural gate,
not a full-song compatibility pass.

The 24 September post-parser private D-Sides replay again imported all 20
songs and 22 charts without touching the live export or personal settings.
Source and staged note rows matched 17,834/17,834, and event rows matched
6,729/6,729. The event-derived `darnell-tunnel` and `pico-tunnel` actors
now have selected-owner files and registry entries; Darnell Hard has all
133 source events. Both targeted strict native starts still failed:
`darnell` raised `Change Character.hx:1 EUnexpected(?)`,
`phillyTruck.hx.update: Invalid field:uCameraBounds`, and a fragment shader
compile error; `spookeez` reached gameplay but its stage raised
`spookyMansion.hx.postCreate: Invalid field:mult`. These are current shared
Codename parser, shader and stage binding gaps, not successful song checks.
The complete private receipt and per-song process logs are under
`tmp/dsides-parser-diagnostic-replay/`.

The current V-Slice importer omitted the separate Freeplay pixel
portraits for eight installed rows across the Miku, Vs Tricky and Wacky
packages. The selected-owner namespaces had none of these files, and
`FreeplayState` supplied a gameplay `HealthIcon` instead. Future Sound's
`no-gf` therefore drew the neutral fallback grid in Freeplay even though
the donor supplies `images/freeplay/icons/no-gfpixel.png`. Shared discovery,
owner-scoped import mapping and menu-only loading at the
[V-Slice 0.3.2 source's 2× scale](https://github.com/FunkinCrew/Funkin/blob/v0.3.2/source/funkin/ui/freeplay/SongMenuItem.hx)
have been added with focused path tests. A new canonical native build passed,
and the private Miku writer audit validated all three charts and its visual
sources with unchanged donor bytes. Eight missing PNGs were then copied into
their selected-owner live namespaces without replacing any existing file;
the owner witnesses and SHA-256 hashes are recorded in
`tmp/vslice-freeplay-icon-refresh-20260924/receipt.json`. This confirms
owned asset presence, while native rendered Freeplay and the actual native
import copy path still need verification. Gameplay `no-gf` is
separately hidden per V-Slice 0.3.2 behavior.

The 24 September combined release build completed through `./run.sh build`.
The initial full 1,109-test run had four failures: two importer extraction
fixtures omitted the new icon field/helper, one test expected the older
Codename unconditional health-icon warning counts, and one source assertion
expected a literal loop that is now factored through a local root variable.
All four test definitions were corrected; the two importer modules and the
source assertion pass focused reruns, while a new full-suite result is pending.
The Codename scanner's role-aware classification now reports 14 raw and 7
selected required health-icon gaps, plus 3 raw and 1 selected optional
`icon-unresolved` reference. A bounded D-Sides comparison showed identical
diagnostic counts in normal and streaming scanner modes. The private Story
menu navigation attempt preserved settings and exited cleanly but did not
prove a Story transition; its input driver is being corrected.

The fresh stable-binary FNAS private owner-menu replay again imported its
`better-clone` Normal chart with 1,224 rows and 204 events, selected the
owner's `FnasMainState`, then failed the rendered menu assertion. The first
runtime error is now a concrete source-backed asset gap:
`Paths.getFrames('main/sonic')` requests an owner-scoped PNG/XML atlas that
exists under the donor's `mods/fnas/images/main/` but was not staged by the
Codename runtime asset planner. No FNAS gameplay or menu parity is claimed.
The private receipt is `tmp/fnas-owner-ui-preview/owner-menu-result.json`;
the live options hash remained `a1a3464c0dbe2e8b710ed806112dcca4d5120b603e2b1e219ed2984d7493e243`.

A fresh private D-Sides native replay on the 24 September build imported all
20 selected songs with no import errors and preserved the protected live
targets and settings. Spookeez Hard now passes strict startup without tagged
diagnostics. Darnell Hard still fails strict startup: its staged `Change
Character.hx` reports `EUnexpected(?)`, and its rain shader reports that the
fragment varying `screenCoord` is not written by the vertex shader. The donor
provides a same-stem `rainShaderSimple.vert`; the importer and shared runtime
are being changed to stage and load it together with the fragment. Receipt:
`tmp/dsides-current-build22/result.json`. Neither song has a new full-length
source-behavior verification yet.

The next combined build stages FNAS `main/sonic` through the new generic
`Paths.getFrames` atlas planner. A private FNAS menu replay no longer reports
the missing atlas, but still fails before labels render: the source state calls
`changeItem()` with zero arguments while the current script bridge requires
one. Its process log also contains a null `setFilters` receiver. This is a
remaining menu runtime defect, not a completed FNAS check. The same private
fixture and owner receipt under `tmp/fnas-owner-ui-preview/` retain the
failure evidence. A D-Sides replay after vertex staging still had the shader
error because PlayState used a second fragment-only shader factory; that
factory is now routed through the shared paired shader loader, awaiting a new
build and native check. The `Change Character.hx` parse diagnostic persists.

The subsequent targeted D-Sides replay staged the sibling vertex and reached
Darnell Hard startup without the earlier shader program error. Its sole strict
failure is now `Change Character.hx:1 EUnexpected(?)`. A runtime-smoke-only
diagnostic confirms the exact staged 3,707-byte script was loaded (SHA-256
`f7a62bb4536c09637e5953b43e3117efe25e99c6ef5dd2ebea3bf20484f0f9dc`)
and shows the normalized source still contains the optional `?offset`
declaration. Spookeez Hard remains strict-pass. This narrows Darnell to the
native HScript parser/normalization route; no full-song pass is claimed.

A private `--smoke-freeplay` render run entered the real Imported Freeplay
list, scrolled from Fantasy Girl 01 to Future Sound, exited with a success
marker, and preserved both live and repository-seed settings hashes. Its
captures are under `tmp/freeplay-icon-proof-20260924/captures/`. The Future
Sound row still rendered a blue fallback portrait although the scoped
`no-gfpixel.png` was present. The menu passed an empty owner to HealthIcon
because `Song.characterRootForSong` only returned Psych/Codename owners.
An explicit V-Slice menu owner route and focused extraction test are now in
source. The next canonical build and private visual replay now show the
source-shaped turquoise Future Sound pixel portrait and pink Rabbit Hole
portrait at the expected 2× scale, with no neutral gameplay icon on the
`no-gf` row. The Freeplay smoke emitted success and the live personal and
private repository-seed settings hashes were unchanged. This verifies those
rendered menu rows; it does not yet verify every installed V-Slice menu row.

The next FNAS native menu replay passed atlas staging but failed earlier in
the new default-argument parser on native C++: PCRE rejected a generated
optional-argument pattern with `missing closing parenthesis`. Haxe `--interp`
focused tests had passed, so this is a native portability defect. The exact
error is in `tmp/fnas-owner-ui-preview/owner-menu.process.log`; menu parity
remains unverified.

After removing the native regex path, the private FNAS menu screenshot visibly
renders the authored `Fnas:After Hours` title and Continue/New Game/Options/
Credits entries; the fixture returned a menu-render success after allowing
OCR whitespace around the stylized title. The same receipt says
`gameplayStarted:false`, and the source state logs a missing owner-scoped
`sounds/menu/scroll` during update. That Ogg exists under the installation's
top-level `assets/sounds`, outside the selected `mods/fnas` folder. This
remaining installation-level asset routing gap blocks menu interaction and
New Game coverage; a rendered menu alone is not FNAS compatibility evidence.

The FNAS private runner now requires both a gameplay transition from New Game
and an empty runtime-diagnostic list before it writes a passing receipt. Its
earlier `status:passed` was only an OCR menu-render success and must not be
counted as a compatibility result. The top-level sound staging change and a
fresh native replay are pending.

The private HXC Story Menu fixture selected Story Mode and then the native
process segfaulted after `StoryMenuState.hx:84`. A synthetic-week character
registration error was corrected in the fixture, but the crash repeated. The
fixture uses a private runtime, repository-seed options, offscreen Xvfb and
dummy audio, and leaves the installed options unchanged. A debugger backtrace
is needed to distinguish fixture content from shared Story Menu behavior;
there is no Story transition pass yet.

The debugger then located the crash in `MenuItem.new`: the PNG-only week-art
branch calls `week.loadGraphic(rawPic)` before constructing `week`. The
synthetic fixture used PNG art without a Sparrow XML, which exercised this
shared branch. A generic null-dereference fix and native replay are pending;
the crash cannot be attributed to the HXC Story adapter.

The new Wacky World video adapter was exercised in full-song private native
replays of Normal, Hard and Nightmare at 5× audio speed. All three reached
natural `song_end` at 153,767 ms with 106/106 chart events and no tagged
interpreter errors. Each process then exited 139 after entering
`VictoryLoopState`, before the runtime-smoke success marker. The strict
results are three failures, not passes, in
`tmp/example-full-playthrough-wacky-video-current.jsonl`. The matching
post-song crash needs teardown diagnosis; these runs kept settings unchanged
and did not interrupt desktop display or audio.

As a control on the same binary and harness, Future Sound Normal ended at
205,333 ms with 9/9 events, no tagged interpreter errors, a smoke success
marker and exit code 0. Its strict result is a pass in
`tmp/example-full-playthrough-future-sound-current.jsonl`. This suggests the
new post-song crash is specific to Wacky World content or lifecycle rather
than every `VictoryLoopState` transition. It does not prove Future Sound's
entire source presentation or editor behavior.

The same current-binary full-song runner gave Expurgation Hard a strict pass:
natural `song_end` at 193,073 ms, 126/126 events, no tagged interpreter
errors, smoke success and exit 0. Receipt:
`tmp/example-full-playthrough-expurgation-current.jsonl`. This clears the
earlier HXC module warning gate for this specific playthrough; separate Story
Menu, cutscene-skip, editor, and source-visual checks remain.

An offline core dump from Wacky World identified the post-song crash as
`FlxCamera.set_alpha` called by `HxcVideoModuleHost.destroy` while the
outgoing `PlayState` camera was being destroyed. The shared video host now
omits HUD camera writes from teardown, while preserving its owned-sprite and
tween cleanup. Focused teardown tests pass 3/3; a native rebuild and
all-difficulty replay are needed to close the crash.

The combined canonical `./run.sh build` succeeded after the Codename
installation-sound resolver, PNG-only week sprite fix, and video teardown
change. A private FNAS menu replay on this binary no longer reports the
missing `sounds/menu/scroll`; it remains a strict failure because New Game
does not enter gameplay and the state logs `EUnknownVariable(StringTools)`.
Receipt: `tmp/fnas-owner-ui-preview/owner-menu-result.json`. The Codename
script binding for that source class is under investigation.

The Story fixture now goes from Title to Story Mode, selects its synthetic
Expurgation week and Hard difficulty, then enters PlayState without crashing;
both live and seed options hashes stayed unchanged. The fixture screenshots
and logs are in `tmp/story-menu-proof-20260924/`. Its PlayState log emits
multiple `hxc-runtime-error` lines for Vs Tricky `.hxc` files, although the
isolated full-song Expurgation runner did not. The UI route therefore has a
remaining shared discovery/runtime gap; the clean process exit proves only
the Story transition, not song compatibility through this route.

On that same combined binary, Wacky World Normal, Hard and Nightmare all
passed the strict private full-song gate: each ended naturally at 153,767 ms,
dispatched 106/106 events, emitted no tagged interpreter errors, wrote a
smoke success marker and exited 0. The teardown crash no longer reproduces.
Receipt: `tmp/example-full-playthrough-wacky-video-fixed.jsonl`. This covers
the three current difficulties and their natural endings; pause, seek, retry,
editor and unaccelerated video synchronization still need separate checks.

The targeted private D-Sides replay after the combined build imported all
20 selected songs and probed Spookeez Hard and Darnell Hard. Spookeez again
passed strict startup. Darnell reached PlayState but failed on its staged
`Change Character.hx` parser diagnostic; the smoke-only normalization trace
shows the `??=` sequence remains in the normalized source after the
coalescing-assignment pass. The paired rain shader no longer fails. Receipt:
`tmp/dsides-current-build22/result.json`.


Further inspection of the Story fixture identified a confinement artifact:
its `assets/imported_mods` directory is a symlink to the installed export.
HXC discovery canonicalizes discovered files to the export path, while the
private game cwd is the fixture, so the existing asset scope check rejects
those files. The resulting `hxc-runtime-error` lines therefore do not yet
establish a live UI-route compatibility defect. The fixture needs a private
bind-mounted owner tree or equivalent in-scope materialization, followed by
a Story replay. Asset scope must not be weakened to hide this fixture gap.

A second canonical build containing the Codename `StringTools.replace`
facade and an exact-character `??=` scan succeeded. Private D-Sides startup
still fails Darnell Hard: native stage counters remain zero at input and the
staged ASCII script still contains `offset ??=` after normalization, while
Spookeez Hard passes. The interpreter fixture sees the operator correctly;
the native discrepancy is still unexplained. The paired shader error remains
absent. Receipt: `tmp/dsides-current-build22/result.json`.

The same build advances the FNAS menu past its former `StringTools` error,
but New Game now crashes when entering PlayState. The donor state calls
`PlayState.__loadSong("better-clone", "Normal")` before switching states;
the current Codename binding exposes the native PlayState class without that
static loader. The process logs a null `__loadSong` call, then segfaults in
`PlayState.create` with an unset `SONG`. The strict private runner reports
failure, and the offline core backtrace is under
`tmp/fnas-owner-ui-preview/fnas-menu-backtrace.txt`. A generic source-style
song loader and failure-safe transition are needed.

The corrected private Story fixture uses a read-only bind of the built asset
tree rather than symlinks outside its cwd. It navigated Story Mode, selected
the synthetic Expurgation Hard week, entered PlayState, and exited 0. This
time its log had no `hxc-runtime-error`, character/stage runtime error, or
“No compatible HScript/Lua module found” lines. Live options and private
seed options hashes stayed unchanged. The current transition screenshot is
still too dark to prove the final playfield, so a delayed capture is pending;
the previous HXC failures were fixture confinement artifacts.

A final corrected Story fixture replay used an empty private home, navigated
the same Hard selection, and captured a clear Expurgation playfield after the
live `FocusCamera @ 4174ms` chart event. The frame shows stage, characters,
receptors and HUD at `tmp/story-menu-proof-20260924/captures/05-playstate-focus-camera.png`.
The current log contains one StoryMenu adapter marker, no HXC runtime,
character or stage errors, and `GAME_EXIT|0`. Live and seed options hashes
remained unchanged. This verifies the Story selection and initial gameplay
route in the bounded fixture; it does not prove a Story playthrough or all
menu presentation details.

The next canonical `./run.sh build` included a public Codename-compatible
`PlayState.__loadSong` route and a null-chart guard. The FNAS private owner
preview now imports its selected chart, renders the authored menu, activates
New Game, enters `better-clone` Normal PlayState, reports no tagged runtime
diagnostics, and exits its strict runner successfully. The New Game screenshot
shows the source scene, receptors and HUD at
`tmp/fnas-owner-ui-preview/fnas-new-game-route.png`; receipt:
`tmp/fnas-owner-ui-preview/owner-menu-result.json`. Live export and personal
settings snapshots were unchanged. This is a menu-to-gameplay startup check;
full song, pauses, cutscenes, endings, and other FNAS states remain unverified.

The subsequent targeted D-Sides replay on this loader build still reports
Darnell Hard as a strict failure, with Spookeez Hard passing. The native
parser's smoke trace now says `rawToken=absent` and
`activeCoalesceAssign=0` even at input, despite showing the exact staged
ASCII file SHA and a nearby raw `offset ??=` excerpt. This isolates a native
token-search discrepancy; no source-behavior pass is claimed for Darnell.

The existing isolated FNAS full-song proof now passes on the loader build.
It re-imported `better-clone` Normal in a private owner, played to natural
ending at 206,896 ms with 204/204 events, observed authored callbacks for
`Camera Flash`, `Camera Movement`, `ConfettiHUD`, `sonic` and
`tedyescrazyasszoom`, and confirmed the terminal camera fade. A captured
confetti video frame shows owner-scoped video playback and shader effects;
the runtime snapshot reports `videoLoaded:true`, `videoPlaying:true` and a
runtime shader. There were no tagged runtime errors and the protected live
assets/settings snapshot was unchanged. Receipt:
`tmp/fnas-native-preview/result.json`; frame:
`tmp/fnas-native-preview/confetti-playing.png`. This is one chart/difficulty
at 5× song rate; the FNAS custom pause, alternate states, retry, seek and
unaccelerated media timing still need coverage.

On the same stable binary, Fantasy Girl 01 Normal passed a strict private
full-song run: natural ending at 201,600 ms, 70/70 events, no tagged script
errors and exit 0 (`tmp/example-full-playthrough-fantasy-girl-current.jsonl`).
Rabbit Hole Normal reached its natural 159,566 ms ending with 592/592 events
and exit 0, but remains a strict failure: the HXC shader adapter reports
unsupported donor operations in `onCountdownStart`, outside the bounded
synthetic filter hook. Receipt:
`tmp/example-full-playthrough-rabbit-hole-current.jsonl`. The mounted source
callback is being mapped into a shared HXC shader lifecycle adapter.

The dedicated native `??=` scanner made Darnell Hard and Spookeez Hard both
pass targeted strict startup. A full private D-Sides import/startup sweep then
tested all 22 source chart difficulties: all 22 reached PlayState, but only
4 met the strict no-diagnostic startup gate; 18 failed. The failure groups
include missing generic Codename class bindings (`FlxSpriteGroup`,
`FlxTypeText`, `FunkinText`), unsupported source events, incomplete actor/
camera placement or character assets, unresolved owner-scoped images, and
other script parse/import diagnostics. The complete per-chart list is in
`tmp/dsides-current-build22/result.json`. These are real compatibility gaps;
reaching PlayState is not a pass. Live installed charts and options were
protected by the private preview and remained unchanged.

The next shared Codename parser change lowers top-level `public`, `private`,
and `static` declaration modifiers before HScript parsing. The exact mounted
`data/stages/stageD.hx` payload now passes a focused extract-and-interpret
test without changing donor bytes (`python3 -m unittest
tools.tests.test_codename_script_parser -v`, 4/4). This has not yet been
checked in a new native build. The shared native event dispatcher also now
handles typed `HScript Call` function names and comma-separated string
arguments, plus camera-specific additive `Add Camera Zoom`. Its focused
interpreter test passes (`tools.tests.test_codename_native_events`, 1/1).
The behavior reference is Codename's [event documentation](https://codename-engine.com/wiki/modding/songs/events)
and [PlayState source](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/PlayState.hx).
The `Camera Modulo Change` path and the other startup failures in the 22-chart
D-Sides sweep remain open.

The initial Dusk `uberkid.png` diagnostic was an importer/resolver error:
the mounted owner supplies `images/stages/dusk/uberkid/Animation.json` and
its atlas pages. Dusk Hard now passes strict startup after the folder-aware
atlas import. A `gfgrunt` character definition remains absent from the
mounted owner and is still an explicit source dependency.
The `BitmapData.png` diagnostic in Try Harder had a different cause: its
stage passes an owner-resolved `Paths.image(...)` bitmap to
`FunkinSprite.loadSprite`, which previously treated the bitmap as the string
`BitmapData`. The shared sprite adapter now accepts resolved bitmaps and
frames directly. Its focused scoped-loading test passes; native confirmation
is pending the coordinated build.

The coordinated canonical `./run.sh build` succeeded. A new private D-Sides
import and 22-difficulty startup sweep then reached PlayState for 19 rows and
passed the strict no-diagnostic startup gate for 10/22, up from 4/22.
Bopeebo, Darnell, Dguy, Foolhardy, Fresh, Soretro, South, and Spookeez Hard
are among the clean rows. The complete current receipt is
`tmp/dsides-current-build22/result.json`; its protected installed files and
personal settings remained unchanged. This is startup coverage, not a
full-song or visual-source pass. The 12 failures include three stale camera
metadata rows, source-missing Dusk art and character definitions, shader
compilation, unsupported Codename modchart classes, Camera Modulo Change,
and Try Harder/Tutorial script or asset behavior. The post-sweep shared
`Paths.image` adapter now recognizes owner-scoped Animate and paged atlas
folders before `FunkinSprite.loadSprite`; focused path/sprite tests pass,
but this atlas fix has not yet had a native replay.

The first native replay after the `Paths.image` resolver change remained at
10/22 strict D-Sides startups. Inspection showed the private importer had
never staged the referenced Animate folders (`Animation.json` and
`spritemap1.*`) for `Paths.image` literals; only direct `.png` assets were
planned. The shared Codename importer now uses the same bounded atlas file
planner for `Paths.image` and `Paths.getFrames`. A focused non-overwriting
import/repair fixture stages a three-file Animate folder and passes. This
importer change still needs a canonical build and private native replay.

The Tutorial startup diagnostic showed a second shared parser gap: HScript
kept Haxe's single-quoted `'songs/$songName/lyrics.json'` literally. The
Codename parser now lowers simple single-quoted identifier interpolation
while leaving comments and double-quoted text intact. The exact mounted
`data/scripts/Lyrics.hx` executes its source path expression as
`songs/tutorial/lyrics.json` in the focused interpreter fixture; the five
Codename parser tests pass. Native confirmation is pending the same build.

The canonical build after both fixes passed. The next private 22-difficulty
D-Sides sweep improved strict startup to **11/22**. Owner Animate folders for
Blammed's end cutscene, Try Harder's RHYME, and Dusk's uberkid are now staged;
Dusk Hard passed. Blammed Hard's remaining startup failure is a fragment
shader compiler error, and Try Harder still has actor placement plus unsupported
`DiscordUtil`/`FlxTextFormat` imports. Tutorial's Haxe interpolation now
resolves to `songs/tutorial/lyrics.json`, but that JSON is not yet staged by
the importer; its startup remains a failure. Full receipt:
`tmp/dsides-current-build22/result.json`. Installed files and personal
settings stayed unchanged.

A further canonical build added bounded top-level song data sidecars to the
same Codename owner namespace. The focused importer/repair fixture now stages
`songs/demo/lyrics.json` without overwriting existing scoped files. In a
fresh private 22-chart D-Sides sweep, Tutorial's `lyrics.json` was present in
the selected namespace but strict startup remained **11/22** (19/22 reached
PlayState): its source uses a relative `Paths.getPath('songs/...')` key, while
the Codename asset facade only accepted an already resolved owner path. The
current receipt is `tmp/dsides-current-build22/result.json`; its owner tree
contains the JSON and its Tutorial process log records the failed relative
lookup. The shared asset facade now resolves owner-local relative paths and
exposes scoped text, bitmap, sound and existence methods. Its focused path
tests pass, but this follow-up has not yet had a successful canonical build
or native replay. A separate generic GLSL scalar-loop normalization now has
a focused fixture; its native shader result is also pending. Neither change
is counted as a runtime pass yet.

The coordinated build then passed, and the next protected private D-Sides
import/startup sweep reached PlayState for **21/22** difficulties and passed
strict startup for **12/22**. Blammed Hard now passes after generic float-bound
shader-loop promotion. Dad Battle Hard advances past its shader compile error
and now reports an unbound source `defaultCamZoom` in its stage callback.
Tutorial Hard advances past the relative `Paths.getPath` lookup and now reports
unbound `rainbow` and `speaker1` in its song callbacks. The source defines
`rainbow` before a top-level `importScript`, exposing a shared nested HScript
scope reset. A new inline-import interpreter path and live gameplay camera
globals have focused tests but still require another native replay. Receipt:
`tmp/dsides-current-build22/result.json`; live targets and user settings stayed
unchanged. The three section-based legacy charts lack camera sidecars, while
Endless, Monster, Pico, Try Harder and Improbable Outset retain distinct script,
placement, event or missing-source blockers.

On that same release binary, the private default-settings Rabbit Hole Normal
full-song run reached its natural 159,566 ms ending, dispatched 592/592 events,
logged no tagged interpreter errors, and exited zero. Receipt:
`tmp/example-full-playthrough-rabbit-hole-shader-current.jsonl`. The bounded
HXC shader callback matcher recognizes the mounted source body and rejects an
extra camera mutation in its focused fixture. Its shader gate remains false
under the default option; the companion option screen and visual shader-on
behavior still require implementation and native source comparison, so this
full-song result is a strict runtime pass, not complete source parity.

The next shared Codename importScript change preserves the parent's live
interpreter scope and keeps imported callbacks alongside the parent's
callbacks. A focused extracted HScript test exercises a variable declared
before an inline import and a callback declared afterward. The canonical
build passed. In another private complete D-Sides startup sweep, Tutorial
Hard's own `postCreate` and imported Lyrics callbacks both ran without tagged
errors; it now passes the strict startup gate. Dad Battle Hard remains a strict
pass. The result is **14/22 strict startup passes, 21/22 PlayState starts**
with live files and options unchanged. Eight rows still fail: Blammed Easy
and Normal plus Bomb Bash Hard lack source-accurate camera metadata for
section-based charts; Endless and Monster need Codename modchart/placement
behavior; Improbable Outset has unresolved owner character/stage dependencies;
Pico needs Camera Modulo Change; and Try Harder has placement and import
binding gaps. This is still startup coverage only. Receipt:
`tmp/dsides-current-build22/result.json`.

The shared legacy section-chart converter now emits the three source parser
camera line slots with original character IDs, positions, order and girlfriend
visibility. A focused extracted Haxe fixture covers the general rules and
the mounted Blammed Easy/Normal charts. The canonical `./run.sh build` passed.
The first private D-Sides replay reused a prior disposable import and therefore
still held its old camera sidecar; it is excluded as evidence for the importer
change. After regenerating that overlay, the new Blammed sidecar contained
Easy, Hard and Normal, and Bomb Bash contained Hard. The protected private
22-chart sweep still reported **14/22 strict startup passes and 21/22
PlayState starts**. Blammed Easy and Normal now explicitly report their three
unresolved source character IDs (`pico-dark`, `bf-dark`, `gf-dark`); no matching
character definition was found under the mounted D-Sides donor. Bomb Bash
then reached stage callback loading but crashed. The sweep verified unchanged
live targets and options. Receipt: `tmp/dsides-current-build22/result.json`.

An offscreen GDB replay under the runtime lock traced Bomb Bash's crash to
`FlxCamera.focusOn` called from HScript with the donor's `camFollow` FlxObject.
The shared interpreter now passes that object's position into Flixel's typed
camera API. A focused HScript fixture exercises the conversion; the next
canonical `./run.sh build` passed. A targeted private Bomb Bash Hard replay
reached `playstate_ready`, had no tagged compatibility errors, exited zero,
and retained live files and options unchanged. Receipt:
`tmp/dsides-current-build22/bomb-bash-camera-focus-result.json`; debugger log:
`tmp/dsides-current-build22/bomb-bash-gdb.log`. A new full-sweep count and
full-song source comparison remain outstanding.

The bounded HXC shader adapter still rejects seven mounted countdown callback
bodies with source operations beyond its exact Rabbit Hole matcher:
`clubroomfestival`, `dokiglitcher`, `evilClubroom`, `evilClubroomSayo`,
`glitcher-monika-mix`, `markov-lyrics` and `wilted`. The 228-file mounted
corpus inventory and selected auto-import aggregate tests pass with these
warnings pinned; five selected callbacks produce the body diagnostic. These
are explicit unsupported cases, not verified shader behavior.

After updating the isolated Haxe interpreter fixture for the camera object
type, the repository's parallel full suite passed: **1,124 tests across 309
modules, 61 skipped, zero failed**. Log:
`tmp/example-compat-fullsuite-camera-focus-rerun-20260924.log`. The preceding
run had one fixture-only failure and is not the final suite result.

On that build, another protected private D-Sides import and 22-chart startup
sweep reported **15/22 strict startup passes and 22/22 PlayState starts**.
Bomb Bash Hard passed inside the complete sweep after the camera call adapter.
The seven failing rows are Blammed Easy/Normal (missing donor `pico-dark`,
`bf-dark`, `gf-dark` definitions), Endless Hard (modchart interpreter/API),
Improbable Outset Hard (selected-owner camera/`gfgrunt` dependency), Monster
Hard (stage placement/modchart), Pico Hard (`Camera Modulo Change`), and Try
Harder Hard (stage placement/script bindings). The run verified protected live
targets and personal options unchanged. Receipt:
`tmp/dsides-current-build22/result.json`. Startup status does not establish
natural endings or visual parity.

Bomb Bash Hard then passed a protected offscreen full-song check at 5×: the
171,089 ms instrumental reached its natural ending, all **336/336 merged
events** dispatched, and the native chart retained all **564/564** source
note rows. There were no tagged interpreter errors, and personal options
remained unchanged. This establishes one full-song runtime pass; source frame,
audio mix, pause/seek and editor parity still need direct comparison. Receipt:
`tmp/dsides-current-build22/bomb-bash-full-song-result.json`.

A separate protected offscreen full-song batch ran the other **14** D-Sides
startup passes on the same compiled build at 5× with botplay and default test
options. All 14 reached one natural ending without a native crash, and every
imported chart retained its source note-row count. DGuy, Ghastly, and Philly
Nice had all authored events dispatched and no tagged interpreter errors;
including the prior Bomb Bash run, this build had **4/15** strict full-song
passes among charts that passed startup. The other runs exposed ten tagged
unsupported-event diagnostics across Blammed, Bopeebo, Dusk, Foolhardy, Fresh,
South, Spookeez, and Tutorial: `Camera Modulo Change`, `BPM Change`,
`Time Signature Change`, and `Alt Animation Toggle`. Dad Battle, Darnell,
Soretro, Blammed, and Tutorial also had **52** events authored after the
instrumental ended (1, 2, 5, 1, and 43 respectively). A timestamp audit found
**zero reachable merged chart events missed**; it does not treat those late
source-authored rows as executed or establish source visual/audio parity.
The raw conservative result and timing audit remain at
`tmp/dsides-current-build22/full-playthrough-result-raw-before-timing-audit.json`
and `tmp/dsides-current-build22/full-playthrough-timing-audit.json`. Protected
live imports and personal options remained unchanged. Shared timing, camera,
and alternate animation handling is now being integrated; this batch predates
those changes.

The next canonical `./run.sh build` passed with the shared Codename camera
modulo/tempo map and alternate-animation event path. A new protected offscreen
five-chart full-song batch at 5× passed **Dusk Hard, Bopeebo Hard, Fresh Hard,
Tutorial Hard, and South Hard**: each reached a natural ending, dispatched all
events whose timestamps preceded that ending, and emitted no tagged
interpreter errors. This exercises two Dusk `BPM Change` rows plus its
`Alt Animation Toggle`, two Bopeebo `Time Signature Change` rows, five Fresh
`Camera Modulo Change` rows, three Tutorial alternate-animation toggles, and
one South BPM change. Tutorial dispatched 214/257 authored events; the other
43 are timestamped after its audio ends and remain recorded rather than
claimed as executed. The batch verified protected live targets and personal
options unchanged. Receipt: `tmp/dsides-current-build22/shared-events-replay-result.json`.
These are runtime event checks, not source visual/audio parity: Codename's
cancelable camera-bop hook, zoom multiplier/cap settings, and non-four-step
legacy beat callbacks remain unimplemented or unverified.

A second protected offscreen full-song batch on the same new binary passed
**Foolhardy Hard, Spookeez Hard, and Blammed Hard** with natural endings and
no tagged interpreter errors. Foolhardy dispatched 124/124 events, Spookeez
332/332, and Blammed 257/258; Blammed's sole remaining Focus Camera event is
authored after its instrumental ends. Live imports and personal options were
unchanged. Receipt: `tmp/dsides-current-build22/camera-tempo-replay-result.json`.

A third protected offscreen full-song batch on the new binary passed **Pico
Hard, Dad Battle Hard, Darnell Hard, and Soretro Hard** with natural endings,
no tagged interpreter errors, unchanged live imports/options, and no reachable
event missing. Their dispatched/authored counts were 76/76, 403/404,
131/133, and 343/348 respectively; the one, two, and five undispatched rows
in the last three charts are all authored after their instrumentals end.
Pico's earlier strict startup failure was the now-supported Camera Modulo
Change event, and this run exercised its full-song path. Receipt:
`tmp/dsides-current-build22/remaining-playthrough-replay-result.json`.
Across the three refreshed batches, twelve distinct D-Sides chart
difficulties have a new-build full-song runtime pass. Bomb Bash, DGuy,
Ghastly, and Philly Nice passed on the immediately preceding build and still
need replay on this timing build; the six remaining D-Sides difficulties have
startup/source dependency blockers. These runtime passes do not establish
rendered source parity, editor round trips, pause/seek behavior, or repeat-load
safety.

After separating delayed `songEvents`/`stepHit` actor writes from startup
placement in the shared scanner, another canonical `./run.sh build` passed.
The first fresh protected private D-Sides import on that binary exited with
SIGSEGV (`-11`) after `import_start`, before a success marker; process log:
`tmp/dsides-current-build22/dsides-full-native-preview-full-import.process.log`.
A second fresh import under offscreen GDB, with the game's native library path
set, completed normally: **20 imported, zero failed**, with 826 scoped assets
copied. Its debugger trace is
`tmp/dsides-current-build22/import-gdb-backtrace.log` and marker log is
`tmp/dsides-current-build22/import-gdb.markers.jsonl`. The different outcome
makes the import crash an unresolved intermittent stability defect; it is not
counted as fixed. The subsequent importer pass skipped the already imported
files and exited cleanly.

On that successful private import, the complete **22-chart startup sweep
passed 16/22 strict checks; all 22 reached PlayState**. Pico Hard now passes
with Camera Modulo Change handled. Blammed Easy/Normal still report their
unresolved dark character IDs. Endless Hard still requires the real pinned
FunkinModchart rendering dependency and adapter. Improbable Outset Hard still
fails on the old binary's qualified-owner source-ID/character lookup despite
its private source files existing. Monster Hard retains a `postCreate`
startup placement mutation and its real modchart dependency. Try Harder Hard
no longer reports unsupported initial placement; only `DiscordUtil` and
`FlxTextFormat` script import bindings remain at startup. The scan records
Try Harder's later `songEvents` mutation separately and does not claim runtime
placement parity. Live imported targets and personal options were unchanged.
Receipt: `tmp/dsides-current-build22/result.json`; preceding startup receipt:
`tmp/dsides-current-build22/result-before-stage-placement-refresh.json`.

The next canonical build added selected-owner source-folder resolution and
shared Codename script bindings. In protected private startup checks,
**Try Harder Hard passed** with no tagged diagnostics. Improbable Outset Hard
still reached PlayState but failed strict startup because the stage resolver
used its display title instead of its qualified chart folder, and its donor
stage script constructed an asset key with two adjacent slashes. Its Camera
Movement diagnostic followed the missing stage/actor runtime. Receipt:
`tmp/dsides-current-build22/qualified-bindings-startup-result.json`.
The selected-owner stage resolver and scoped path normalization have since
been changed and pass focused interpreter checks; native verification is
pending the next build.

On the owner-and-binding build, protected offscreen 5× full-song replays passed
**Try Harder, Bomb Bash, DGuy, Ghastly, and Philly Nice Hard** with natural
endings, source-matching note counts, no tagged script errors, and no reachable
chart event missed. Try Harder dispatched 657/658 source events; its last
authored row is after the instrumental ends. The other four dispatched all
authored events (336, 733, 465, and 302). Protected live imports and personal
options were unchanged. Receipt:
`tmp/dsides-current-build22/new-full-songs-result.json`. Combined with the
earlier twelve same-generation runs, **17 distinct D-Sides chart difficulties**
have a current full-song runtime pass. This is still short of rendered source
parity, editor round trips, pause/seek checks, and repeat-load safety.

The intermittent fresh-import SIGSEGV was examined in the retained compact
core backtrace at `tmp/dsides-current-build22/import-failure-46993-bt.log`.
The worker was in `CoolUtil.stringifyJson` -> TJSON -> hxcpp `IsInt` with an
invalid `Dynamic` object pointer. The backtrace identifies neither the chart
nor the earlier corruption; malformed donor JSON alone does not explain this
failure site. A later debugger-slowed retry succeeded, so the crash remains
unresolved. The next build logs the source chart, difficulty, and destination
immediately before each serialization, and a separately prepared private
overlay will be used for the next retry. The exported 844 MB diagnostic core
was removed from `tmp/` after preserving its compact backtrace.

The first full Python suite after the owner/binding build ran **1,130 tests in
311 modules, with 61 skipped and two failures**. Both failures were stale
standalone interpreter fixtures: one lacked the new authored animation suffix
field on its mock `Note`, and one pulled in the production `Song` module after
the owner lookup began calling `Song.storageFolder`. Both fixture repairs
passed their focused tests; a complete rerun is pending after the stage/path
build.

The next canonical `./run.sh build` passed after shared stage-manifest and
scoped-path changes. A targeted startup on the existing private overlay
cleared Improbable Outset's missing-stage and Camera Movement diagnostics,
but its stage script still could not load an existing donor fog image because
the importer had not staged the asset behind a concatenated key containing
adjacent slashes. `HxcAssetPlanner` now normalizes those repeated separators
in bounded static `Paths.*` references before the selected-owner copy plan;
the leading slash remains visible to the importer's safety check. The focused
planner test resolves the real expression shape and retains an absolute-key
sentinel for the downstream safety check.

After another canonical build, a **fresh, separately prepared private D-Sides
import passed: 20 songs imported, zero failed, 827 scoped assets copied**.
All 22 source chart serialization starts were recorded, and the newly staged
`images/stages/tricky/tricky_fog.png` is present in the selected owner. The
offscreen Improbable Outset Hard startup then passed strict checks with no
tagged diagnostics, and its 5× full-song replay reached a natural ending with
946/946 notes, 109/109 events dispatched, and no interpreter errors. The
protected live import targets and personal options stayed unchanged. Receipts:
`tmp/dsides-import-crash-probe/result.json`,
`tmp/dsides-import-crash-probe/improbable-startup-result.json`, and
`tmp/dsides-import-crash-probe/improbable-full-result.json`. **18 of 22 D-Sides
difficulties** now have both strict startup and full-song runtime passes
across private owner overlays; this still does not prove rendered/audio parity
or seek, pause, editor, repeat-load and cross-owner transitions. The four
remaining strict failures are Blammed Easy/Normal (unresolved dark character
IDs in the donor), Endless Hard (real FunkinModchart dependency), and Monster
Hard (initial `postCreate` placement plus the same dependency).

The complete Python suite after the stage/path build passed 1,129 tests and
failed one of 1,130: the mounted HXC native scanner audit process exited 245
after source-root discovery. This is the previously recorded intermittent
scanner allocator defect, not evidence of a chart mismatch. Its latest log is
`tmp/dsides-current-build22/fullsuite-stage-path.log`. A subsequent full-suite
rerun on the asset-planner source state is still required.

A second separately prepared D-Sides importer retry on the same asset-planner
build also completed: 20 imported, zero failed, 22 chart serialization starts,
and unchanged protected live files/options. Receipt:
`tmp/dsides-import-crash-probe/retry2/result.json`. The retry's disposable
overlay was removed after its receipt was saved. Two successful fresh retries
do not erase the earlier worker SIGSEGV.

The latest HXC scanner failure has a retained systemd core (PID 71145). It
faulted in hxcpp `GlobalAllocator::MarkAll` while dispatching through an
invalid object vtable; `Path.normalize` on the stack triggered allocation and
collection but is not proved to have corrupted the object. An older allocator
core showed a duplicate large-recycler pointer, but the two failures are not
proved to share one cause. The next discriminator is the alleged object's
allocation/page metadata and its mark-queue entry in that retained core,
before changing importer path logic or treating a passing retry as a fix.

Read-only inspection of that core's hxcpp metadata narrowed the failure:
the bad address was the entry just popped from `MarkAll`'s work chunk, inside
a registered 32 KiB GC block, but its allocation-start bitmap does not mark
the address as an object start. Its first word is the invalid dispatch target
seen at the fault. This favors a malformed/non-live queued pointer or
corrupted start metadata over a valid object whose header was merely changed;
it does not identify the write or queue insertion that introduced it.

The complete suite rerun on the asset-planner build passed **1,131 tests across
311 modules, 61 skipped, zero failed** in 185.0 s. The mounted HXC scanner
passed this run, but its retained prior GC-marking core remains an unresolved
intermittent defect. Log: `tmp/dsides-current-build22/fullsuite-asset-planner.log`.

Two protected same-process offscreen transitions between D-Sides' qualified
Improbable Outset Hard and Vs Tricky's existing canonical Improbable Outset
Hard passed in both directions. Each run recorded both selected chart visits,
destroyed the first PlayState before the second was ready, and emitted no
tagged interpreter errors. The disposable options, protected live imports,
and personal settings were unchanged. Receipt:
`tmp/dsides-import-crash-probe/cross-owner-result.json`. This checks owner
selection and early teardown across imports; it does not cover full-song
endings for the Vs Tricky chart or repeated seek/pause sequences.

A same-process repeated load of the selected D-Sides Improbable Outset Hard
also passed two ready visits with first-state destruction, no tagged script
errors, and unchanged protected files/options. Receipt:
`tmp/dsides-import-crash-probe/repeat-result.json`. The superseded first
D-Sides private runtime overlay was removed from `tmp/`; receipts and logs
remain. Repeated load does not by itself prove pause, seek, or cutscene-skip
behavior.

The current canonical binary passed all ten selected **offscreen, default
settings, bounded startup** rows for the named Expurgation, Wacky World
Hard/Nightmare, Rabbit Hole, Fantasy Girl 01, VS Freddy, Ballistic, Future
Sound, Resonance, and Cursed Expurgation regressions. The smoke harness
reported ten startup/PlayState/success marker passes and zero failures;
receipt: `tmp/dsides-current-build22/named-regression-smoke.log`. These five
second launches do not replace source visual/audio comparison or full-song
event, ending, pause and skip checks. TAKEDOWN still has no chart or matching
file in the mounted donor/archive/runtime inventory.

A read-only preflight against the current live export checked the selected
owner manifest, source note-count expectation, chart parse, and real
instrumental for all 177 imported-package chart rows. **156 rows are ready
for a native full-song gate and 21 are blocked before launch**; the blocked
rows include 15 stale/missing live D-Sides variants, three absent PERFEXION
outputs, plus one each for bully-mod, the empty `baka` variation key, and
FNAS. Receipt: `tmp/live-package-full-preflight.json`. This snapshot does not
include the separate 78-row Psych source archive, and readiness is not a
gameplay or source-parity pass. The private D-Sides and FNAS results above do
not overwrite this live-export count.

The installed Modding Plus VS Freddy package then passed **9/9 distinct
chart difficulties** across Fired, Let Us In, and Slaughter in private Xvfb
5× practice/botplay natural-ending runs. Every selected chart had a matching
owner, source note count and instrumental before launch; every game run
emitted exactly one native song-end marker with all chart events dispatched,
and the process logs contained no tagged interpreter errors. Receipt:
`tmp/modding-plus-full-result.jsonl` (summary: 9 passed, zero blocked or
failed). The repository and live options SHA-256 digests exactly matched the
saved `tmp/modding-plus-settings-before.json` values afterward. These runs
do not yet establish rendered sprite/placement, dialogue, editor, pause,
seek, menu or source audio-mix parity.

A source/runtime file audit found a concrete visual ownership gap behind those
passes: the selected VS Freddy owner has no character atlas namespace, so
`bf-dark` and `gf-dark` resolve from the merged global registry. Their donor
atlases have 496 and 252 named frames, while the current shared runtime
atlases have 299 and 55. The other five referenced character atlases and the
six song stems compared byte-identically; stage scripts/assets also match
under the selected owner. The donor `monster` cutscene script differs from
the shared runtime copy, and direct song smoke bypasses Story Menu, the
Slaughter cutscene, and Let Us In dialogue. Receipt:
`tmp/vs_freddy_source_audit.md`. A shared owner-qualified character fix and
Story/menu visual verification are required before calling the package
compatible.

The Psych Bruce hotfix passed the exact-owner/chart/audio preflight for all
three Normal charts, and each private Xvfb run reached natural ending with
all chart events dispatched (0/0, 383/383, and 402/402). **All three strict
gates failed**, however: the stage translator reports unsupported
`setPosition()` and `fpSong()` calls, then `stage.start` raises
`EUnknownVariable(dadOpponent)`. The mounted package defines those names only
in `stages/nullspace.lua`; its bundled Psych v0.2.8 source provides no
definition for either `dadOpponent` or `fpSong`. Thus the source's own required
stage API remains unidentified and rendered parity cannot be inferred from
the song endings. Receipt: `tmp/bruce-hotfix-full-result.jsonl` (zero passed,
three failed). No donor script or live stage was rewritten to mask the gap.

All three HL17 Buck charts passed the installed-runtime 5× natural-ending
gate with their 126/126, 120/120, and 5/5 chart events dispatched and no
tagged interpreter errors. Receipt: `tmp/hl17-full-result.jsonl`. The static
source audit, `tmp/hl17_source_audit.md`, establishes that these are **not
source-parity passes**: the selected owner lacks three referenced videos,
two shaders, three fonts, `data/global.hx`, and its `data/states` scripts,
although most of those copy paths exist in the current shared importer.
It also lacks the source's private `Bopper` class library, and its
`Flx3DView`/Away3D stage callback is recorded as unsupported by the camera
sidecar. The source-created 3D plane and its camera/cleanup behavior cannot
be inferred from note and event totals. The shared Codename asset facade and
literal importer now accept owner-scoped `Paths.obj` model references; the
standalone path and scoped-copy tests passed. A private owner refresh and
full stage/script/video verification remain required.

The current canonical binary also passed all **10/10 Vs Tricky chart
difficulties** in private Xvfb 5× practice/botplay natural-ending runs:
Expurgation Hard, Hellclown Easy/Normal/Hard, Improbable Outset
Easy/Normal/Hard, and Madness Easy/Normal/Hard. Every selected chart passed
owner/chart/audio preflight, emitted one natural song-end marker with all
events dispatched, and had no tagged interpreter error. Receipt:
`tmp/vs-tricky-full-result.jsonl`. Expurgation's 126/126 event check and
193.073-second source duration specifically pass this strict runtime gate.
This does not establish equivalent sprites, cameras, cutscenes, menus,
editor results, or behavior at 60/240/480 FPS; earlier source parity gaps
remain open.

Wacky World UPDATE's Normal, Hard, and Nightmare charts likewise passed
**3/3** selected-owner/chart/audio preflights and strict private Xvfb 5×
natural-ending runs, with all dispatched chart events and no tagged
interpreter errors (`tmp/wacky-current-full-result.jsonl`). These runs do
not close the reported visual/audio issue or validate its cutscene, menu,
editor, and pause/seek behavior against the source package.

The new canonical build and private import previews add two distinct owner
checks. A fresh HL17 import under `tmp/hl17-refresh-preview/runtime-overlay`
restored the previously stale owner videos, shaders, fonts, global/state
scripts, and `models/plane.obj`; its three chart manifests selected that
owner, and protected installed bytes were unchanged. A fresh VS Freddy import
under `tmp/vs-freddy-refresh-preview/runtime-overlay` copied donor-identical
`bf-dark`/`gf-dark` PNG and XML atlases plus its cutscene registry and
`monster.hscript` into the selected owner, without changing protected installed
bytes. Receipts: the respective `result.json` files in those directories.
These are import/materialization results, not story or rendered parity.

The private HL17 full-song test initially produced misleading missing-character
logs because the test overlay symlinked owner media outside the game's allowed
working directory. The offscreen matrix now copies the selected owner's media
into the disposable runtime; the full-song gate also rejects explicit missing
scoped assets. A corrected Gordonteen Bucks run found zero missing scoped
assets and reached its natural ending, but **failed the strict gate with eight
unsupported source imports** from its 3D stage and song script, including
`Flx3DView`, Away3D geometry/lens classes, and Codename `Options`. Receipt:
`tmp/hl17-refresh-preview/gordon-owner-materialized.jsonl`. The earlier 3/3
HL17 ending result remains an ending/event observation, not a clean
compatibility pass.

The rebuilt game passed an actual private Xvfb Escape/Return pause and resume
sequence on Fired Normal with the repository default settings: it emitted one
pause and resume marker, stopped music during pause, held its music clock, and
continued afterward. Receipt: `tmp/fired-pause-resume-result.json`. This is
one chart's native pause path; it does not cover every owner script or seek.

A subsequent private Story-mode native check launched Slaughter Normal from
the freshly imported VS Freddy owner with default test settings. The donor's
`monster.hscript` emitted its `wink` and `help` traces once, handed off to a
real `song_start` marker with music playing, and produced no missing-donor
dependency diagnostic. The gameplay visual snapshots showed the owner's
`bf-dark` and `gf-dark` atlases at **496 and 252 frames**, matching the donor
frame counts rather than the former shared 299/55-frame atlases. Receipt:
`tmp/vs-freddy-refresh-preview/story-result.json`. This validates one Story
intro and character load; dialogue, skip, source frame placement over time,
menu transitions, editor round trips, and all nine refreshed difficulties
still need direct verification.

After the shared owner and test-overlay changes, the current canonical
`./run.sh build` completed. The full parallel Python suite passed **1,135
tests across 314 modules, 61 skipped, zero failed** in 206.9 seconds;
`tmp/example-mods-fullsuite-story-final.log` is the receipt. Repository and
live-export `options.json` SHA-256 values still match the pre-run saved
values in `tmp/modding-plus-settings-before.json`.

All **9/9 VS Freddy difficulties passed again from the fresh private import**
under default offscreen settings, at 5× audio rate. Fired, Let Us In, and
Slaughter each passed Easy/Normal/Hard selected-owner/chart/audio preflight,
natural ending, complete event dispatch, and the tagged error gate; receipt:
`tmp/vs-freddy-refresh-preview/full-playthrough.jsonl`. Let Us In Easy's
native snapshot selected the donor's 496-frame `bf-dark` and 252-frame
`gf-dark` atlases. A scoped live refresh then checked all three installed
manifests, found 38 absent and zero conflicting owner files, backed up any
preexisting owner trees, copied only those missing character/cutscene files,
and found both personal and seed options hashes unchanged. Receipts:
`tmp/vs-freddy-refresh-preview/live-refresh-plan.json` and
`live-refresh-result.json`. This updates the installed owner; source parity
for dialogue, skip, menu, editor and frame placement remains open.

An independent private-Xvfb Story launch against the **installed runtime
after the scoped refresh** also passed: Slaughter's owner script emitted its
intro traces, produced a real `song_start` with music playing, and had no
missing-owner diagnostic. Receipt:
`tmp/vs-freddy-refresh-preview/story-live-result.json`.

The Codename importer now discovers the selected owner's flat character
definition directory as well as chart-listed IDs, with a 512-entry limit and
root-bound path checks. A fresh private HL17 import copied 194 assets, kept
all protected installed bytes unchanged, and staged 18 character XML files,
the `source/Bopper.hx` class, its literal atlas dependencies, and the model
asset. Receipt: `tmp/hl17-character-preview/result.json`. The executable
private class is still unavailable; staging its source and media does not
provide its runtime behavior. The detached Codename `Options` facade and
shared `executeEvent` callback route passed their focused Haxe/HScript tests,
and `./run.sh build` completed after these changes; receipts:
`tmp/example-mods-character-diagnostic-build.log` and the focused test logs
in the full suite below.

On the refreshed private owner, Gordonteen Bucks now constructs its
script-created characters without the former false missing-character
diagnostics and dispatches its script-created camera event without an
`executeEvent` error. All three HL17 Buck charts reached natural endings
with **126/126, 120/120, and 5/5 events**, but **0/3 passed the strict
compatibility gate**. Every chart still reports six unsupported Flx3D,
Away3D, and OpenFL 3D-stage imports. Huggyteen Dollars additionally reports
unsupported `FlxKey` and private `Bopper` imports; Linkinteen Parks reports
`Bopper`. Receipt: `tmp/hl17-character-preview/all-charts-final.jsonl`.
These are explicit source-behavior blockers, including the 3D stage render
and private class choreography. No chart or donor file was edited to hide
them.

The native full-song harness now waits five real seconds after song end and
exit from `PlayState`, keeping its original deadline for delayed Story
transitions. Wacky World Normal reached 153.767 seconds of source audio,
dispatched all 106 events, emitted no tagged error, and exited five seconds
after its natural ending. Its previous bounded run waited about 38 seconds
after song end. Receipt: `tmp/wacky-fast-end-result.jsonl` and the native
`tmp/runtime-smoke/logs/0-wacky-world-wacky-world.log`. This checks an
immediate teardown window, not later menu or source visual parity.

After the character diagnostic change, the final parallel Python suite
passed **1,138 tests across 315 modules, 61 skipped, zero failed** in
192.5 seconds (`tmp/example-mods-fullsuite-character-diagnostic-final.log`).
`git diff --check` passed. The SHA-256 digests of both the repository seed
and installed personal `options.json` still match
`tmp/modding-plus-settings-before.json`; the scoped live VS Freddy dark
atlases and `monster` cutscene script remain present after the last build.
The three private import runtime overlays were removed after verification;
receipts and logs remain under `tmp/`, with the cleanup record at
`tmp/example-mods-preview-cleanup.json`.

## Psych Ballistic family, 25 September 2026

An exact-source audit of the mounted `psych/vswhitty` package compared all
twelve standard, beta, HQ and remix Ballistic charts (Easy/Hard/Normal). The
imported charts retain their source note arrays, event arrays and checked
stage/character/BPM/speed fields. All 29 checked source/runtime files are
byte identical: the four songs' instrumental and vocal tracks, their scripts
and available dialogue/event sidecars, both stage Lua/JSON pairs, four global
Lua scripts and their readme, and the HQ death/rumble sounds. Receipt:
`tmp/vswhitty-ballistic-source-audit.json`.

The shared Psych stage translator now routes literal GameOverSubstate
death/loop/end sound choices into song-local state; playback resolves the
selected owner's sound or music asset when the corresponding game-over action
runs. The shared Lua sound bridge retains tagged `playSound` effects for
`soundFadeOut`, `soundFadeIn` and `stopSound`, and stops them at PlayState
teardown. The HQ intro previously reported `soundFadeOut` as unknown; the
current native replay no longer does. The private offscreen input driver can
press Accept at bounded intervals until the real `song_start`, allowing the
HQ script's timed cinematic and multiline dialogue to advance. This input
stops before gameplay and never changes the default test options. Focused
tests, canonical `./run.sh build` and the full parallel suite passed; the
suite receipt is `tmp/example-mods-fullsuite-tagged-sound-final.log`:
**1,140 tests across 316 modules, 61 skipped, zero failed**.

On that same final binary, all **12/12 Ballistic family difficulties passed**
the strict private-Xvfb 5× practice/botplay full-song gate. Every run reached
one natural `song_end`, dispatched every recorded event and logged no tagged
interpreter error; disposable options remained unchanged. Standard and beta
used the secondary-key intro skip; HQ advanced its source dialogue via Accept;
remix required no input. Standard/beta/remix had 16/16 events per difficulty;
HQ had 82/82. Receipts:
`tmp/vswhitty-ballistic-standard-beta-final.jsonl`,
`tmp/vswhitty-ballistic-hq-easy-tagged-result.jsonl`,
`tmp/vswhitty-ballistic-hq-rest-result.jsonl`, and
`tmp/vswhitty-ballistic-remix-result.jsonl`. The HQ game-over override is
compiled, owner-resolved and covered by focused source tests, but actual
game-over playback was not triggered in this batch. These results do not yet
compare source rendering, audio mix, character/camera placement over time,
editor round trips, all menu paths, pause/seek or cross-owner transitions.

A separate read-only pass over all 47 installed vswhitty chart difficulties
found their source notes and event arrays intact, but 37 imported charts
replace the donor's authored `song` title with a normalized storage key. For
example, the source `Ballistic (HQ)` becomes `ballistic-(hq)`. The chart title
feeds gameplay title text and script `curSong`, so this is a known source
identity discrepancy even in Ballistic's 12 passing full-song rows. Receipt:
`tmp/vswhitty-all-chart-source-audit.json`. A format-level importer/runtime
title-storage split and owner-scoped, backed-up refresh are required before
claiming source-matching presentation or script identity.

The next eight vswhitty full-song attempts reached natural endings, but all
failed the strict gate on one explicit `4chan.lua` diagnostic:
`GameOverSubstate.characterName` was unsupported. The attempt's repeating
Accept input also correctly sent no key because these songs reached
`song_start` before the first interval; requiring a delivery marker was a
test-harness false failure. The shared stage translator and PlayState now
carry Psych's game-over character name per song, and GameOverSubstate selects
that actor on death. The full-song harness records whether optional Accept
was delivered without failing a song that started on its own. On the rebuilt
binary, **8/8 Faucet/Faucet HQ/Hungry/Hungry HQ difficulties passed** natural
endings with no tagged interpreter errors: both Faucet charts dispatched 0/0
events, Hungry's three charts 23/23, and Hungry HQ's three 61/61. Receipts:
`tmp/vswhitty-faucet-hungry-result.jsonl` (original failures) and
`tmp/vswhitty-faucet-hungry-gameover-final.jsonl` (fixed replay). Actual
game-over actor/audio playback remains to be triggered natively.

The Psych importer now retains a safe source `song` title while native chart,
script and audio lookup uses the selected storage folder. It writes
`compatPreserveSongTitle` so the gameplay HUD keeps authored punctuation and
case. A protected fresh import of the exact mounted vswhitty root passed all
**47/47** chart comparisons for title, notes, events, and selected owner,
without changing installed charts or options. Private HQ Normal then reached
`song_end` with runtime identity `Ballistic (HQ)`, 82/82 events and no script
error. Receipts: `tmp/vswhitty-title-preview/result.json` and
`hq-normal-playthrough.jsonl`. A title-only refresh then checked the 47
source, private and installed chart payloads and owner manifests, backed up
all 47 installed charts under `tmp/psych-title-backups/`, changed only their
`song` title and preservation flag, and left both options digests unchanged.
Plan and receipt: `tmp/vswhitty-title-preview/live-refresh-plan.json` and
`live-refresh-receipt.json`. Installed HQ Normal and Faucet HQ passed again
after the refresh, with source song identities `Ballistic (HQ)` and
`faucet (hq)` in the native end marker. Receipts:
`tmp/vswhitty-title-preview/hq-normal-live-after-refresh.jsonl` and
`faucet-hq-live-after-refresh.jsonl`. The rest of the 47 difficulties still
need replay on the refreshed charts before a current-build package claim.

The first complete suite after the Psych title change found six stale
extraction/assertion fixtures; after updating them, one mounted audit still
expected normalized Psych titles. That audit now independently expects the
source title only when its value is a safe import identity. The next full
suite reached 1,144 tests with a single known intermittent HXC scanner exit
250 immediately after `ROOTS=16`, before chart comparison. A full retry on
the same source passed **1,144 tests across 317 modules, 61 skipped, zero
failed** in 181.0 seconds. Receipts:
`tmp/example-mods-fullsuite-psych-title-fixtures-final.log` and
`tmp/example-mods-fullsuite-psych-title-fixtures-retry.log`. The passing
retry does not identify or clear the scanner's intermittent allocator defect.

The first refreshed-title Lo-Fight/Low-Rise batch ran twelve difficulty rows
to natural endings. Lo-Fight and Lo-Fight HQ Easy/Hard/Normal plus Low-Rise
Easy/Hard/Normal (**nine rows**) failed the strict gate on the same explicit
missing `bfwhit` character and health icon dependency. An exact-name audit
found 15 chart references to `bfwhit` and one to `bf-santa`; neither character
definition appears in the mounted vswhitty package, the Psych source archive,
or the installed custom-character registry. Receipt:
`tmp/vswhitty-character-source-dependencies.json`. No donor asset or chart
was substituted. The other three Low-Rise HQ rows exposed a separate shared
translator omission: literal `setProperty('moonlight2.alpha', 0.4)` from the
source `better-hqr3.lua` was diagnosed and dropped. Static stage conversion now
retains numeric alpha on known stage sprites and continues to diagnose unknown
tags or dynamic values. Focused Haxe tests and canonical `./run.sh build`
passed (`tmp/example-mods-psych-stage-alpha-build.log`). On that build,
**Low-Rise HQ Easy/Hard/Normal passed 3/3** strict natural endings with 92/92
events each and no tagged interpreter errors; receipt:
`tmp/vswhitty-lowrise-hq-alpha-final.jsonl`. The first-failure batch is
`tmp/vswhitty-lofight-lowrise-refreshed.jsonl`. Remaining vswhitty rows are
still being replayed, and actual game-over playback is still unverified.

The next refreshed-title batch covered all six Overhead and all nine
Underground difficulties. Every row reached its natural ending with complete
event dispatch. Overhead standard had 79/79 events and HQ had 81/81, but all
six failed the strict gate on the exact missing `bfwhit` character and icon.
All nine Underground rows initially failed only on an undefined Psych
`removeLuaScript` callback in their source song scripts: two calls per
standard/HQ difficulty and one per in-game mix difficulty. The shared bridge
now resolves the requested Lua path inside the selected owner, permits the
current chart's copied song script to remove an owner stage script, closes
every live matching interpreter while leaving its created stage objects, and
clears the active identity for later reload. A separate interpreter-instance
check prevents a stale path from closing a different stage after a stage swap
reuses the `stage` scope. Focused extract-and-interpret tests cover duplicate
removal, reloading, cross-owner rejection, static stage callback closure and
scope reuse. The first-failure receipt is
`tmp/vswhitty-overhead-underground-refreshed.jsonl`.

On the first removal build, **9/9 Underground difficulties passed** the
strict private-Xvfb 5× natural-ending gate: standard 180/180, HQ 208/208 and
in-game mix 166/166 events on each Easy/Hard/Normal chart, with no tagged
interpreter errors. The later scope-safe build also passed in-game mix Easy at
166/166. Receipts: `tmp/vswhitty-underground-remove-lua-final.jsonl`,
`tmp/vswhitty-underground-scope-final-check.jsonl`,
`tmp/example-mods-psych-remove-lua-build.log`, and
`tmp/example-mods-psych-remove-lua-scope-build.log`. This checks gameplay
event dispatch and interpreter diagnostics, not source frame/audio parity,
game-over playback, editor round trips, pause/seek or menu navigation.

A subsequent source-identity audit invalidated **Underground Easy's apparent
pass** above. Its donor and installed Easy chart both explicitly select
`player1: bf-santa`, while the default chart selects `bf`; the native loader
borrowed the valid default actor because the selected actor has no definition
in the mounted package or Psych archive. The absence was hidden from strict
runtime diagnostics. The shared Psych difficulty merge now keeps explicit
character and stage IDs even when unresolved, so the runtime can report the
actual dependency instead of silently changing the source chart. A focused
extract-and-interpret test covers the Psych override and preserves legacy
fallback behavior. The full-song gate now compares the selected Psych chart's
explicit character IDs with a `playstate_start` identity snapshot taken before
intro scripts can intentionally swap actors. This avoids confusing an authored
cinematic swap with a loader mismatch. In the corrected offscreen Underground
Easy replay, the initial actor marker now requests `bf-santa` and
the engine emits the exact missing character/icon diagnostics. The song still
reached its natural ending with 180/180 events, but correctly failed the
strict compatibility gate. The other eight variants remain in the replay
queue. Receipt: `tmp/vswhitty-underground-authored-graphics.jsonl`. The
earlier nine-row result remains an event/lifecycle observation, not nine
compatible source difficulties.

The corrected nine-row replay reached natural endings and complete event
counts for every Underground chart. Easy failed on the exact missing
`bf-santa` character/icon, while the other eight rows had no tagged
interpreter errors. A 47-chart source-to-installed visual-field audit then
found that in-game mix Hard and Normal explicitly author `gfVersion:
gf_JUICY` but the installed native `gf` was the stock value. Its Easy chart
omits `gfVersion`; the old importer had also written a synthetic `gf` there,
blocking inheritance from Normal. Thus the three in-game mix rows are not
source-visual passes despite their clean endings. Audit and playback receipts:
`tmp/vswhitty-graphic-fields-audit.json` and
`tmp/vswhitty-underground-authored-graphics.jsonl`.

The shared Psych importer now translates each difficulty's own `gfVersion`
before song-level fallback and leaves a sparse `gf` field absent when only the
stock default was available. A fresh private import of the exact mounted
vswhitty owner passed **47/47** source title, note, event and explicit
girlfriend comparisons, leaving installed charts/options unchanged. Its
in-game mix Normal/Hard charts now carry `gf_JUICY` and Easy has no `gf` field.
A generic owner-scoped refresh verified source/preview/live owner and payloads,
backed up the installed originals, and changed only the `gf` field in 13 of
47 charts (including removal of ten stale synthetic defaults). The user's
newer live options file remained byte-identical throughout this import and
refresh. Receipts: `tmp/vswhitty-graphics-preview/result.json`,
`live-gf-plan.json`, `live-gf-receipt.json`, and
`tmp/example-mods-psych-gf-version-build.log`. On the refreshed runtime,
**in-game mix Easy/Hard/Normal passed 3/3** strict private-Xvfb natural
endings with 166/166 events and no interpreter errors. Each run's pre-script
chart marker and rendered girlfriend marker both show `gf_JUICY`; Easy gets
that value through default-chart inheritance. Receipt:
`tmp/vswhitty-ingame-mix-gf-refresh.jsonl`. The other ten charts whose stale
synthetic `gf` field was removed also passed **10/10** strict offscreen natural
endings: Faucet HQ 0/0, Hungry HQ 61/61, Low-Rise HQ 92/92 and Underground HQ
208/208 events per chart, with no interpreter errors. Their pre-script chart
markers all select the stock `gf` after fallback. Receipt:
`tmp/vswhitty-graphics-preview/remaining-gf-playthrough.jsonl`. A
post-refresh read-only pass found zero explicit
`player1`/`player2`/stage/`gfVersion` differences across all 47 source and
installed charts, and the strengthened owner/payload refresh planner found
zero remaining `gf` differences from the private import. Receipt:
`tmp/vswhitty-graphic-fields-audit-after-refresh.json`.

The first full suite after the importer change ran 1,147 tests and failed one
mounted auto-import audit module: its expected chart metadata still required
Psych's synthetic `gf` field on sparse charts and the stock value instead of
explicit `gfVersion` on two in-game mix charts. The audit expectation now
mirrors the source format and the shared importer rule. The other modules,
including the mounted HXC scanner, passed that run; a targeted audit and full
suite retry were then completed. The targeted mounted audit passed, and the
final full run passed **1,147 tests across 318 modules, 61 skipped, zero
failed**, including the native HXC scanner. Logs:
`tmp/example-mods-fullsuite-psych-gf-version.log`,
`tmp/example-mods-mounted-audit-gf-retry.log`, and
`tmp/example-mods-fullsuite-psych-gf-version-final.log`.

### FNAS owner-wide song HUD and story ending (25 September)

The FNAS `minigameyeaaaa` state uses Flixel groups and the global collision
API. Shared Codename bindings now expose `FlxGroup`, `FlxG.worldBounds`,
`collide` and `overlap`; the collision rectangle stays interpreter-local and
native bounds are restored after every check. Focused HScript tests cover a
zero-argument overlap callback, null second operand, thrown callback and
constructor-created group teardown. A private direct-entry import rendered
the minigame room on Xvfb without tagged state errors:
`tmp/fnas-owner-ui-preview/minigame-direct-result.json` and
`minigame-direct.png`. Direct entry does not prove the story ending route or
ring/room interactions.

The first story-mode smoke dispatched all 204 authored events but reached the
native victory screen. That uncovered three shared gaps: Codename runs
owner-wide scripts directly under `songs/`, the gameplay `PlayState` binding
did not expose live `isStoryMode`, and the script's `inst.onComplete` was bound
to an audio asset rather than the playing sound. The importer now stages only
the owner's immediate `songs/*.hx` files, and PlayState loads them before
song-local scripts. The live PlayState and instrumental façades provide those
source properties and the legacy story reset. The `onStartSong` callback is
dispatched alongside `onSongStart`; owner-checked `ModState` creation remains
inside the selected namespace. A private gameplay frame shows the authored
FNAS HUD and seven owner-created HUD objects; the short receipt is
`tmp/fnas-owner-ui-preview/story-minigame-result.json` and the frame is
`story-minigame-playing.png`.

A botplay ending was deliberately rejected as route evidence: this fork's
demo-mode completion ends PlayState without calling the sound's `onComplete`.
The final test used private Xvfb, repository default options, practice mode
for unattended missed notes, 5× audio rate, and the installed owner selected
from the chart's manifest. It reached the **natural audio completion** of
`better-clone` Normal with **204/204 events**, invoked the source completion
callback, and rendered the minigame room three seconds after the song end.
The checkerboard-room screenshot matches direct entry, no tagged script/state
errors appeared, and the installed export plus personal options stayed
byte-identical. Receipt, marker stream, log and frame:
`tmp/fnas-owner-ui-preview/story-minigame-result.json`,
`story-minigame.markers.jsonl`, `story-minigame.process.log`, and
`story-minigame-after-end.png`. The private importer deleted its disposable
owner/runtime overlay after the run. Ring pickup, room progression, FNAS
pause/game-over behavior, cutscene skip, retry, seek, source audio/visual
comparison and repeated owner switching were unverified at this point. This is one
song/difficulty and one story-ending transition, not FNAS package parity.

The first full suite after this change failed two standalone Haxe fixtures:
the character-runtime fixture lacked `FlxBasic`/`FlxTypedGroup` stubs for the
new constructor cleanup, and the event-drain fixture lacked the instrumental
facade field. Both fixtures now compile and the latter exercises an authored
completion callback after the bounded event tail. The final suite passed
**1,150 tests across 320 modules, 61 skipped, zero failed**, including the
mounted HXC scan (`tmp/example-mods-fullsuite-fnas-story-verified.log`).
The first direct-entry probe captured the minigame room and its animated ring,
but its short input captures did not establish player movement. A longer input
replay waited on the runtime lock held by a game on the desktop display, so
it was stopped without launching another game or changing installed files.
The input checks below supersede that limitation. Lock-wait receipt:
`minigame-input-lock-wait-result.json`.

### D-Sides converter versus installed charts (25 September)

The current mounted-donor `test_codename_import.py` passed in the final full
suite. It converts all **22** D-Sides charts, checks that each source note
has one unique native row with matching time, lane, sustain and origin, and
checks the GF-line rows in `dad-battle` (1), `monster` (49) and `tutorial`
(126). Thus the older private writer preview's missing GF rows are stale
converter evidence. At this historical check, the installed `blammed` Hard
still had 400 rows against 1,019 source rows, and Easy/Normal had stale rows.
The later owner-matched refresh is recorded below. Source visuals and
interaction checks remain. Test log:
`tmp/example-mods-fullsuite-fnas-story-verified.log`.

### FNAS first ring, room two and repeated import stability (25 September)

The private Imported Mods chooser displayed only states whose owner
directories existed. An early input driver indexed the unfiltered catalog,
landed on the credits state and falsely accepted its live process. The driver
now mirrors visible owner resolution and requires the minigame's checkered
room. On an unmodified donor-script replay, the blue player proxy moved from
pixel center `(619, 287)` to `(671, 290)` after Right and `(671, 337)` after
Down. A private **diagnostic-only copy** of the minigame script recorded the
first ring callback changing `thering.alpha` from `1` to `0.001` at overlap;
the source copy was never changed. The same input route with the **unmodified
source script** then crossed the exit hitbox and rendered room two. The
strict screenshot check measured a 53.49 mean RGB difference across the
stage region versus room one, well above its threshold of 20. No tagged
state/script errors appeared and the live export and personal settings were
byte-identical. Source-script receipt and frame:
`tmp/fnas-owner-ui-preview/minigame-direct-result.json`,
`minigame-ring-step-11.png`; diagnostic-only log:
`minigame-ring-diagnostic.process.log`. Rooms three and four, the final
minigame outcome, pause/game-over, retry, seek and source frame/audio parity
remain unverified.

One native FNAS import crashed at chart serialization and a six-run isolated
replay reproduced it once. The saved native core dump for PID 313457 shows
`tjson.TJSONEncoder.encodeValue` under `CoolUtil.stringifyJson` and
`ModuleFunctions.importSong`. This is a generated plain-JSON chart, so the
shared import writer now uses `haxe.Json.stringify` for converted chart
output; permissive TJSON reading of authored JSONC remains intact. Focused
import/storage tests passed **23/23**, a canonical `./run.sh build` passed,
and **40/40** further isolated native FNAS imports succeeded. Each output
parsed with 1,224 rows and the expected selected owner, and the protected
live files stayed unchanged. Receipts and build log:
`tmp/fnas-owner-ui-preview/import-reliability-result.json`,
`import-json-stability-result.json`, and
`tmp/example-mods-import-json-stability-build.log`. The broader full suite
has since passed as recorded below. Other-owner repeated import runs are
still required after this serializer change.

The import writer was separately found to replace embedded Codename
section-chart titles with the folder key. Source `blammed` Easy/Normal both
author `Blammed`, while the older owner-matched private preview stores
`blammed`; pure Codename charts derive their identifier from metadata and
still need the folder key for case-sensitive audio. The shared writer now
retains the explicit section-chart title and records its preservation marker,
while leaving generated Codename chart identifiers unchanged. Focused
`test_codename_import.py` and `test_import_storage_key.py` passed **22/22**
tests against this rule. The old private preview predates the fix and was not
applied to live charts. The later owner-matched preview and scoped refresh are
recorded below.

### D-Sides owner refresh and current native blockers (25 September)

An exact-installation-root private import selected
`assets/imported_mods/codename-engine-d-sides-redux-codename-engine-cancelled-d97d25757d`
and reproduced source Blammed Easy/Normal/Hard note counts of **788/858/1,019**.
It preserved the explicit `Blammed` title in the two section charts and used
the lowercase storage key in the pure Codename Hard chart. The private run
left installed files and settings byte-identical. A guarded, owner-scoped
refresh then backed up and replaced only these three live charts. Its identity
guard accepts a case-only change when the new title matches the chart storage
folder; unrelated titles and foreign owners remain rejected. All three
installed chart hashes now match the preview, and repository and live option
hashes match the pre-refresh plan. Evidence:
`tmp/dsides-current-build22/check-owner-title.stdout.json`,
`owner-title-refresh-plan.json`, `owner-title-refresh-receipt.json`, and its
backup path in the receipt.

A subsequent exact-root private pass checked all **22** D-Sides charts against
source note origins and events, and all 22 reached `playstate_ready`. **0/22**
met the strict diagnostic gate. Owner-wide `songs/*.hx` scripts currently
produce common parser/import errors on every chart (including the flattened
`FlxBasePoint` import, a class declaration requiring an executable module
loader, and an editor `Charter` import); specific stage/character diagnostics
also remain. This is startup evidence only, not full-song compatibility.
Receipt: `tmp/dsides-current-build22/full-after-title-run.json`. A shared Codename point
binding for `FlxBasePoint` and the implicit `FlxPoint.get` script global has
since been added and passed its standalone execution test; a rebuilt native
Bopeebo Hard replay removed both point-related diagnostics. It still reports
12 tagged lines, including the class/module loader, editor `Charter`,
`MusicBeatTransition`, scoring `RatingManager`/`WindowPreset`, `FlxStringUtil`,
and an indexed-loop syntax gap. Receipt:
`tmp/dsides-current-build22/point-binding-native-one.json`. The latter
bindings need source behavior, not silent script omission.

The canonical `./run.sh build` for the point binding passed
(`tmp/example-mods-codename-point-bindings-build.log`). The final full
`python3 tools/run_tests.py` pass completed **1,152 tests across 321 modules,
61 skipped, zero failed**, including mounted auto-import and HXC scans
(`tmp/example-mods-fullsuite-dsides-refresh-point-bindings.log`). This suite
does not clear the native diagnostics above.

### Codename indexed loops and source formatting (25 September)

Codename's indexed `for (key => value in iterable)` syntax previously lowered
every iterable as an array and required an immediate braced body. That changed
Map keys into numeric indices and rejected the mounted D-Sides `Debug.hx`
nested loop. `CodenameScriptParser` now keeps the complete nested body and
uses a shared key/value iterator for arrays, `CodenameMapCompat` and native
maps. It also rewrites numeric `0...count` loop iterators at the parsed AST
level because HScript cannot reflect the native `IntIterator` inline methods.
The mounted `Debug.hx` parses with an explicit editor import binding supplied
by a standalone fixture; this does **not** establish editor behavior in the
game. A separate shared binding delegates the D-Sides UI score formatter to
Flixel's `FlxStringUtil.formatMoney` source implementation. Focused parser and
binding tests passed **12/12**, and `./run.sh build` passed
(`tmp/example-mods-codename-indexed-loop-build.log`).

The rebuilt exact-owner private D-Sides pass checked all 22 imported source
note/event sets and started Darnell Hard and Spookeez Hard under private Xvfb.
Both reached PlayState, and their remaining tagged lines fell to ten each;
the `FlxBasePoint`, implicit `FlxPoint`, indexed-loop and `FlxStringUtil`
diagnostics seen earlier were absent. Both still fail the strict gate because
the class/module loader, editor `Charter`, transition and scoring APIs remain
unimplemented. It left the live export and settings unchanged and removed
its disposable runtime overlay. Receipt:
`tmp/dsides-current-build22/indexed-loop-targeted.json`.

### Codename rating manager and input windows (25 September)

The previous Codename hit path used local Judge percentages and ignored
scripts that replaced `PlayState.instance.ratingManager`. The shared engine
now exposes Codename's four window presets, sorted custom ratings, inclusive
judgement boundaries and historical `lastHitWindow`. Imported Codename notes
use that maximum for the source strumline input gate; hit events receive the
selected rating's name, score, accuracy, health, splash and combo-break rule.
The default `shit` rating breaks combo as in Codename's source flag. Non-
Codename notes keep their existing timing path. A focused Haxe interpreter
test executes D-Sides-style imports and custom `epic` registration and checks
the 37.8/50 ms boundaries, replacement, defaults and other presets. The
canonical `./run.sh build` passed
(`tmp/example-mods-codename-rating-build.log`).
Source comparisons: [RatingManager](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/scoring/RatingManager.hx),
[HitWindowData](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/scoring/HitWindowData.hx),
[StrumLine](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/game/StrumLine.hx),
and [Flags](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/system/Flags.hx).

On that binary, a freshly prepared exact-owner D-Sides private Xvfb pass
again matched all **22** source chart note/event sets and started Darnell
Hard and Spookeez Hard. Both reached PlayState. The scoring imports no longer
emit diagnostics; the remaining explicit blockers are the class declaration
in `composerIntro.hx`, editor `Charter`, and `MusicBeatTransition`. Both still
fail the strict gate. The runner confirmed the installed export and personal
settings stayed unchanged; its disposable overlay was removed. Receipt:
`tmp/dsides-current-build22/rating-targeted-result.json`. This short startup
does not exercise judged note inputs or prove source-matching visuals/audio.
After updating the extracted-method fixtures for the new timing fields, the
complete `python3 tools/run_tests.py` suite passed **1,157 tests across 323
modules in 185.9 seconds, 61 skipped, zero failed**. The relevant tests now
check custom rating event values, combo breaks and strict early/late input
boundaries. Receipt: `tmp/example-mods-fullsuite-rating-manager-final.log`.
Both repository and live options hashes still match the pre-refresh plan.

### Earlier D-Sides full startup sweep and shader diagnosis (25 September)

The scoring build then under test was replayed against **all 22** exact-owner D-Sides
chart difficulties under private Xvfb. Source notes and events matched for all
22, and all 22 reached `playstate_ready`; **0/22** passed the strict diagnostic
gate. `composerIntro.hx` has an unsupported enum/type declaration,
`Debug.hx` and `UI.hx` import the unimplemented editor `Charter`, and
`stickerTransition.hx` imports `MusicBeatTransition` on every chart. Blammed
Easy/Normal also lack the exact dark-character assets. Endless Hard and
Monster Hard import the unsupported `modchart.Manager` and `PlayField` modules;
Monster additionally has four actor placement failures. Endless also reports
an ownership conflict while reordering a camera. Bomb Bash Hard reaches song
start but reports a stage shader assignment error. The full receipt is
`tmp/dsides-current-build22/rating-full-22-result.json`, with individual
process logs beside it. The private runner confirmed both protected live
files and personal settings remained unchanged; its disposable overlay was
removed. These starts do not establish playthrough or source presentation
parity.

Bomb Bash's imported `3D Floor.frag` is byte-identical to the donor and
declares `curveX`. Its stage declares `camFollowPos:Float` without an initial
value, then uses it in arithmetic before the first assignment. The native log
records null operands before the shader write; the shared shader bridge
reported the resulting null as an unknown uniform. The bridge now
distinguishes a declared uniform with an unsupported value from a genuinely
missing uniform, with a focused regression test. [Codename's upstream HScript
interpreter](https://github.com/CodenameCrew/hscript-improved/blob/master/hscript/Interp.hx)
also initializes unassigned script variables to null; the donor's intended
visual behavior at this point is therefore unresolved. The error remains a
strict compatibility failure until the source runtime behavior is reproduced
and compared. No chart, stage, shader, or donor file was changed to hide it.

The shared `CodenamePaths` facade now supports the source folder-listing
forms `getFolderDirectories` and `getFolderContent`, including optional
relative path prefixes and extension removal. It lists only direct children
within the selected owner and skips symlink escapes. A focused Haxe test covers
the owner boundary, missing folders, prefixes and extensions. The shared
importer now stages bounded, owner-local files reached through a literal
folder-listing call, including one child directory level for scripts that use
the returned directory in a later dynamic file-listing call. The extracted
importer test verifies copy, missing-only repair, and rejection of a foreign
symlink. This removes an API and import-plan gap in sticker transitions. The
private exact-owner D-Sides refresh now materializes the referenced
`songs/stickerTransition.hx` and 16 sticker sound files without changing the
installed owner or settings. The executable `StickerPack` and
`MusicBeatTransition` classes still need separate implementation. Source API:
[Codename Paths](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/assets/Paths.hx).

The shared importer also follows bounded literal `MusicBeatTransition.script`
assignments so a transition script named in a song callback is staged under
the selected owner. It reports unresolved or unsafe references. The
`funkin.editors.charter.Charter` import now names a real native chart editor
adapter with exact-owner song/difficulty checks; editor presentation and round
trip behavior still need an offscreen check. `window` and `FlxG.timeScale` are
bound to live host state and the time scale resets at song teardown.

Codename's normal HUD exports `missesTxt`, `iconArray`, mutable score and
scroll globals, and replaceable icon bump callbacks. The selected-owner
Codename host now exposes these real native objects and the source `fpsLerp`,
`quantize`, and `Flags.ICON_LERP` values. Its icon decay uses elapsed time;
a focused interpreter test checks equivalent one-second decay at 60, 240 and
480 FPS. This is a narrow utility check, not a complete gameplay FPS check.
`./run.sh build` passed, and the latest private D-Sides Darnell Hard and
Spookeez Hard startup replay reached gameplay with source chart/event parity
and **no `UI.hx` interpreter errors**. Both still fail the strict gate on
`composerIntro.hx`'s enum/type declaration and the missing transition runtime.
The private replay confirms protected live files and personal settings are
unchanged. The latest audio-facade build repeated the same two starts with
the same four diagnostics per chart (two parser telemetry lines, the composer
declaration, and the missing transition binding); no HUD error returned.
Receipts: `tmp/dsides-current-build22/hud-targeted-result.json` and
`tmp/dsides-current-build22/hud-audio-targeted-result.json`.
The earlier all-22 sweep predates these fixes; no all-chart or full-song HUD
parity is claimed.

The shared Codename `CoolUtil.playMusic` facade now interprets arguments in
the source order (persist, volume, loop, default BPM), and `playMenuSong`
accepts the source fade-in boolean. This fixes a shared menu/game-over audio
API mismatch found while inventorying `Flags.DEFAULT_BPM` use in the mounted
Codename scripts. The character script host also receives that shared utility
facade and both source flag values currently used by the mounted scripts.
Focused interpreter coverage checks argument order, loop/persist settings,
the BPM value, fade-in path, and reset of native song-position/BPM-map state
when new menu music starts. Native menu and game-over audio comparison is
still pending.

The latest completed `python3 tools/run_tests.py` run passed **1,160 tests
across 325 modules in 185.6 seconds, 61 skipped, zero failed**. The canonical
`./run.sh build` passed before the latest private D-Sides replay. Evidence:
`tmp/example-mods-fullsuite-hud-audio-final.log` and
`tmp/example-mods-codename-hud-audio-build.log`. Repository seed and live
options SHA-256 hashes match the protected baseline; the disposable runtime
overlay was removed. The subsequent Conductor reset tweak and transition work
need a new full suite and native build before they are counted as verified.

The mounted D-Sides `songs/composerIntro.hx` and custom Story menu both
declare enums with duplicate constructor names, and neither script refers to
its enum afterward. [Codename's current HScript parser](https://github.com/CodenameCrew/hscript-improved/blob/master/hscript/Parser.hx)
has a class declaration path but no enum declaration path;
[Codename's HScript host](https://github.com/CodenameCrew/CodenameEngine/blob/main/source/funkin/backend/scripting/HScript.hx)
catches parser failures and leaves the script expression unset. This suggests
the donor declaration may fail in the source engine too, but the mounted
Windows executable's exact bundled parser version has not been confirmed.
The pinned upstream parser rejected the mounted enum declaration in a
standalone Haxe interpreter check with `EUnexpected(ComposerData)`; commit,
source hashes and output are in
`tmp/codename-upstream-enum-parser-receipt.json`.
The engine continues to report the declaration explicitly; it does not
silently remove an unused enum or count the script as compatible.

Blammed Easy and Normal directly name `bf-dark`, `pico-dark`, and `gf-dark`
in their source charts. A case-insensitive search of the complete mounted
D-Sides Codename installation found no definition or atlas under any of those
exact IDs; other `*-dark` assets do exist. The runtime's six unresolved actor
diagnostics across those two charts therefore identify missing source
dependencies, not a case-sensitive importer omission. The engine retains the
authored IDs and reports the missing owner assets rather than substituting
similar characters from another package. These two difficulties cannot meet
visual parity from the mounted donor alone.

## D-Sides modchart renderer dependency blocker (25 September)

The mounted D-Sides owner still imports `modchart.Manager` and
`modchart.engine.PlayField` in `data/stages/spookyEvil.hx` (Monster Hard) and
`songs/endless/scripts/modchart.hx` (Endless Hard). These are part of
FunkinModchart's real receptor/note renderer, not utility-only script classes.
Monster constructs a `Manager` in `postCreate`, adds it to `FlxG.state`, reads
`manager.playfields[0]`, registers seven modifiers (`Bounce`, `OpponentSwap`,
`Scale`, `Stealth`, `Tipsy`, `Transform`, `Zoom`) and schedules 34 `ease`
events across `Alpha`, `Bounce`, `OpponentSwap`, `Tipsy`, `tipsySpeed`, `x`,
`y`, and `Zoom`. Endless uses the same manager lifecycle, checks the authored
`FlxG.save.data.modCharts` gate, registers 14 modifiers (`Beat`,
`CenterRotate`, `Confusion`, `Drunk`, `LocalRotate`, `OpponentSwap`,
`ReceptorScroll`, `Reverse`, `Scale`, `Skew`, `Stealth`, `Tipsy`, `Transform`,
`Zoom`), schedules 59 `set` events and 104 `ease` events, and changes live
strum positions in its `postUpdate`, `stepHit` and `beatHit` hooks. Both scripts
import `PlayField` even though their authored code obtains the actual instance
from `manager.playfields[0]`.

The Endless timeline uses general percentage channels `Alpha`, `Beat`,
`CenterRotateY`, `Confusion`, `Drunk`, `DrunkX/Y/Z`, `LocalRotateX/Y/Z`,
`OpponentSwap`, `ReceptorScroll`, `Reverse`, `Scale`, `skewX/Y`, `TipsyY/Z`,
`X` and `Y`; its lane-indexed loops additionally write `Alpha0-3`,
`Confusion0-3`, `X0-3` and `Y0-3`. `set`/`ease` times are source beats; the
separate `stepHit` callback uses integer steps 656, 784, 900, 910, 913 and
1167. The authored `LocalLotateX/Y` set names are misspelled and have no
matching upstream modifier channel; leave them as authored rather than
silently rewriting source content. Monster's explicit player target 3 and
Endless's explicit targets 0/1 require adapter line indices to stay aligned
with the mounted chart, while the default target `-1` applies across every
adapter player. Curves include the source `FlxEase` back, bounce, circ, cube,
expo, quad, quart, quint and sine variants. Six calls omit the ease function;
the script host must pass a null value in that argument slot so the upstream
linear fallback is used.

The upstream source reference checked for this audit is CodenameCrew's
FunkinModchart **1.2.5**, commit
[`029cb648292f307c76c636311f3a1020ca0f8e19`](https://github.com/CodenameCrew/FunkinModchart/tree/029cb648292f307c76c636311f3a1020ca0f8e19).
The mounted D-Sides owner does not include that dependency's source or a
version lock, so 1.2.5 is a verified implementation reference, not proof of
the exact library revision in the donor executable. In that source,
[`Manager`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/modchart/Manager.hx)
extends `FlxBasic`, creates a real `PlayField`, updates it every frame and
renders actual arrow items through `CtxRenderer`. [`PlayField`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/modchart/engine/PlayField.hx)
extends `FlxSprite`; it owns a modifier group and beat-sorted event timeline.
Its `set` and `ease` calls update modifier percentages consumed by the note and
receptor renderers. A class binding that accepts the imports but does not
transform live receptors, taps and holds would not implement this API.

This checkout does not contain FunkinModchart. Its haxelib metadata names
version 1.2.5; the library's [`include.xml`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/include.xml)
mounts its arrow/eye shape CSV assets, and [`extraParams.hxml`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/extraParams.hxml)
defines compile-time Flixel extensions. Its
documented Codename setup requires the library include macro and engine defines
(`FM_ENGINE=CODENAME`, empty `FM_ENGINE_VERSION` for Codename 1.0). The bundled
[`Codename adapter`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/modchart/backend/standalone/adapters/codename/Codename.hx)
cannot be compiled unchanged here: it imports Codename's
`funkin.game.Note`, `PlayState`, `Strum`, `Splash`, `Conductor` and `Options`,
and reads their engine-specific strumline, camera and splash APIs. A port needs
a project adapter implementing the library's [`IAdapter`](https://github.com/CodenameCrew/FunkinModchart/blob/029cb648292f307c76c636311f3a1020ca0f8e19/modchart/backend/standalone/IAdapter.hx)
contract: song time
and fractional beat, BPM-aware step conversion, live per-line/key-count and
receptor coordinates, scroll/downscroll, note ownership/lane/hit/hold timing,
HUD camera, hold subdivisions, and the live receptor/tap/hold/splash draw lists.
The existing `Conductor` has a BPM-change map but no `curBeatFloat`; the
adapter must derive a continuous beat from that map rather than use the
integer-only `MusicBeatState.curBeat` for easing. Rendering also needs correct
Flixel visibility/camera restoration and lifecycle cleanup.

The full dependency is 86 Haxe files (about 6,485 lines). It uses a compile-time
modifier registry and injects storage/visibility support into Flixel objects,
as well as a triangle-drawing helper. Those build-wide hooks can affect all
sprites, so they require a separate compile and render review before being
enabled. No library source, adapter, import binding or global build setting was
added in this pass; the two charts remain blocked on the actual renderer.

The focused verification gate for a later port is:

- Compile the pinned library plus the project adapter and confirm that every
  D-Sides modifier name resolves through the real modifier registry.
- Execute both unmodified mounted scripts in an interpreter fixture. Check
  manager state membership, the Endless `modCharts` gate, one real playfield,
  the 59/34 authored `set`/`ease` event counts, explicit player targets,
  generated lane names, beat ordering, and the source's six `ease` calls that
  omit an easing function (upstream `EaseEvent` treats a null easing function
  as linear).
- Under private offscreen Xvfb, sample live receptor, tap and hold draw output
  with modcharts enabled at representative Monster beats 268, 342, 403 and
  608, and Endless beats 36, 100, 132, 228, 292 and 388. Compare measured
  positions/alpha/rotation against upstream modifier output; a successful
  script load or unchanged screenshot is a failure of this gate.
- Run both charts to natural ending, assert manager updates and reachable
  scheduled events, then leave PlayState and verify renderer hooks/resources
  are released before starting another chart.

No offscreen rendering result is claimed for Monster Hard or Endless Hard.

The Endless stage script rebuilds Flixel's camera list, and its shared rating
script later moves `camHUD` above the rating camera. The old interpreter-local
camera facade rejected the second, same-owner reorder. Its host-camera journal
now stacks same-owner mutations and restores them in reverse even if the stage
scope unloads first; a different owner remains isolated. It also exposes a
snapshot of Flixel's default draw targets because the stage preserves those
flags while rebuilding its camera order. A focused Haxe/HScript test exercises
the donor's `defaults.contains` access, same-owner camera sequence,
different-owner rejection, and out-of-order cleanup. The canonical release
build passed, then a private D-Sides refresh started Darnell Hard, Spookeez
Hard, and Endless Hard under Xvfb. Endless no longer reports a camera ownership
error; its ready snapshot shows seven cameras. Protected live imports and user
settings remained unchanged, and the disposable overlay was removed. All
three still fail other strict diagnostics. Receipt:
`tmp/dsides-current-build22/camera-lifecycle-endless-result.json`.

That Endless replay also exposed ignored HScript calls to Flixel's inlined
`FlxPoint.addPoint` and a null `e.note.strumLine` read during Codename note
callbacks. The shared camera event now exposes a script-visible mutable point,
and `Note.strumLine` resolves to its bound Codename input line. Focused HScript
tests exercise both exports. They have not yet been rebuilt or replayed
natively, so camera movement and note-callback parity remain unverified.

Codename gameplay now dispatches the source-shaped `onGamePause`,
`onGameOver`, and cancellable `onSongEnd` callbacks at the matching native
transition seams. `onSubstateClose` runs while the closing substate and paused
flag are still visible, as the mounted Codename scripts expect. These seams
are needed by D-Sides' transition script, Debug playback reset, and stage
audio resume. Native pause, game-over, ending, and skip behavior still need
offscreen replay after the transition runtime lands.

The pasted Wacky World Freeplay log reported `EUnknownVariable(hxcAssetRoot)`
while loading `PVE_VideoModule.hxc`. The shared Freeplay module interpreter
now seeds its selected manifest root before execution. A locked release build
passed, followed by a private Xvfb run with a one-song Wacky World Freeplay
registry in a disposable runtime. Both the video module and extra-events
module loaded, the run emitted `freeplay_start` and `success`, exited 0, and
left the default options bytes unchanged. No `hxc-freeplay-load-error`
appeared. Receipt: `tmp/user-paste-freeplay/result.json`. This checks module
load, not video playback or the song's full lifecycle.

The same pasted log showed a null `CoolUtil.playMenuSFX` call and an
unsupported `Options.antialiasing` read. The shared Codename facade now maps
all six source CoolSfx IDs to owner-scoped sound keys; missing keys diagnose
explicitly. Its detached Options view supplies Codename's documented `true`
antialiasing default without changing native settings. Focused Haxe tests
exercise six sound IDs, the default call, supported option reads, and detached
writes. The later SIGSEGV in the pasted log cannot yet be attributed to the
null sound call; the same exact menu route requires a private native replay.

A private D-Sides Darnell Hard pause/resume run delivered Escape and Return,
emitted `pause_open` and `pause_resume`, and held the music clock during pause.
That run preceded installation of the owner-scoped `data/stickerTransition.hx`.
The file is now present and byte-identical to the donor, but there is no
reviewed receipt for its addition, so the earlier result only verifies the
fallback transition. The shared lifecycle now supplies an event to open and
close callbacks; focused tests pass and a later canonical build passed.
Evidence: `tmp/dsides-transition-pause-result.json`.

With the sticker script present, the Darnell pause/resume probe timed out after
both input markers. The subsequent private process log attributes the outgoing
script error to a missing owner-scoped
`images/transitionSwag/stickers-set-1/spookies2.png`. The installed owner has
the `data/stickerpacks/default.json` metadata but none of its referenced
`images/transitionSwag` files. The incoming source script cancels the default
transition and schedules no completion when its static `lastStickers` list is
empty. This is an importer dependency and transition recovery gap, not a
passing pause/resume check. Evidence:
`tmp/runtime-smoke/logs/dsides-sticker-error-probe.process.log` and
`tmp/dsides-sticker-pause-replay-result.json`.

A private Endless Hard replay after the shared `FlxRuntimeShader` tween bridge
reached song start and exited successfully, without its earlier `saturation`
property error. It still logs `songs/rgbNotes.hx` null receptor access,
unsupported `modchart.Manager`/`modchart.engine.PlayField`, missing
`images/game/score/epic.png`, and `songs/UI.hx` missing the live `combo`
global. The bridge therefore clears one crash only. The combo global has since
been bound to native state and passed a focused Haxe read/write test; its
native replay is pending. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-shader-tween-retest.process.log`.

### 25 September: sticker refresh, transition handoff, and receptor replay

The importer now reads bounded Codename sticker-pack metadata and stages its
referenced images within the selected owner. A fresh private D-Sides import
reported `imported=20`, `skipped=20`, `copiedAssets=984`, and no import errors.
All 83 referenced sticker entries across the donor's default, bonus and
weekend packs matched the preview by hash. The installed owner had the
default JSON but lacked 83 images and two pack JSON files. A narrow add-only
refresh backed up the existing default pack, manifest and options, then
added exactly those 85 absent files (3,917,968 bytes) under the runtime locks.
It refused replacements and symlinks and did not change existing owner files
or the user's options. Evidence: `tmp/dsides-sticker-refresh-preview/result.json`,
`tmp/dsides-sticker-refresh-preview/sticker-refresh-plan.json`, and
`tmp/dsides-sticker-refresh-preview/sticker-refresh-receipt.json`.

The first run with those assets rendered the outgoing transition but hung on
the incoming transition. The source `static var lastStickers` existed in an
HScript closure but was absent from the transition scope's shared variable
map. The interpreter now retains declared transition statics in that map,
and the outgoing host captures them before it marks the transition finished.
An executable Haxe fixture passes an array from an outgoing callback to an
incoming scope. Two private Darnell Hard offscreen pause/resume probes then
emitted `pause_open`, `pause_resume` and `success`, with both transition
directions rendering and finishing. A Return sent before the native pause
menu accepted input gave no `pause_resume`; that attempt is an input-timing
non-result. Resume while the outgoing transition is still in flight remains
unverified. Evidence: `tmp/runtime-smoke/logs/dsides-sticker-static-fixed.log`
and `tmp/runtime-smoke/logs/dsides-sticker-early-resume.log`.

The shared input-line adapter now exposes live native receptors by authored
player/opponent/GF role; extra unmapped lines stay empty. `PlayState` also
exports the live combo, and native `StrumNote.getAnim()` reports the current
animation. Focused tests passed and the canonical release build passed. A
private Endless Hard startup replay reached gameplay and exited successfully
without the earlier `rgbNotes.hx` null `getAnim`, missing `combo`, or shader
`saturation` errors. It still reported three unsupported actor placements,
the missing owner-scoped `images/game/score/epic.png`, and unsupported
`modchart.Manager`/`modchart.engine.PlayField`; this is not a strict song
pass. Evidence: `tmp/runtime-smoke/logs/dsides-endless-getanim-retest.process.log`.

The pasted HL17 import log exposed missing shared imports and private UI
classes. `CodenameImportBindings.addShared` now explicitly binds the reported
`Math`, `FlxRect`, `Main`, `Type`, `haxe.Timer`, FPS, text, sprite, MemoryUtil
and Framerate APIs. `HLTypeText` is provided through a shared owner-scoped
adapter: it resolves `trebuc.ttf` from the selected owner and reproduces
HL17's glyph spacing, outline, reveal, callback and fade behavior while owning
its timers, tweens and group cleanup. The donor Haxe class itself remains
non-executable; focused tests cover the adapter and its constructor binding.
The window classes still depend on `HLUIWindow`, `HLUIComponent`, `HLUIBox`,
`Layout`, `HLUITable`, tab, label, button, checkbox and number-stepper classes
that are absent from both mounted donor and installed owner. Those imports
remain explicitly unsupported. `Sys` also stays unavailable because its
`exit` API could terminate the host game. The pasted SIGSEGV was not attributed
to an engine defect by the captured route.

An exact private route through Title, Main Menu and Imported Mods to the
installed `HL17MainMenu.hx` stayed alive for six seconds after state launch.
It reported the expected four unsupported imports for
`HLCreditsWindow`, `HLOptionsWindow`, `HLSelectWindow` and `Sys`, then showed
the imported-state diagnostic instead of executing the menu. No SIGSEGV was
reproduced on that route; this does not prove the earlier crash impossible,
and HL17 menu behavior remains unsupported. Evidence:
`tmp/runtime-smoke/logs/hl17-main-menu-exact.process.log` and
`tmp/runtime-smoke/logs/hl17-main-menu-exact.png`. The test used seed
options, private XDG paths and an isolated owner overlay; post-run live
options SHA-256 was
`2a85e43ce2f434b9ad97f374ed12d98b9a85eb5ce36f32f6a9f437a378f07e87`.

A bounded Wacky World Freeplay run on the current release binary used the
private selected-owner overlay, private Xvfb, dummy audio and repository
default options. It reached `freeplay_start`, profiled both parse and execution
of `PVE_VideoModule`, then emitted `success`; the process log had no
`hxc-freeplay-load-error`, `hxc-freeplay-error` or `EUnknownVariable` lines.
The previously pasted `hxcAssetRoot` error was not reproduced. Repository and
overlay options retained SHA-256
`0693e6470fa0d6ba48f2a1ab3f99bbbf8a98598d94d6d2a48db65d9d5f7ac66d`.
Evidence: `tmp/hxc-freeplay-assetroot/result.json`, `process.log` and
`markers.jsonl`.

The conventional Codename `images/game/score/*.png` folder contains runtime
selected rating art that literal script scanning cannot infer. The importer
now stages up to 128 flat PNG entries inside the selected owner, with
diagnostics for unsafe entries. A fresh private D-Sides native import copied
all 15 source score images byte for byte and left protected installed files
unchanged. A reviewed add-only refresh placed those 15 absent images
(158,791 bytes) into the installed D-Sides owner under the runtime locks,
with a backup of the selected manifest and live options. Evidence:
`tmp/dsides-score-refresh-preview/result.json`,
`tmp/dsides-score-refresh-preview/score-refresh-plan.json`, and
`tmp/dsides-score-refresh-preview/score-refresh-receipt.json`.

Shared Codename imports now bind real Haxe `Type` and `Timer.stamp`, native
OpenFL display/text constructors and memory usage, the game's actual `Main`
display root, and a facade over its live FPS counter. The detached
`Framerate.debugMode` does not write personal settings. Focused tests and a
canonical release build passed. A private Endless Hard startup replay then
exited successfully without the previous unsupported `data/global.hx`
imports or missing `game/score/epic.png` error. This checks startup
diagnostics only; the source global overlay's full display lifecycle and
every debug mode are not yet verified. The run still reports three
unsupported actor placements, `composerIntro.hx` class declarations and
the real FunkinModchart `Manager`/`PlayField` dependency. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-score-global-retest.process.log`.
`FramerateCounter`, `Sys`, the HL17 private UI classes and the missing HLUI
framework remain explicit dependencies.

Source review found a lifecycle gap behind the previously clean import lines:
`CodenameModRuntime.loadGlobal` executed `data/global.hx` but omitted its
`new()` and `update()` hooks. The shared global runtime now calls `new()`,
dispatches frame updates, and calls `destroy()` after successful creation.
The FlxG facade gives each canonical import owner its own save-data view
instead of exposing the native personal save. A private Endless Hard startup
replay no longer reports null access through the global FPS overlay.
Source overlay rendering, every debug mode, and persistence parity still need
visual and behavioral comparison. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-global-fps-order.process.log`.

A subsequent Endless Hard two-visit check found a separate shared reload
failure: visit 1 reached `playstate_ready`, then the process exited 255 at
`playstate_reload_begin` with OpenFL `Error #2007: Parameter child must be
non-null`. A no-active-owner control reproduced it, ruling out the global
script as its cause. A debug native stack traced the null child through
`PlayState.releaseCodenameScope` to `CodenameCameraFacade.release` and
`CameraFrontEnd.insert`. Flixel had reset and destroyed old cameras before
the old PlayState's script cleanup, leaving a null `flashSprite` on a host
camera that the facade tried to reattach. Camera cleanup now skips restoring
old host restoration after a reset, including hosts detached before the
reset, and skips destroying already-destroyed owned cameras. A
focused executable reset test, release build, and private offscreen two-visit
checks both with and without the D-Sides owner passed. Both native runs
reached `playstate_ready` on visit 2; the owner run had no actor cleanup
errors. These are bounded repeated-startup checks, not two full-song passes.
Evidence: `tmp/runtime-smoke/logs/dsides-endless-repeat-debug-assets.process.log`,
`tmp/runtime-smoke/logs/endless-repeat-no-owner-camera-fix.log`, and
`tmp/runtime-smoke/logs/dsides-endless-repeat-camera-fix.log`, and
`tmp/runtime-smoke/logs/dsides-endless-repeat-camera-reset-detached.log`.

A private HL17 `gordonteen-bucks` Buck startup on this build exited
successfully and no longer reported `data/global.hx` imports. Its six
`data/stages/17.hx` Flx3D/Away3D imports remain unsupported, including an
unbound OpenFL `System` import; the run does not exercise the separately
failing imported `HL17MainMenu` route. Evidence:
`tmp/runtime-smoke/logs/hl17-main-shared-import-retest.process.log`.

The next shared actor-plan pass rechecked the exact selected-owner stage
script against the imported camera sidecar's broad legacy `stage-script`
marker. The mounted `tenmaStage.hx` has camera and prop changes but no
startup actor-pose writes, while its XML supplies all three slots. Focused
placement tests and a canonical release build passed. A private Endless Hard
startup replay exited successfully and no longer emitted the three
`unsupported-placement` diagnostics. Its native character markers reported
opponent `(600,770)`, player `(1470,878)`, and girlfriend `(1130,674)`,
matching the three authored XML slot coordinates. This establishes initial
slot placement; rendered geometry parity and later script
movement still need source comparison. The replay continues to reject
`composerIntro.hx`'s `enum ComposerData` and the genuine FunkinModchart
imports. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-placement-retest.process.log` and
`tmp/build-20260925-placement-diagnostics.log`.

The parser now names the exact unsupported owner declaration instead of a
generic class/type message. An executable Haxe test confirms the mounted
`composerIntro.hx` enum cannot be parsed by the current HScript module
runtime; a separate Haxe 4.3.6 compile of its two `CHARACTER` constructors
reported `Duplicate constructor CHARACTER`. No declaration was silently
elided. `HLTypeText` now has a shared owner-scoped adapter rather than relying
on executing its staged Haxe class source; the HL17 window classes remain
blocked by their absent UI framework.

The full suite after the parser and placement changes passed **1,176 tests
across 334 modules**, with 61 skipped and zero failures. `./run.sh build`
completed successfully before the native placement replay. `git diff
--check` passed. Evidence:
`tmp/full-suite-20260925-placement-diagnostics.log` and
`tmp/build-20260925-placement-diagnostics.log`. Disposable private import
overlays were removed after their refresh receipts and protected-file hashes
were verified.

After the global lifecycle and camera teardown changes, `./run.sh build`
passed again. The final full suite on the detached-camera reset fix passed
**1,176 tests across 334 modules**,
with 61 skipped and zero failures; the extraction fixtures were updated for
the new display, save-view and global-update interfaces. `git diff --check`
passed. Evidence: `tmp/full-suite-20260925-camera-lifecycle-reset.log`,
`tmp/runtime-smoke/logs/endless-repeat-no-owner-camera-fix.log`, and
`tmp/runtime-smoke/logs/dsides-endless-repeat-camera-fix.log`. These checks
close the reproducible null-child reload crash, not the remaining source
compatibility gaps or the unverified full-song switching matrix.

A read-only source audit of the mounted D-Sides donor and selected owner
found two FunkinModchart import sites: `songs/endless/scripts/modchart.hx`
and `data/stages/spookyEvil.hx`. No `modchart` package source, Manager or
PlayField implementation, or pinned dependency configuration is present in
the donor or local toolchain. Endless uses a Manager playfield with 14
modifier families, 59 `set` calls, and 104 beat-based `ease` calls;
`spookyEvil` uses seven families and 34 eases, including an explicit player
index 3. A shared integration needs the actual FunkinModchart library and
an adapter over native timing, receptors, notes and indexed players. Binding
empty classes would hide missing visual and gameplay behavior, so these
scripts remain explicitly unsupported. No installed or donor files changed
during this audit.

## 25 September — D-Sides full-song diagnostic

An offscreen private Endless Hard run at 25× reached all 464 dispatched
events and the natural song end, then crashed in `VictoryLoopState.beatHit`.
The debug build identified a null animation on `bfmobian`: the victory
screen had recreated the selected owner's XML/Animate character through
the older `char.png` constructor. The shared post-song constructor now uses
the live PlayState's selected-owner character plan, and victory animation
checks handle an absent current animation. The GF victory threshold now uses
the native 0–100 accuracy scale. A release rebuild and private full-song
replay passed through the victory transition and exited normally.
Evidence: `tmp/runtime-smoke/logs/dsides-endless-full-song-debug.process.log`
and `tmp/runtime-smoke/logs/dsides-endless-full-song-replay.process.log`.

The same run exposed generic script API gaps. The Codename judgement group
now exposes reflectable `recycleLoop`, and its CoolUtil facade supplies
`resetSprite` and `addZeros`. Shader tweening retains authored scalar numeric
uniform values when OpenFL reports an uninitialized parameter value. Song
scripts now see the live `subState`, while owner-scoped transition scripts
use the selected song metadata through the existing PlayState facade. An
offscreen release replay reached the 148,271 ms end, dispatched all 464
events, completed the sticker transition, and exited with no rating-pop,
shader-uniform, metadata, or substate callback errors. It did report a later
`EUnknownVariable(newHealthBar)` from a stage reading a `public var` exported
by a separate song UI script; shared cross-script public-variable resolution
is under repair. The genuine FunkinModchart `Manager` and `PlayField` imports
remain unsupported in this build, so the successful run does **not** claim
visual or gameplay source parity. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-full-song-uniform-replay.process.log`.
The offscreen runner now offers `strict_diagnostics=True`; it treats tagged
script errors, unsupported APIs, and guarded null accesses as failures even
when the game emits a success marker. The latest Endless process log has
three such diagnostics (two real FunkinModchart imports and the shared
`newHealthBar` export), so its strict result is not yet a compatibility pass.

The current D-Sides importer was also run offscreen in a private overlay.
It reported 20 imported, 20 already present, zero failures, zero missing
dependencies, and matching chart/audio checks for previously mislisted
Bomb Bash and Improbable Outset. The inventory now records 20/20 songs and
22/22 chart files present, separately from gameplay compatibility. No
installed content or personal options were changed by that check. The
release options file retained SHA-256
`2a85e43ce2f434b9ad97f374ed12d98b9a85eb5ce36f32f6a9f437a378f07e87`.

The user's earlier Wacky World Freeplay log showed
`EUnknownVariable(hxcAssetRoot)` while loading `PVE_VideoModule.hxc`. The
current Freeplay runtime seeds that owner asset root before interpreter
execution. A bounded offscreen Freeplay probe against the installed Wacky
World owner on the current release binary completed both PVE module parse
and execution profiles and emitted `success`, with no HXC diagnostic or
asset-root error. It used private default options and dummy audio; the
private overlay was removed. This verifies module initialization only,
not its video callback behavior. Evidence:
`tmp/hxc-freeplay-assetroot/result.json`, `process.log`, and `markers.jsonl`.

## 25 September — real FunkinModchart integration gate

The engine now pins FunkinModchart 1.2.5 through `run.sh` and `Project.xml`,
compiles its real Manager, PlayField, modifier, event, and renderer classes,
and supplies a PlayState/Strumline/Note adapter. The shared Codename script
host also supports per-interpreter `disableScript()` and cross-script
`public var` exports. `./run.sh build` passed; focused interpreter, parser,
character, and modchart tests passed 13/13, and `git diff --check` passed.

The first strict offscreen Endless Hard replay on this build reached the
natural 148,271 ms ending, dispatched 464/464 events, completed the sticker
transition, exited zero, and left the private default settings unchanged.
It failed strict compatibility on one real structural limitation:
`[funkin-modchart-unsupported] Codename source lines 0 and 2 share one native
receptor group`. The current shared Codename line mapper projects GF and
opponent lines onto the same native enemy group; the modchart adapter
correctly rejects ambiguous indexed rendering. Distinct source-line
receptors and note ownership are under implementation. No source visual
parity is claimed. Evidence:
`tmp/runtime-smoke/logs/dsides-endless-modchart-full.log` and
`tmp/runtime-smoke/logs/dsides-endless-modchart-full.process.log`.

The next canonical `./run.sh build` passed with distinct native receptor
groups for each authored Codename line and source geometry in camera sidecars.
A fresh private D-Sides import reported 20 imported songs, zero failures and
zero missing dependencies for the 22 inventoried charts; protected installed
files and the default options seed stayed unchanged. A reviewed, backed-up
owner-scoped refresh added only five geometry fields to 57 existing line
records in 19 sidecars. `blammed` needed a separate reviewed plan because its
old sidecar contained Hard only; Easy and Normal were appended after their
installed native charts were shown semantically identical to the fresh
preview (788 and 858 source rows), while older Hard metadata was preserved.
Backups: `tmp/import-refresh-backups/20260925T105548024485Z` and
`tmp/import-refresh-backups/20260925T105913703430Z`. Import and plan receipts:
`tmp/dsides-line-refresh/receipt.json`, `line-only-plan.json`, and
`blammed-plan.json`. Twelve refresh tests passed.

The first strict accelerated Endless Hard replay after the refresh reached
the natural end and complete 464/464 event dispatch, but found one source
`beatHit` failure: direct iteration of a Codename strumline. The shared line
object now exposes its live receptor iterator, with a focused test. The
following `./run.sh build` and strict offscreen Endless Hard replay passed:
natural song end, 464/464 events, zero script diagnostics, zero missing
modifiers, and normal exit. The private default settings overlay was used
and personal options retained the same SHA-256. This is a bounded runtime
pass, not direct visual comparison of FunkinModchart output. Evidence:
`tmp/dsides-line-refresh/endless-full-result.json`,
`endless-iterator-result.json`, and their named logs under
`tmp/runtime-smoke/logs/`.

Monster Hard exercises a fourth **visible** GF-role source line with 49
authored notes. The first accelerated offscreen run reached its natural end
but failed strict diagnostics for old Sparrow `char.png` scripts, missing
`graphicCache`, and numeric JSON parameters passed to `Std.parseInt`. A
reviewed owner-scoped refresh replaced exactly 15 importer-generated character
scripts with the new generated atlas API and backed up originals at
`tmp/import-refresh-backups/20260925T111818185691Z`; protected owner assets and
personal/default settings were unchanged. Focused refresh tests passed (5/5).
The shared numeric parsing bridge and owner-scoped graphic cache also have
focused tests. The next canonical `./run.sh build` passed. Monster Hard then
loaded BF/GF Animate frames and reached the natural ending with no character
initialization or graphic-cache binding error. It still failed strict native
checks with 21 diagnostics: the shared stage-placement guard prevented all
source strumline objects for a stage script, so `spookyEvil` and Change
Character accessed null lines and the source `cpu` alias was unavailable.
Its `postUpdate` also reached an unimplemented receptor `noteAngle` field.
The measured source instrumental ends at 177,804 ms while 34 of the 127
authored chart events occur afterward; all 93 events due before audio end
were dispatched. The generic smoke marker now records `dueEvents` separately
from `totalEvents`, and the full-song gate checks the due count. The stage,
receptor and visual/cutscene parity gaps remain open. Evidence:
`tmp/dsides-line-refresh/monster-full-result.json`,
`monster-full-v2-result.json`, the corresponding logs under
`tmp/runtime-smoke/logs/`, and the backed-up refresh plan.

The next canonical build passed after shared Codename note-angle presentation,
direct strumline iteration, and a bounded stage-placement exception for extra
actors were added. Seventeen focused tests passed. Monster Hard v3 again
reached its natural ending with 93/93 events due before audio completion;
the 127 total includes 34 authored after the 177,804 ms instrumental ends.
Strict validation still failed with 21 diagnostics. The selected-owner camera
sidecar identifies `spookyEvil`, but the native actor-plan loader rejected the
stage identity before attaching the four source lines. The chart omits its
stage field, so legacy song-name fallback supplied `spooky` to the loader;
the importer metadata and mounted source both select `spookyEvil`. This is an
engine identity resolution gap, not a reason to alter the donor chart. Evidence:
`tmp/dsides-line-refresh/monster-full-v3-result.json` and
`tmp/runtime-smoke/logs/dsides-monster-four-line-v3.process.log`.

An opt-in Codename state trace uses `--codename-state-trace` without changing
ordinary startup or enabling chart smoke routing. The private FNAS full-room
replay reached rooms one through four and logged the source `it's over` final
outcome. Its 1.6-second timer requested `MainMenuState`; the engine accepted
the switch and entered the new state's pre-create hook, yet the rendered frame
remained black for over 15 seconds. This narrows the remaining issue to state
creation, transition or rendering after the accepted request. The route used
Xvfb, dummy audio, default test options and the runtime lock, and did not
change donor scripts. Evidence:
`tmp/fnas-minigame-full-route-v4/full-route.process.log` and the route's
screenshots and receipt under `tmp/fnas-minigame-full-route-v4/`.

The Psych archive was then imported with real media into a disposable native
runtime under `tmp/psych-archive-real-import/`. Native Auto discovery found 26
songs, imported 26 with zero chart failures, and copied 847 supported assets.
All 76 chart difficulties for those songs have the source note-row count and
the same selected-owner manifest; all 26 imported instrumentals match the
archive bytes. `ridge` and `smash` remain missing because the source archive
does not contain their instrumentals. The importer reported one explicit
dependency gap: `noteSkins/NOTE_assets` has no sheet in the archive. The
private 78-row preflight therefore reports 76 ready and two blocked. A strict
offscreen Bopeebo Easy natural-ending replay passed with no tagged script
diagnostics. These receipts do not establish source visual/audio parity for
the remaining rows. Evidence: `tmp/psych-archive-real-import/result.json`,
`private-matrix.json`, `private-preflight.jsonl`, and `bopeebo-easy-v1.json`.
The next strict 2Hot Easy private replay reached its natural 120,000 ms ending
with no due chart events, but failed source behavior checks: `pico-playable`
and its gameplay health icon were not resolved, and `phillyStreets` fell back
to the neutral stage. Source character and stage JSON definitions exist in
the archive's `base_game/shared` tree. The generic Psych importer/runtime
resolution path therefore remains incomplete despite note and audio parity.
Evidence: `tmp/psych-archive-real-import/2hot-easy-v1.jsonl` and its named
process log under `tmp/runtime-smoke/logs/`.

The first version of that private overlay mistakenly left several shared
asset directories linked to the live export. The importer added 102 files
(30,725,189 bytes) there and replaced the live diagnostic
`assets/module/import/import-report.txt`. Its asset copier checks for an
existing destination before each copy. An immediate postrun audit moved all
102 newly added files to a retained backup under
`tmp/psych-archive-real-import/live-leak-backup/` and restaged them in the
private runtime. A follow-up live-file scan found only the replaced diagnostic
report modified; its prior contents were not backed up and cannot be
reconstructed exactly. The live personal options and repository default
options retained their prior SHA-256 values. The private harness now owns the
affected folders before another run. This is an audit limitation, not a
compatibility pass or a change to donor/imported chart content.

On the same canonical build, the three inventoried Hatsune Miku V-Slice rows
passed the strict accelerated offscreen natural-ending gate with default test
settings: Fantasy Girl 01 delivered 70/70 due events, Future Sound 9/9, and
Rabbit Hole 592/592. None logged a tagged interpreter failure. This repeats
bounded gameplay checks after the current shared changes; direct source
rendering, audio mix, menus and editor parity are still separate requirements.
Evidence: `tmp/example-miku-full-20260925.jsonl` and its named native logs.

The next canonical `./run.sh build` passed with the owner-scoped hscript-ex
class loader, imported Psych character atlases, and Codename stage-identity
fix. Twenty-two focused checks passed. Monster Hard v4 selected the authored
`spookyEvil` stage and reached its natural ending, but the live chart's older
`bf`/`gf` primary IDs disagree with its selected-owner camera metadata's
`bf-costume`/`gf-costume`. Actor initialization refused that mismatch before
creating the third and fourth source lines. Its 19 script diagnostics are
therefore still a real compatibility failure, and a private chart replay with
source primary IDs is pending. Evidence:
`tmp/dsides-line-refresh/monster-full-v4-result.json`.

The exact-owner private Monster chart replay retained the source
`bf-costume`/`gf-costume` primary identities and materialized the extra
`bambino` actor. It reached the 271,946 ms source-audio ending with 127/127
events dispatched. Strict validation still failed: the shared `Change
Character` script read an absent `stage.characterPoses` map three times, and
the post-switch bitmap cache sweep destroyed a graphic referenced by the
new sticker transition, exiting with native code 255. The stage pose map now
comes from validated Codename XML slots, and the extra cache sweep has moved
before new-state creation; both await a canonical rebuild and repeat native
check. The private chart is not yet a live refresh. Evidence:
`tmp/dsides-line-refresh/monster-full-private-v5-result.json` and its named
process log under `tmp/runtime-smoke/logs/`.

The follow-up Monster private replay cleared those diagnostics but still
crashed after its sticker transition because `VictoryLoopState` allocated
graphics in its constructor before Flixel destroyed the previous state.
Deferring that construction until the state factory runs after teardown
resolved the crash. Monster Hard then passed strict natural-ending replays
against both its private source chart and a one-chart, owner-scoped installed
refresh: 127/127 source events, source primary and extra actors, no script
diagnostics, and a clean exit. The installed chart was backed up automatically
at `tmp/owned-chart-backups/1790342471-737408/`; the preview/live chart hashes,
selected owner, and options were checked by the refresh tool. This is a
complete-song gate for one difficulty, not all D-Sides visual/audio/camera
parity. Evidence: `tmp/dsides-line-refresh/monster-full-private-v7-result.json`,
`monster-owned-chart-refresh-receipt.json`, and
`monster-full-installed-v8-result.json`.

A second Psych archive import in a fully private asset tree imported 26 songs
with zero import errors and copied 851 assets. The referenced
`noteSkins/NOTE_assets` sheet and XML now materialize from the sibling
`assets/shared` root, along with all three source `pico-playable` Sparrow
atlases and its gameplay icon. Scan reports 31 missing dependencies, mostly
compiled Psych stage classes; import success does not clear them. 2Hot Easy
reached its natural ending, but the first generated multi-atlas script used a
constructor unavailable in this fork's HScript `FlxAtlasFrames` facade and
rendered zero Pico frames. The shared renderer now calls the existing
`combineSparrow` API. After a backed-up, private-only generated-script
refresh, the same native replay rendered 421 Pico atlas frames and the
remaining strict diagnostic was the explicitly unsupported source
`PhillyStreets` class. That v2 replay used a manual private script refresh;
the clean native reimport is recorded below. Evidence: `tmp/psych-archive-real-import-v2/result.json`,
`2hot-easy-v3-result.json`, `2hot-easy-v4-result.json`, and the owner's
private `assets/module/import/import-report.txt`.

The clean v3 reimport on the rebuilt binary used a separate fully private
runtime with no asset symlinks. It imported all 26 source-audio songs with zero
import errors, 851 copied assets, and 31 scan-time missing dependencies. The
compiled-stage findings span `StageWeek1`, `Tank`, `Limo`, `PhillyStreets`,
`Mall`, `School`, `PhillyBlazin`, `SchoolEvil`, and `MallEvil`; repeated chart
references do not make these executable source stages. The
generated selected-owner `pico-playable` script contains `combineSparrow`
without a manual refresh. An offscreen 2Hot Easy natural-ending replay
attached its 421-frame atlas, selected the expected owner, and emitted no
other script diagnostics. It still logged the compiled `PhillyStreets` stage
as unsupported, so the chart does not pass source parity. The live options,
import report, character registry, and installed 2Hot chart hashes were
unchanged. Evidence: `tmp/psych-archive-real-import-v3/result.json` and
`2hot-easy-native-result.json`.

A read-only class audit maps these nine compiled stages to all 76 imported
archive chart rows and names their source callbacks, assets, cutscenes,
effects, and note handlers (`tmp/psych-compiled-stage-audit.md` and `.json`).
Eight target HScript stages cover only portions of those classes;
`PhillyBlazin` has no target stage script. Completing this within the goal's
shared-layer rule requires a general owner-scoped compiled-stage execution or
import translation path plus common stage services, followed by source
behavior checks for every affected chart. Hand-editing individual target
stage scripts would not satisfy that rule.

A direct source-class feasibility probe confirms the current loader cannot
execute those archived classes as-is. `StageWeek1` parses in isolation but its
wildcard stage-object import is rejected, and its `objects.Character`
dependency uses unsupported `final` syntax. `PhillyStreets` stops at its own
`enum` declaration; its dependencies additionally use `using`, aliased
imports, and more `final` and `enum` declarations. The existing owner-scoped
class loader is wired to Codename states only, while PlayState and StageHelper
have no Psych `BaseStage` class host or lifecycle delegation. A shared parser,
import, and stage-runtime layer is required before source callbacks can be
tested. This is a feasibility result, not a stage-parity result. Evidence:
`tmp/psych-class-runtime-feasibility.md`.

A bounded owner-loader extension now expands referenced wildcard modules and
normalizes initialized `final` declarations, conflict-free aliases, and
`StringTools` calls on statically proven String receivers. A standalone owner
fixture executes those forms and rejects reassignment, dynamic extension
calls, and shadowed aliases; the existing owner-scope fixture also passes.
A direct read-only archive probe moves `StageWeek1` past its wildcard import
but stops in `objects.Character` at `new Map<String, Array<Dynamic>>()`
(`EUnexpected(<)`); `PhillyStreets` still stops at `enum NeneState`.
Neither source class executes, and the Psych `BaseStage` host remains absent.
Evidence: `tools/tests/test_codename_script_class_loader_owner_syntax.py` and
the mounted source probe reported in this session.

The Psych importer now preserves bounded `.hx` source files under the exact
selected import owner's `source/` namespace. It rejects path escapes, oversized
or unreadable source, and destination links outside the owner; existing owner
files are never overwritten. A focused private fixture passed. A disposable
import of the extracted archive copied **157/157** Haxe modules with zero
rejects; `StageWeek1`, `PhillyStreets`, and `BaseStage` hashes matched source,
and every copied path resolved under the private owner. The private tree was
removed and the live import was unchanged. This supplies authored source for
a later runtime and does not execute it. The combined canonical
`./run.sh build` passed after this importer and the HL17 options changes.
Evidence: `tools/tests/test_psych_source_import.py` and
`tmp/example-psych-source-hl17-combined-build-retry.log`.

The pasted Wacky World Freeplay `EUnknownVariable(hxcAssetRoot)` trace is no
longer reproducible on the current canonical build. A private owner-registry
offscreen route entered real Freeplay, parsed and executed `PVE_VideoModule`,
then returned to the main menu. The generated module reads `hxcAssetRoot`,
and `HxcFreeplayRuntime` seeded that variable from the selected owner before
execution. The exact error and other HXC Freeplay diagnostics were absent;
live settings and protected assets were unchanged. This covers the Freeplay
module path, not all Wacky World video playback. Evidence:
`tmp/wacky-freeplay-assetroot-recheck-20260925/verification-summary.json`.
A focused Haxe-interpreter regression now extracts the real Freeplay seeding
method and checks two separate owners: each module initializer, later update
callback, and `Paths` proxy sees its own manifest root. Its five focused tests
pass. This pins the reported root-variable failure without treating one menu
visit as complete Wacky World parity (`tools/tests/test_hxc_freeplay_routing.py`).

The pasted HL17 options import failure has a separate source syntax cause:
its owner-scoped `HLOptionsWindow.hx` ends a multiline array field with `]`
immediately before a `private var` declaration. The shared class loader now
retries only that bounded field-terminator repair after a parse failure.
Synthetic and mounted HL17 module tests register the options class without
altering donor or installed source. Native options-menu behavior still needs
replay after the menu's missing imported art is addressed.

The rebuilt private HL17 import copied all eight missing menu image files,
matching their donor hashes. An add-only, owner-scoped refresh installed just
those eight absent files into the existing selected owner, with a per-file
rollback list; the catalog, existing imported content, and live options hashes
were unchanged. Private offscreen main-menu routing rendered its four rows,
and the options path passed the earlier missing `Reflect` binding after the
shared binding was added. It then reached a separate HScript-ex class-method
reentrancy failure (`EUnknownVariable(gameplay)`); options behavior remains
unverified. Evidence: `tmp/hl17-menu-native/private-import-menu-asset-receipt.json`,
`owner-scoped-refresh-receipt.json`, and the private native menu logs.

A focused HScript-ex regression reproduced the HL17 options initializer's
outer locals disappearing after it called another script-class method. The
repository-owned class patcher now saves and restores the caller's interpreter
frame, including the exception path; its standalone class test passed from a
fresh upstream patch twice. On the combined native build, opening Options no
longer reports `EUnknownVariable(gameplay)`. It next reports an inherited
native `visible` property as absent from `HLOptionsWindow`; control-key reads
are also unresolved, so the menu remains an active parity defect. Evidence:
`tmp/hl17-menu-native/native.process.log` and the focused
`test_codename_script_interp.py` class regression.

The next shared HScript-ex patch resolves inherited native properties,
including false and null values, while rejecting truly absent fields. The
options adapter maps Codename `P1_` and `P2_` keys to the primary and
alternate keyboard slots of native player one, and exposes key labels. Its
focused interpreter tests passed. The patcher also migrated the existing
partially patched local hscript-ex cache safely; the canonical `./run.sh build`
then succeeded (`tmp/hl17-owner-class-combined-build.log`). In a protected
offscreen Xvfb route, the owner menu opened the Options constructor with no
class or parser errors, and live options/catalog and donor hashes were
unchanged. The captured Options window is still a blank gray panel with
unreadable multicolor glyphs. The log retains two guarded null writes and
explicit unsupported option reads for gameplay shaders, low memory mode,
VRAM-only sprites, and auto pause. The native route's `status: passed` records
constructor reachability only and is **not** a visual, menu-interaction, or
settings parity pass. Evidence: `tmp/hl17-menu-native/result.json`,
`hl17-options-click.png`, and `native.process.log` in that directory.

The refreshed 255-row source matrix separates installed coverage from
private imports. The live export has 168 owner/variant-matched structural
rows, 155 with source note-row count parity. Private import evidence covers
99 structural rows, including 81 absent from installed coverage, for 249/255
combined structural rows. The private D-Sides overlay has 22/22 chart hashes,
note counts, event counts, and selected-owner manifests matching its import
receipt, but its prior startup gate failed strict diagnostics on all 22. The
six still structurally uncovered rows are PERFEXION Extra/Extras/Gallery,
Psych archive ridge/smash (without source instrumentals), and the empty DDTO
`baka` alternate-normal candidate. No structural row is counted as source
gameplay parity. Evidence: `tmp/example_mods_chart_matrix.json`,
`tmp/example_mods_chart_matrix_refresh_2026-09-25.md`, and
`tmp/example_mods_chart_matrix_dsides_private_overlay_audit_2026-09-25.json`.

A read-only audit of the six structurally uncovered rows traced them to source
content and inventory semantics rather than a demonstrated importer failure.
PERFEXION Extra/Extras share one chart payload and have no package audio;
Gallery has zero notes and no source stage definition. Psych ridge/smash have
no source instrumentals or archive owner provenance. The DDTO++ baka
alternate-normal note map is empty and is not declared by its variation
metadata; the 790-note alternate chart is already imported. Paths and hashes
are in `tmp/uncovered-six-audit.json`.

On the next canonical build, a private offscreen startup sweep checked all
22 D-Sides chart rows against source hashes and the exact selected owner.
All 22 reached PlayState, passed owner assertions, and preserved protected
live files and default test options; 19 passed strict diagnostics. Bomb Bash
Hard wrote a null value to the `curveX` shader uniform because HScript left
an uninitialized typed `Float` at null; shared top-level primitive-field
hoisting now supplies Haxe's `0`/`false` defaults. A rebuilt, owner-pinned
Bomb Bash strict native replay passed without script diagnostics. Ghastly
still fails in both visits: its three primary actors are present, but the
stage's three dark actors at occurrence index 1 are absent and the source
`alpha` writes hit null. Tutorial's `iconP2` object was present; the native
HScript null-call guard also reports a missing method with the same message.
The shared `HealthIcon.setIcon` alias now delegates to `switchAnim`, and a
rebuilt owner-pinned Tutorial strict native replay passed without diagnostics.
The shared stage-placement analysis now distinguishes indexed actor aliases
whose only writes change alpha from aliases that alter geometry. The rebuilt
Ghastly two-visit strict replay constructed all six expected actors, including
the three secondary dark actors at occurrence index 1; both visits and the
Bomb Bash replay finished with zero script diagnostics. Protected live files,
repository default options, and private default options matched their
pre-run snapshots. That makes 22 of 22 D-Sides rows with a strict startup
pass across the initial sweep and targeted replays. These are startup gates only, not
song-wide source parity. Evidence:
`tmp/dsides-line-refresh/current-22-startup-result.json`,
`ghastly-bomb-post-float-result.json`, and
`tmp/tutorial-icon-probe/native-result.json`.

The FNAS private full-room route passed on that build: rooms one through four,
the authored final `it's over` outcome, native switch request, source-global
redirect to the selected owner's `FnasMainState`, and a rendered final menu
(measured luma 0.0817). The run stayed in private Xvfb with dummy audio and
default test options; the installed asset snapshot and default options were
unchanged. This verifies that route, not the installation's remaining pause,
retry, cutscene, editor, and source frame/audio parity. Evidence:
`tmp/fnas-minigame-full-route-v5/result.json`, `full-route.process.log`, and
`final-owned-menu.png` in the same directory.

The parallel full Python suite on that build ran 1,203 tests across 344
modules in 126.3 seconds, with 61 skips and 13 failing modules. The failures
are stale standalone fixture dependencies introduced by shared source changes
(for example, omitted `CodenameStrumlineLayout` and `psychImageReferences`
fixture bindings); focused repairs and rerun are underway. This suite result
is **not** a passing test gate.

The next full suite ran 1,208 tests across 345 modules in 162.2 seconds,
with 61 skips and three remaining fixture failures. The two stage harnesses
omitted the new `characterPoses` map, and the mounted Auto scanner fixture
omitted three Psych stage-check helpers and their source type. After updating
those harnesses, the exact mounted scanner test passed, and the full suite
passed **1,208 tests across 345 modules in 237.6 seconds, with 61 skips and
zero failures** (`tmp/example-full-suite-post-psych-fixtures.log`). A focused
Codename stage test subsequently also verified that published camera offsets
reach `characterPoses` and are cleared on teardown. Passing source tests do
not imply the remaining source visual and scripted behavior is compatible.

The current HL17 private native Options route now renders a readable window,
title, tabs, rows, and checked controls without the empty Flixel logo fallback.
Its reflected Downscroll edit persisted from `false` to `true` in private
default settings and remained checked after a second native process started.
The installed settings and catalog, repository seed settings, and donor source
hashes were unchanged. This is one menu interaction, not HL17 menu parity:
two null `alpha`/`visible` class-method writes have not been attributed to an
exact source expression. That earlier build also emitted three
unsupported-toggle diagnostics at construction even when a script never read
those fields. Evidence: `tmp/hl17-menu-native/downscroll-restart-result.json`,
`downscroll-after-restart.png`, and the two session logs in that directory.

On the next build, the facade initialized those three unsupported fields
silently because construction is not a source read. Its unsupported writes
still diagnose, and the HL17 native harness keeps an explicit capability list
that prevents a false menu-parity pass. Actual source uses remain unimplemented:
`gameplayShaders` in Linkin Teen Parks, `lowMemoryMode` around stage 17's
optional Flx3D view, and the `gpuOnlyBitmaps` menu pointer.
The rebuilt private menu route still rendered the Options window and persisted
Downscroll across restart with protected hashes unchanged; it remained
`status=partial` with two null writes. The class loader reported three static
owner-relative unsupported pointers at `source/HLOptionsWindow.hx:52`, `:62`
and `:67`, separately from observed runtime errors. A follow-up shared parser
scan also covers direct `Options` uses in classless stage/song companions,
with token-mask fixtures that exclude comments and strings. These diagnostics
identify source references; they do not implement the missing options.

The owner-scoped Psych Haxe loader now parses additional bounded source forms:
referenced wildcard and aliased imports, initialized `final` declarations,
generic constructor types whose concrete target is known, unused bare foreign
imports, untyped prefix `cast`, and StringTools calls on statically proven
native FlxSprite animation names. The owner-scoped nullable Lime text facade
and narrow Flixel bindings have focused interpreter coverage. A direct mounted
`StageWeek1` probe advanced to `objects/Note.hx:429`, where
`ClientPrefs.data.noteSkin.trim()` has a source String declaration but no
owner-scoped runtime `ClientPrefs` binding, so lowering its syntax alone would
leave source behavior unresolved. No Psych compiled stage executes yet; all 76 privately imported
archive chart rows still lack compiled-stage source parity. The archive's 157
Haxe files were preserved exactly in a disposable import probe, which proves
source retention only. Evidence: `tmp/psych-native-import-audit.md` and the
focused `CodenameScriptClassLoader` tests.

The installed Hopkins Hard chart was refreshed in two owner-checked, backed-up
steps from the mounted Codename converter. The first changed only its note
sections, restoring 90 hidden girlfriend-line notes and sub-millisecond source
timing for **526/526** raw source rows. A private offscreen natural-ending
replay then exposed a stale `bf` player field against the exact owner's
`boyfriend` actor plan. The second step changed only that field. On replay,
the owner actor and camera diagnostics cleared, all 38 due events dispatched,
and the natural ending was reached with unchanged options. A rebuilt offscreen
replay after the Options constructor fix passed the strict gate with zero
interpreter errors, all 38 events dispatched and one natural song-end marker.
This verifies Hopkins Hard's accelerated botplay path, not its complete
visual/audio or editor parity. Both backups and plan/receipt hashes are under
`tmp/hopkins-note-refresh/`; the clean replay is
`post-facade-full-playthrough.jsonl` there. The matrix at that checkpoint recorded 156
of 168 installed structural rows with raw note-row-count parity. The separate
V-Slice source gameplay-row audit still distinguishes Madness's four/eight/
eight authored lanes 12–15 that upstream v0.3.2 does not route to either
playable strumline; 83 of 84 installed V-Slice difficulty rows match their
source gameplay-row count. The remaining `baka` alternate-normal entry is an
empty undeclared source variation, while its populated alternate chart is
imported. Neither row-count result establishes full source gameplay parity.

A subsequent package-wide HL17 offscreen preflight found all three Buck
difficulties installed with the expected selected owner and source
instrumentals. The accelerated botplay runs for Gordonteen Bucks, Huggyteen
Dollars, and Linkin Teen Parks each reached a natural song end and dispatched
126/126, 120/120, and 5/5 due events respectively. **None passed the strict
script gate.** Their shared stage 17 script imports Flx3DView, Flx3DUtil,
Flx3DCamera, Away3D Geometry/PerspectiveLens, and OpenFL System without an
executable owner binding; the latter two songs also import a staged but
unregistered `Bopper` Haxe class, and Huggyteen imports FlxKey. Those source
dependencies must execute before stage visuals and scripted effects can be
called compatible. Evidence: `tmp/hl17-menu-native/three-song-preflight.jsonl`
and `three-song-full-playthrough.jsonl`.
The read-only stage audit found neither Flx3D nor Away3D in the pinned local
toolchain or HL17 donor. Stage 17 requires a real `Flx3DView` model/camera
surface and `Flx3DUtil.is3DAvailable()`; its owner-scoped `plane.obj` and
`gradient.png` are already present. The OBJ names an absent `testStage.mtl`,
whose necessity is unknown without the source loader. The stage's `insert`
calls also require a FlxBasic-compatible view and correct layer moves.
Evidence: `tmp/hl17-menu-native/3d-dependency-audit.md`. A separate read-only
trace found that `Bopper.hx` is staged correctly but PlayState's song-script
loader never calls the owner class loader before rejecting `import Bopper`.
Even after class registration, its HScript proxy must safely expose its native
FlxSprite superclass to scene insertion, mutation, and one-time cleanup.

The owner class bridge is now wired into PlayState song scripts and ModState
scene insertion. A focused Haxe interpreter fixture loads the exact mounted
`Bopper.hx`, proves owner Paths and native FlxSprite mutation, and rejects
foreign, released, manually created, unsafe, or non-FlxBasic proxies. The
canonical rebuilt HL17 three-song full-playthrough sweep no longer reports
`Bopper` imports; all three still reach natural endings with their due events
but fail on the unbound 3D stage imports. Huggyteen additionally reports an
unbound `FlxKey` import, and Linkin Teen Parks now advances to an `autoPause`
facade error. The shared FlxKey enum-abstract runtime view and scoped
`FlxG.autoPause` property were added after that replay; their native checks
remain pending. Evidence:
`tmp/hl17-menu-native/post-owner-class-full-playthrough.jsonl` and the
focused owner-class/FlxKey interpreter tests.

After the HL17 source-use scanner and its standalone fixture update, the
canonical `./run.sh build` passed (`tmp/example-hl17-classless-source-use-build.log`).
The full Python suite passed **1,217 tests across 347 modules in 241.5
seconds, with 61 skips and zero failures**
(`tmp/example-full-suite-final-hl17-source-use.log`). `git diff --check` was
clean; repository seed and live personal option hashes remained unchanged.
This is the current source/build gate, not package-wide source parity or a
60/240/480 FPS native behavior comparison.

The next PERFEXION private offscreen natural-ending sweep preflighted six
rows. Extra Hard, Extras Hard, and Gallery Normal are blocked by missing
installed charts and source audio. Resonance Hard and Hardold passed the
strict accelerated botplay gate with 59/59 and 45/45 due events and natural
endings. Xfracture Hard reached its natural ending and dispatched 34/34
events, but failed the strict gate with 20 interpreter/dependency errors.
The source script order maps `compat_song_0`, `_6`, `_19`, and `_20` to
`10scriptnote.lua`, `BlackStart.lua`, `noteMoveOnPress.lua`, and `Qnote.lua`.
The `_19` watchdog exposed a shared translator defect: non-unit numeric Lua
`for` loops did not advance. The translator now advances them, and focused
ascending/descending interpreter fixtures pass. The Lua-only interpreter
now reads undeclared globals as nil and diagnoses arithmetic on nil; a LuaJIT
oracle confirmed the latter. This leaves the donor's undeclared `anglevar`
arithmetic explicitly defective rather than treating a successful chart end
as source parity. `linear` is passed as a nil optional ease value, while
`Qnote.lua` supplies undeclared `min`/`max` to `getRandomFloat`; their runtime
effects require another rebuilt replay. The actual mounted
`noteMoveOnPress.lua` translated and executed its `onCreatePost` callback in
an isolated interpreter with mocked engine reads; the dynamic step was read
once, executed its expected iteration, and terminated without a watchdog
(`tmp/xfracture-lua-audit/Fixture.hx`). The missing Xfracture girl-mad,
Night-PXT, Night-Girl, Crazy-Girl, girl icon, and bedroom visual sources are
absent from the donor package itself; available PerfeXion character/icon
bytes are materialized. Exact donor paths and conditional refresh procedure
are in `tmp/perfexion-xfracture-dependencies.md`. Evidence:
`tmp/perfexion-preflight-current.jsonl`,
`tmp/perfexion-full-playthrough-current.jsonl`, and
`tmp/lua-compat-focused.log` (34/34 tests) and
`tmp/lua-compat-all-modules.log` (38/38 Lua module tests). The canonical
`./run.sh build` passed in `tmp/example-owner-class-lua-build.log` and
preserved both settings hashes and all nine refreshed D-Sides chart hashes.
On the rebuilt native Xfracture full-song replay, the numeric-loop watchdog
and `EUnknownVariable(linear/min)` errors disappeared. It again reached a
natural ending with 34/34 due events, but the strict gate still failed on
the absent donor visual dependencies, source `anglevar` nil arithmetic, and
`noteMoveOnPress.lua` countdown arithmetic on a nil value. Its isolated
`onCreatePost -> onUpdatePost -> onCountdownTick(3)` sequence succeeds when
the shared Psych globals are seeded, so the native callback ordering or live
binding behind that last error needs a separate diagnosis. Evidence:
`tmp/xfracture-lua-audit/post-build-full-playthrough.jsonl` and its process
log. No source parity claim is made for Xfracture.

A fresh isolated D-Sides import from the exact mounted root then verified all
22 chart rows against source note origins, event counts, selected owner, and
available media while leaving the installed tree and both option files
unchanged. Nine installed Hard charts had stale note counts and, in several
cases, wrong stage or other chart fields: Bopeebo, Dad Battle, Darnell,
Endless, Fresh, Pico, South, Spookeez, and Tutorial. The owner-checked chart
refresh tool backed up and replaced **only** those nine chart JSON files from
the current converter output. All nine installed hashes now match the private
preview; exact backup paths and before/after hashes are in
`tmp/dsides-current-chart-refresh/refresh-receipt.json`. The refreshed matrix
has **165/168** installed structural rows with source raw note-row-count
parity; the three remaining raw mismatches are Vs Tricky Madness's authored
lanes 12–15, which the source game itself leaves unrouted. This is structural
and source chart-field evidence, not D-Sides visual/audio or full-song parity.
Evidence: `tmp/dsides-current-chart-refresh/result.json` and
`tmp/example_mods_chart_matrix.json`. Native replay on the refreshed charts
is pending beyond one Darnell Hard offscreen natural-ending probe: it passed
the strict script gate with zero interpreter errors, 90/90 due events, and
unchanged options (`tmp/dsides-current-chart-refresh/darnell-full-playthrough.jsonl`).
The package preflight has 18 installed ready rows and four private-only rows
whose installed owner or variant is unverified; it does not promote those
private rows to installed coverage.

The next canonical `./run.sh build` passed with the selected
`CodenameCrew/away3d` revision `ca30a80ca3c56f266fb3cd067fdeb43b0bb9784d`
and shared Flx3D bindings (`tmp/example-3d-integration-build.log`). The
owner-scoped OBJ resolver reported the mounted HL17 model's absent
`testStage.mtl`. A later instrumented offscreen run reached Away3D's resource
completion callback but reported **zero asset-complete events** and an entirely
transparent 3D snapshot at frames 1, 2, and 60. The earlier loader-finished
message did not establish model rendering; this remains an active shared-engine
loader defect. Evidence: `tmp/runtime-smoke/logs/hl17-gordonteen-3d-probe.process.log`.
The shared loader investigation traced that blank result to data type: the
owner path returned `haxe.io.Bytes`, while Away3D's parser accepts String or
OpenFL `ByteArrayData`. It silently parsed empty text from the Haxe bytes.
The adapter now converts model and mapped dependency bytes to OpenFL byte
arrays; native rendering needs a rebuilt replay before this fix is counted.
The next canonical build passed (`tmp/example-hl17-byte-health-build.log`).
Short private HL17 replays no longer report the state script's top-level
`health` error, but they fail later in `postCreate`: the selected owner lacks
the donor's `images/hud/damage/0.png`, the 3D stage reports its otherwise
present `models/plane.obj` as missing, and Huggyteen's song scope still cannot
read `camHuggy`. These are active gaps, not strict passes. Evidence:
`tmp/hl17-menu-native/byte-health-reprobe.json` and the paired process logs.
The current importer now enumerates direct PNG children of a literal folder
used in a dynamic Codename `Paths.image` expression, under the selected owner
with a bounded scan. The focused importer fixture passed 10/10. An exact-owner
HL17 repair plan selected only the donor's four `images/hud/damage/0.png`–`3.png`
files, with matching donor hashes and zero conflicts. The checked add-only
apply created those four files; 404 existing planned inputs, both owner
registries, and personal options stayed unchanged. The post-apply plan has
zero candidates and conflicts. Evidence: `tmp/hl17-gameplay-hud-repair/plan.json`,
`post-apply-plan.json`, and
`tmp/import-refresh-backups/20260925T195757523184Z/created.json`.
The rebuilt private startup replays now pass the missing HUD PNG lookup but
still fail strict diagnostics. The state `postCreate` reaches
`playerStrums.onMiss.add` and `playerStrums.cpu`, which are source StrumLine
fields absent from the current native-bound `playerStrums`; the callback
failure again releases its `camHuggy` export. The 3D smoke marker proves the
view is the owner-bound `CodenameFlx3DView`, yet its model read returns null
for an installed OBJ. Both shared bindings are under investigation. Evidence:
`tmp/hl17-menu-native/post-owner3d-hud-probe.json` and
`tmp/runtime-smoke/logs/hl17-gordonteen-owner3d.process.log`.
The next canonical build (`tmp/example-hl17-3d-dynamic-build.log`) corrected
the native temporary's inferred type. Gordonteen's private 3D probe now emits
one geometry and one mesh asset, then completes with two assets; bitmap samples
change from zero alpha on frame 1 to ten nontransparent, nonwhite samples on
frames 2 and 60. This proves the selected-owner model parsed and painted in
the offscreen native renderer, although stage image/source placement still
needs visual comparison and the state HUD script still fails its strumline
callbacks. Evidence: `tmp/hl17-menu-native/3d-dynamic-probe.json` and
`tmp/runtime-smoke/logs/hl17-gordonteen-3d-dynamic.process.log`.
An isolated Xvfb capture at nine seconds now visibly shows the authored
gray-white gradient floor behind the characters and desk; the previous
capture had a plain white background. The capture kept repository and live
options byte-identical. This is visual evidence for the plane, not a
frame-by-frame source comparison. Evidence:
`tmp/hl17-menu-native/gordonteen-3d-stage-after-bytes.png` and its process log.
The pasted HL17 menu import diagnostics are stale relative to the current
owner class loader: the private native menu reached `codename-imported-create-ready`
without unsupported import/module errors, and its Options click instantiated
the owner window and completed without a script failure. This does not verify
the Load or Credits buttons or the Seven editor shortcut; `EditorPicker` is
still an explicit unavailable API. Three Codename Options fields also remain
nullable by design, and the menu probe logged unattributed null writes to
alpha/visible. Evidence: `tmp/hl17-menu-native/native.process.log`,
`tmp/hl17-menu-native/result.json` and its Options screenshot.
An offscreen three-song HL17 Buck replay reached natural endings and dispatched
126/126, 120/120, and 5/5 due events with unchanged personal options.
Gordonteen Bucks had no script errors. Huggyteen Dollars and Linkin Teen Parks
still failed the strict gate because their song scripts read `camHuggy`, which
the donor custom PlayState exports with `scripts.set` and this engine has not
yet propagated to the song scopes. Neither ending alone establishes visual or
menu parity. Evidence: `tmp/hl17-menu-native/post-3d-full-playthrough.jsonl`.
An additional private Xvfb capture at nine seconds showed the Gordonteen
characters and desk over a plain white background. The process log reported
`Loader Finished`, but that image alone did not establish that the authored
gradient OBJ plane rendered. The model callback/render-snapshot path remains
under review. The capture used dummy audio and seed options, then confirmed
both options files retained their original bytes. Evidence:
`tmp/hl17-menu-native/gordonteen-3d-stage.png` and
`gordonteen-3d-stage.process.log`.

The Xfracture countdown nil trace has a separate shared-engine explanation:
Psych's `getPropertyFromGroup('strumLineNotes', index, 'y')` reads a combined
enemy-first/player-second receptor list, while this fork exposed an empty
legacy `strumLineNotes` group. A live combined receptor lookup and 4-key/8-key
focused fixture have been added. The rebuilt Xfracture Hard replay reached a
natural ending with 34/34 due events; the former `noteMoveOnPress.lua`
countdown nil arithmetic was absent. Strict compatibility still fails on the
donor's missing character, icon and stage sources and `10scriptnote.lua`'s nil
`anglevar` arithmetic. Evidence:
`tmp/xfracture-lua-audit/post-combined-group-playthrough.jsonl`.

The pre-final shared-engine snapshot passed `python3 tools/run_tests.py` with
1,224 tests across 350 modules, 61 skipped and zero failures in 247.8 seconds.
This run preceded the latest HL17 model-byte and state-global changes; those
changes require focused tests, another canonical build, and native probes
before their behavior can be claimed. Evidence:
`tmp/example-full-suite-state-3d-psych.log`.
The mounted `10scriptnote.lua` still reads an undeclared `anglevar` in its own
Lua state. A local of the same name in a separate event script cannot supply
that value; the donor defect remains explicitly diagnosed rather than silently
filled by the compatibility layer.

The shared Codename strumline view now supplies the native player's live
`cpu` property and `onMiss` signal to selected-owner state scripts. On the
rebuilt short offscreen check, Gordonteen Bucks passed the strict native
diagnostic gate with the state script active and the 3D plane rendered.
Huggyteen Dollars still produced twelve null-index diagnostics before
PlayState readiness; its state HUD and song callback are under investigation.
These are startup probes, not full-song or source-parity passes. Evidence:
`tmp/example-hl17-strum-bridge-build.log`,
`tmp/hl17-menu-native/post-strum-bridge-probe.json`, and the paired
`tmp/runtime-smoke/logs/hl17-*-strum-bridge.process.log` files.

On the rebuilt private HL17 menu route, Options, Load and Credits each
reached the selected-owner window with default test options and the game
stayed alive. Load rendered a blank portrait: the installed owner lacked
three `images/songSelect/` PNGs that exist in the donor, although its
placeholder was present. The current importer already selects direct PNGs
from the class source's dynamic `Paths.image("songSelect/" + value)` folder;
this was stale installed output. An exact-owner checked create-only refresh
added the three absent portraits with matching hashes and zero conflicts,
preserving the existing placeholder, owner catalog, and both settings files.
The refreshed private Load screenshot visibly shows the donor Gordonteen
portrait; Options, Load and Credits still reach create-ready without a state
script or missing-asset diagnostic. The two untagged null-write diagnostics
were traced to the selected owner's `data/global.hx` update callback: its
`postStateSwitch` initializer had never been dispatched, leaving the volume
tray and tick objects null. The shared global runtime now dispatches that
owner-scoped lifecycle hook after state creation and applies source/callback
context to diagnostics. A rebuilt private offscreen click probe opened
Options, Load, and Credits, reached owner create-ready in all three cases,
kept the game alive, and reported zero runtime diagnostics. Default private
options remained unchanged. This verifies bounded menu entry, not every
setting interaction. Evidence:
`tmp/hl17-menu-native/window-click-probe.json`,
`tmp/hl17-menu-native/hl17-load-window-click.png`, and
`tmp/hl17-menu-native/song-select-assets-refresh-{plan,backup,receipt}.json`.
The window-entry probe has not yet exercised options tabs/rebinding, the
three-song Load carousel and launch, Credits links, Back/Quit, or the editor
shortcut. Source inspection found `CoolUtil.openURL` missing from the credits
binding; the shared facade now passes validated absolute HTTP(S) URLs to
Flixel's browser action. An injected-opener test covers the authored links
and rejects unsafe forms without launching a browser; an actual Credits row
click remains unverified. `EditorPicker` is still mapped to an unavailable API, and
`gameplayShaders`, `lowMemoryMode`, and `gpuOnlyBitmaps` present as unsupported
option fields. Those are active menu and gameplay coverage gaps despite the
three clean window-entry checks. The source Quit row calls `Sys.exit(0)`;
the current compatibility facade returns to the native main menu, so its
meaning also differs from the donor until explicitly verified or changed.

The current native Gordonteen Bucks full-song replay used the selected owner,
its state script, private default options, dummy audio, and the runtime build
lock. It exited normally at the source audio length (114.487 s), dispatched
126/126 due events, and logged no interpreter errors. The private options
remained unchanged. This clears its strict full-song runtime gate, while
source frame/audio comparison, manual input, endings outside practice mode,
and repeat switching are separate checks. Evidence:
`tmp/hl17-menu-native/post-state-gordonteen-full.jsonl`.

A private Psych archive source-only refresh copied 157/157 selected-owner Haxe
modules with matching donor hashes and zero overwrites. All 251 preexisting
owner files outside `source/`, the Dad Battle Easy chart, owner manifest,
import report, and options retained their hashes. The first offscreen native
Dad Battle Easy probe used its real stems and default test options; it reached
the natural ending and logged three Spotlight event dispatches. It did **not**
execute `StageWeek1`: the class constructor tried to resolve the imported
`backend.BaseStage` as `states.stages.BaseStage`, producing an explicit
superclass binding error and native-stage fallback. No compiled-stage parity
is claimed. Evidence: `tmp/psych-archive-real-import-v3/source-refresh-{backup,receipt}.json`
and `stageweek1-native-result.json` with process log and spotlight screenshots.

The Huggyteen null-index diagnostics were traced to the imported
`Bopper.setCharacter` class method, which assigns a default local array.
The tracked hscript-ex patch had routed that local assignment to a pending
native-super field, leaving the local null; four Boppers produced the 12
diagnostics. The shared patch now gives method locals and formal parameters
precedence over native-super/pending fields. The mounted Bopper fixture and
the canonical build pass; Huggyteen Buck's rebuilt strict short native start
reports zero diagnostics and unchanged options. Its full-song replay is still
pending. Evidence: `tmp/example-hscript-local-assignment-build.log`,
`tmp/hl17-menu-native/post-local-assignment-probe.json`.
The following Huggyteen Buck natural-ending run revealed a separate late
failure around 45.612 s after an authored `Screen Alpha` event: native HScript
exited 255 with `The object does not have the property "alpha"`, so no
`song_end` marker was recorded. It is an active full-song gate failure despite
the strict startup pass; the property receiver is under investigation.
Evidence: `tmp/hl17-menu-native/post-local-huggy-full.jsonl` and its
`tmp/runtime-smoke/logs/1-huggyteen-dollars-huggyteen-dollars-buck.process.log`.

The rebuilt Psych archive superclass alias passes focused mounted-class
instantiation tests, but the private Dad Battle Easy native replay now
segfaults during `StageWeek1` creation, immediately after the selected-owner
`stage.json` is applied and before `stage_loaded` or any compiled-stage
execution marker. The test kept real donor stems and default options; no
Spotlight callback or natural ending occurred in this run. This is a new
native runtime blocker, under offline backtrace investigation, not a stage
compatibility pass. Evidence: `tmp/example-psych-super-alias-build.log` and
`tmp/psych-archive-real-import-v3/stageweek1-native-result.json` with process
and marker logs.

The user-provided transition compile diagnostics were checked against the
current source and canonical `./run.sh build`: the current transition bridge
builds successfully, including its transition-owned `flipY` camera field.
The pasted Wacky World `hxcAssetRoot` failure also does not reproduce in the
current owner-scoped Freeplay module interpreter. A focused generated-module
initializer test passes, and the rebuilt binary passed a strict offscreen
Wacky World Hard startup/gameplay probe with zero diagnostics and unchanged
options. This is a bounded load check, not a full song or source-parity pass.
Evidence: `tmp/example-user-pasted-current-build.log`,
`tmp/example-user-wacky-current-native.json`, and
`tmp/runtime-smoke/logs/example-wacky-hard.process.log`.

The private Psych Dad Battle Easy chart lists both MP3 and Ogg copies of each
split vocal stem. Its native run logged MP3 decode failures; trying both
encodings could also double the voice mix where MP3 decoding succeeds. The
shared mixer now selects one encoding per stem basename and prefers the
native audio extension. The focused fixture exercises alternate encodings
and keeps Player and Opponent separate. This change is in the rebuilt native
binary. The next private native Dad Battle Easy process log contains no MP3
stem load errors, but the active Psych stage crash prevents a full audible
replay yet. Evidence: `tmp/psych-archive-real-import-v3/stageweek1-native-process.log`.

## 27 September continuation: compiled-stage replay and remaining gates

The canonical `./run.sh build` completed with the owner-scoped HScript-ex
native group and tween argument bridges. In a private Psych archive runtime,
Dad Battle Easy now loads and executes the source `StageWeek1` class. Its
`Dadbattle Spotlight` event turned on at 32,000 ms, retargeted at 42,667 ms,
and turned off at 53,333 ms. The accelerated offscreen botplay run reached
the natural ending at 86,666 ms with 23/23 due events and exited 0. It used
Xvfb, SDL dummy audio, the runtime lock, and the repository's default test
options; the private options stayed unchanged. No interpreter diagnostics or
MP3 stem decode errors occurred. The single alpha access trace is an
informational smoke probe, and the earlier spotlight screenshots are from a
different binary, so current-build visual and audible parity are unverified.
Evidence: `tmp/example-psych-tween-huggy-alpha-build.log` and
`tmp/psych-archive-real-import-v3/stageweek1-current-alpha-verification.json`.

The next private archive probe, 2Hot Easy, reached its natural ending with
the current binary but did not run its `PhillyStreets` source class. The
HScript-ex parser rejected its top-level payload-free `NeneState` enum and
the runtime reported the compiled-stage fallback. This is an explicit
source-stage compatibility failure even though gameplay and the ending
completed. The shared enum path and the stage's further dependencies are
under investigation.

The first broad automated run on this source snapshot reported 1,239 tests
across 356 modules, 61 skipped, and 14 failed modules. Thirteen failures
were isolated HScript tests that compiled `ScriptClassScope` without Flixel
while its new native argument bridge imported Flixel types unconditionally;
the bridge is now conditional on Flixel compilation. A focused rerun of the
affected modules left one fixture that omitted Flixel's setter-backed camera
alpha property; that stub has been corrected. The temporary Codename alpha
diagnostic was also removed after locating a native reflection failure on
`FlxCamera.alpha`. Focused interpreter, options, character, and compiled-stage
tests pass; the complete suite and native Huggyteen replay still need to be
rerun after the next coordinated build. Evidence:
`tmp/example-psych-tween-huggy-alpha-tests.log` and
`tmp/example-prebuild-focus-tests-retry.log`.

The next coordinated `./run.sh build` passed, and the complete automated
suite then passed **1,242 tests across 357 modules**, with 61 skipped and
zero failed. The two options files retained their prior SHA-256 values:
repository seed `0693e647…` and live personal file `2a85e43c…`.
Evidence: `tmp/example-alpha-enum-editor-build.log` and
`tmp/example-alpha-enum-editor-tests.log`.

This build did **not** clear two native runtime gates. The private HL17
Huggyteen Bucks full replay still exits 255 at 45.612 seconds on an `alpha`
property write; the typed FlxCamera bridge is compiled, but the script's
actual receiver at failure is a dynamic value rather than that camera.
The shared interpreter's variable/receiver resolution is being traced. The
private Psych archive 2Hot Easy replay reaches `song_end` with its default
options unchanged, but `PhillyStreets` still falls back: the initial simple
enum normalizer mistakes a valid comma-separated switch case for a shadowing
declaration and rejects `STATE_LOWER`. A bounded parser correction is in
progress. These are explicit failures of source behavior, not passing stage
or full-song compatibility claims. Evidence:
`tmp/hl17-menu-native/alpha-receiver-full-20260927.process.log` and
`tmp/psych-archive-real-import-v3/philly-streets-2hot-alpha-enum-result.json`.

The HL17 key-7 editor picker opens in an offscreen private native menu.
Escape and Back return to the menu; Enter on the initial Chart choice enters
the native ChartingState. The adapter reports that Codename's
CharterSelection and other editor choices are unavailable. Its current
native button labels are clipped/garbled at this capture size, so text
rendering remains a visual defect despite the route working. The offscreen
probe used dummy audio and left seed, private and personal options unchanged.
Evidence: `tmp/hl17-menu-native/key7-editor-picker-probe.json` with its
screenshots and process log.

The Psych owner loader's simple-enum shadow check initially treated the
valid `case STATE_RAISE, STATE_LOWER:` branch as a typed declaration. The
generic declaration scanner now excludes that switch syntax, and an exact
owner-loader fixture gets through the `PhillyStreets` enum and its native
`ShaderFilter` import. It then stops at `RainShader`'s `FlxShader` import.
That source relies on OpenFL's compile-time shader macro to compose GLSL
and generate uniform/input fields; HScript-loaded owner classes do not run
the macro. A type alias alone would execute the stage with missing rain
effects. The source also calls an old `FlxCamera.setFilters` method absent
from pinned Flixel 6.1.2. These are explicit stage dependencies pending a
source-faithful shared runtime adapter and native GL verification.
Evidence: `tmp/psych-archive-real-import-v3/philly-streets-2hot-owner-loader-after-shaderfilter.json`
and the focused owner-loader tests.

The next canonical build passed with the corrected enum scanner, native
ShaderFilter binding, generic imported-state Quit route, readable editor
picker labels, and a smoke-only camera-receiver identity trace. In the
rebuilt private Psych 2Hot Easy replay, `STATE_LOWER` no longer causes a
parser rejection. `PhillyStreets` still does not execute because its
`RainShader` needs `flixel.system.FlxAssets.FlxShader` and compile-time
shader generation; the runtime reports that unsupported stage dependency
explicitly. The chart reached its natural 120,000 ms ending with zero
authored chart events, but fallback rendering cannot count as stage parity.
It used Xvfb, dummy audio, default test options and the exclusive runtime
lock; the private options and live personal options (new user-session
baseline `034f1281…`) were unchanged. Evidence:
`tmp/example-alpha-identity-picker-enum-build.log` and
`tmp/psych-archive-real-import-v3/philly-streets-2hot-enum-rain-result.json`.

In the same binary, HL17's key-7 editor picker opens, renders its five
choices and Back label readably in the native screenshot, returns to the
menu through Escape or Back, and enters the native ChartingState from Chart.
The chart path is explicitly partial because Codename CharterSelection is
missing; Character, Stage and Alphabet editors remain unavailable. The
shared Quit bridge now uses host type and live owner state rather than any
mod-path check, with an injected callback test for safe verification; no
native Quit click was performed. The private picker probe used Xvfb and
dummy audio, and did not alter personal settings. Evidence:
`tmp/hl17-menu-native/key7-editor-picker-probe.json` and
`tmp/hl17-menu-native/editor-picker-opened-by-key7.png`.

The next complete automated run passed **1,243 tests across 357 modules**,
with 61 skipped and zero failed. This includes the current HXC Freeplay root
binding, Codename transition host, options, and importer checks. The user's
newly pasted `hxcAssetRoot`, unsupported-import and transition compiler trace
matches an older September 25 runtime/build: the September 27 source and
canonical build already contain the root seeding and Codename bindings and
compile successfully. The earlier private real Freeplay Wacky World recheck
above remains the native evidence for the root-variable fix; the current
root-seeding source hash still matches that recheck, so no duplicate native
run was needed. HL17's separate late `alpha` failure remains
reproducible and is being traced through native tween targets. Evidence:
`tmp/example-alpha-identity-picker-enum-tests.log` and
`tmp/example-alpha-identity-picker-enum-build.log`.

The shared Codename `FlxTween.tween` facade now passes an owned HScript class
proxy's native `FlxBasic` target to Flixel's reflective tween writer. A
focused owner-scoped sprite fixture confirmed that alpha reaches its native
superclass, while a plain anonymous tween target stays unchanged. The
canonical build passed, and the private Huggyteen Bucks full replay that had
exited 255 at 45.612 seconds instead exited 0 at the natural 133,894 ms
ending. It dispatched **120/120** due chart events, recorded zero strict
runtime diagnostics and a smoke success marker. The previously failing
`alpha` property error did not recur; a temporary identity trace also
confirmed the later source `camGame.alpha` write targets the seeded native
camera. Live and private options SHA-256 values stayed `034f1281…` and
`0693e647…`. This clears the reproducible late crash in that bounded
botplay replay; repeated loads, source visual/audio parity, and other HL17
charts still require separate checks. Evidence:
`tmp/example-tween-proxy-unwrap-build.log` and
`tmp/hl17-menu-native/tween-proxy-unwrap-full-20260927.log`.

After removing the smoke-only receiver trace, another canonical build passed.
The resulting binary SHA-256 `395c1fb8…` repeated the same private Huggyteen
Bucks run: process exit 0, natural song end at 133,894/133,894 ms,
**120/120** due events, success marker, zero strict script diagnostics, and
no alpha error. The live and private options hashes again stayed
`034f1281…` and `0693e647…`. This is the exact clean-source binary evidence
for the shared tween fix. Evidence:
`tmp/example-alpha-clean-final-build.log`,
`tmp/hl17-menu-native/alpha-clean-final-full-20260927.log`, and its
`.process.log` companion.

The shared asset planner now expands only literal inclusive
`FlxG.random.int(min,max)` ranges, capped at 128 values, when collecting
`Paths.sound` and `Paths.music` calls. Focused tests passed for a numbered
`0..12` intro, bounded music paths, ordinary literals, and dynamic/reversed/
oversized refusals. A read-only mounted `IntroState.hx` scan identified its
13 authored numbered sounds. An add-only private owner refresh copied exactly
those absent Ogg files; donor and destination hashes matched, no existing
owner files were overwritten, and default/private/live settings hashes stayed
`0693e647…`/`0693e647…`/`034f1281…`. Evidence:
`tmp/hl17-menu-native/intro-sound-refresh-20260927T035122Z/receipt.json`
and the focused `test_hxc_visual_assets_round13.py` and
`test_codename_data_dependencies.py` suites (12 passing tests).

The first two Intro playback probes were inconclusive. The first stayed
on native TitleState, so it never entered the imported intro. A second probe
used the genuine Imported Mods chooser and visibly selected its IntroState
row, but its single-frame Return key did not launch the state. No intro script
trace or numbered Ogg open was observed. Both negative probes restored the
temporary private catalog to SHA-256 `dc871cc5…`; current file hashing
confirms that value, and both preserved settings and owner intro inputs.
Evidence: `tmp/hl17-menu-native/intro-menu-audio-native-probe.json`,
`tmp/hl17-menu-native/intro-menu-audio-native-ui-route-probe.json`, and the
saved chooser screenshots. A later held-Return replay completed the UI route;
its evidence is recorded below.

The `PhillyStreets` shader gap was audited against the copied Psych source
and pinned OpenFL/Flixel implementations. `RainShader` is a `FlxShader`
subclass whose GLSL and uniform fields are generated by OpenFL's compile-time
`ShaderMacro`; the owner HScript-ex loader has no macro pass. The same source
uses a `typedef`, setter-backed shader properties, a native `ShaderFilter`
constructor and `FlxCamera.setFilters`, each of which requires a separate
generic adapter or binding. The pinned camera has a `filters` property but no
`setFilters` method. A type alias or empty filter would omit the authored
rain effect, so the stage remains an explicit unsupported dependency until a
runtime GLSL materializer, owner-scoped shader proxy bridge, camera filter
lifecycle and native GL verification are complete. No stage-specific patch
or placeholder was added.

The user's live Linkinteen Parks report exposed a stale Codename event chart:
the source `Camera Follow Pos` event had been flattened to a native row with a
JSON string in `v1`, while its authored metadata column was absent. The source
event script therefore was not discovered, and the legacy camera handler
received that JSON instead of the authored `1030,270` coordinates. A scoped
read-only HL17 event refresh initially rejected all three Buck charts because
the old hxcpp serializer placed the generated foreign-payload JSON keys in a
different order than the portable Haxe renderer. The refresh planner now
accepts only exact semantic equality for importer-shaped Codename payloads,
rejecting duplicate keys, changed params, and foreign fields. Its transaction
and focused tests passed (11 cases). A fresh plan selected exactly three HL17
Buck charts with zero skips; the reviewed apply backed up their old bytes at
`tmp/import-refresh-backups/20260927T042730885900Z`. Each chart kept every
non-event field equal, every event count equal (Gordonteen 126, Huggyteen 120,
Linkinteen 5), and gained metadata on every event row. Live settings before
and after were SHA-256 `d75a2419…`; the repository seed and private settings
remained `0693e647…`. Evidence:
`tmp/hl17-linkteen-event-refresh-plan-v2-20260927.json` and the backup files.
An immediate repeated plan selected zero candidates and zero skips after the
planner's idempotent current-metadata check. Evidence:
`tmp/hl17-linkteen-event-refresh-idempotence-v2-20260927.json`.

The canonical `./run.sh build` passed after this refresh and the smoke-only
camera trace. A real-time, private Xvfb/dummy-audio Linkinteen Buck probe
exited 0 with success and zero strict script diagnostics through 70 seconds.
The selected source `data/events/Camera Follow Pos.hx.onEvent` executed at
chart time zero. The native video-end callback restored both game/main camera
visibility and destroyed the intro video at +17.77 seconds; the +20.5-second
offscreen screenshot visibly shows the first character and HUD, and the
+56.2-second screenshot shows the next authored background video. The
+15-second black screenshot agrees with the source MP4's black frame at that
time; the markers still show the intro playing. This fixes the reported
persistent black scene in this bounded replay. It is not a complete
source-parity or full-song pass: later sections, ending, reloads, editor and
menu routes still need their own evidence. Evidence:
`tmp/hl17-linkteen-camera-build-20260927.log`,
`tmp/hl17-menu-native/linkinteen-camera-probe.result.json`, and its three
`linkinteen-camera-*.png` screenshots.

The full parallel Python suite after this change passed **1,247 tests across
358 modules**, with 61 skipped and zero failed. Evidence:
`tmp/hl17-linkteen-post-refresh-full-tests-20260927.log`.

A later private held-Return chooser probe entered imported `IntroState.hx`,
opened `sounds/intro/soundFull.ogg` and a numbered `sounds/intro/9.ogg`, then
switched to `HL17MainMenu.hx`; OCR found Load Game, Credits, Options and Quit.
The donor source calls the playback API for both clips. With Xvfb and SDL
dummy/null audio, the observed file opens and API path establish routing, not
audible quality. No Codename or scoped-audio diagnostics were captured. The
temporary private catalog was restored byte-for-byte (SHA-256 `dc871cc5…`),
all Intro inputs stayed unchanged, and live/private/seed options retained
their before hashes (`d75a2419…`/`0693e647…`/`0693e647…`). Evidence:
`tmp/hl17-menu-native/intro-sound-refresh-20260927T035122Z/intro-menu-native-held-enter-probe-receipt.json`
and the held-enter screenshots and process trace under `tmp/hl17-menu-native/`.

The first post-refresh three-song HL17 Buck sweep used 5x offscreen botplay,
required natural song endings, and kept live and private settings hashes
unchanged. Linkinteen Parks passed its strict script gate through 186,666 ms
with all 5/5 due events. Gordonteen Bucks reached 114,487 ms and 126/126
events, and Huggyteen Dollars reached 133,894 ms and 120/120 events, but both
failed the strict gate: their restored event scripts require the legacy
`flixel.FlxMath` import plus owner classes (`HLTextbox` and `RobloxTextbox`,
respectively). The selected owner also lacks `models/testStage.mtl` referenced
by `models/plane.obj`; the 3D loader reports this and continues without MTL
data, so exact material parity remains unverified. These chart successes are
not yet clean compatibility passes. Evidence:
`tmp/hl17-menu-native/post-refresh-full-buck-sweep.json` and the three
`tmp/runtime-smoke/logs/hl17-post-refresh-*.process.log` files.

The later user report that Linkinteen Parks' large playable character freezes
after the first transition is reproducible. A 100-second, real-time private
Xvfb run with default private settings and dummy audio exited cleanly with no
strict script diagnostics and unchanged settings hashes. Native motion markers
show the source script switching visibility from player occurrence 0 to 1 at
beat 100 (55.56 seconds). At beats 104–160, hidden occurrence 0 continued to
receive `singLEFT`/`singRIGHT`/`singUP`/`singDOWN`, while visible occurrence 1
remained on idle frame 0; after beat 164 the next visible actor also stayed
idle. The background video's playback clock advanced throughout. Evidence:
`tmp/hl17-menu-native/linkinteen-motion-probe.result.json`, its marker log,
and four `linkinteen-motion-*.png` captures.

This is a stale imported-chart provenance problem, not an authored No Anim
instruction. Codename's chart type 0 means the implicit default; `noteTypes[0]`
would apply only to type 1. All 616 installed Buck note rows are still three
columns long, whereas the current shared Codename importer writes its authored
line/note provenance in column 13. The 669 Gordonteen and 638 Huggyteen Buck
rows are likewise stale. With no provenance, `Note.codenameOrigin` is null and
the line-aware native hit path is bypassed, leaving only the old primary
boyfriend animated. A second 68-second private Xvfb probe confirmed all five
actors were correctly bound to player line slots 0–4, while zero Codename hit
markers appeared despite autoplay and normal notes. It exited cleanly with no
strict diagnostics and unchanged settings. Evidence:
`tmp/hl17-menu-native/linkinteen-hit-probe.result.json` and its marker log.
The shared engine now reports missing Codename note provenance explicitly.
The selected-owner refresh planner matched all **1,923** Buck notes to their
source rows, including equal-time rows and older numeric coercion, without
changing section or chart fields. The reviewed apply backed up the exact
installed files in `tmp/import-refresh-backups/20260927T052302194613Z` and
appended source-line metadata to the 669 Gordonteen, 638 Huggyteen and 616
Linkinteen rows. An immediate repeated plan found zero candidates and zero
skips. Live settings retained SHA-256 `d75a2419…`, and the repository seed
retained `0693e647…`. The refresh tool rejects edited or ambiguous note rows;
its two focused tests passed. Evidence: `tmp/hl17-note-refresh-plan-20260927.json`,
`tmp/hl17-note-refresh-idempotence-20260927.json`, and
`tmp/hl17-note-refresh-tests-20260927.log`.

After refresh, a **100-second real-time** offscreen Xvfb replay exited 0 with
zero strict diagnostics, normal note and video progress, and unchanged settings.
At beat 100 the source script made player slot 1 visible. That actor sang
`singLEFT` at beat 104 and 108, `singRIGHT` at beat 112, `singUP` at beat 128,
and `singDOWN` at beat 144. After the beat 164 switch, visible player slot 2
sang `singUP` at beat 168. Source actor hit markers and rendered screenshots
agree. This clears the reported large playable character freeze after the first
Linkinteen transition in the bounded replay. The refreshed Linkinteen chart
still needs a new natural-ending pass and source visual/audio comparison.
Evidence: `tmp/hl17-menu-native/linkinteen-provenance-verified.result.json`,
its marker log, and `linkinteen-provenance-*.png` captures in the same folder.

The selected-owner HLTextbox and RobloxTextbox classes now pass a standalone
exact-source execution fixture for lyric creation, both native drawing calls,
timer callbacks, group placement and delayed state removal.
The compatibility path supplies Haxe's inherited position defaults, handles
numeric ranges in the pinned interpreter, and unwraps owner-scoped script
sprites at native FlxSpriteUtil calls. The native HL17 Gordonteen/Huggyteen
event callbacks and full-song replays passed after a canonical rebuild.
Ten focused regression tests pass in
`tmp/hl17-linkinteen-focused-gate-20260927.log`. The first parallel full-suite
run found five fixture mismatches, now corrected and passing in the focused
gate, plus a native heap abort in the mounted auto-import audit. That audit
passed when rerun alone in 137.8 seconds. A serial full-suite rerun then
passed **1,253 tests across 361 modules**, with 61 skips and zero failures
in 537.2 seconds. The parallel abort did not recur under serial load; its
underlying allocator fault remains unexplained. Evidence:
`tmp/hl17-linkinteen-post-textbox-full-tests-20260927.log`,
`tmp/hl17-linkinteen-hxc-audit-rerun-20260927.log`, and
`tmp/hl17-linkinteen-serial-full-tests-20260927.log`.

The subsequent strict 5x offscreen full-song sweep passed Gordonteen Bucks,
Huggyteen Dollars and Linkinteen Parks Bucks. Each reached exactly one natural
song end, with all due chart events dispatched and zero strict script
diagnostics. A shared `FlxTween.completeTweensOf` facade method and demo clock
completion guard cleared the earlier Gordonteen and Linkinteen diagnostics.
The repository default and installed personal settings were byte-identical
before and after the sweep. Linkinteen's visible player slot sang at beats
104, 168, 236 and 300 after the four source transitions; no beat hooks
replayed at the ending. The HL17 owner still references a missing
`testStage.mtl`, which the mounted donor also lacks. Source presentation
parity for every HL17 song and difficulty remains unverified. Evidence:
`tmp/hl17-menu-native/post-strumline-full-buck-sweep.json` and the three
matching logs under `tmp/runtime-smoke/logs/`.

A later repeat on the transition-cleanup build again ended all three songs
with 126/126, 120/120 and 5/5 events dispatched, and options unchanged.
Gordonteen and Huggyteen passed the strict gate. Linkinteen reported null
`visible`/`playAnim` accesses from `incrementChar()` at beat 100 even though
runtime actor snapshots retained source occurrences 0 and 1 on line 1. This
intermittent script-facing actor view defect reopens the Linkinteen strict
gate; the current report path above contains the failed repeat receipt.

### Imported base-song ownership and package naming (27 September 2026)

The installed `monster-hard.json` had D-Sides Codename content (180 BPM,
`bf-costume`, `spookyEvil`) while the repository's engine-owned Monster Hard
chart remains 95 BPM with the original player. The installed folder also had
a D-Sides `compatScripts.json` selected root, so its apparent import owner was
misleading. The source copy of the base chart was intact; the backed-up
installed-base repair described below has now restored it.

The shared importer now reserves every tracked base chart folder through
`assets/data/baseSongKeys.json` and refuses an existing unowned folder. It
plans an owner-qualified chart/audio destination before writing and before
classifying scan duplicates. The test uses the same guard for Codename,
Psych, V-Slice, Modding Plus, and ModdingPoop. Qualified songs keep a distinct
Freeplay entry labeled with their package name. Metadata-backed names use
`pack.json`, `_polymod_meta.json`, or `mod.json`; interactive imports prompt
for a label when metadata is absent, and unattended imports record an inferred
label. Labels never change owner IDs or storage keys. Provenance records the
name source without persisting the donor's absolute path.

Same-name songs from separate physical source directories now survive mixed
Auto discovery independently, and each candidate retains its own source
chart/audio folders through asset merging. Duplicate scanner views of the
same physical source still collapse by completeness. A single-inner-mod
compiled Codename release keeps its historical outer owner, so scoped refresh
does not duplicate its existing charts. The source scanner confirmed the
D-Sides release appears as both outer and inner roots, and the focused
same-name candidate test passed.

The latest focused ownership, workflow, prompt, same-name selection and
demo-clock gate passed 40 tests. `./run.sh build` completed after the edits
and preserved the installed options
SHA-256 `034f1281c822aa4b78824a191551dc59ada5584a6d1c55633b7f49ce6c30cabd`.
The first offscreen HL17 replay attempt correctly refused to run when a
separate `./run.sh` launch acquired the runtime lock. A later D-Sides refresh
also refused while the desktop game held the lock and made no import writes.
The first scoped D-Sides import found 40 source views and planned ten
base-name collisions. Nine qualified chart folders were written before the
asset merger rejected their still-incomplete ownership manifests. The shared
ownership guard now accepts only a bounded, same-owner, exact-destination
`importProvenance.json` during that intermediate writer state; a completed but
invalid manifest still fails closed. Six focused ownership tests pass, including
foreign-owner, wrong-destination, malformed-provenance and base-key cases. A
canonical `./run.sh build` passed. The resumed private offscreen import then
reported nine imported, 31 skipped duplicate/already-owned views, zero failed,
and zero missing dependencies; receipt:
`tmp/dsides-import-smoke/20260927T083405/markers.log`.

The read-only collision-repair plan confirmed the installed base Monster Hard
hash `3e9f3a6b...` differed from the tracked source `e07a7904...`, while the
qualified D-Sides chart hash was `416675e9...`. After a scoped backup, the
repair restored the base chart byte for byte, removed only old foreign
sidecars/audio whose bytes matched the qualified copy, and preserved the
qualified owner manifest. Freeplay retains the base Monster and a separate
`Monster · D-Sides REDUX · Codename Engine` entry. The live options and Freeplay
registry were unchanged by repair. Receipt:
`tmp/import-refresh-backups/20260927T083449-base-collision-monster/repair-report.json`.
The structural chart matrix predates this repair and still needs regeneration.

### D-Sides Try Harder follow-up (27 September 2026)

The pasted Try Harder log exposed four separate issues. Shared HScript
bindings now protect registered class aliases from a bare assignment in one
script while preserving the assignment expression's value; the exact donor
`events.hx`/`Lyrics.hx` fixture and synthetic alias tests pass. The shared
Codename shader translator now promotes numeric scalar literals in GLSL
vector arithmetic while preserving integer loops and array indexes; its
focused tests pass. The importer now discovers a literal `setIcon` dependency
and stages a selected-owner icon; the owner-scoped runtime icon lookup has
focused tests, but the installed D-Sides icon still needs a backed-up refresh.
Source inspection showed that the donor's `add(screen)` passes an array after
its sprites were already added individually. The shared scene bridge now
accepts arrays of native sprites with order and duplicate protection. The chart's type-2
`MorbiusGF` actor and its atlas exist, so the null
`strumLines.members[2].characters` access came from the compatibility view.
The engine now retains nullable indexed actor slots for note routing while
exposing only bound characters to scripts, with structured unresolved-actor
diagnostics. Seven focused actor tests pass. The shared shader loader now
normalizes integer-coordinate GLSL in both raw-source and file paths. Chart
transition selection, source song metadata, and sticker pack assets now use
the selected owner without activating a global mod session. The actor view
stays dense across direct script Array edits. Focused tests and a canonical
`./run.sh build` passed.

The subsequent strict 5× offscreen Try Harder Hard replay reached one natural
song ending, dispatched all 657 events due before the 262,022 ms instrumental
ended, reported zero runtime diagnostics and zero GLSL compiler errors, and
left installed/default options unchanged. The 658th authored event is after
audio completion and was correctly not due. The sticker outro created 85
stickers and completed. Receipt: `tmp/dsides-import-smoke/try-harder-result.json`
and `tmp/runtime-smoke/logs/dsides-try-harder-strict-final.process.log`.
This is a full-song automated regression pass, not a source visual/audio or
all-difficulty parity claim. Cross-owner transition cleanup and the post-edit
full-suite gate remain open.

A repeat on the transition-cleanup build reached the same natural ending with
all due events, and the GLSL/sticker/scene errors stayed absent. It exposed an
intermittent `songs/UI.hx#onPostNoteHit` null `hasAnim` access near beat 88,
despite a live type-2 GF actor. The repeat failed strict diagnostics, so Try
Harder was not a stable pass on that build. The script bridge was subsequently
changed to read and write `CodenameInputLine.characters` through its typed
accessor instead of reflective access, which bypassed the computed property on
native. Its focused HScript fixture covers indexed reads, method calls, direct
array edits, and reassignment; all five interpreter tests and `./run.sh build`
passed. Two strict offscreen Try Harder Hard replays on the typed-access build
both reached one natural ending, dispatched 657/657 due events, reported no
diagnostics, completed the sticker outro, and left personal/default options
unchanged. Receipts: `tmp/dsides-import-smoke/try-harder-typed-access-repeat1.json`,
`tmp/dsides-import-smoke/try-harder-typed-access-repeat2.json`, and their
matching `.process.log` files. This verifies the intermittent symptom under
two repeats; broader difficulty/source parity and cross-owner transition
cleanup remain open.

The same typed-access build passed two strict offscreen Linkinteen Parks
replays, each with one natural ending, 5/5 due events, zero diagnostics, and
unchanged settings. Receipts:
`tmp/hl17-menu-native/linkinteen-typed-access-repeat1.json` and
`tmp/hl17-menu-native/linkinteen-typed-access-repeat2.json`. A subsequent
full three-song HL17 sweep on that build passed strict diagnostics and natural
endings: Gordonteen 126/126, Huggyteen 120/120, and Linkinteen 5/5 due events,
with unchanged settings. Receipt:
`tmp/hl17-menu-native/post-strumline-full-buck-sweep.json`. The sweep is
offscreen and omits source visual/audio comparison. Gordonteen and Huggyteen
still report that donor `testStage.mtl` is absent, so their 3D material
appearance remains unverified.

### Frame-rate parity and V-Slice HXC follow-up (27 September 2026)

The configurable cap is 480 FPS and the native startup marker now reports
the saved cap alongside FlxG's update and draw rates. A strict offscreen
60/240/480 run of imported V-Slice `ajena` reached the same 21,199 ms natural
ending with all 3/3 due events at each cap and left installed options intact.
Its measured gameplay medians were 60, 239, and 346.5 FPS; the host did not
sustain 480. All three runs also reported the same five HXC null-access
diagnostics during imported character/module scripts (two `color` writes,
`contains`, `push`, and `startsWith`), and the module update log repeated an
unresolved `FreeplayState` variable. The strict parity gate therefore failed;
this is an active V-Slice compatibility gap rather than a frame-rate pass.
Receipt: `tmp/runtime-smoke/fps-cap-parity-ajena.json`. A lightweight base
Tutorial parity run first exposed an older D-Sides import in the unqualified
base Tutorial folder: its `compatScripts.json` loaded D-Sides UI/song scripts
and produced eight null-access diagnostics at every cap. After a scoped,
backed-up repair, Tutorial reached the identical 67,250 ms natural ending at
60, 240, and 480 configured FPS with zero diagnostics, unchanged installed
settings, and measured medians of 60, 240, and 333 FPS. The 480 FPS offscreen
host measurement was below the runner's 75% cap-attainment threshold, so the
behavioral parity check passed while sustained 480 FPS remains inconclusive.
Receipt: `tmp/runtime-smoke/fps-cap-parity-tutorial-repaired.json`.

### Base-song collision repair audit (27 September 2026)

The D-Sides owner-qualified import exposed older writes into nine protected
base song folders. Monster Hard was restored earlier; Tutorial Hard and nine
changed chart files across Blammed, Bopeebo, Darnell, Fresh, Pico, South, and
Spookeez were then restored from the repository seed with per-folder backups.
Old foreign `compatScripts.json` and generated `noteInfo.json` sidecars were
removed only after ownership and qualified-copy checks. The scoped repair
also removed donor `Inst.ogg`/`Voices.ogg` files only where no base seed file
owned that exact path and the bytes matched the qualified copy. All 29
protected base folders now have no foreign owner manifest and match their
repository seed JSON files byte for byte. All nine D-Sides qualified folders
retain their compatibility manifest and provenance. Personal options and the
Freeplay registry were unchanged throughout. Receipts:
`tmp/base-collision-batch-repair-audit.json` and the eight per-folder reports
under `tmp/import-refresh-backups/20260927T095*-base-collision-*/` (in addition
to the earlier Monster backup). This repairs installed content; the current
importer now plans owner-qualified collisions before writing.
An offscreen 5× base Blammed Normal replay after the audio-sidecar cleanup
reached a natural ending with strict diagnostics clear and unchanged options:
`tmp/base-blammed-after-ownership-repair.json`.

### Psych Weiner source and startup follow-up (27 September 2026)

The previously omitted Psych package has a separate 47-file source inventory
at `tmp/psych_weiner_inventory.json`: one Hard chart with 1,046 rows, including
ten `Hotdog_Note` rows, an authored `weiner` stage, two character definitions,
two song Lua scripts, a custom note Lua script, a week entry, and their media.
Its installed chart and stems match the source-owner identity, but the old
installed folder lacked `compatScripts.json`. A one-song isolated import with
the current shared writer produced the exact same chart and a manifest for the
existing owner; `tmp/psych-weiner-private-import-audit.json` retains the
identity/hash comparison after its disposable staging directory was removed.
An add-only, owner-checked refresh installed just that
manifest without changing settings or Freeplay; receipt:
`tmp/import-refresh-backups/20260927T091158707076Z-weiner-manifest/refresh-report.json`.
The next offscreen startup selected the authored `weiner` stage rather than
the fallback `stage`.

That startup exposed two script defects which an older success-marker-only
diagnostic gate had missed: `stagelight_right.flipX` was rejected by the
Psych stage translator, and a song `createPost` callback failed with a null
function pointer. The source callback calls `setHealthBarColors`, which was
absent from the shared Psych interpreter seed. The static stage translator
now accepts literal flip booleans on known sprites; the PlayState Psych API
now binds `setHealthBarColors` and retains authored colors across native bar
refreshes within the song. Focused stage, health-bar, and strict diagnostic
tests pass; a rebuilt native replay is still required before either fix is
counted as runtime coverage. Receipts: `tmp/psych-weiner-startup.json`,
`tmp/psych-weiner-manifest-startup.json`, and
`tmp/psych-weiner-one-row-matrix.json`. The custom note visual and health/death
behavior still require source comparison.

The next canonical build and 5× offscreen Weiner Hard run passed one natural
118,350 ms ending with zero interpreter diagnostics, zero due chart events,
the authored `weiner` stage, the live owner-scoped `hotdognote.png` atlas,
and unchanged installed options. Receipt:
`tmp/psych-weiner-postfix-playthrough.jsonl` and its process log. The note's
live marker still showed automatic hit allowed, contrary to the source
`ignoreNote` write. Shared Psych note fields and number coercion now carry
`hitHealth`, `missHealth`, `ignoreNote`, and the authored `noteType` alias into
native judgement; focused tests pass. A rebuild and new live note check are
pending. The passing natural ending alone does not cover death/retry flow,
Freeplay/week presentation, editor round trips, or visual/audio source parity.

### Shared HXC, Psych note, and rebuilt native checks (27 September 2026)

The HXC analyzer now accepts only declared owner-scoped mutable Constants
fields during module initialization and routes sprite pixel reads through a
bounded native helper. A focused test parsed and executed the mounted
`IconColoredHealthBar` module, including its mutable StringMap cache and
per-root color writes; the adjacent null-runtime and HXC compatibility tests
passed. HXC `destroy` callbacks now receive the common lifecycle payload,
with optional-event adapters for zero-argument source methods. A canonical
`./run.sh build` passed after these changes and the shared Psych note patch.

The rebuilt Weiner Hard chart passed a 5× offscreen natural 118,350 ms ending
with zero interpreter diagnostics and unchanged installed settings. Its live
custom note marker reports the selected owner's 24-frame atlas,
`noteType=Hotdog_Note`, `ignoreNote=true`, `hitHealth=0`, `missHealth=0`, and
`autoHitAllowed=false`, confirming the source custom-note Lua writes reached
native notes. Shared `hitCausesMiss` handling follows the Psych miss and
good-hit callback order, mutes vocals, and uses the native splash gate; it has
focused tests but still needs a mounted source case with a true hazard flag.
Receipt: `tmp/psych-weiner-post-note-playthrough.jsonl`.

Ajena Normal reached its same 21,199 ms natural ending at configured 60,
240, and 480 FPS, dispatched 3/3 events at each cap, and reported no runtime
diagnostics or settings change. Gameplay medians were 60, 239, and 325.5 FPS.
The runner marks 480 FPS inconclusive because the host did not sustain its
75% cap-attainment threshold; behavioral parity passed. Receipt:
`tmp/runtime-smoke/fps-cap-parity-ajena-hxc-module-and-destroy.json`.

The same rebuilt binary passed all three HL17 Buck charts at 5× through
natural endings with zero interpreter diagnostics and unchanged settings:
Gordonteen 126/126, Huggyteen 120/120, Linkinteen 5/5 due events. Try
Harder Hard passed with 657/657 due events under the same strict gate.
Receipts: `tmp/hl17-post-shared-note-playthrough.jsonl` and
`tmp/try-harder-post-shared-note-playthrough.jsonl`. These telemetry checks
do not settle Linkinteen terminal visual parity, the missing HL17 3D material,
or package-wide source matching.

The first required serial Python run found one isolated fixture failure: its
extracted `Note` class lacked fields added to the shared Psych note API. The
fixture now declares those fields and checks ignored/hazard botplay avoidance.
The full serial rerun passed **1,276 tests, 61 skipped**, with no failures;
receipt: `tmp/serial-full-tests-20260927-combined-rerun.log`.

### Package-wide Modding Plus and ModdingPoop replay (27 September 2026)

On the rebuilt binary, all nine VS Freddy Modding Plus chart difficulties
(Fired, Let Us In, and Slaughter at Easy, Normal, and Hard) reached natural
endings in 5× offscreen play with no interpreter diagnostics and unchanged
installed settings. This is runtime completion evidence; source visual,
audio-mix, cutscene-skip, pause, editor, and menu parity remain separate.

The ModdingPoop Cursed Expurgation Hard run reached its 193,073 ms natural
ending and did not change settings, but failed the strict script gate. Its
stage repeatedly requested `assets/sounds/staticSound.ogg`; the mounted
package contains that file only under
`assets/images/custom_stages/cursedgation/staticSound.ogg`. The source stage
also calls `cstaticthing()` without a definition and calls `doStopSign()`
while its function definitions are commented out. The process reported
missing-sound and unknown-variable diagnostics. These are explicit source
reference/dependency gaps; no donor files or chart behavior were rewritten to
mask them. Receipt: `tmp/mplus-poop-full-playthrough.jsonl` and its final
process log.

A follow-up audit of the complete mounted package and Flixel's `SoundFrontEnd`
confirmed that the stage's explicit `assets/sounds/staticSound.ogg` lookup is
exact: Flixel does not search a stage folder or match sound basenames. The
package has no `assets/sounds` directory. `cstaticthing()` is a stage-local
misspelling of the only `staticthing()` declaration, while the sole
`doStopSign*` definitions are commented out. These missing source behaviors
cannot be supplied by a general engine hook without inventing stage effects;
the package remains an explicit failed compatibility case.

### D-Sides selected-owner full-song sweep (27 September 2026)

The 22 current owner-provenance-matched D-Sides chart rows were run to natural
endings at 5× speed in private offscreen native processes. Each run retained
the installed settings and dispatched all due chart events. Sixteen rows
passed the strict interpreter-diagnostic gate; six failed. Blammed Easy and
Normal reported Camera Movement without a live actor plan because the
generated script and camera sidecars disagree on the selected difficulty and
stage after an earlier re-import. Ghastly, Monster, South, and Spookeez Hard
each reported unsupported placement for three actors; the shared stage
classifier currently treats startup opacity writes as geometry changes. These
failures remain open pending shared importer and compatibility fixes plus
replay. Receipt: `tmp/dsides-current-full-playthrough.jsonl`.

The shared importer now reconciles generated script and camera sidecars as
one selected-owner pair; the stage classifier no longer treats opacity-only
writes as actor geometry. A private source import generated 20 internally
consistent pairs. A scoped refresh backed up and replaced only 21 changed
generated metadata files under the selected owner, while hashing all 22
installed charts and the user options before and after. Backup and receipt:
`tmp/import-refresh-backups/20260927T110802376317Z/receipt.json`.

The six failed rows were replayed at 5× offscreen. Ghastly, Monster, South,
and Spookeez Hard now reach natural endings with all due events and zero
diagnostics, yielding **20/22 strict D-Sides passes** across the original
sweep and replay. Blammed Easy and Normal also reach natural endings but each
reports unresolved `pico-dark`, `bf-dark`, and `gf-dark` source character IDs.
The selected source package contains no matching `data/characters` XML or
`images/characters` atlas for these IDs. Its similarly named `bf-costume-dark`
and `gf-costume-dark` files are different authored identities, and no
`pico-dark` definition is present. The unrelated VS Freddy package contains
two same-named dark characters, so borrowing installed global assets would
cross ownership. The source package supplies no valid generic fallback;
these are explicit missing dependencies. Receipt:
`tmp/dsides-six-post-refresh-playthrough.jsonl`.

The fresh owner-qualified importer path also received a shared ordering fix:
it now records the accepted destination provenance before the compatibility
manifest checks ownership. A clean private offscreen import on the rebuilt
binary found 20 songs and 22 charts, reported zero scan errors, finished with
the native `success` marker, and generated 20 script/camera pairs with matching
difficulty stages. The generated pair bytes matched the backed-up live refresh
exactly; the private harness verified protected live files were unchanged.
Receipt: `tmp/dsides-current-build22/paired-sidecar-owner-order.markers.jsonl`
and `tmp/dsides-current-build22/dsides-full-native-preview-paired-sidecar-owner-order.process.log`.

A consolidated current chart matrix replaces the stale D-Sides rows in the
older 255-row snapshot and includes the separately inventoried Psych Weiner
Hard row, yielding 256 source chart/difficulty rows. Read-only native
preflight reports 173 structurally ready and 83 blocked. All 22 D-Sides rows
are structurally ready, though the two Blammed source dependencies above still
fail gameplay diagnostics. The 78 Psych archive rows remain blocked in this
live-runtime matrix because the reference archive has not been installed into
the live owner namespace; a private archive import was audited separately.
Other blocked rows are three PERFEXION entries, one undeclared empty DDTO++
chart key, and one FNAS entry. Receipts: `tmp/example_mods_current_chart_matrix.json` and
`tmp/all-example-current-256-dry-run.jsonl`.

The DDTO++ Baka `alt/normal` blocked row is an over-inclusive raw chart-key
inventory entry, not a playable source difficulty. The variation metadata
declares only `alt`; its `normal` note-map key is empty and undeclared. The
authored 790-note `alt` variation is imported as `baka-alt/baka-alt.json` and
passes source note-count/owner preflight. The older matrix should retain the
empty key as an audit finding rather than count it as a playable difficulty.
Excluding that placeholder gives 255 metadata-declared playable rows: 173
structurally ready and 82 blocked in the current live runtime.

The Psych archive's `PhillyStreets` source class remains a compiled-stage
compatibility gap even though its art, atlases, audio, stage JSON, and videos
are present. The owner loader reaches `RainShader` but lacks its Flixel shader
base; the source further requires generated GLSL uniform fields, `.value`
parameter objects, and camera filter installation/removal. Psych's implicit
imports and some utility/game-over bindings also remain incomplete. The
current fallback stage does not establish Philly source visual, cutscene, or
cleanup parity. This is a shared stage/shader bridge task, not a chart-specific
substitute.

### Shared-fix gate on the rebuilt binary (27 September 2026)

After the paired-sidecar, stage-opacity, importer first-write, note-splash,
and actor-plan changes, the full serial repository suite passed **1,279 tests,
61 skipped**. Receipt: `tmp/serial-full-tests-20260927-after-fixture-reconcile.log`.
The canonical `./run.sh build` completed successfully. On that binary,
Ghastly Hard and Weiner Hard both reached one natural ending at 5× in private
offscreen runs, dispatched every due event (465/465 and 0/0 respectively),
reported no interpreter diagnostics, and preserved installed settings.
Receipt: `tmp/recent-shared-fixes-two-row-playthrough.jsonl`. These passes
verify the recent shared fixes; they do not establish complete visual, audio,
cutscene, editor, or source parity.

The same binary completed all six current ProjectFunkin V-Slice and Wacky
World chart rows: Fantasy Girl 01, Future Sound, Rabbit Hole, and Wacky World
at Normal, Hard, and Nightmare. Every row reached one natural ending,
dispatched all due events, reported zero interpreter diagnostics, and left
installed settings unchanged. Receipt:
`tmp/vslice-six-current-build-playthrough.jsonl`. These are runtime
regressions; the 5× botplay harness does not establish note-hit behavior,
full-rate timing, or source visual/audio parity.

All ten Vs Tricky chart rows (Expurgation Hard; Hellclown, Improbable Outset,
and Madness at Easy, Normal, and Hard) passed the same strict 5× private
offscreen natural-ending gate. Every row dispatched all due events, logged no
interpreter errors, and preserved installed settings. Receipt:
`tmp/vs-tricky-ten-current-build-playthrough.jsonl`. Presentation, manual
note interaction, editor, cutscene, and full-rate behavior remain unverified
by this sweep.

The three HL17 Buck chart rows also passed the current-build strict 5×
offscreen gate: Gordonteen Bucks 126/126, Huggyteen Dollars 120/120, and
Linkinteen Parks 5/5 dispatched/due events, with one natural ending per row,
zero interpreter diagnostics, and unchanged settings. Receipt:
`tmp/hl17-three-current-build-playthrough.jsonl`. Linkinteen's source script
explicitly hides the game and HUD cameras at step 1312, which explains the
terminal hidden-camera telemetry; source visual parity at each earlier
transition still needs direct comparison. Earlier real-time captures establish
visible actor singing after the first transitions, but this accelerated run
does not replace that visual check.

A fresh **1× real-time** private Linkinteen replay captured 57, 95, 132, 169,
and 184 seconds after song start, spanning all four authored character
transitions and the terminal camera hide. It reached the 186,667 ms natural
ending, dispatched 5/5 events, reported zero strict diagnostics, and left
repository, installed, and private settings unchanged. The first three
post-transition frames show gameplay scenes and a visible large character;
the fourth shows the hallway scene. At 184 seconds both cameras are black,
matching the source script's explicit hide at step 1312. This clears the
reported UI-only black screen during the first transitions in this bounded
replay. The fourth frame does not by itself establish the final character's
visibility or motion, and no source-engine frame-by-frame visual or audio
comparison has been completed. Receipt and five PNG captures:
`tmp/hl17-menu-native/linkinteen-full-visual.result.json` and
`tmp/hl17-menu-native/linkinteen-full-visual-*.png`.

A read-only comparison against the mounted Linkinteen source script
(`codename/hl17_v3/mods/HL17/songs/linkinteen-parks/scripts/script.hx`,
`beatHit` lines 133–184 and `stepHit` lines 142–154) reconciled this capture
with the authored transition sequence. The full visual marker stream records
the visible player singing after **each** swap: slot 1 at beat 104, slot 2
at beat 168, slot 3 at beat 236, and slot 4 at beat 300. The two background
videos are hidden and destroyed by beat 232; the game and HUD cameras hide
at the authored terminal step. The five real-time captures show the first
four scenes and the terminal black frame. This clears the reported stationary
large character and early UI-only black screen for the bounded source path;
it does not establish frame-by-frame presentation parity for the entire HL17
installation. Gordonteen/Huggyteen's 3D material appearance still lacks a
comparable post-fix capture, and the mounted donor has no `testStage.mtl`.

### Hold geometry and Codename receptor glow (27 September 2026)

The shared note snap path centered every sustain piece using the first note
width seen in the song. A different hold-head atlas, a narrow tail frame, or a
moving/scaled receptor could therefore put the trail off the head's visible
center. The Codename per-frame receptor alignment also replaced the snap
position and dropped sustain centering. `Note` now retains its own hold head's
drawn-frame center, caches it on the head for tails that spawn after judgement,
and both native and
Codename position paths align every tail to that center. The correction is
computed from the active frame origin, offset, scale, and width each frame;
there are no chart or package branches. The production-method Haxe regression
checks narrow tails, receptor movement, a changed head offset, and post-hit
head retention (`tools/tests/test_sustain_trail_alignment.py`).

Codename hit dispatch previously played the receptor confirm animation but
skipped the shared timer that returns it to `static` after a tap/hold. Accepted
Codename hits now enter that lifecycle unless their source callback cancels
strum glow. The production-method Haxe regression in
`tools/tests/test_codename_note_core.py` verifies the confirm remains until its
animation finishes, then returns to `static`. `./run.sh build` passed, and a
private offscreen Ghastly Hard replay on that binary reached its 135,754 ms
natural ending with 465/465 due events, zero interpreter diagnostics, and
unchanged settings (`tmp/ghastly-sustain-glow-current-build.jsonl`). This
native run does not yet measure rendered trail pixels or every Codename
receptor animation; those visual checks remain open.

A later private Ghastly visual capture found a remaining Codename placement
offset: head and tail moved together, but the trail was visibly right of the
receptor. This was constructor lane padding being captured as if a source
script had moved the note. Generated chart notes now record their construction
baseline, and Codename binding keeps only the post-generation authored x
change; script-created notes retain their explicit absolute binding. The
focused regression checks this distinction and preserves native/style atlas
offsets. The first capture is a **before** receipt, not a visual pass:
`tmp/ghastly-sustain-visual/ghastly-sustain-visual.result.json` and four PNGs.
It also logged an intermittent `songs/UI.hx#onPostNoteHit` null `hasAnim`
diagnostic under the visual harness, which the ordinary Ghastly replay did not
show. The before visual harness is therefore a strict failure.

The rebuilt **after** Ghastly visual replay reached its natural ending at 5×,
captured four Xvfb frames, and logged **zero** strict diagnostics. The green
receptor/trail medians from the affected before frame were x=345/x=385
(40 px apart); in the after frame they were x=358/x=357 (1 px apart).
These are sampled rendered green pixels in separate holds of the same style,
not a full frame-by-frame source-engine comparison. The generic Codename
`hasAnim` alias now resolves native/borrowed `Character.hasAnimation`, and the
after capture no longer logs the UI callback error. Evidence:
`tmp/ghastly-sustain-visual-after/ghastly-sustain-visual.result.json` and four
PNG captures; focused tests:
`tools/tests/test_sustain_trail_alignment.py`,
`tools/tests/test_codename_input_initialization.py`, and
`tools/tests/test_codename_character_animation_alias.py`.

The corrected strict runner marks the Psych archive's 2Hot Hard replay
**failed**, despite reaching its 120,000 ms ending: source `PhillyStreets`
fell back to JSON-only stage metadata and logged three additional class
dependency diagnostics. Receipt:
`tmp/psych-2hot-hard-strict-stage-playthrough.jsonl`. The earlier 2Hot Hard
receipt that reported a pass omitted these stage diagnostics from its strict
gate and must not be used as compatibility evidence.

The owner class loader now lowers Haxe indexed `for (key => value in source)`
loops through lazy key/value iteration, including changes to array entries and
length during a loop. The real archive `StoryMenuState` loop normalizes in a
focused test; native `./run.sh build` passed. A strict private 2Hot Hard replay
advanced past the previous `lime.utils.Assets` import blocker but still
**failed** source-stage loading: `GameOverSubstate` imports an unbound
`flixel.math.FlxPoint`, so `PhillyStreets` again fell back to JSON-only stage
metadata. Receipt: `tmp/psych-2hot-hard-indexed-loop-stage-playthrough.jsonl`.
This is evidence of a narrower class-loader gap, not a Psych stage pass.

The next generic class-loader pass binds the Flixel point constructor used by
the source game-over dependency and erases generic annotations in imported
class type positions, including `RainShader`'s structural `Array<{...}>`
field. Its regression uses the installed source file and checks that a
generic-looking expression remains untouched
(`tools/tests/test_psych_indexed_module_loops.py`). `./run.sh build` passed.
Strict private 2Hot Hard still **fails** at source stage initialization after
reaching the natural ending: the next dependency is `backend.Song`'s native
`haxe.Json` import, reached through `GameOverSubstate` and `StoryMenuState`.
The fallback and full dependency chain remain explicit in
`tmp/psych-2hot-hard-structural-generic-stage-playthrough.jsonl`.

The owner-scoped Lime Assets facade now passes a production-helper fixture
covering owner precedence, native fallback, sibling-owner refusal, traversal
refusal, and unchanged Lime cache/event objects
(`tools/tests/test_psych_owner_lime_assets.py`). The compiled-stage map also
binds native `haxe.Json` and `FlxGraphic`; the 12 focused Psych/character tests
and canonical `./run.sh build` pass. The subsequent strict private 2Hot Hard
replay again reached its natural ending but **failed** source-stage loading:
`options.GameplayChangersSubstate.hx` has a still-unsupported HScript-ex parse
form (`EUnexpected(;)`) in the transitive `GameOverSubstate` dependency. JSON
fallback and the full chain are logged in
`tmp/psych-2hot-hard-owner-assets-json-stage-playthrough.jsonl`. The owner
facade covers Lime imports only; raw OpenFL Assets and Paths call sites still
need separate source-behavior review.

The next shared pass also scopes compiled-stage OpenFL Assets reads using a
common canonical owner resolver, and binds a per-song Psych game-over class
surface. A source-style HScript assignment test confirms that stage writes to
death sound and character fields reach native `setPsychClassProperty`; nonzero
source `deathDelay` produces an explicit unsupported error. The owner asset
fixture covers sibling IDs, traversal, symlink escape, library/movie-clip ID
rejection and native fallback; 11 focused tests and `./run.sh build` pass.
Strict 2Hot Hard still **fails** source-stage loading at the next dependency:
`cutscenes.CutsceneHandler` imports unbound `flixel.util.FlxSort`. The game
reached its natural ending through the JSON-only fallback; receipt:
`tmp/psych-2hot-hard-gameover-openfl-expression-stage-playthrough.jsonl`.
The scoped Assets facades do not yet redirect `Paths.txt` values that a source
stage later passes to native `CoolUtil.coolTextFile` (School/SchoolEvil
dialogue), so those reads remain a separate owner-resolution gap.

Adding the native `FlxSort`, `FlxDestroyUtil`, and `FlxPieDial` bindings lets
the mounted `PhillyStreets` source class register and enter its `create`
callback. The next strict 2Hot Hard private replay still **fails**: source
`create` raises `EInvalidAccess(x)` and the runtime applies JSON-only stage
metadata. The process log records the callback error and renderer access
context, while the strict result records the fallback:
`tmp/psych-2hot-hard-cutscene-native-bindings-stage-playthrough.jsonl`.
`tools/run_runtime_smoke_matrix.py` now counts every `[psych-stage]` failure
directly as a diagnostic, so later callback errors cannot be cleared by an
ending marker or by the absence of a fallback line.

### Directional character offsets (27 September 2026)

The shared legacy player-facing orientation exchanged left/right sing, miss,
and hold frame arrays but kept `animOffsets` under their original animation
names. Later `Character.playAnim` looks up the new name and applied the old
frame's offset. Psych and V-Slice conversion preserve the authored offset per
animation, so this mismatch affects their player characters whenever that
legacy orientation runs. The orientation helper now swaps each present
left/right frame pair and its offsets together, preserving one-sided offset
removal. The extracted production helper test checks the three pairs and
missing-key behavior (`tools/tests/test_character_animation_orientation.py`),
and `./run.sh build` passed. Up/down paths and native visual parity remain
under audit; this is not evidence that every reported directional placement
issue is cleared.

A source-contract audit did not find a second deterministic up/down mapping
defect. Psych's `Character.hx` stores each JSON animation offset under its
name and reads that same name at playback; the importer and native legacy
character follow the same mapping. V-Slice emits all four directional offsets
and the runtime reads both axes from the active animation. The existing
V-Slice geometry fixture exercises left/down/up/right at two scales, and the
Psych dance fixture passes (5 focused tests). A source-engine visual comparison
of the reported charts is still needed to resolve any remaining placement
error; the mapping audit alone cannot clear it.

The same rebuilt binary completed a 5× offscreen Ghastly Hard replay with
four Xvfb captures, zero strict diagnostics, and unchanged repository,
installed, and private settings. Receipt:
`tmp/ghastly-character-orientation-native/ghastly-sustain-visual.result.json`.
This verifies the shared character edit did not break that Codename gameplay
route; it does not compare directional character pixels against the source.

A separate V-Slice Wacky World Normal 5× offscreen replay on the same binary
reached its 153,767 ms natural ending, dispatched all 106 due events, and
logged zero strict interpreter diagnostics:
`tmp/wacky-character-orientation-playthrough.jsonl`. This covers one
V-Slice runtime route after the shared offset edit, not visual pose parity or
all Wacky World difficulties.

A follow-up read-only audit traced Codename XML x/y, Psych JSON `offsets`,
V-Slice animation offsets, and legacy `addOffset` through import and playback.
Each active route retains the authored per-animation values. No second
source-backed shared correction was established, so no further character
code was changed. Codename suffix variants such as `-alt`, `-dodge`, and
`-loop` still need source facing-rule comparison before changing their
left/right mapping. The user's broader directional placement report remains
open pending source-versus-native pose captures, including up/down.

### Owner-scoped Psych source-stage media and groups (27 September 2026)

The strict private 2Hot Hard replay advanced from an unresolved `gfGroup.x`
access to an `EUnknownVariable(FlxAnimate)` dependency after a shared
`PsychBaseStageActorGroupCompat` view was added. The view reads the three
authored role anchors from StageHelper, moves the live actor with group
coordinates, inserts `addBehind*` scenery relative to that actor, and updates
the native placement used by later character swaps. The source-backed group
fixture and native `./run.sh build` passed. Receipt:
`tmp/psych-2hot-hard-stage-group-playthrough.jsonl`.

The selected source archive kept its `weekend1/images/abot` and
`weekend1/images/phillyStreets` files in globally mapped directories, outside
the imported owner's namespace. A generic Psych media importer now copies
mapped image, video, font, shader and animation trees under the selected
owner without overwriting existing files; it validates every copied path and
rejects symlinks that escape the donor root. The paired owner `Paths` facade
uses stage JSON's `directory` library, returns `FlxGraphic` from `image`, and
loads folder-based Animate atlases. Focused two-owner, symlink, Paths,
Lime/OpenFL, and stage-group tests passed; `./run.sh build` passed.

The existing fully private archive runtime was backed up at
`tmp/psych-archive-real-import-v3/owner-media-refresh-backup-20260927/`.
Its first scoped importer refresh copied owner media but exited with 26
duplicate-song errors because this older disposable runtime lacked the new
`baseSongKeys.json` registry. After copying that repository registry into the
private runtime only, the same non-overwriting refresh passed. The current
base-song collision rule also created 23 owner-qualified chart folders in
that disposable runtime; the original 2Hot owner manifest and options hashes
stayed unchanged. Receipt:
`tmp/psych-archive-real-import-v3/owner-media-refresh-20260927-v2.receipt.json`.
No live or donor files were refreshed.

The next strict 2Hot Hard 5× offscreen replay still **fails** source-stage
execution. It now loads owner graphics and reaches ABotSpeaker, then logs
`Invalid field:curFrame` because Psych's FlxAnimate controller exposes
`anim.curFrame` and the installed library does not. An earlier null
`viz.animation.curAnim.finish()` and null subtraction also need explanation.
The chart reaches its natural ending through a JSON-only fallback, which is
not a compatibility pass. Receipt:
`tmp/psych-2hot-hard-owner-media-paths-playthrough.jsonl` and the named
process log under `tmp/runtime-smoke/logs/`.

The source `ABotSpeaker` animation registration used seven Haxe interpolated
prefixes (`'viz$i'`). The owner class loader previously left those literal,
causing a null `viz.animation.curAnim.finish()` call. It now reuses the
classless interpolation transform; a source-backed seven-prefix fixture
passes. The same parser now handles balanced braced expressions such as
`'combo${game.combo}'`, arithmetic in braces, and explicit empty/unclosed
diagnostics. The installed FlxAnimate renderer is wrapped with Psych's
`anim.curFrame` and `anim.length` controller properties; its focused fixture
checks reordered atlas-frame indices. Relevant focused tests and the canonical
native build passed.

The first strict 2Hot Hard replay after those changes identified the braced
interpolation gap in the mounted `PhillyStreets` class:
`tmp/psych-2hot-hard-animate-interpolation-playthrough.jsonl`. After the
shared parser fix, the same source class reached `create` and exposed an
unbound standard Flixel `FlxMath` import:
`tmp/psych-2hot-hard-braced-interpolation-playthrough.jsonl`. Binding that
class let `create` advance through ABotSpeaker and the camera-side check.
The next strict replay still **fails** when source `RainShader` construction
reads a missing generated GLSL `uScreenResolution` uniform:
`tmp/psych-2hot-hard-flxmath-playthrough.jsonl`. These are source-stage
failures despite natural chart endings, not compatibility passes.

The next native shader bridge avoided OpenFL's numeric uniform reflection
onto undeclared C++ fields, moving the same stage failure from
`uScreenResolution` to sampler `uBlurredScreen`:
`tmp/psych-2hot-hard-native-shader-data-playthrough.jsonl`. The shared adapter
now registers numeric and sampler wrappers in `ShaderData` while retaining
the authored GLSL. After its focused RainShader uniform test and canonical
build passed, the next 5× private offscreen replay executed source
`PhillyStreets.create` but failed in `createPost` on a missing `Note.blockHit`.
Receipt: `tmp/psych-2hot-hard-sampler-animate-playthrough.jsonl` and its
process log. That result file said `passed` because the full-playthrough
checker did not recognize the generic `[psych-stage]` callback tag; it is
**not** a compatibility pass. The checker now treats that tag as a failure,
with a focused regression test. A shared `Note.blockHit` field and input /
botplay gates now match Psych's source rule that player notes remain blocked
until a stage clears the flag. Focused note and input tests passed; a new
native replay is pending. The Animate controller also gained Psych's
completion listener API, with three focused tests passing. Story cutscene
lifecycle, source visual/audio parity, and every other archive difficulty
remain unverified.

The next 5× private 2Hot Hard replay exposed a source class field whose
declaration had no initializer: `ABotSpeaker.snd`. The shared owner class
loader now seeds uninitialized declared fields with Haxe defaults before
constructing the class. Its focused class-loader fixture and canonical native
build passed. The subsequent strict replay reached the natural ending with
source `PhillyStreets` active and no script diagnostics:
`tmp/psych-2hot-hard-classfield-playthrough.jsonl`. This is a gameplay/script
pass only. Offscreen visual captures at 2, 10, and 20 seconds showed the
authored street scenery, rain shader, notes, HUD and ABot but **none of the
three characters**. The capture receipt is
`tmp/psych-2hot-source-stage-visual/psych-2hot-source-stage-visual.result.json`.
The engine instantiated all three sprite atlases and reported positions in
its native markers; stage scenery was drawn above them because compiled
Psych `create()` ran after this engine had already added actors. The shared
stage adapter now inserts `create()` objects ahead of the first actor, then
lets `createPost()` and later additions append as authored. An extracted
Haxe draw-order fixture and canonical native build passed. The same private
offscreen capture then showed Darnell, Nene, and Pico visibly layered in
front of the authored street at the early checkpoint; the later checkpoint
retained the in-frame actors during camera movement. It reached the natural
ending with zero strict diagnostics and unchanged options hashes; the capture
receipt above now contains the post-fix screenshots. This verifies the
specific draw-order defect, not full source visual/audio parity or story
cutscenes. The current compiled-stage fixture module has
an unrelated incomplete Haxe test harness (missing flixel-addons/tjson and
`Main.cwd`) and is not cited as a passing module.

The shared `ScriptClass`/`FlxBasic` bridge now preserves authored update,
draw, destroy, remove and owner-release behavior for owner objects inserted
into native Flixel groups. A focused cutscene lifecycle fixture covers timer
advance, configured `accept` input, skip/removal, and the transition flag;
`tools/tests/test_psych_script_class_basic_lifecycle.py` passes. The owner
stage bindings expose the active `FlxG.state` and `Controls.instance.pressed`
to source classes. Native 2Hot stage visual replay passed after these source
changes. A separate story-mode replay initially fell through to the native
victory transition because the adapter's `songName` getter read this fork's
HUD text object rather than Psych's `Paths.formatToSongPath(SONG.song)`. The
shared song-name helper and static story-flag getter now follow the source
contract. The selected owner stage registered its ending callback, played
the owner's 28.4-second ending video, and reached the victory state with zero
strict diagnostics and unchanged settings. Captures at 28 and 40 seconds show
different video frames: `tmp/psych-2hot-source-stage-visual/psych-2hot-story-stage-visual.result.json`.
That initial Space press tested only this fork's old immediate native skip.
The shared Psych video bridge now exposes the active clip as
`game.videoCutscene` with replaceable finish and skip callbacks, so a source
stage can chain an intro video to its next authored cutscene. The selected
owner remains the video source. Psych clips use one second of held mapped
Accept input; the native controls adapter reads each configured keyboard or
gamepad binding's held state because this engine's ordinary Accept action is
bound only as a one-frame menu press. At 5× smoke speed, a 0.04-second tap
left the source ending video active and a later 0.75-second hold skipped it;
success followed natural song end by 5.3 seconds. The private receipt is
`tmp/psych-2hot-source-stage-visual/psych-2hot-story-stage-skip.result.json`:
return code zero, no strict diagnostics, all marker gates present, and all
repository, installed and private settings hashes unchanged. A fresh full
video replay also passed after these changes:
`tmp/psych-2hot-source-stage-visual/psych-2hot-story-stage-visual.result.json`.
The compiled-stage countdown handoff now marks the intro seen even without
native cutscene metadata. The callback fixture and held-video fixture pass.
The archive contains a `darnell` stage intro callback but no `darnell` chart,
so its two-part video/cutscene chain is not yet a native playthrough pass.
Other Psych story routes and source visual/audio parity remain unverified.

Psych character orientation now reads preserved selected-owner `flip_x` JSON
at runtime and applies the source `flip_x != isPlayer` rule without this
engine's legacy LEFT/RIGHT frame-and-offset swap. The focused mounted BF
fixture checks the source definition and all named directional offsets;
`tools/tests/test_psych_character_orientation.py` passes. This avoids a
re-import and leaves non-Psych character rules unchanged. Cross-format BF/dad
directional placement still needs visual source comparison, especially at
non-unit scale and across chart-specific character swaps.

A further private probe exercised the archive's Darnell source-stage intro
against a chart copied and stage-id adapted **only inside a disposable test
overlay**; the Psych archive inventory itself has no Darnell chart. The first
attempt registered no start callback because HScript-ex could not reflect
Haxe's compile-time `Function.bind` from an interpreted method. The shared
interpreter patch now partially applies ordinary function arguments; its
focused direct and source-class callback fixture passes. The source class
loader now selects `#if sys`, `#if cpp`, and `#if VIDEOS_ALLOWED` branches
according to native capabilities. Without the video define, Psych's no-video
timer fallback retained a method-local argument and later raised
`EUnknownVariable(videoName)`. Follow-up source failures identified three
shared contract gaps: HScript-ex evaluated assignment values twice, treated
function-valued class fields as methods rather than callable fields, and
PlayState lacked Psych's public section camera API. The interpreter now
evaluates assignment values once and calls stored callbacks; PlayState exposes
`moveCameraSection`, `moveCamera`, `cameraSpeed`, and the forced camera flag
using native character and stage camera offsets. A canonical `./run.sh build`
passed. The same disposable Darnell intro probe now registers the authored
start callback, skips the selected-owner video, enters the second cutscene,
reaches song start, exits zero, and reports zero strict diagnostics:
`tmp/psych-2hot-source-stage-visual/darnell-intro-probe/report.json`. Options
hashes were unchanged. This is **not** a Darnell chart pass or proof of all
source-stage effects: the archive contains no Darnell chart, the probe uses a
disposable chart/stage overlay, and it stops at song start.

The final build's actual 2Hot Hard story route passed twice under offscreen
Xvfb and dummy audio: the full ending video and a separate 0.04-second tap
followed by a 0.75-second held Accept skip. Both reached natural song end and
the victory transition with zero strict diagnostics, return code zero, and
unchanged options hashes. Receipts are
`tmp/psych-2hot-source-stage-visual/psych-2hot-story-stage-visual.result.json`
and `tmp/psych-2hot-source-stage-visual/psych-2hot-story-stage-skip.result.json`.
Strict smoke and full-song checkers count plain `Null Function Pointer` and
`Invalid field:` errors, as well as missing selected-owner stage videos.

Both offscreen matrix and full-song diagnostics now reject missing selected
owner stage videos explicitly, so a natural song-end marker cannot turn a
failed source cutscene into a compatibility pass. Focused diagnostic and
callback tests pass. The clean serial suite after interpreter and orientation
fixes passed **1,309 tests, 61 skipped** in 571.6 seconds; receipt:
`tmp/full-suite-psych-stage-clean.log`. The later camera and skip-request
changes passed a 36-test focused set. The final serial suite on those changes
passed **1,309 tests, 61 skipped** in 577.7 seconds; receipt:
`tmp/full-suite-psych-stage-final.log`.
The wider goal still needs package-by-package source comparisons and complete
all-difficulty native playthrough evidence; this stage probe does not establish
general Psych or other engine compatibility.

The same final binary also replayed all three inventoried HL17 Codename charts
offscreen at 5× to natural song ends: Gordonteen Bucks/Buck, Huggyteen
Dollars/Buck, and Linkinteen Parks/Buck. All three returned passing status and
zero strict interpreter errors; receipt: `tmp/hl17-current-post-psych.jsonl`.
This is a regression check after the shared Psych changes, not a fresh visual
comparison of Linkinteen Parks' transitions or character movement.

The current rebuilt PERFEXION Xfracture Hard replay reached its 138,294 ms
natural ending and dispatched all 34 due events, but **failed** the strict
gate. The donor has JSON for `girl-mad`, `Night-PXT`, and `Night-Girl` without
their referenced character atlases; `Crazy-Girl` and the `bedroom` stage
definition are absent. The active `10scriptnote.lua` reads undefined
`anglevar` in arithmetic, which Lua cannot turn into a valid pose/size value.
The engine now includes the loaded source path in each callback error, so this
is distinguished from an opaque `compat_song_0` failure. The private offscreen
receipt is `tmp/perfexion-xfracture-source-diagnostics.jsonl`; settings were
unchanged. No donor files were edited or replacement art invented.

The D-Sides Try Harder selected-owner icon audit found a registered `zeph`
character without `custom_chars/zeph/icons.png`, while the donor's direct
`images/icons/zeph/icon.png` strip exists. The shared HealthIcon resolver now
uses a selected owner's direct strip when its character registry has no custom
strip, without borrowing from another owner. The focused Haxe fixture covers
registered, unregistered, custom-strip precedence, and sibling-owner cases;
`./run.sh build` passed. A fresh offscreen Try Harder Hard run reached its
natural ending, dispatched all 657 due events, and logged zero strict errors
with unchanged settings. Its native log records `zeph` and `zephmoldy` icons
selected from the exact D-Sides owner; the Zeph installed PNG SHA-256 equals
the donor's (`981ce507...b972c`). Receipt:
`tmp/try-harder-direct-icon-marker.jsonl` and its `processLog` path.
This proves the selected asset path and gameplay regression; a pixel-by-pixel
source HUD comparison remains unverified.

### Psych Tank compiled-stage replay (27 September 2026)

The private Psych archive owner now runs its `states.stages.Tank` class on
Guns Easy. The source depends on a cross-package `BGSprite` import supplied
implicitly by `source/import.hx`, iterates `gfGroup`, and calls `dance()` on
script sprites through a native `FlxTypedGroup.forEach`. Shared class-scope,
inherited-method, actor-group, and native-callback adapters now preserve those
Haxe behaviors. Focused standalone tests cover each boundary, and
`./run.sh build` succeeded.

An offscreen Xvfb/dummy-audio replay on the rebuilt binary reached Guns Easy's
140,472 ms natural ending and victory transition with **zero strict script
diagnostics**, return code zero, and unchanged protected options hashes.
Receipt: `tmp/psych-archive-real-import-v3/tank-guns-easy-current-v7.json`;
the selected-owner class execution marker is in
`tmp/runtime-smoke/logs/psych-archive-tank-guns-easy-v7.process.log`.
This is one chart and difficulty, not a source visual/audio parity finding or
an all-difficulty archive pass.

### V-Slice directional animation offsets and Psych stage defaults (27 September 2026)

The selected Wacky World donor defines player character WackyPomni's
`singLEFT` offset as `[0, 5]` and `singRIGHT` as `[-15, 72]`. Its generated
character script retained both values, but the shared legacy player setup
exchanged the two frame/offset pairs. A pre-fix native hit trace observed LEFT
using `[-15, 72]` and RIGHT using `[0, 5]`. V-Slice characters now keep their
authored directional pairs while the player sprite still receives its facing
flip. The rebuilt offscreen trace observed 12 player hits across all four
directions: LEFT `[0, 5]`, RIGHT `[-15, 72]`, UP `[24, 95]`, and DOWN
`[25, -5]`. Both traces passed strict diagnostics, and the after trace kept
protected settings unchanged. Receipts:
`tmp/wacky-world-offset-before.json`, `tmp/wacky-world-offset-after.json`,
and their `processLog` files. The V-Slice, legacy, Psych, and Codename
orientation fixtures pass. These are runtime animation-offset measurements;
a full source screenshot comparison and all-difficulty pass remain open.

The rebuilt binary subsequently replayed **all three** Wacky World
difficulties (Normal, Hard, Nightmare) offscreen at 5× through natural song
ends. Each passed the strict diagnostic gate; protected options hashes were
unchanged. Receipt: `tmp/wacky-world-full-after-offset-fix.json`. This extends
the gameplay regression check, while source visual/audio parity and editor
round trips remain unverified.

A separate archive replay of Spookeez Easy reached its natural ending but
executed `StageWeek1`, because the donor chart omits `stage` and the old
importer stored the host default. The donor's `StageData.hx` maps that song
to `Spooky`. `PsychStageInference` now parses the selected donor's literal
stage switch during import, preserving explicit chart and `info.txt` stages.
Its parser, selected-owner, and metadata precedence tests pass. A scoped,
backed-up refresh patched the stage field in **30** owner-matched private
archive chart files (canonical and qualified folders; Easy, Normal, and Hard
for five source-mapped songs), with **zero** skipped candidates. The plan
revalidated donor notes/events, owner provenance, the exact old stage value,
file hashes, and settings before applying a stage-only replacement. Receipts:
`tmp/psych-stage-refresh-plan-20260927-v3.json` and
`tmp/psych-stage-refresh-applied-20260927.json`; originals are in the backup
directory named by the apply receipt. The rebuilt offscreen Spookeez Easy
replay then executed `states.stages.Spooky`, reached the natural ending with
zero strict diagnostics, and left protected options unchanged. Receipt:
`tmp/psych-archive-real-import-v3/spooky-spookeez-easy-refreshed-v2.json`;
class execution is in its `.process.log`. The earlier incorrect-stage receipt
is `tmp/psych-archive-real-import-v3/spooky-spookeez-easy-current-v1.json`.
The other refreshed rows still need individual source-behavior checks.

### Psych SchoolEvil compiled-stage replay (27 September 2026)

Thorns Easy initially reached its natural ending while falling back to the
host stage: the selected source `SchoolEvil` class could not resolve Flixel's
`FlxTrail`, then its imported `DialogueBox` dependency could not resolve
`FlxTypeText`. Both classes now have shared Psych compiled-stage bindings.
On the rebuilt binary, an offscreen Xvfb/dummy-audio replay executed
`states.stages.SchoolEvil`, reached its natural ending, reported **zero strict
script diagnostics**, and left protected options unchanged. Receipt:
`tmp/psych-archive-real-import-v3/school-evil-thorns-easy-v3.json`; the class
execution marker is in
`tmp/runtime-smoke/logs/psych-archive-school-evil-thorns-easy-v3.process.log`.
This verifies the class runs through
one chart difficulty. Source visual/audio parity, dialogue behavior in story
mode, and the archive's other difficulties remain unverified.

### Psych mapped sound libraries and refreshed-stage sweep (27 September 2026)

The importer retained mapped Psych images and videos but skipped `sounds`
folders below mapped libraries such as `assets/base_game/week3/sounds`.
`mergePsychRuntimeMedia` now copies those trees to the selected owner at their
relative library paths without replacing existing files. Its owner-isolation,
repeat-import, and symlink fixture passes. A scoped add-only refresh of the
private archive owner added **99** previously absent mapped sound files
(8,444,532 bytes), verified their source and destination hashes, and left all
protected options unchanged. Receipts:
`tmp/psych-mapped-sounds-refresh-plan-20260927.json` and
`tmp/psych-mapped-sounds-refresh-applied-20260927.json`.

The five refreshed **Easy** charts each executed the source stage class and
reached a natural ending. Monster, South, and Spookeez passed the strict
diagnostic gate; Blammed and Pico failed because `PhillyTrain.start()` read a
null `sound` field during the `Philly` beat callback. The mapped sound refresh
did not change that failure, so the class field/argument bridge is being
repaired separately. All five protected settings checks passed. Receipt:
`tmp/psych-stage-refresh-five-easy-20260927.json`; a post-sound Blammed
recheck remains failed in
`tmp/psych-archive-real-import-v3/philly-blammed-easy-sounds-v2.json`.

### Compiled-stage field shadowing and current native replays (27 September 2026)

The selected Psych source declares `PhillyTrain.sound` without an initializer
while its constructor also takes an argument named `sound`. HScript-ex was
putting method arguments into the instance variable map, then restoring the
old value after the constructor, which erased `this.sound`. The repeatable
shared interpreter patch now seeds declared fields and binds arguments in
local frames. The exact source-shaped constructor/nested-call fixture passes
(`tools/tests/test_hscript_class_parameter_shadowing.py`), and `./run.sh
build` succeeded. Pico Easy then executed `states.stages.Philly`, reached its
natural ending, and passed strict diagnostics with settings unchanged:
`tmp/philly-pico-easy-after-class-fix.json`.

Blammed Easy also reached its natural ending with the constructor fixed, but
its first `Philly Glow` callback failed on `FlxColor.alphaFloat`. That is a
separate Int-backed abstract property gap; its strict receipt is
`tmp/philly-blammed-easy-after-class-fix.json`. A shared interpreter color
property bridge was required. This historical result did **not** clear Blammed.

On the same build, Ghastly Hard and Linkinteen Parks Buck reached natural
endings offscreen with zero strict diagnostics and unchanged protected
settings. Linkinteen dispatched all five due chart events. Receipts:
`tmp/ghastly-receptor-reset-after-fix.json` and
`tmp/hl17-linkinteen-after-receptor-class-fix.json`. A focused Haxe fixture
checks that sustain confirmation timers wait through fractional final tails
and reject stale resets; the native receipts do not record receptor animation
states or sustain pixel centers. Existing Ghastly screenshots predate the
current head-anchor implementation, so current visual parity remains open.

The Int-backed `FlxColor` bridge subsequently passed its focused direct and
compound assignment fixture and a canonical build. Blammed Easy then advanced
past the first lighting event but failed later in the same source callback on
`EUnknownVariable(PhillyGlowParticle)` when a wildcard-imported class was
passed to `FlxTypedGroup.recycle`. Receipt:
`tmp/philly-blammed-easy-after-color-bridge.json`. The owner-scoped class
value/recycle behavior required another shared runtime fix; this historical
color-bridge build still failed strict diagnostics.

On this color-bridge build, D-Sides Try Harder Hard passed another strict
offscreen natural ending with zero diagnostics and settings unchanged
(`tmp/dsides-try-harder-after-color-bridge.json`). Pico, Monster, South and
Spookeez now each have strict full-song passes for **all three** Easy,
Normal and Hard difficulties across the refreshed archive replays. The
additional Normal/Hard receipts are
`tmp/psych-archive-pico-all-difficulties-color-build.json`,
`tmp/psych-archive-monster-normal-hard-color-build.json`,
`tmp/psych-archive-south-normal-hard-color-build.json`, and
`tmp/psych-archive-spookeez-normal-hard-color-build.json`. These runs checked
source stage class execution, natural ending, strict interpreter diagnostics
and protected settings; they are not source visual/audio/editor parity checks.

The owner class scope now resolves imported script classes as runtime values
without publishing sibling-owner symbols. `FlxTypedGroup.recycle` creates,
reuses, and rotates their native bridges while returning the owner script
object. The wildcard import, group reuse/rotation, constructor-shadow, and
color-property fixtures pass; the patcher is idempotent and `./run.sh build`
passed. On that final binary, **Blammed Easy, Normal, and Hard all reached
natural endings with zero strict diagnostics and unchanged protected
settings**. Easy dispatched all 119 due events; the source `Philly` class
executed. Normal and Hard also dispatched all 119 due events each. Receipts:
`tmp/philly-blammed-easy-after-owner-recycle.json` and
`tmp/psych-archive-blammed-normal-hard-owner-recycle.json`. The five refreshed
stage songs therefore have strict full-song passes for all 15 Easy/Normal/Hard
rows across these builds. The archive contains many more charts, and these
passes do not establish source pixel/audio parity, editor round trips,
pause/seek/skip behavior, or repeated loads for each row.

A final-binary five-song Easy sweep replayed Pico, Blammed, Monster, South and
Spookeez after owner-class recycling was added. All five executed their
selected source stage, reached natural endings, reported zero strict
diagnostics and preserved repository, installed and private settings hashes.
Receipt: `tmp/psych-five-easy-final-binary.json`. On that same binary,
Ghastly Hard, Linkinteen Parks Buck and D-Sides Try Harder Hard also passed
strict full-song checks with unchanged settings:
`tmp/codename-three-final-binary.json`. These native gates still do not record
receptor pixel alignment or expiration, directional pose pixel parity, or
source audio mix comparison.

The final automated suite after reconciling the standalone Haxe test fixtures
passed **1,319 tests across 393 modules in 206.1 seconds**, with 61 skipped
and zero failures (`tmp/full-suite-final-after-fixture-reconcile.log`). The
fixture changes expose current production helper and animation fields to the
isolated test harnesses; they do not change donor files or game content.

A final-binary private Xvfb Ghastly Hard capture reached the 66,000 ms smoke
endpoint with four screenshots, zero strict diagnostics, and unchanged
repository, installed, and overlay options
(`tmp/ghastly-sustain-visual-final/ghastly-sustain-visual.result.json`). In
its `mid-holds` frame, the sampled gray up receptor, blue hold head, and blue
tail have horizontal pixel centroids at x=1045.07, 1045.10, and 1044.40,
respectively. This directly checks the visible alignment in one current
frame; it does not establish every style, moving receptor, or source-engine
frame parity. The screenshot is
`tmp/ghastly-sustain-visual-final/ghastly-sustain-visual-mid-holds.png`.
The same capture shows the opponent up receptor glowing in `early-holds` and
back at its gray static appearance in `next-holds` about 0.9 seconds later.
This is one native expiry observation, not a survey of every receptor style.

### Codename suffix poses and indexed source-stage group members (27 September 2026)

The mounted Codename `Character.hx` enumerates every XML animation name
starting with `singRIGHT` and swaps the corresponding left/right frames and
offsets when the player slot disagrees with `playerOffsets`. The shared helper
had swapped only the base and miss names. It now receives the authored
animation-name order and handles every suffix, including one-sided pairs.
The mounted D-Sides `bf.xml` includes a concrete `-dodge` pair with distinct
offsets; no package or character ID selects the fix. The production helper
test covers base, miss, alt, dodge, hold, missing counterparts and matching
orientation, and the four Codename, legacy, Psych and V-Slice focused
orientation tests pass. The stable canonical build passed
(`tmp/build-after-codename-suffix-and-indexed-group-stable.log`). A native
source-versus-rendered pose comparison for each suffix remains open.

An untested Psych archive `Satin Panties` Hard replay executed the selected
compiled `Limo` stage, then failed after `Kill Henchmen` when source
`grpLimoDancers.members[i].x` read a native lifecycle bridge without an `x`
field. The before receipt is
`tmp/psych-archive-real-import-v3/satin-panties-hard-limo-native-smoke-20260927.json`.
The owner-scoped HScript array-index read now returns the bridge's source
object for this scope, without replacing the native group member; foreign
scope bridges remain isolated. The focused HScript-ex group regression checks
indexed read, property write-through, unchanged native storage and scope
isolation; it and three adjacent native-group bridge tests pass. On the rebuilt
binary, `Satin Panties` Hard executed `states.stages.Limo`, reached its
96,079 ms natural ending, dispatched 2/2 due events, logged zero strict
diagnostics and preserved repository, installed and private settings hashes.
Receipt: `tmp/psych-archive-real-import-v3/satin-panties-hard-limo-final.json`.
This proves one source-stage runtime path, not source visual/audio parity or
the archive's remaining chart difficulties.
After correcting the patcher's pristine-copy marker, the final parallel
automated suite passed **1,320 tests across 393 modules in 209.5 seconds**,
with 61 skipped and zero failures
(`tmp/full-suite-after-indexed-group-and-codename-suffix.log`). The earlier
single `test_codename_script_interp.py` fixture failure was confined to the
patch script's insertion marker; that module now passes all five tests.
`./run.sh build` then reported the release build up to date after the marker
fix (`tmp/build-final-after-patcher-marker.log`); `git diff --check` passed.

The full-playthrough driver's default matrix still pointed to the
25 September inventory after owner-qualified D-Sides collision repairs. It
now defaults to `tmp/example_mods_current_chart_matrix.json`, whose current
read-only preflight yields 173 ready and 83 blocked raw rows (one is the
undeclared empty DDTO++ Baka key). This changes test selection, not imported
charts. `tools/tests/test_example_full_playthrough.py` passes all eight tests;
full-song verification of the 173 ready rows remains open.
The same driver now enables the smoke harness's strict diagnostic gate for
each full-song row, so a callback or dependency error outside its shorter
legacy log regex cannot be counted as a pass. Its eight focused tests pass.

### V-Slice stage named props and Psych source blend constants (27 September 2026)

The current-matrix DDTO++ `Ajena` Normal row passed its 21,199 ms strict
natural ending with 3/3 due events and zero diagnostics. `Baka` Alt reached
151,636 ms and dispatched 45/45 due events but initially failed on three
null prop accesses (`blend`, `alpha`, `setPosition`); this was not counted as
compatible (`tmp/ddto-first-three-current.jsonl`). Source Stage HXC calls
`getNamedProp` with the JSON-authored names, while generated stage HScript
kept only sanitized `vSliceProp_*` locals. New importer output now registers
each exact authored name. For old imports, selected V-Slice generated prop
blocks register their live sprites in the stage element map in memory, and
ambiguous sanitized-name matches remain unresolved. The first attempted
runtime lookup used HScript's public `variables` map, but top-level `var`
declarations are locals captured by callbacks; its replay retained all three
errors (`tmp/ddto-baka-alt-named-props-after.jsonl`). The corrected mapping
passed all 59 V-Slice importer/stage compatibility focused tests, the
canonical `./run.sh build` (`tmp/build-vslice-legacy-prop-registration.log`),
and a strict offscreen Baka Alt replay on the existing import: natural
151,636 ms ending, 45/45 due events, zero diagnostics, unchanged options
(`tmp/ddto-baka-alt-legacy-props-after.jsonl`). No donor or imported file was
edited. This establishes one script path, not every DDTO++ chart or visual
parity.

The private Psych archive `Blazin` Hard replay cleared the Animate `danced`
callback errors after a generic character generator fix. It then exposed
unqualified `MULTIPLY` from Psych's source BlendMode enum; the compiled-stage
bindings now publish the existing full blend facade, and focused blend/dance
tests pass. The next replay got past `MULTIPLY` and revealed a separate
`GameOverSubstate.deathDelay` dependency. Its strict result remains failed,
with receipt `tmp/psych-archive-real-import-v4/blazin-hard-phillyblazin-after-blend-binding.jsonl`.

A shared per-song `deathDelay` bridge now accepts finite nonnegative source
values and defers the native game-over transition while gameplay stays still.
The zero path remains immediate. Eight focused Psych dance/blend/game-over
tests and canonical `./run.sh build` pass
(`tmp/build-psych-deathdelay-after-vslice-props.log`). The next private Blazin
replay got past stage construction, then failed `createPost` on
`Invalid field:noAnimation` and a null camera `focusOn` access. It reached
the 122,666 ms natural ending with unchanged options but remains a strict
failure (`tmp/psych-archive-real-import-v4/blazin-hard-phillyblazin-after-death-delay.jsonl`).

The next current-matrix DDTO++ batch records Baka Normal as a strict pass at
151,301 ms, Bara no Yume Normal as a failure despite its 175,503 ms ending
because of two null `alpha` writes, and Beathoven Natsuki Mix Normal as a
failure before `playstate_ready` with unsupported HXC callbacks and a native
allocator abort. Receipt: `tmp/ddto-next-three-current.jsonl`. The latter
two are under source/bridge investigation, not counted as compatible.

The generic HXC loader now keeps a recognized class with no PlayState hooks
as a parseable empty scope. Beathoven's selected song class only implements
Freeplay metadata, so its prior empty-output rejection was a loader defect.
The focused parse-and-execute test and canonical build pass
(`tmp/build-psych-note-camera-hxc-empty.log`). Beathoven Normal then reached
its 108,575 ms natural ending with 23/23 due events, no native abort, and
unchanged options. It remains a strict failure on ClubroomFestival's
unsupported `onCountdownStart` shader callback
(`tmp/ddto-beathoven-empty-hxc-after.jsonl`). The existing shader descriptor
adapter would suppress that callback's additional shadow refresh and
character positioning, so broadening its scope without composing those
actions would silently lose source behavior.

The same build adds Psych `noAnimation`/`noMissAnimation` hit and miss gates
and camera `focusOn` forwarding (focused Haxe tests pass). The private Blazin
replay then SIGSEGV'd during `PhillyBlazin.createPost`, before stage load
(`tmp/psych-archive-real-import-v4/blazin-hard-phillyblazin-note-camera-hxc-empty.jsonl`).
The retained core's native stack points to
`FlxTypedContainer.onMemberAdd` through `PsychBaseStageCompat.addBehindBF`:
the script passed a Psych actor-group facade into native `PlayState.insert`
instead of its live actor. The scene boundary is under generic repair; this
is an open native crash, not a strict pass.

The shared scene boundary now resolves Psych actor-group placement facades to
their live native actors for add/remove/insert and actor-index lookups. Its
focused member-order regression and the canonical build pass
(`tmp/build-psych-actor-group-scene.log`). The next private Blazin Hard
replay executed the selected `states.stages.PhillyBlazin`, reached
`stage_loaded`, `playstate_ready`, `song_start`, and its 122,666 ms natural
ending, returned 0, and logged zero strict diagnostics/interpreter errors.
Private and installed settings hashes remained unchanged. Receipt:
`tmp/psych-archive-real-import-v4/blazin-hard-phillyblazin-actor-group-scene.jsonl`.
This validates one compiled stage run-through, not its frame-by-frame visual
or audio parity. The donor character constructor also sets `skipDance` for
two source characters outside imported JSON; their exact idle/dance behavior
remains to be compared and represented generically.

The mounted Psych source sets `skipDance` in its engine Character constructor
for some characters and later toggles it in stage/game-over code. The archive
character JSON has no such field, and the current importer has no donor
engine-profile input from which to recover constructor defaults. A shared
runtime flag can preserve dynamic toggles, but the initial policy cannot be
inferred safely from JSON or animation names without a character-specific
rule. This is an explicit source-input gap for exact Blazin idle/dance parity.
Refreshing generated character scripts, if needed, must target only exact
old-template bytes in the selected owner and preserve user edits/registries.

A shared mutable `Character.skipDance` flag and early `dance()` guard now
support stage-driven runtime toggles for imported standard and Animate
characters without changing sing/direct animation calls. The synthetic
HScript toggle test and canonical build pass
(`tmp/build-psych-skipdance-runtime.log`). This does not recover source-only
constructor defaults. A fail-closed importer could extract literal defaults
from an explicitly supplied donor Psych `Character.hx` into owner-scoped
metadata, but ordinary mod roots do not contain that file; unrecognized
constructor syntax would need an explicit unsupported diagnostic.
The latest binary also re-passed the private Blazin Hard strict ending at
122,666 ms with zero diagnostics and unchanged options after this runtime
guard (`tmp/psych-archive-real-import-v4/blazin-hard-after-skipdance-runtime.jsonl`).

The next parallel automated run covered **1,329 tests across 398 modules**
with 61 skipped. Three standalone fixture failures from the preceding run
were corrected, and their nine targeted tests pass. The remaining failure
was the mounted auto-import scanner aborting in glibc with
`corrupted size vs. prev_size while consolidating`
(`tmp/full-suite-after-skipdance-and-fixture-reconcile.log`). The exact
scanner test passed when rerun alone in 150.2 seconds
(`tmp/hxc-mounted-auto-import-alone-after-skipdance.log`). This is an
intermittent native allocator defect under investigation, not a green full
suite or proof that the scanner is stable.

The separate ModdingPoop Cursed Expurgation Hard strict replay reached its
193,073 ms ending but failed on 135 script diagnostics
(`tmp/moddingpoop-current-strict.jsonl`). The mounted donor stage script calls
`cstaticthing()` at line 251 but defines `staticthing()` at line 444; the
donor's literal `assets/sounds/staticSound.ogg` path is absent while a file
with that basename is under the stage directory. Its modchart declares
`gramlan` null, writes `gramlan.x` every update from the first frame, and
does not initialize it until the later `doGremlin` callback. These are
source/package defects or unresolved source path conventions, not a reason
to fabricate a song-specific engine alias. The strict row remains failed;
the engine's null-write recovery allowed the rest of the chart to reach its
ending, which does not establish source-matching behavior.

Modding Plus `Fired` Easy, Hard, and Normal each passed the strict offscreen
natural-ending check at 249,654 ms with zero native script diagnostics and
unchanged options (`tmp/modding-plus-fired-all-current.jsonl`). This covers
those three chart difficulties' run-through path, not frame-by-frame source
visual/audio or editor parity.

Modding Plus `Let Us In` Easy, Hard, and Normal also passed strict offscreen
natural endings at 164,241 ms, with zero native script diagnostics and
unchanged options (`tmp/modding-plus-let-us-in-all-current.jsonl`). Their
source visual/audio and editor parity remains unverified.

Modding Plus `Slaughter` Easy, Hard, and Normal passed the same strict gate at
203,100 ms with zero diagnostics and unchanged options
(`tmp/modding-plus-slaughter-all-current.jsonl`). All nine inventoried Modding
Plus chart difficulties now have strict natural-ending passes on this binary;
source visual/audio comparisons, repeated loads and editor round trips are
still open.

The separately inventoried Psych `Weiner` Hard row passed a strict offscreen
118,350 ms natural ending with zero diagnostics and unchanged options
(`tmp/psych-weiner-current-strict.jsonl`). This is a run-through check, not
source visual/audio or editor parity.

The three current-matrix Psych `vs_brucedaworst_update_2_hotfix` rows all
reached natural endings with unchanged options but failed the strict gate.
Each selected `nullspace.lua` stage reported unsupported `setPosition()` and
`fpSong()` calls, followed by null visual reads and nil arithmetic; the
diagnostic pattern is shared across the three rows
(`tmp/psych-brucedaworst-all-current.jsonl`). A generic Psych Lua stage API
translation is under investigation. None of these rows count as compatible.

Read-only source comparison narrowed this failure. The selected donor stage
uses `dadOpponent.visible`, `dadOpponent.setPosition(...)`, and
`PlayState.instance.fpSong()` in its six-line `onCreate`. The full Lua
translator preserves all three expressions, but the stage interpreter has no
`dadOpponent` binding and neither the package nor this engine defines an
`fpSong` contract. The null width access causes nil arithmetic before the
later calls run. The two `unsupported-stage-api` warnings came from the
unused static fallback converter; `loadPsychStageCompat` now emits those
warnings only when it actually selects or recovers through that fallback.
This diagnostic fix does not make the three chart rows compatible.
The rebuilt native Bruce Normal replay confirms the selected full Lua path now
reports three actual runtime diagnostics rather than five; it still reaches
the 92,800 ms natural ending and fails strict compatibility with the same
null actor/nil arithmetic path, with options unchanged
(`tmp/psych-bruce-stage-warning-selection-after.jsonl`).

The pinned hxcpp 4.3.2 `FreeLarge` patch now guards the live-list ownership
check before clearing the allocation marker, reading the header, changing
accounting, or recycling. The original no-capacity marker path remains as
upstream. The exact-source and idempotence tests pass 3/3, and canonical
`./run.sh build` recompiled `Immix.cpp` successfully
(`tmp/build-hxcpp-ownership-and-stage-diagnostic.log`). The patch addresses
one unchecked duplicate-recycle route seen in the native allocator audit;
scanner and full-suite stability checks are still running, so no general
native-crash resolution is claimed yet.

The exact mounted auto-import scanner test passed once on the patched native
toolchain in 192.1 seconds
(`tmp/hxc-mounted-auto-import-after-hxcpp-guard.log`). The first broad parallel
suite exposed three private diagnostic-overlay test failures because that
overlay still expected pristine installed `Immix.cpp` bytes; its private
source pin is being reconciled with the normal guarded toolchain. A single
scanner pass does not establish intermittent-crash stability.
After the private diagnostic patchers accepted both exact pristine and
run.sh-managed hxcpp sources, all 23 overlay tests passed
(`tmp/auto-import-diagnostic-cache-after-hxcpp-guard.log`). The first full
parallel suite finished **1,332 tests across 399 modules**, 61 skipped, with
only that overlay module failing; its mounted scanner passed under parallel
load (`tmp/full-suite-after-hxcpp-ownership-guard.log`). A clean full-suite
rerun followed after the overlay fix.

The clean rerun completed: **1,332 tests across 399 modules**, 61 skipped,
**zero failed**, including the mounted auto-import scanner under parallel
test load (`tmp/full-suite-after-hxcpp-private-overlay-fix.log`). This removes
the overlay test break and supplies one additional native scanner pass; the
historically intermittent allocator fault still warrants continued native
song/switching stress rather than a claim of exhaustive stability.

An exact song/difficulty/variant audit of strict native receipts against the
current 256-row matrix found **89 of 255 chart routes** with a passing
natural-ending receipt. The excluded row is DDTO++ Baka Alt Normal, an empty
undeclared variant key; FNAS After Hours Better Clone Normal remains an
inventoried chart route with private-only structural evidence. Current strict
coverage by package is: bully 1/1; HL17 3/3;
PERFEXION 2/6; Bruce 0/3; vswhitty 32/47; Psych source archive 2/78;
Miku 3/3; DDTO++ 3/68; Vs Tricky 10/10; Wacky 3/3; Modding Plus 9/9;
ModdingPoop 0/1; D-Sides 20/22; Weiner 1/1. These are run-through counts,
not visual/audio/editor parity. The installed DDTO++ rows beginning with
Carol Roll Sayori Mix through Crucify Yuri Mix (seven difficulties) have
owner/chart/note parity and are the next native batch. The Psych archive's
78 rows remain a separate installed-owner/import coverage gap despite two
passing private-runtime source-stage replays.

Archive ownership audit found this is deliberate isolation: the matrix marks
the archive as `referenceOnly` and does not attribute canonical song folders
to it. Of 78 same-path candidates, 71 files exist but 30 rows select D-Sides
and 48 have no archive owner manifest. The importer correctly plans
owner-qualified destinations for base/foreign collisions; 27 archive songs
would need such destinations, and only 26 songs/76 rows have packaged Inst
audio. The existing v4 private runtime is unsafe as an import promotion base:
379 of its paths are symlinks into v3, and v3 has 169 symlinks into the live
runtime, including shared data/settings paths. No live or v4 refresh was made.
A fresh independent runtime, scoped path manifest, and backups are required
before promoting archive content without risking other imports or settings.

The seven-row DDTO++ native probe produced two strict passes (Carol Roll
Sayori Mix Normal and Constricted Normal) and five failures
(`tmp/ddto-next-seven-after-hxcpp-guard.jsonl`). Catfight Normal SIGSEGV'd
in the native `PlayState.tweenScrollSpeed(Dynamic)` after its HXC script called
the V-Slice positional API with a missing per-line `scrollSpeed`; the retained
system core is PID 2420748. Cheerful Vision Normal and Crucify Yuri Mix
Easy/Normal/Hard reached natural endings with exact event dispatch but each
failed on a selected HXC stage `onCountdownStart` body. These remain failed
until source-backed shared bridges pass replay, rather than being counted from
their endings.

FunkinCrew's source API confirms the missing contract: `Strumline` owns a
mutable `scrollSpeed` and `resetScrollSpeed`; PlayState's positional
`tweenScrollSpeed` accepts a scalar, seconds, easing callback and named lines,
while `tweenCameraZoom` accepts zoom, seconds, direct/stage-relative mode and
easing. The shared native bridge now exposes these methods, keeps per-line
speed only after a script explicitly changes it, uses that speed for note
travel/sustain scaling, and cancels/pauses/resumes source tweens with gameplay.
The event-object scroll handler remains for chart events and rejects a missing
payload without native dereference. Focused production-method Haxe coverage
passes (`tools/tests/test_vslice_scroll_speed_api.py`); canonical build passes
(`tmp/build-vslice-scroll-camera-bridge.log`). Catfight Normal then passed its
186,085 ms natural ending with 38/38 due events, zero script diagnostics,
return code 0, and unchanged options
(`tmp/ddto-catfight-after-source-scroll-api.jsonl`). Exact frame-by-frame
scroll/camera parity and pause/seek behavior remain to be checked.

## Current offset, HXC, and archive checks (2026-09-28)

V-Slice character geometry now keeps the authored `CharacterData.offsets`
separate from role/stage placement. The shared character draw path applies
the current animation offset relative to that global offset at the actor's
scale. New imports mark authored globals; existing generated characters
snapshot their legacy global values before a stage can reposition them.
HXC indexed `animOffsets[0/1]` and `globalOffsets[0/1]` reads route through
the current receiver's native character. The focused Haxe fixture and all
58 V-Slice importer tests pass. Rabbit Hole Normal reached its natural
ending with 592/592 due events and no script diagnostics on this build
(`tmp/rabbit-hole-after-global-offset-bridge.jsonl`). Rendered directional
pose comparison across formats is still open.

A second, independent orientation audit found that the legacy player-facing
path swapped only three fixed left/right animation pairs, and gated even
those on an unsuffixed `singRIGHT`. The shared helper now discovers every
matched `singRIGHT<suffix>`/`singLEFT<suffix>` pair and carries each pair's
frame list and named offset together. This covers alt-only and other
suffixes while leaving Psych authored flip metadata, Codename's own pair
logic, and V-Slice authored direction labels on their existing paths.
The donor Modding Plus `vsfreddy_1_9_5` parents character provides a real
left/right alt pair with distinct offsets. Focused production-helper Haxe
tests for standard, alt-only, and unpaired suffixes pass. The rebuilt native
binary runs the imported VS Freddy `Fired` Normal row to its 249,654 ms
natural ending with zero diagnostics (`tmp/vsfreddy-firing-after-orientation.jsonl`).
Rendered directional pose comparison is still open.

The DDTO++ four-route strict batch on this build is recorded in
`tmp/ddto-target-after-shader.jsonl`. Cheerful Vision Normal now reaches a
natural ending with zero script diagnostics, including the formerly failing
EvilClubroomSayo stage callback. Catfight Normal and Drinks On Me Normal
reach natural endings but strict checks fail because donor HXC
`CustomTitleBar.hxc` requests `assets/dokicon.png`, absent from the mounted
DDTO source. Constricted Normal also reports a null division in the donor
`constricted.hxc#start`; source behavior is under investigation. The missing
icon is an explicit source dependency; these rows are not counted as clean
passes. The strict parser now counts null-operand/null-iterator and missing
window-icon diagnostics, so earlier apparently clean receipts with those
lines are superseded by `tmp/ddto-reclassification-after-null-diagnostics.json`.

The current full automated suite passes **1,346 tests across 402 modules**,
61 skipped, zero failed (`tmp/full-suite-after-hxc-count-reconciliation.log`).
`./run.sh build` passed on this source (`tmp/build-after-character-stage-constants.log`).
The live options hash was unchanged. An isolated physical private import of
the Psych source archive imported 26 songs/76 difficulties with owner/chart
note-row parity; two source rows (Ridge Normal and Smash Normal) lack packaged
instrumentals (`tmp/psych-archive-isolated-import-v5/result.json`). The
private runtime's direct runner passed a current-binary 2Hot Easy natural
ending with zero diagnostics and unchanged private options
(`tmp/psych-archive-isolated-import-v5/direct-2hot-probe.jsonl`). The complete
76-row offscreen run is in progress; no comprehensive archive gameplay or
visual/audio parity claim is made from import and preflight alone.

The ongoing archive sweep first exposed Cocoa and Eggnog Easy/Normal/Hard
with the same two Mall-stage errors at their first `Hey!` event:
`trim` was treated as a missing String method, and `MallCrowd.heyTimer`
received a null value that failed its later `> 0` check. The selected
Psych source has global `using StringTools` (`source/import.hx`) and its
`PlayState.triggerEvent` changes an empty/nonpositive `Hey!` duration to
0.6 seconds before calling `BaseStage.eventCalled`. Shared interpreter
StringTools extension routing and stage event value normalization have
focused production-interpreter/Haxe tests and rebuilt native replays. All six
rows failed in the pre-fix sweep receipts.

The completed pre-fix archive sweep returned **67 strict passes and nine
failures out of 76** (`tmp/psych-archive-isolated-import-v5/direct-all-76.jsonl`).
The nine were exactly the six Mall rows above and Stress Easy/Normal/Hard,
whose selected Tank stage failed while reading the imported `TankmenBG`
source class's static `animationNotes` field. The rebuilt binary now passes
all six Cocoa and Eggnog Easy/Normal/Hard rows to natural audio completion,
with zero native script diagnostics and unchanged private options
(`tmp/psych-archive-isolated-import-v5/replay-mall-after-hey.jsonl`).
The focused source interpreter, stage event, and character orientation batch
passes 25 tests (`tmp/focused-after-hey-orientation.log`); source visual and
audio parity and the Tank static field repair remain open.

Constricted Normal was replayed on the rebuilt binary after binding Psych's
`defaultHUDCameraZoom` alias to the live HUD zoom. The former null arithmetic
diagnostic is gone; the row reaches its 120,727 ms ending and dispatches all
63 due events. Its sole remaining strict diagnostic is the DDTO source's
missing `assets/dokicon.png` dependency, so the row remains failed
(`tmp/ddto-constricted-after-default-hud-zoom.jsonl`).

HScript-ex class statics now live in the selected owner's `ScriptClassScope`.
Interpreter property reads/writes and native compatibility writes share one
declared static variable, which is released with that owner. The focused
static fixture passes (`tools/tests/test_script_class_static_fields.py`).
Psych's retained `source/objects/Character.hx` declares a companion-chart
animation mapping; a bounded source parser reads the actor, chart, static
target, initial pose and dance setting from that source rather than embedding
their names in engine code. The native compiled-stage path reads only that
selected chart folder and passes the mapped note array to both the character
and owner static field. Stress Easy/Normal/Hard now reach their 124,032 ms
natural endings, each dispatches 5/5 due events, and each has zero script
diagnostics (`tmp/psych-archive-isolated-import-v5/replay-stress-after-static-map.jsonl`).
All three PlayState-ready traces show 505 scheduled notes, `shoot1`, and
`skipDance=true` on the girlfriend actor. This establishes the source data
handoff; frame-by-frame tankmen animation and random spawn parity still need
visual comparison.

A fresh **single-binary, offscreen natural-ending sweep passed all 76/76
imported Psych archive difficulties** with zero strict script diagnostics,
one natural ending per row, and unchanged private options
(`tmp/psych-archive-isolated-import-v5/direct-all-76-after-static-map.jsonl`).
The selected archive still has two source rows without donor instrumentals
(Ridge Normal and Smash Normal), so those are explicitly unimported. This
full-song gate does not cover source frame/audio comparison, editor round
trips, seeking, pause/resume, menu paths, or failure recovery; it is not the
goal's complete archive compatibility verdict.

The first offscreen Wilted Normal replay crashed at its timed note-style swap
after reaching the event. A native debugger located the fault in
`Note.switchType`: a live sustain segment could still reference an earlier
segment whose Flixel animation controller had been released. The shared swap
path now excludes destroyed note slots and tests the predecessor's live
animation controller before changing its hold frame. The rebuilt private run
reached the 151,088 ms natural ending with all 34/34 events and no crash
(`tmp/wilted-after-sustain-prev-and-point.jsonl`). The generic HXC adapter also
preserves bounded `FlxPoint.get`/`new FlxPoint` field initializers, removing
the stage-camera null errors seen before countdown. A later shared HXC actor
binding fix removed the pixel-character field errors, and replaying the donor
`setScale` lifecycle callback initialized character script state before its
screen-position callback. The latest native trace records the initial Monika
actor at its authored 0.9 scale and reaches the 151,088 ms ending with 34/34
events (`tmp/wilted-final-clean.jsonl`, run token `0.084`). The final clean
binary has no temporary scale probes. **Wilted still fails the
strict gate** because the mounted donor lacks `assets/dokicon.png`, requested
by its window script. Rendered source parity and interactions remain open; the
natural ending alone is not a compatibility pass.

After removing temporary native scale probes, `./run.sh build` passed
(`tmp/build-hxc-final-clean.log`) and the full parallel test suite passed
**1,356 tests across 405 modules, with 61 skipped and zero failed**
(`tmp/full-suite-final-after-clean.log`). `git diff --check` was clean.

### Psych archive installed-owner promotion (28 September 2026)

The same native Auto importer used in the isolated trial was run offscreen
against the installed release runtime under the build/import lock. Scoped
backups of the existing registries and options are retained at
`tmp/psych-archive-live-promotion-backup/`. The import reported 26/26 songs,
zero failures, and 1,734 copied assets. Its 26 selected-owner manifests use
the archive's own `psych-engine-fnf-psychengine-main-d942d5457b` root.
Hashes of all 517 preexisting chart JSON files were unchanged, including
base and D-Sides collisions, and the live options file was restored byte for
byte (`tmp/psych-archive-live-promotion-backup/receipt.json`).

The updated installed-owner matrix is
`tmp/example_mods_current_chart_matrix_after_psych_promotion.json`.
Native preflight finds **76 ready / 2 blocked** archive rows. Ridge Normal
and Smash Normal remain blocked because the mounted ZIP has no corresponding
instrumentals (`tmp/psych-archive-live-matrix-preflight.jsonl`). On the
installed runtime, 2Hot Hard, Monster Hard, and Stress Hard each passed an
offscreen natural ending with zero diagnostics and unchanged personal options
(`tmp/psych-archive-live-sample.jsonl`); Monster checks a base/D-Sides name
collision and Stress checks the compiled stage static-field path. The full
76-row natural-ending sweep remains the isolated-runtime receipt above.
Neither that sweep nor these three installed samples prove source visual,
audio, editor, menu, pause/seek, skip, or failure-recovery parity.
The refreshed 256-row cross-package preflight is 249 structurally ready and
seven blocked (`tmp/all-example-preflight-after-psych-promotion.jsonl`); this
is an import/media gate, not a complete compatibility result.
One of those seven is DDTO++ Baka's empty, undeclared `alt/normal` chart key,
which is retained in the raw inventory for audit but is not a playable source
difficulty. The playable tally is therefore 249 structurally ready of 255,
with six blocked by absent installed chart or source media.

The offscreen importer now accepts a single validated package label when
exactly one selected package lacks authored metadata, using the interactive
importer's existing name map. This is needed to install FNAS without silently
adopting a folder-derived Freeplay label; its name choice is pending. The
focused harness suite passed 23 tests and the full suite passed **1,356 tests
across 405 modules, 61 skipped, zero failed** after this change
(`tmp/full-suite-after-import-name-option.log`). The final `./run.sh build`
passed (`tmp/build-import-name-validation-final.log`), retained all 26 archive
owner manifests, and preserved personal options byte for byte.

A current installed DDTO++ preflight finds 67 structurally ready chart rows
and one undeclared empty difficulty key (`tmp/ddto-installed-preflight-current.jsonl`).
Crucify Yuri Mix Normal/Easy/Hard then each reached its 173,550 ms natural
ending with all 38/38 events and no new engine script diagnostics. All three
remain strict failures solely because the selected donor's
`assets/dokicon.png` window icon is absent from the mounted package
(`tmp/ddto-crucify-three-current.jsonl`). These endings are not source
visual/audio or interaction parity evidence.

The installed Psych archive initially used its extracted folder name as a
Freeplay label even though its source `Project.xml` authors the title
`Friday Night Funkin': Psych Engine`. Shared package-name detection now reads
that bounded XML title and avoids appending an engine suffix already present
in the title. A scoped, backed-up live metadata refresh updated 26 archive
provenance records and 25 owner-qualified Freeplay rows; it touched no charts,
audio, donor files, or personal options
(`tmp/psych-archive-label-refresh-20260928/receipt.json`). The remaining
unqualified Blazin entry stays in its existing Freeplay slot. The production
name helper's focused seven-test suite passes
(`tmp/test-import-song-ownership-project-title.log`).

The first offscreen menu run selected the installed owner-qualified `2hot`
row from Imported Freeplay and reached `ModifierState`; the original harness
stopped there, correctly failing its gameplay gate. The generic harness now
accepts only the default Play action and waits for `PlayState`. A rebuilt
offscreen run then selected that same archive row, passed through
`ModifierState`, reached `PlayState`, started the song, and emitted success
with zero strict diagnostics and unchanged personal options
(`tmp/psych-archive-freeplay-to-gameplay-27s.receipt.json`). Its live registry
label is `2Hot · Friday Night Funkin': Psych Engine`. This covers the real
menu-to-gameplay route for one selected row, not the archive's other menus or
source-rendered parity.

An editor round-trip regression found that editing or deleting an event
loaded from a companion `events.json` was undone on reload or gameplay merge.
The shared chart model now persists a companion source signature on edited
rows and an inert tombstone on deleted rows; both the editor and
`SongEvents.collect` suppress the unchanged source event. The source sidecar
remains untouched. An extracted Haxe fixture covers edit, move, delete,
save/reload, runtime event collection, and unchanged owner/difficulty routing.
Forty focused editor/event/import/menu tests pass, and `./run.sh build`
passes (`tmp/build-editor-sidecar-and-freeplay.log`). A live native editor
round trip with UI input remains open.

The final parallel full suite passed **1,358 tests across 405 modules, with
61 skipped and zero failures**
(`tmp/full-suite-after-editor-sidecar-and-menu-final.log`). The first sweep
found one extracted smoke-test fixture that omitted the new Freeplay state
fields; its focused test passed after the fixture was updated, and the final
full sweep is clean.

An opt-in `--smoke-chart-editor` path and private overlay runner are now
implemented for a native ChartingState create → event edit/delete → Quick Save
→ reload → runtime event collection check. The runner copies only its selected
chart folder into `./tmp`, injects two generic companion rows there, and
compares installed chart, sidecar and options bytes after cleanup. Its 47
focused tests pass. The runner subsequently passed on the 28 September
combined native build under private Xvfb and default test options. The
receipt and its one-owner scope are recorded in the latest-status section.

## Legacy Codename pending-state bridge — 28 September 2026

The old global HScript field `FlxG.game._requestedState` now reads and writes
through `CodenameRequestedStateCompat`, which maps it to Flixel 6's
`_nextState`. Known concrete `LoadingState` and Codename runtime targets are
leased to their outgoing state and the exact recorded request. A deferred
Codename outro binds the lease after Flixel's completion callback writes the
request. Source writes remain direct assignments and return the assigned
value. Cancellation, destroy-before-finish and owner clearing release their
leases; the normal finishing handoff stays available through `preStateSwitch`.
Each lease also installs a one-shot `postStateSwitch` cleanup, removed when
cleared, so a chart-owned handoff without an active global runtime cannot leave
stale compatibility state behind. The native trace reads the script-facing
`_requestedState` getter to report this value rather than Reflect-reading the
physical `_nextState` field.

Source/interpreter verification passed:

- `python3 -m unittest tools.tests.test_codename_requested_state_compat` — 2
  tests. The extracted Haxe fixture covers concrete and deferred known-target
  leases, request/outgoing-state scoping, setter return and direct-write
  behavior, request replacement, cancellation cleanup, one-shot
  `postStateSwitch` cleanup/removal, and zero factory invocations. Source checks
  confirm the production interpreter, switch paths, deferred callback, destroy
  cleanup, and script-facing trace getter are wired to the helper.
- `python3 -m unittest tools.tests.test_codename_script_interp.CodenameScriptInterpTest.test_constructor_context_and_async_cleanup_are_scope_local`
  — 1 test. The extracted production interpreter executes the legacy global
  script redirect from a concrete native menu state to an imported state.

The bounded final-build HL17 offscreen menu route reached
`HL17MainMenu.hx`'s create-ready marker. Its global pre/post trace reported
`CodenameImportedState` as the requested state on both sides of the callback,
so this route verified startup and the script-facing trace getter but did not
exercise the donor's `MainMenuState` or `FreeplayState` type checks. Existing
HL17 menu paths inspected here switch to imported `IntroState`, launch
`PlayState` directly, or clear the owner before returning to native menus; no
ordinary route was found that requests native MainMenu or Freeplay while that
global callback remains active. The native receipt is
`tmp/hl17-menu-native/result.json`; its overall status is partial because the
separate static source-use scan reports `gpuOnlyBitmaps`, not because of a
requested-state redirect failure. Native HL17 coverage of those two typed
redirects remains open.

These checks do not establish native timing for every transition. An unknown
factory remains its raw `_nextState` value and is never invoked by the bridge.
The observed Shift+Escape `resetGame()` request is a `TFunction` with no
associated concrete target, so legacy `Std.isOfType(requestedState,
TitleState)` remains false for that request. This is an explicit compatibility
limit; invoking the factory before Flixel destroys the outgoing state could
break lazy state construction and the runtime bitmap-cache guard. The donor
global script remains an unmodified regression fixture, with no chart-name or
mod-name conditions added.

## D-Sides Try Harder event-end audit — 28 September 2026

The earlier `657/658` count is source-matching. The selected donor contains 625
rows in `songs/try-harder/events.json` and 33 embedded rows in
`songs/try-harder/charts/hard.json`, for 658 total. The final companion row is
at 255650.397575 ms. The final embedded `Camera Movement` row is at
262573.474498 ms, 551.161 ms after the 262.022313-second instrumental ends.
The donor and installed `Inst.ogg` are byte-identical (SHA-256
`41446b1cd648951fa4ea761184cb38da6c16fdd57976e5cba8da053cdabb0b2f`), and
both decode to 262.022313 seconds.

The available Codename source snapshot sorts events by time and dispatches a
row only when its timestamp is at or before `Conductor.songPosition`
(`tmp/codename-upstream-v1.0.1/PlayState.hx:1117,1407`); song start assigns
`inst.onComplete = endSong` (`:1050`). The shared queue flushes through the
instrumental boundary before ending (`source/PlayState.hx:11234-11288`). Thus
657 events are due and 657 dispatch; the one later chart row is correctly not
due. A fresh offscreen native marker records `dueEvents=657`,
`dispatchedEvents=657`, `totalEvents=658`, with a zero-diagnostic strict pass
and unchanged settings (`tmp/try-harder-direct-icon-marker.jsonl`,
`tmp/codename-three-final-binary.json`). No event-timing fix is indicated.

This full-song event result does not prove pixel or audio parity. Receptor
alignment/expiry, directional pose pixels, source audio mix, pause/seek/skip,
and repeat-load/switch behavior still require their shared compatibility
checks for this and the other example rows.

## Shared 3D readback allocation check — 28 September 2026

The pinned OpenFL 9.5.2 `Context3D.drawToBitmapData` path previously
allocated a full 2560×1440 byte array and `Image` wrapper for each Away3D
snapshot. `tools/patch_openfl_context3d_readback.py`, applied by `./run.sh`,
now retains one array and wrapper per context, replaces them on resize, and
drops them on disposal. The GPU readback, bitmap copy, and Flixel upload still
occur. Its exact-source/idempotence and build-hook tests passed 20/20; the
release build completed in
`tmp/build-codename-base-openfl-readback-20260928.log` (binary SHA-256
`ab853e4dff9d6b29c2d71c2be5c473d3399410ed0ff1a16afbf68fd3f4e6ed48`).

The same private Xvfb/dummy-audio Gordonteen scene profiler was run for 20
game seconds with repository default options except the FPS setting. Active
3D-scene median sampled FPS changed from **60/78/76** to **60/104/100** at
60/240/480 FPS settings. Peak process RSS changed from **1207.6/1188.3/1183.8
MiB** to **1003.9/1012.6/1005.1 MiB**. Median RSS changed from
**1097.9/1081.5/1072.1 MiB** to **896.5/912.5/904.2 MiB**. All three new
processes exited 0 with protected options unchanged. Before/after receipts
are `tmp/hl17-menu-native/gordonteen-perf-gpu-{before,after}-{60,240,480}.json`.

These short samples show lower allocations and better observed frame rate in
this environment. They do not prove stable memory during a whole song or
repeated switching, source-matching 3D pixels, or elimination of the user's
reported 1.3 GiB oscillation. The selected donor itself lacks the OBJ's
referenced `testStage.mtl`, which remains an explicit runtime diagnostic.
The reported floor-in-front-of-desk depth problem is still open; the cached
readback buffer does not change scene ordering or material rendering.

### HL17 Gordonteen floor/desk source audit — 28 September 2026

The selected HL17 source defines the ground as the `Flx3DView` containing
`models/plane.obj`; `data/stages/17.hx:38-53` inserts that view before gf, dad,
and boyfriend and explicitly supplies `images/textures/gradient` as the mesh
texture. The chart's gf actor is `barney`, whose `data/characters/barney.xml`
uses `images/characters/gordonteen/Desk Guys`; `Desk Guys.xml` describes its
idle frames as 959×404 rectangles. The donor image's `idle0009` crop has a
full-frame alpha bounding box, and the lower desk region is opaque. Installed
stage script, song script, and `models/plane.obj` hashes match their selected
donor copies. The song and stage scripts are therefore not missing a desk
asset or drawing a separate floor sprite over it.

The OBJ's line 3 references `mtllib testStage.mtl`. No MTL file exists anywhere
under the selected donor owner `mods/HL17` or the installed HL17 owner; the
exact unresolved dependency is
`mods/HL17/models/testStage.mtl` →
`assets/imported_mods/codename-engine-hl17-v3-b2d7aa552d/models/testStage.mtl`.
Native logs emit `[codename-3d-mtl-missing]` for that path and continue through
geometry and mesh completion. Since the donor has no sidecar to import and the
stage supplies its own gradient material, this is a source-package gap, not a
recoverable importer omission. No replacement MTL or texture was fabricated.

The older 25 September capture
`tmp/hl17-menu-native/gordonteen-3d-stage-after-bytes.png` shows the white plane
cutting across the composite desk. In the later 28 September installed-owner
capture, `tmp/hl17-menu-native/gordonteen-3d-snapshot-restored-late-480.png`,
the full gray desk front is visible in front of the plane. Its receipt records
a successful 480-cap run with unchanged private options; the paired process
log reports `view=27` and `gf=29` at draw frames 2, 60, 300, 360, and 420. The
pinned Flixel group also refuses duplicate insertion of the same object, so
the stage's repeated `insert` calls leave the 3D view before gf. This newer
installed capture suggests the reported ordering is no longer reproduced in
that scene, but neither capture is from the donor Codename runtime. Keep the
user's visual report open until a matched donor-versus-installed rendered
comparison establishes source parity. If the current default-options scene
reproduces the cutoff, a private `lowMemoryMode` comparison can isolate the
3D-view path without changing donor or personal settings.

### Automated suite after installation-overlay and readback changes

`python3 tools/run_tests.py --jobs 2` passed **1,424 tests across 428 modules**
with 61 skipped and zero failures
(`tmp/full-suite-codename-overlay-openfl-fixtures-fixed-20260928.log`). The
first run after the generic installation-overlay helper compiled the native
binary but left four standalone extracted-Haxe fixtures without the new helper
source. Those fixtures were updated, their affected modules passed targeted
reruns, and the complete suite then passed. This establishes shared-source and
importer fixture behavior; native source presentation parity and the remaining
inventory checks are separate gates.

### Fresh Codename owners and safeguarded live refresh (28 September 2026)

Fresh private imports of the exact mounted HL17, D-Sides, and FNAS outer
installations selected their existing live owners without touching the
installed files. The imports reported 3, 20, and 1 songs respectively,
with zero importer errors or missing dependencies. The D-Sides private
chart check resolved 22/22 imported destinations through recorded
provenance and started 22/22 PlayStates. FNAS used the user-selected
`FNAS After Hours` package label. Private receipts are
`tmp/codename-base-refresh-{hl17,dsides,fnas}-20260928/result.json`.

The final explicit generated-replacement plans added 9 HL17, 9 D-Sides,
and 4 FNAS owner files. They replaced 7 HL17 and 30 D-Sides generated
files whose exact source and old destination bytes were verified. The
D-Sides `songs/blammed/__cammie_compat_camera.json` remained a conflict:
the new generic character fallback would change source character IDs to
`bf`, but the selected source lacks `gf-dark`, `pico-dark`, and `bf-dark`
definitions, so there is no sufficient parity proof for this camera sidecar.
The plan preserved it unchanged. D-Sides owner-qualified chart folders were
resolved via `importProvenance.json.sourceFolder`, avoiding same-name base
chart evidence.

Apply receipts under `tmp/import-refresh-backups/20260928T182101585364Z`,
`20260928T182116509323Z`, and `20260928T182121378392Z` contain exact-file
backups and rollback data. Independent post-apply verification in
`tmp/codename-base-overlay-refresh-20260928/protected-after.json` checked
1,359 prior files: 37 planned replacements matched 37 backups, 22 additions
matched the plans, 1,322 other files were byte-identical, and the one
conflict was preserved. The repository options SHA-256 stayed
`0693e6470fa0d6ba48f2a1ab3f99bbbf8a98598d94d6d2a48db65d9d5f7ac66d`;
personal live options stayed
`285b2ce8234e38483693eaac81e080e9947c63b9584a1e169cb705be74085255`.
`./run.sh build` then succeeded and a second hash audit found the same
protected contents. The resulting release binary SHA-256 is
`e3bbeaf1b5b569bae1654a58b25fc69a2f582786fccc917e4c1ffaa97dcdf0c9`.

The complete post-refresh `python3 tools/run_tests.py --jobs 2` run passed
**1,430 tests across 428 modules**, with 61 skipped and zero failed
(`tmp/full-suite-after-owner-refresh-20260928.log`). The focused owner
refresh helper suite passed 20/20 cases, including bad-provenance rejection,
opt-in generated replacements, backups, and rollback. Automated tests do
not certify source rendering, animation, audio, menus, or cross-song cleanup.

### FNAS non-botplay ending on the refreshed owner

The offscreen private Better Clone Normal story/practice run did not enable
botplay. It reached the 206,896 ms natural audio end, dispatched 204/204 due
events, exited cleanly, reported zero strict script diagnostics, and left
repository and personal settings byte-identical. The process marker says
`codename-audio-complete hasOnComplete=true`; a frame captured one second
after `song_end` displays the authored `mini/r1` room and Sonic sprite from
`data/states/minigameyeaaaa.hx`. Evidence is
`tmp/codename-base-refresh-fnas-20260928/story-practice-no-botplay-result.json`,
its process log, and
`story-practice-no-botplay-after-song-end.png` in the same directory. The
runner did not record the state name in its marker stream, so its boolean
`authoredMinigameStateObserved` is false despite the visual handoff. Minigame
input, collision, music, and final exit still need source comparison.

### Confirmed donor media gaps

The PERFEXION Demo1 source contains Extra Hard, Extras Hard, and Gallery
charts, but no Extra, Extras, or Gallery instrumental under any case-insensitive
media path; Extra and Extras are byte-identical charts that both author
`song: "Extra"`. The only packaged song audio roots are RG, Resonance, and
Xfracture. Its `data/Extra/function.lua` and `data/Extras/function.lua` also
call `playMusic('extra_menu', ...)`, but the package has no
`music/extra_menu.ogg`.

The selected Psych archive contains Ridge Normal and Smash Normal charts,
but no corresponding Inst audio among its 354 audio members or nested
ZIP/FLA contents. Psych source `Paths.inst(song)` resolves to
`formatToSongPath(song)/Inst`, and source PlayState calls it with the chart's
authored song name. The archive SHA-256 is
`a337e2872b18516314b853b95cd1d0c1c20b8882e71323565e364eaca8e80ecd`.
These five chart rows are blocked by missing donor media, not an unhandled
importer lookup. The current 256-row matrix preflights 250 ready rows, these
five source-media blockers, and one undeclared empty Baka variant key.

### Refreshed Linkinteen Parks full-length visual check

The installed HL17 Buck chart ran at 1× through its 186,666 ms natural
ending in a private 1280×720 Xvfb display. All five due events dispatched,
the native process exited 0, there were no strict diagnostics, and the
repository seed, private default options, and personal live options kept
their original hashes. The five captured frames in
`tmp/hl17-after-refresh-20260928/` show the large playable actor with stage,
background video or scenery, strumline, and HUD after the first four
transitions. The last frame is black at the source script's intentional
step-1312 camera/HUD hide, after those transitions.

The runtime actor markers disprove the earlier stationary-after-first-
transition failure in this run: between 55 and 80 seconds the first switched
actor reported six distinct `(animation, frame)` poses, including left,
right, and up sing animations; the later actor windows at 92–115, 130–150,
and 165–185 seconds reported five, five, and six distinct poses. This checks
live native animation state, not only a static screenshot. Evidence is
`tmp/hl17-after-refresh-20260928/linkinteen-full-visual.result.json`, its
marker/process logs, and its five PNGs. Donor frame-by-frame comparison,
pause/resume and all difficulty/route combinations remain open.

### Refreshed Gordonteen bounded 3D frame profile

The post-refresh release build repeated private default-options Gordonteen
Bucks checks at configured 60, 240, and 480 FPS. All three bounded runs
exited 0, kept personal and private settings unchanged, and reported only
the explicit missing donor `testStage.mtl` diagnostic. Peak sampled RSS was
1,014.2, 1,005.7, and 1,001.7 MiB respectively. The 60-cap run settled
near 60 FPS; the 240/480 runs began around 90–110 FPS while the 3D view was
active and later reached their configured caps after a stage change. The
engine therefore has no additional 3D frame gate, but this host did not
sustain 240 or 480 FPS through the heavy view. Each run is about 23 seconds;
long repeated-load memory stability and donor visual parity remain open.
Receipts are
`tmp/hl17-after-refresh-20260928/gordonteen-perf-gpu-after-{60,240,480}.json`.

### HL17 donor Gordonteen desk/floor comparison

A read-only Wine comparison copied the exact mounted `hl17_v3` installation
into a private `tmp/hl17-donor-render-compare-20260928T184132Z/source-copy/`
and used a private Wine prefix, Xvfb display, and dummy audio. It opened the
authored HL17 menu and Chapter Select, selected Gordonteen Bucks, and captured
the source gameplay entry and frames three and seven seconds later. The
mounted donor tree SHA-256 stayed
`eb9c2f07258af37bd17df22bfb8f63fe00d82d5774f7d103064f5fe331f16ca8`
before and after the run; the private clone also remained unchanged.
Receipt: `tmp/hl17-donor-render-compare-20260928T184132Z/receipt.json`.

The source `donor-gordonteen-plus-3s.png` shows the 3D floor behind the
desk. The installed `tmp/hl17-menu-native/gordonteen-3d-snapshot-restored-late-480.png`
also shows the full desk front ahead of the floor; the earlier screenshot's
plane crossing the desk is therefore no longer reproduced in these two
captures. They are at different gameplay moments and have different camera
framing, so this establishes the reported layer order in sampled frames,
not complete visual parity. The donor's missing `testStage.mtl` remains a
source-package gap.

### D-Sides package-local fallback sidecar proof and refresh

The selected D-Sides source has no `DEFAULT_CHARACTER` override, so Codename
uses its default `bf`. The package itself contains a valid `bf.xml` and
its referenced `BF/BF_assets` Animate atlas. The shared planner now requires
one donor package resolved from the installed chart provenance, the same
source fallback decision in donor and both owners, and exact XML, atlas,
converted-asset, generated-script and registry evidence before accepting a
null-to-fallback camera mapping. It rejects changed mappings outside the
unchanged `missingCharacters` list or ambiguous package roots. The focused
repair module passed 24/24 cases during this review.

The final plan
`tmp/codename-base-overlay-refresh-20260928/dsides-local-fallback-plan.json`
contained exactly one generated replacement and no additions or conflicts:
the selected owner's Blammed camera sidecar. Apply took a timestamped backup
at `tmp/import-refresh-backups/20260928T190316751529Z`. Independent audit
`tmp/codename-base-overlay-refresh-20260928/protected-after-dsides-fallback.json`
checked 1,359 prior files: 38 total planned replacements across all three
Codename refreshes, 22 verified additions, 1,321 other files unchanged,
and unchanged repository and personal options. This is a provenance and
asset-equivalence proof for the generic source fallback; a rendered donor
camera comparison is still open.

The final post-guard, post-fallback `python3 tools/run_tests.py --jobs 2`
run passed **1,434 tests across 428 modules**, with 61 skipped and zero
failed (`tmp/full-suite-after-song-end-and-dsides-fallback-20260928.log`).

On that same build and refreshed owner, Blammed Hard, Easy, and Normal each
reached the 128,704 ms natural ending with zero script diagnostics and
unchanged private options. Their due/dispatched event counts were 257/257,
231/231, and 231/231 respectively. Receipt:
`tmp/dsides-blammed-after-local-fallback-20260928.jsonl`. This validates
song completion and event dispatch after the fallback change; source camera
framing and character presentation still need donor comparison.

### Current-build 60/240/480 FPS natural-ending parity

The installed V-Slice Ajena Normal row ran offscreen to the same 21,199 ms
natural ending at configured 60, 240, and 480 FPS. Each run dispatched all
3/3 due events, exited cleanly with zero runtime diagnostics, and kept
installed and private settings unchanged. Measured gameplay medians were
60.0, 237.0, and 267.5 FPS. The parity checker reports no behavioral
problems but marks overall cap attainment **inconclusive** because this host
did not sustain its 480 target. The result is
`tmp/ajena-fps-parity-after-owner-refresh-20260928.json`; the exit code 2
signals that rate-attainment limit, not a chart or event failure.

### Shared post-song beat callback guard

The first refreshed three-song HL17 5× sweep passed Gordonteen Bucks and
Huggyteen Dollars through natural endings with 126/126 and 120/120 due
events. Linkinteen Parks reached its 186,666 ms ending and 5/5 events but
then received a `beatHit` after `codename-audio-complete` began exiting the
state. Its script attempted to switch a now-null character, producing two
`hscript-null-access` diagnostics. This was a song lifecycle error exposed
by accelerated catch-up, not a missing actor during the earlier 1× gameplay
check. The original failing receipt is
`tmp/hl17-after-refresh-20260928/full-three.jsonl`.

`PlayState.stepHit` and `beatHit` now stop script dispatch when `endingSong`
is true. The rebuilt release passed the same Linkinteen Parks Buck 5×
natural-ending replay with 5/5 events, zero diagnostics, and unchanged
private options. The passing receipt is
`tmp/hl17-after-refresh-20260928/linkinteen-post-end-guard.jsonl`. A full
cross-engine regression suite and other ending routes are still required
for this new guard. This rebuilt release binary SHA-256 is
`c8021821e5f5271f4294cfdb9d4cb12e82839d48fbb8d3e8e21fa5c570c3a603`.

The same rebuilt binary also passed the selected-owner D-Sides Try Harder
Hard 5× natural-ending check: 657/657 due events dispatched, no script
diagnostics, and private options unchanged
(`tmp/dsides-try-harder-after-beat-guard-20260928.jsonl`). This checks the
reported failure route on the current build, while visual/audio source
comparison and other difficulties remain separate.

### HL17 Linkinteen donor presentation comparison (open)

The current release binary (`526525eb00528a8738960afebb553e837d2b5045b33daa1d8316123cc763c872`)
completed a private offscreen 1× Linkinteen Parks Buck replay with zero strict
diagnostics and unchanged settings. Frames were captured at song positions
57.073, 95.086, 132.061, 169.019, and 184.068 seconds; receipt:
`tmp/hl17-source-presentation-compare-20260929/linkinteen-current.result.json`.
The read-only donor replay preserved the mounted donor tree (898 files,
463,395,341 bytes), but two bounded menu-route attempts did not enter Chapter
Select. Its menu frames and logs are under
`tmp/hl17-source-presentation-compare-20260929/`. There is therefore no
matched donor gameplay frame or song-time anchor yet, so the large actor's
animation, transition layers, and camera framing are **not verified against
source** by this run. The subsequent pre-fix 20× corpus stress test emitted
two Linkinteen null-access callbacks, so that row failed its strict gate.

The old 20× row's audio-complete marker had `songPosition: 0` before those
callbacks. The shared demo clock had sampled the native channel's transient
end-of-track zero while `playing` was still true, rewinding MusicBeatState
before the completion callback. `updateDemoClock()` now recognizes a near-end
zero wrap regardless of that transient channel flag, while preserving the
initial zero of short songs and pause/backward-seek behavior. The rebuilt
binary (`dfc6bfaa35a6f9fb1f5d64aff5100d6fa28c1ee58c9fc1d01956ee3dc1c70dca`)
passed the same Linkinteen Buck 20× natural-ending row: 5/5 events, zero
script diagnostics, unchanged private options
(`tmp/linkinteen-rebuilt-20x-20260929.jsonl`). Its 1× after-transition actor
motion and donor visual parity remain separate checks. The rebuilt 1×
actor-motion replay then matched seven beat targets 100–124 (song positions
55.560–68.899 seconds) to the same large player actor, `eli1`, at line 1,
occurrence 1, input 1. It stayed visible, existing, and active in every
sample; animation/frame pairs included idle 0, singLEFT 3, singLEFT 2,
singRIGHT 3, and singUP 3. The singLEFT 3→2 change establishes frame
advancement within one animation after the first transition. The run ended
naturally with zero strict diagnostics and unchanged installed/private
options. Receipt: `tmp/hl17-menu-native/linkinteen-animation-1x.result.json`.
This directly checks the reported frozen large actor, while matched donor
frames for overall presentation remain unavailable.

### Rebuilt example corpus sweep, first batch (in progress)

The refreshed current-mount matrix's rows 0–59 produced 34 strict passes,
23 failures, and three source-media blockers on the pre-fix release binary
(`tmp/example-mods-current-build-rows-0-59-20260929.jsonl`). All 60 rows
were accounted for; the three blocked PERFEXION charts have no supplied
instrumentals. The subsequent rebuilt Linkinteen targeted replay is recorded
above and does not retroactively pass the original failed row or the other
packages. The remaining 196 matrix rows still need this build's native gate.

That batch's Psych `Relentless-Bitchass` Normal row aborted during
native note construction after 256 notes (`corrupted double-linked list`, exit
250). A stored 97.4 MB coredump for PID 4186340 shows glibc detecting heap
corruption in `opendir` while `FNFAssets.resolveCaseInsensitivePath` was called
from `NoteKeys.newKey` inside `Note.new`. That stack identifies where corruption
was detected, not where it was caused. The preceding stage callbacks also
depend on undefined `dadOpponent`/`fpSong()` APIs in the mounted Bruce package;
those are separately diagnosed script dependencies, not an explanation for
the allocator crash. Both defects remain open and require a native replay
after a shared fix.

On the next rebuild, three isolated 20× Relentless-Bitchass replays each
reached the 172,800 ms natural ending, dispatched 402/402 events, and left
private options unchanged without another native abort
(`tmp/relentless-rebuilt-replay-{1,2,3}-20260929.jsonl`). They remain strict
failures due to the same three `nullspace.lua` diagnostics. The single stored
heap-corruption core is still unexplained; three successful process exits do
not establish a root cause or long-session stability.

Other first-batch strict failures have source-level causes. PERFEXION
`Xfracture`'s `10scriptnote.lua` uses `anglevar` without assigning it, making
`angleshit` nil before unary negation and multiplication. PERFEXION
`Resonance`'s `Loading Screen.lua` removes `loadingCD` after its fade, then
continues comparing `getProperty('loadingCD.alpha')` with zero in `onUpdate`.
The compatibility interpreter preserves Lua nil arithmetic and comparison
errors; treating missing values as zero would conceal these source defects.
The Bruce package's `nullspace.lua` accesses `dadOpponent` and `fpSong()`,
but its README targets a clean Psych install, the extracted Psych v0.2.8
source lacks both names, and the package contains no fork defining them.
The exact actor and function behavior cannot be inferred
from source, so the affected stage rows remain unsupported until their source
contract is known. Natural-ending markers for these rows are not compatibility
passes.

`Resonance` also schedules repeating `THEGOUSET.lua` trail timers that keep
subtracting alpha after the event stops creating the corresponding sprites;
the resulting missing property yields nil in Lua arithmetic. The first-batch
`Xfracture` row additionally reports selected-source omissions for the
`girl-mad`, `Night-PXT`, `Night-Girl`, and `Crazy-Girl` characters, the
`girl-mad` icon, and the `bedroom` stage. The first-batch
Vs. Whitty Lo-Fight, Low Rise, and Overhead failures currently inspected
share a different source dependency: selected package content has no
`bfwhit` character or health icon, so the runtime reports the missing actor
instead of counting its fallback as visual compatibility. These are grouped
source blockers in the sweep results, not per-chart engine exceptions.

### Current 256-row example sweep and next shared fixes (in progress)

`tmp/example-mods-current-256-sweep-20260928/rows.jsonl` records the
source-provenance-matched 20× offscreen natural-ending sweep as it runs. Its
first 47 rows contain 20 strict passes, 24 failures, and three source media
blockers. This is a baseline against the release binary before the fixes
below; failed rows remain failed until the rebuilt binary is replayed.

The selected Bully owner contains native converted characters but had omitted
the source Codename `data/characters/*.xml` and `images/characters/*` paths.
Runtime actor construction therefore could not find three chart-authored
characters and then could not find the engine default `bf` fallback. The
shared importer now retains each converted character's exact source XML and
mapped atlas under its selected owner, without overwriting existing files.
The importer test checks the owner paths, preserved case, and no global
leakage; the focused 20-test Codename suite passed. A scoped, backed-up owner
refresh and native Bully replay remain pending the sweep's runtime lock.

The baseline Psych rows reveal several distinct cases. Ballistic and
Lo-Fight intro dialogues wait for real keyboard input under default
`alwaysDoCutscenes`; the existing private-Xvfb input driver will replay
their full and skip paths. Ballistic HQ also reads `FlxG.game.ticks` through
Psych's class-property bridge during its story intro; that bridge now walks
the live `FlxG.game` instance for nested reads and writes, pending native
verification. Lo-Fight's `bfwhit` actor and health icon have no definition
or media anywhere in its selected donor package. The Bruce package's
`nullspace.lua` calls `dadOpponent` and `fpSong()`; neither identifier has
an implementation in the supplied package or Psych source, so the source
fork is needed to reproduce them faithfully.

Resonance's loading script reads a sprite after it destroys that sprite;
its timer script also reads trail tags after disabling their creation.
Xfracture uses `anglevar` in a song script without declaring it in that
script or any shared global. The supplied Psych implementation also returns
nil for those cases, so Lua's nil arithmetic has not been weakened to hide
the authored defects. Separate Xfracture character/stage dependencies remain
unresolved. A focused Lua interpreter test now confirms that a parenthesized
`getSongPosition() / crochet` expression reads seeded and refreshed timing
globals. Ballistic HQ's default-settings run enters its authored story
intro (`inCutscene` is true and the script advances `stops`), so its early
division uses `FlxG.game.ticks`. A post-build input-driven replay must
confirm the class-property bridge fix and subsequent dialogue progression.

### Character-resolution diagnostics in the 256-row baseline

Seventeen rows in the baseline carry `[character-resolution]`: fifteen
vswhitty difficulties reference `bfwhit` (Lo-Fight, Lo-Fight HQ, Low-Rise,
Overhead, and Overhead HQ, each Easy/Normal/Hard); Underground Easy references
`bf-santa`; and Xfracture Hard references `girl-mad` plus the script-swapped
`Night-PXT`, `Night-Girl`, and `Crazy-Girl`. These are source dependency
blockers, not a character resolver or stale-import defect. The mounted
vswhitty donor and Psych archive contain no `bfwhit` or `bf-santa` definition,
atlas, or matching icon. PERFEXION supplies JSON definitions for `girl-mad`,
`Night-PXT`, and `Night-Girl`, but their named character atlases are absent;
the `girl` icon is also absent. It supplies no `Crazy-Girl` definition. The
three available JSONs are already preserved under the selected PERFEXION
owner, while the shared Psych importer correctly does not create playable
registry entries without source atlases. A refresh cannot supply these absent
bytes, so the fallback and missing-dependency diagnostics remain explicit.
Evidence: the [baseline rows](../../tmp/example-mods-current-256-sweep-20260928/rows.jsonl),
[vswhitty exact-name audit](../../tmp/vswhitty-character-source-dependencies.json),
and [PERFEXION Xfracture dependency audit](../../tmp/perfexion-xfracture-dependencies.md).

### Codename 480 FPS performance investigation — 29 September 2026

The selected-owner Try Harder Hard chart reproduces substantial lag in a
private, default-settings offscreen run with only `fpsCap` changed to 480.
After warm-up, the existing release binary reported 18–20 FPS per one-second
gameplay sample (19 FPS median), with about 47–53 ms between updates. The
65-second safety watchdog stopped the bounded sample, so this receipt is a
performance baseline rather than a natural-end pass. The installed options
file and the private options copy were byte-identical before and after.
Evidence: `tmp/codename-performance/try-harder-480-pre-instrumentation-20260929T024928Z.json`
and its `.markers.jsonl`/`.process.log` companions.

Xvfb used Mesa llvmpipe (`Accelerated: no`), so its absolute FPS does not
measure the desktop GPU. Source-only smoke instrumentation now separates
update and draw percentiles, the PlayState script/native update phases, and
Codename character draw hooks; it is pending a coordinated build and replay.
No performance behavior has been changed or claimed fixed on this evidence.

A second bounded run used gamescope's headless backend and verified the child
GLX renderer as the accelerated AMD Radeon RX 7900 XT. It reproduced the
reported desktop symptom: 37 FPS median after the cold first sample, with
33–39 FPS warm one-second windows at the same 480 cap. CPU use was about one
core (101% median); the adapter-wide GPU busy counter was 39% median and 45%
maximum. That counter includes other desktop work and cannot attribute GPU
time to the game, but does not indicate a saturated card. The run completed its requested 35-second song
window and emitted a success marker. The installed and private settings hashes
were unchanged. Evidence:
`tmp/codename-performance/try-harder-480-pre-instrumentation-headless-gl-20260929T025731Z.json`
and its `.markers.jsonl`/`.process.log` companions.

The first instrumented hardware-GL replay attributed 25.46 ms per frame to
`PlayState`'s Codename update call, with a 37 FPS warm median; drawing took
under 1 ms at the reported percentile. A narrower second replay attributed
27.20 ms per frame to the imported `songs/rgbNotes.hx` update callback, while
each other callback, binding refresh and actor commit was below 0.1 ms per
frame. This bounded sample timed out before the requested 35-second song
window completed, but produced six stable gameplay windows and no script
error marker; it is profiling evidence, not a playthrough pass. The script
iterates each strumline's live note collection. The shared
`CodenameLineNoteQuery.collectIndexed` currently searches the growing result
with `indexOf` for every chart note and sorts the full result on each lookup,
making the collection a candidate for a source-preserving algorithmic fix.
Evidence: `tmp/codename-performance/try-harder-480-post-instrumentation-headless-gl-20260929T030219Z.json`
and `tmp/codename-performance/try-harder-480-post-instrumentation-headless-gl-20260929T032128Z.json`.

The shared Codename note view now indexes chart-note identities once,
preserves their authored line order, and merges only dynamically added active
notes into each query. Its `forEachAlive` follows Codename's visible-note
window (`songPosition + limit`, default 1,500 ms) while leaving full `members`
available to scripts. A 1,264-note Haxe interpreter benchmark measured the
indexed query at 275.7 ms for 100 rounds versus 406.0 ms before this change
(1.47×); the visible-window callback rule is the larger native gain. On the
same private headless RX 7900 XT setup and 480 cap, Try Harder Hard's warm FPS
median rose from 37 to 468. Codename update time fell from roughly 25–27 ms
per frame to 0.345 ms, including 0.217 ms in `rgbNotes.hx`. The new run
completed its bounded window, exited 0, and kept repository, installed, and
private options unchanged. This establishes the performance regression fix
for this case; source visual parity and other Codename charts still require
their own checks. Evidence:
`tmp/codename-performance/try-harder-480-post-instrumentation-headless-gl-20260929T035000Z.json`
and its `.markers.jsonl`/`.process.log` companions.

### D-Sides imported owner menu route — 29 September 2026

The private Xvfb/dummy-audio menu harness selected the one D-Sides owner
entry and observed exact-owner create-ready traces for authored TitleState,
MainMenuState, and FreeplayState. The earlier unsupported `Chart` and
`HighscoreChange as HC` imports no longer appear after the shared binding and
alias-parser build. The Freeplay `create` callback then emitted
`[codename-asset] Missing scoped asset: .../images/menus/freeplay/icons/gf.xml`.
The route receipt is therefore **failed**, despite the state create-ready
trace. Donor/package dependency and importer resolution are under review;
no same-named asset from another owner was substituted. Installed files and
personal options were unchanged. Evidence:
`tmp/dsides-owner-native-menu-route-20260929-v2/receipt.json` and
`tmp/dsides-owner-native-menu-route-20260929-v2/route.process.log`.

### Psych class-property intro probe — 29 September 2026

A second private Ballistic HQ Easy intro run sent no input and used the
repository's default settings. The shared `getPropertyFromClass` bridge
resolved `flixel.FlxG`, normalized `game.ticks`, and returned an integer
(`2345`) from the live `FlxGame`. The process exited 0 after the bounded
15-second sample; its logs contained no Lua nil-arithmetic or HScript error.
This verifies the previously failing class-property expression in the
unskipped intro branch. It does not establish full dialogue progression or
natural ending. Installed and private options remained byte-identical.
Evidence: `tmp/psych-class-property-probe/ballistic-hq-easy-no-return-result.json`
and `tmp/runtime-smoke/logs/ballistic-hq-psych-class-probe-no-return.process.log`.

### Dynamic Codename atlas import and sound-cache lifecycle — 29 September 2026

The D-Sides Freeplay script composes an atlas key from a constant directory
and each song's runtime icon ID. The mounted selected donor contains 31
complete direct PNG/XML pairs under that directory, while the earlier
installed owner lacked the directory. Shared Codename runtime asset planning
now resolves statically known dynamic atlas directory prefixes, stages direct
paired assets under the selected owner (or its validated installation asset
overlay), and diagnoses unsafe or unresolved expressions. Its focused Haxe
fixture enumerates more than 128 files without a silent scan cap. The focused
atlas and HScript sound-lifecycle suites passed 3/3; the wider focused
Codename/psych set passed 12/12. `./run.sh build` completed cleanly with
release binary SHA-256 `bd86da05ff6106894bd6f4a03dc2fa1e5d1599dd964551491415040287023f15`.

The refresh plan at `tmp/dsides-dynamic-atlas-refresh-plan.json` recorded
source hashes. A backup of all 14 pre-existing Freeplay owner files and four
protected metadata/settings hashes was written under
`tmp/import-refresh-backups/20260929T040821Z-dsides-dynamic-atlas/` before
applying anything. The missing-only transaction copied 62 files (67,768
bytes), verified their source hashes, preserved all pre-existing owner files
and protected inputs, and wrote `receipt.json` beside the backup. The
installed personal options hash remained
`b2a492df3b48f37400ce824d0a120341be70189431886a5799cb53a6b7f1110a`.
The desktop Funkin process initially held the repository runtime lock, so
the refreshed route ran after that lock was released.

The subsequent private Xvfb/dummy-audio route passed on the refreshed owner.
It observed exact-owner create-ready traces for TitleState, MainMenuState,
and FreeplayState, found no Codename script diagnostics, and verified the
selected cassette title bar changed on Down (Tutorial to Bopeebo, ink-column
similarity 0.2914) then returned on Up (0.8517 similarity to the initial
Tutorial label). The screenshots visibly show both authored cassette labels;
the earlier OCR-only run had falsely failed on the pixel font, so the final
gate uses the selected cassette's isolated title-bar pixels. Installed
inputs and private settings were unchanged. Evidence:
`tmp/dsides-owner-native-menu-route-20260929-v4/receipt.json` and its
`dsides-freeplay-tutorial.png`, `dsides-freeplay-bopeebo.png`, and
`dsides-freeplay-tutorial-restored.png` captures. This verifies menu access,
not D-Sides gameplay/source parity; the verified shared correction and paired
offscreen evidence are recorded in the [FunkinModchart draw ownership
section](#funkinmodchart-draw-ownership-29-september-2026) below.

### Carol Roll allocator-crash follow-up — 29 September 2026

One earlier 256-row sweep crashed during Carol Roll Sayori Mix Normal's HUD
creation with `malloc(): unsorted double linked list corrupted`. The retained
sweep logs for several other process exits were overwritten by later runs,
so they do not establish repeatable crashes. A fresh single-row private
Xvfb/GDB replay of Carol Roll on release binary `bd86da05…` used the default
private options, 20× song rate, `MALLOC_CHECK_=3`, and
`MALLOC_PERTURB_=165`. It reached PlayState, dispatched all 22 due events,
emitted `song_end` and `success`, and exited 0 without SIGABRT or allocator
diagnostics. Its strict row still fails on DDTO++'s donor-missing
`dokicon.png` window-icon request. The allocator fault remains an
intermittent stability risk, not a verified shared source defect from this
single passing repro. Repository and installed settings hashes were
unchanged. Evidence: `tmp/carol-roll-repro-20260929/result.json` and
`process.log` in the same directory.

`PlayState.destroy()` now releases cached HScript `FlxSound`s and clears the
four per-path script audio maps after script callbacks finish. The focused
lifecycle test covers live/dead entries and leaves unrelated group sounds
untouched. This is a cross-song ownership fix; the active Try Harder bitmap
set remained steady at 58–59 entries (~1,000 MB) in the earlier 480 FPS
sample, so no single-song RSS reduction is claimed without a switching
measurement.

## FunkinModchart draw ownership — 29 September 2026

The shared `PlayState.draw()` hook now prepares one live arrow snapshot before
the native Flixel group pass. When the current state's visible, attached
FunkinModchart `Manager` owns note rendering, the adapter bypass-hides the
native note/receptor sprites before that pass. `CtxRenderer` continues to read
the preserved `_fmVisible` source flags and draws the transformed items from
the same snapshot. The snapshot is reused, avoiding a second arrow collection
per draw. When the manager is hidden, detached, destroyed, or associated with
another state, visibility is restored from `_fmVisible`. The parent-draw gate
also restores sprites when a pause substate prevents `FlxState` from drawing
its members. This is shared engine behavior; it contains no song or package
checks.

The release build passed before the private visual replays. Baseline binary
SHA-256 was `bd86da05ff6106894bd6f4a03dc2fa1e5d1599dd964551491415040287023f15`;
the rebuilt binary was `dcfd3426346e23b0ac2ff050c55328945781a02342c6f4d3a68df792b56dfa30`.
Both old and new binaries completed owner-active D-Sides Endless Hard replays
under private Xvfb with dummy audio, each reporting success, 33 gameplay
frame-stat windows, and no failure markers. The runner selected the owner from
the chart's `compatScripts.json` and passed it through `--smoke-owner-root`, so
the owner's global script enabled the authored modchart. The paired captures
were taken at 28,080 ms on the old binary and 27,959 ms on the rebuilt binary:

- Old: `tmp/endless-double-notes-baseline/before-28s.png`.
- Rebuilt: `tmp/endless-double-notes-baseline/after-28s.png`.

At this beat window, the old image retains the four affected receptors in
their static top row. The rebuilt image shows the authored reverse/Y movement
relocating lanes while transformed falling notes and receptors remain visible;
the duplicate static receptor pass is absent. Nearby one-second frame windows
reported draw P95 of 1 ms on both builds. Total-cost P95 was 3 ms on the old
run and 2–3 ms on the rebuilt run. The rebuilt pre-draw scan measured a median
of about 31 microseconds per update across its 33 windows, with a maximum of
about 71 microseconds. These counters are millisecond-quantized and the replay
timings are bounded observations, not a benchmark claim.

`python3 -m unittest tools.tests.test_codename_modchart_draw_ownership -v`
passed 2/2 focused tests, including update-reset visibility, transformed
renderer visibility, manager-hidden restoration, and the pause parent-draw
gate. The native replay confirmed notes and receptors remained visible during
the modchart. It did not include interactive pause/resume verification and
does not certify full Codename source parity. Both runs used private runtime
overlays, isolated XDG storage, default test settings, and dummy audio; no
personal settings were changed. Temporary overlays were removed after each
run. Detailed logs and frame counters are in
`tmp/endless-double-notes-baseline/{before,after}.{markers.jsonl,result.json}`.

The clean `python3 tools/run_tests.py` rerun after narrowing the standalone
demo-control extraction passed 1,498 tests across 444 modules in 238.4 seconds:
61 skipped, zero failed. The test-only fixture had previously included the
new FlxState `draw()` override while extracting unrelated demo-speed methods;
its isolated rerun and the final full suite both passed. Evidence:
`tmp/full-tests-20260929-endless-clean.log`.

### Current strict tail sweep and shared HXC filter choice (2026-09-29)

The offscreen default-settings tail sweep is still running across matrix rows
157–255. Results are appended under
`tmp/example-mods-example-mods-tail-157-255-20260929/rows.jsonl`, with a
separate process log and marker record for each row. Through row 180, eleven
DDTO++ rows fail solely on the donor's absent `assets/dokicon.png`. Row 163
also exposed an unsupported HXC preference-controlled shader filter callback;
row 170 aborted during HScript character atlas creation with native allocator
heap-corruption detection. Both remain unverified as compatible. The row 170
core and `coredumpctl` stack are preserved in the sweep's `logs/` directory;
the stack locates allocator detection during a generic `combineSparrow` atlas
load but does not prove where the earlier heap write occurred.
Rows 179–180 reached `playstate_ready` only after roughly 41–46 seconds,
including 16–20 seconds of measured bitmap decoding. Their fixed 45-second
smoke windows then expired without a natural ending. These two results are
test-window failures; their full playthrough and source parity remain unknown.
The follow-up runner must start its duration window after readiness.
Row 192 showed the same harness flaw: ready at 36.1 seconds, timeout at
43.3 seconds, no native script diagnostic or song ending.
The existing `FNFAssets.getBitmapData` timer encloses synchronous
`BitmapData.fromFile`, so its 16.59/20.08 seconds include both storage reads
and PNG decoding; the current aggregate markers cannot separate them. These
two cold starts reported 37 bitmap misses and 12 hits. Several distinct
initial character atlases decode to roughly 64–128 MiB each, and a swap
preload references a roughly 256 MiB atlas. No cache or asynchronous loading
change is justified from these counters alone; a per-key read/decode profile
is needed after the lock is free.

The shared HXC analyzer now recognizes an exact boolean switch over two
declared shader filter lists only when the preference is read from the
root-scoped save view, each filter belongs to an owned shader descriptor for
the target camera, and no other filter assignment remains. It lowers the two
authored array orders through the native filter resolver. Dynamic filter
expressions and unowned preference sources remain rejected. The mounted
228-file corpus check and four focused shader callback tests pass, including
the newly accepted countdown body. This change has not been built or replayed
natively yet because the tail sweep holds the runtime build lock. The earlier
snapshot of seven unsupported shader callbacks above describes an older
build, not the current source tree.

Separately, `Conductor.songPosition` now begins at numeric zero so early
source callbacks cannot read null before the countdown sets the clock. Its
focused extracted-Haxe test passes. Smoke-only phase markers were added for
the previously observed second-load stall and Psych skin note setup; these
provide a narrower failure location on the next locked native probe without
per-note log spam in ordinary runs. Neither change has a post-build native
receipt yet.

Read-only source comparison of first-sweep script failures found a donor
contract problem in Resonance: its Lua timer removes `loadingCD`, but a later
update continues comparing that tag's missing `alpha` to a number. The Psych
bridge returns null for missing tags, as a Lua property read would; replacing
that value with zero would hide the authored error. Bruce's `nullspace.lua`
references `dadOpponent` and `fpSong()`, neither of which occurs in the
bundled Psych v0.2.8 source. Their intended fork behavior is not available
from this donor. These remain diagnosed dependencies/source defects; no
song-specific alias or no-op was added. The bundled Psych source's
`FunkinLua.call` reports `Lua.pcall` errors and continues registering the
callback, so repeated update errors match that error lifecycle.
Evidence: exported `assets/data/resonance/Loading Screen.lua:34-40,44-59`;
the bundled Psych archive's `source/psychlua/FunkinLua.hx:1608-1634`
and `:1102-1116`, plus `ReflectionFunctions.hx:19-23`; Bruce's
`mods/stages/nullspace.lua:4-7` and README's clean-Psych install instruction.

The reported Psych Ugh dual-note ownership was rechecked against the supplied
Psych archive. Its `PlayState` uses lane modulo four for column and `lane < 4`
for player ownership; `mustHitSection` is not an ownership inversion. Ugh's
imported lane/time/section rows match the donor, and the shared runtime
passes the lane-derived ownership into heads, sustains and lifts before
routing player input and strumlines. Existing ownership tests pass for all
three Ugh difficulties and 76 imported Psych charts. The selected-owner
native `chart_note_sides` receipt matches the source head counts for Easy
141/155, Hard 256/270, and Normal 227/241, all with retained
`psych_v1_convert` format (`tmp/psych-ugh-all-difficulties-note-sides.jsonl`).
All 76 installed Psych ZIP charts also preserve every authored source `song`
field and ordered note array
(`tmp/psych-archive-source-field-parity-20260929.json`). These checks address
the reported dual-note ownership in chart generation; a fresh rendered-lane
and player-input comparison remains open.

The earlier tail-run plan called for another HXC filter callback replay,
repeated atlas-abort investigation, slow-start readiness checks, Ugh chart
identity, cross-song stall profiling, and Psych skin phase markers. The
current receipts above supersede its Ugh identity/count item; other items
require their own reported results and are not counted as passes here.

The earlier `Invalid field:null` note-generation receipt identifies a valid
Psych head note (lane 3, no sustain, empty `arrowSkin`) at the outer
`head-psych-skin` phase. It does not locate the dereference within
`PsychSkinRuntime.reloadNote` or the following RGB palette/bind work; later
loads of the same chart family passed. The new subphase marker must first
reproduce the failure before a cause or fix can be claimed.

### 2026-09-29 accelerated completion and result-screen checks

The crash/completion gate uses the existing demo song-rate path with practice
and botplay, up to 50×. Linkinteen Parks has 186.667 seconds of authored audio;
at 50× its observed `song_start` to `song_end` interval was 3.74 seconds and
startup to settled smoke success was 12.7 seconds without the optional global
results pack (`tmp/linkinteen-50x-crash-gate-20260929.jsonl`). This gate checks
natural ending and event dispatch, not timing-sensitive visual parity: camera
effects and timers can accumulate differently when gameplay is accelerated.
Those checks still require 1× offscreen playback and screenshots.

With the imported Psych global results pack enabled, the same 50× case first
reached its natural end but logged two Linkinteen null actor accesses after
`song_end`; Return opened native pause rather than dismissing the provider.
A private 20× A/B overlay without the provider passed strict diagnostics. The
shared cause was the engine releasing `endingSong` and leaving `canPause` true
when Psych `onEndSong` returned `Function_Stop`. The supplied Psych source
keeps `endingSong=true` and `canPause=false` while a script owns the ending.
The shared lifecycle now does the same. A rebuilt strict 50× run created the
provider screen, accepted Return, reached Freeplay, and passed the native
ending-handoff gate with zero diagnostics, no post-end actor accesses, and
unchanged options (`tmp/runtime-smoke/logs/lifecycle-provider-linkinteen-enter-50x.process.log`).
The rebuilt `--dismiss-ending` driver then passed the same 50× case with an
explicit `end_handoff {state: FreeplayState}` marker after `song_end`, five of
five events dispatched, and no interpreter errors
(`tmp/linkinteen-end-handoff-driver-20260929.jsonl`). This validates the Linkinteen accelerated ending
path; the results screen's visual and audio parity and other chart endings
still require source comparison at 1×. The crash-only gate continues to check
song completion alone.

The same generic 50× ending driver passed all three installed Psych archive
Ugh difficulties. Each delivered all 11 due events, created a single
`end_handoff` to Freeplay after Return, logged zero native diagnostics, and
left options unchanged (`tmp/psych-ugh-all-difficulties-end-handoff-20260929.jsonl`).
This is ending/lifecycle coverage; the previously reported dual-note input
ownership still needs its separate rendered and input check.

The installed editor matrix's first 120 rows now has 114 passing round trips,
five skips for absent source media, and one unresolved native heap abort on
Psych archive Senpai Normal. Replays of prior Eggnog and South failures passed
after deferring Quick Save reload until `ChartingState.update`. Senpai Normal
still aborts in a plain serial second editor create, after the note panel and
before the character panel; a gdb-wrapped replay passed, so the fault is
timing/layout sensitive. Valgrind stopped in the loader with an unsupported
instruction before entering the game and provides no evidence about that heap
fault. Every editor replay kept its source chart, sidecar, and user options
unchanged (`tmp/example-editor-matrix-20260929.json` and row 0114 logs).

The full Python suite ran 1,561 tests across 460 modules: 66 skipped and eight
modules failed to compile their isolated fixtures after shared type/API additions
(`tmp/full-tests-after-global-results-20260929.log`). Their fixture corrections
now pass in a focused rerun of all eight modules (40 tests); a full rerun is
pending, so this is not yet a passing automated gate. A subsequent 1,563-test
full run narrowed the failures to two additional source-shape fixture checks
for the new ending lifecycle and native handoff watcher; both affected modules
pass focused reruns after their fixtures were updated
(`tmp/full-tests-after-fixture-fix-20260929.log`). The third full run passed:
1,565 tests across 461 modules, 66 skips and zero failures
(`tmp/full-tests-third-pass-20260929.log`). A later small offscreen driver
extension for combined intro and ending input passed its focused 21-test suite;
the full suite preceded those Python-only edits.

### Accelerated Psych ending callbacks and Ballistic handoff (2026-09-29)

The 50× full-song harness now distinguishes natural audio completion from a
completed ending handoff. Its combined intro and ending input driver exposed a
shared Psych lifecycle gap: an imported `onEndSong` returning `Function_Stop`
kept `endingSong` true, and `PlayState.update` returned before `onUpdatePost`.
Psych scripts can use that post-update callback to receive Accept and call
`endSong()` a second time. The supplied Psych source likewise dispatches
`onUpdatePost` while an ending is held. The compatibility branch now dispatches
script post-update callbacks during the hold while leaving gameplay processing
gated. No donor script, chart, package name, or timing constant was changed.

The initial Ballistic Hard replay reached natural audio end and dispatched all
16 due events, but timed out in PlayState after the private-window Enter input
(`tmp/ballistic-hard-diagnostic-20260929.jsonl`). A smoke-only probe confirmed
the selected script returned `Function_Stop`. After the shared callback fix,
the same replay observed `accept=true`, the script's second end callback
continued, and `end_handoff` reached Freeplay without interpreter diagnostics
(`tmp/ballistic-hard-end-callback-fix-20260929.jsonl`). The complete 50×
Ballistic Easy, Hard, and Normal replay passed with 16/16 event dispatches,
zero native diagnostics, Freeplay handoff, and unchanged personal options in
every case (`tmp/ballistic-all-difficulties-end-callback-20260929.jsonl`).
Linkinteen Parks Buck was repeated after the fix: its configured Psych global
results screen accepted Enter and reached Freeplay with zero diagnostics and
unchanged options (`tmp/linkinteen-postupdate-results-regression-20260929.jsonl`).
These accelerated runs establish completion and callback control flow; they do
not establish source-matching visuals, animation, note ownership, or audio at
normal speed. The editor Senpai heap abort and the Mario stage-source gap
described above remain open. The focused ending/input suite passed 24 tests;
the full automated suite passed 1,568 tests across 461 modules, with 66 skips
and zero failures (`tmp/full-tests-after-ending-callback-fixture-20260929.log`).
Its first run had one stale test assertion that assumed a single
`onUpdatePost` call site; the fixture now checks both the held ending and
normal gameplay paths (`tmp/full-tests-after-ending-callback-20260929.log`).

### Fast completion sweep and source declaration audit (2026-09-29)

The offscreen 50× completion-only gate ran matrix rows 120–179 with default
test settings (`tmp/example-rows-120-179-fast-completion-20260929.jsonl`). It
recorded 60 results: 37 clean passes, 22 strict failures, and one blocked row.
Every one of the 59 runnable rows reached natural audio end, dispatched every
due event, and left personal options unchanged. All 22 failures share one
explicit `missing-donor-dependency` finding: DDTO++'s unchanged
`scripts/modules/CustomTitleBar.hxc` requests `dokicon.png`, but that file is
absent from the supplied Example Mods tree and installed owner/engine assets.
The selected-owner resolver correctly refuses to borrow a similarly named
file from another package. The blocked row is the undeclared, empty `normal`
key in the Baka Alt raw chart; base Baka Normal and Baka Alt are installed as
separate playable entries. The gate's nonzero exit is intentional while these
findings remain. Accelerated completion does not verify visual, audio, input,
editor, or normal-speed timing parity.

A refreshed source-declaration inventory
(`tmp/example_mods_chart_matrix_runtime_declared_20260929.json`) separates
242 declared chart/difficulty rows, of which 237 have structural import coverage, from 14 raw
V-Slice keys that their sibling metadata does not declare for selection. Six
are empty; eight contain notes, so their source data remains in separate
diagnostics. The source metadata for Crucify Yuri Mix, Dokidoggle, Titular MC
Mix, and You and Me declares only `normal`; the converter's metadata-first
selection rule does not import their other raw note-map keys as selectable
difficulties. Five inventoried rows remain structurally unavailable because
their donor packages lack required instrumental audio (PERFEXION Extra,
Extras, Gallery; Psych archive Ridge and Smash). Gallery also has zero source
notes and no stage implementation. The refreshed catalog copy records the
current extracted Psych source and FNAS source paths without changing the
baseline inventory or any imported files.

The supplied Nightmare Vision installation has 60 song folders and 194 direct
JSON files with chart-shaped envelopes across its two content packs. A
subsequent isolated writer selected 180 chart files; 14 of the other files
are named `events.json` and require source-sidecar classification before
they can be counted as playable difficulties. Its original engine recognizes
`psych_v1_convert` as a legacy Psych-format member and then applies the
legacy lane conversion; this family was missing from the compatibility
adapter. Four charts declare three playfields. In the donor, field 2 is an
independently rendered, automatic BF-controlled strumline; 47 authored notes
use it in each of the three populated charts. The current engine represents
native note ownership with a player/opponent boolean, so those charts remain
explicitly unsupported pending shared N-field note, receptor, input, scoring,
callback, and cleanup support. This is a source behavior gap, not a reason to
reassign those notes to one of the existing lines. Two source song folders
lack vocals; all 60 have a recognized instrumental. Importer changes and
native verification for this package are tracked separately from this source
inventory.

### Isolated Nightmare Vision native import and accelerated completion (2026-09-29)

The shared importer now recognizes Nightmare Vision's two installed content
packs, normalizes its `psych_v1_convert` legacy member, and records source
menu difficulties separately from raw chart keys. Its native import was run
offscreen against a fully private runtime copy under the build lock. The
import found and installed all 60 song folders (28 new and 32 old), with zero
failed imports and zero final missing dependencies
(`tmp/nmv-native-import-report-20260929/import-preparation.json`). The isolated
writer compared 180 chart payloads and all donor chart bytes without a
semantic mismatch (`tmp/nmv-mounted-import-audit-passing-20260929.log`). The
three unsupported new-pack Monster difficulties and Tutorial's `gf` key stay
explicitly marked unsupported until the native game supports a third field;
they are not presented as playable.

The private runtime's old-pack Fresh Normal reached its natural 100,800 ms
audio end at 50× speed, dispatched all 4 due events, and exited with zero
strict diagnostics and unchanged default options
(`tmp/nmv-private-fresh-native-20260929.json`). This is a completion check,
not evidence of normal-speed visual, input, audio or source-script parity.
The live export's protected options, Freeplay registry, base-song keys,
Monster Hard and Tutorial charts, and difficulty registry retained their
pre-import SHA-256 values. A checksum comparison of the 7.7 GB live export
against the private copy found only the expected private Freeplay registry and
import-report changes (`tmp/nmv-private-preexisting-diff-20260929.txt`).
The final automated rerun passed 1,585 tests across 464 modules, with 66
skipped and zero failures
(`tmp/full-tests-after-nmv-fixture-fix-20260929.log`). The preceding full run
found four standalone Haxe extraction fixtures that lacked the new shared
source signatures; those fixtures were updated and passed focused reruns
before the final full run. `./run.sh build` reported the release build up to
date, and `git diff --check` found no whitespace errors.

### Accelerated declared-row sweep 180–241 (2026-09-29)

The refreshed 242-row source-declared matrix preflight found all 62 rows in
this range runnable. The offscreen 50× completion pass first used isolated
per-song overlays for rows 180–182, then a physically separate private runtime
for rows 183–241 to avoid repeating large overlay setup. The private files
checked had distinct inodes from the live export, and each launch reset only
its private default options and save scope. Receipts are
`tmp/example-rows-180-241-fast-completion-20260929.jsonl` and
`tmp/example-rows-183-241-fast-direct-20260929.jsonl`.

All 62 rows reached natural audio completion, dispatched every due event, and
left personal settings unchanged. The strict gate recorded 51 passes and 11
failures: eight reached the already identified missing DDTO++ `dokicon.png`
window-icon request; `you-and-me` reached song end but then spent 245 seconds
in the Freeplay return path and timed out; Cursed Expurgation Hard emitted
HScript errors from its byte-identical donor stage/modchart (including
commented-out functions still called by `stepHit` and a sprite used before
creation); and Try Harder Hard reached song end with 657/657 due events before
glibc aborted with `corrupted double-linked list` as the shared Psych results
provider created its first sprite. The following replays narrow those initial
failures. The 50× gate still says nothing about visual, audio,
input, editor, or normal-speed frame parity.

The `you-and-me` timeout was traced to the smoke harness: Freeplay completed
creation and continued updating, but completion-only mode had installed its
state-independent post-song observer only for strict handoff runs. After the
generic observer fix, an offscreen completion-only replay emitted exactly one
`song_end` and one `success` five seconds later with no `end_handoff` marker
(`tmp/you-and-me-post-watch-20260929.json`); a strict-handoff replay emitted
exactly one of each (`tmp/you-and-me-strict-handoff-20260929.json`). This
corrects the false timeout classification; the earlier high CPU observation
is not a measured Freeplay performance regression.

Try Harder's allocator abort did not reproduce in a 5× replay or three
instrumented 50× replays. The latter traced successful constructor,
`makeGraphic`, property and camera writes, insertion, and results callback
completion (`tmp/try-harder-5x-native-20260929.json`,
`tmp/try-harder-50x-sprite-diagnostic-20260929.json`,
`tmp/try-harder-50x-repeat-pair-20260929.json`). The original native abort
remains a real intermittent stress finding without a grounded shared behavior
fix. Bounded smoke-only sprite markers were retained to localize recurrence.

The final parallel automated rerun after the smoke-marker fixture repairs
counted 1,588 tests across 465 modules, 66 skipped, and one failed module
(`tmp/full-tests-after-sprite-fixture-fix-20260929.log`). The failure is the
mounted native auto-import scanner: its `--counts-only` subprocess returned
SIGSEGV (`-11`, surfaced as exit 245) during Psych chart-reference extraction.
The retained core (PID 365965) maps the fault to `values[1]` in
`PsychScriptDiscovery.collectChartReferences`, after its row passed the array
type check. The array base was unaligned and `0x01`-poisoned. The core lacks
the chart path and enough locals to establish whether prior memory corruption
or hxcpp GC lifetime caused the stale pointer, so no source guard or retry was
added. A subsequent isolated ordinary scan and a GC-debug scan each passed
all 24 roots, reporting 265 candidate records, 241 selected and 119 missing
dependencies; those successes do not clear the intermittent native fault.
The automated gate remains failed and full compatibility is not verified.
The instrumented release binary built successfully through `./run.sh build`
(`tmp/post-smoke-watch-build-20260929.log`), and the live options, Freeplay
registry, base-song keys, representative base charts and difficulty registry
retained their pre-run SHA-256 values. The disposable private runtime copy was
removed after the replays; receipt logs and the original system core remain.


## 30 September — Default results identity and Codename note/animation follow-up

`ResultsCharacterCompat` makes the configured fallback results provider read a
validated presentation family, defaulting to BF for unknown requested identities.
Focused resolver/Lua tests passed (3 tests). The native provider's actual
`onCreate` ran on Satin Panties Nightmare: requested `bf-car` selected BF.
Synthetic identity changes in the same private run selected BF for unknown and
misleading substring names, and Pico for `pico`/`pico-speaker`, without script
errors. Receipt: `tmp/results-character-native-20260930/receipt.json`; binary
`602c0dbe210d08c551463caee1a246915e12ad58840d6111e92dc0baf1e0903d`.
This tests character selection, not the ending animation presentation. The
private instrumented companion was restored byte-for-byte.

The current Codename note-type implementation now stages source note scripts,
selected-difficulty type tables, and their assets. Native Try Harder testing
observed all 68 ice heads using the custom atlas and source type index. Its
synthetic hit/input probe exposed a case-sensitive nested asset lookup failure
for the ice effect. That run is failed, not a compatibility pass.

A full native refresh crashed during event-row array checking before any
protected file changed. Core PID 559200 contains an invalid Haxe object vtable
`0x0101010101010101` in `hx::ArrayCanCast`, called from
`ModuleFunctions.codenameAuthoredEventNames`. The corruption remains unexplained.
Production Haxe interpreter helpers produced a separately labelled structural
preview for 20 songs/22 charts. A missing-only private refresh added 27 unique
files and verified all 1,087 backed-up existing files unchanged. This is not a
native importer pass. Receipts are in `tmp/codename-note-types-import-20260930/`.

The integration run counted 1,628 tests across 480 modules, 65 skipped, with four
failing modules caused by fixture dependencies/types omitted after the new
metadata helpers. Focused fixture repairs are being checked; the aggregate gate
is not yet a passing final gate.

The four integration failures above were repaired as fixture drift: camera-plan
extraction (2 tests), mounted audit (6), ModPlus E2E (1), and the focused HXC
mounted count check (1) passed. These are source/interpreter checks; no native
scanner crash was cleared by them.

Normal-speed offscreen playback on binary `602c0dbe...e0903d` now visibly plays
the authored grab animation: frames 3 and 31 at 88.0/89.2 seconds. It also
reproduced the first-person defect at 91.5 seconds: the active POV player actor
is on camGame while the corner effect is on camHUD, despite the donor timer
assigning `boyfriend.camera = camHUD`. The script alias still referenced the
hidden pre-swap actor. The shared alias binding now follows the current first
actor in source lines 0/1/2, matching Codename's dad/boyfriend/gf getters. Nine
focused alias/lifecycle tests passed; native after-change verification pending.
Screenshots and receipt: `tmp/codename-grab-native-20260930-before-alias/`.

The subsequent native setup crash (PID 578236, build `d36b2a6d...173df256`)
was localized to a null atlas passed to FlxSprite.setFrames. Unlike the scanner
fault, its receiver is valid and this is a null dependency, not evidence of heap
corruption. Adding a shared atlas-construction diagnostic exposed the exact
mechanism: case-aware lookup found an Animate directory with the same basename
as a Sparrow raster, and explicit Sparrow loading passed that frame collection
as a bitmap. `Paths.image` now supports `checkForAtlas`; explicit Sparrow and
Packer requests select raster input. The focused collision fixture passes.
The diagnostic build's danger-note probe passed all 68 atlas/type IDs and
freeze/stun, cancelled hit scoring, damage, sustain-clip cancellation, miss
cancellation and alternating-input release checks, but its stage callback failed
on the atlas collision. That run remains failed overall.

The next full suite counted 1,631 tests across 481 modules, 65 skipped, with two
failures: a native-event extraction fixture missing its new helper, and a path
fixture run before the in-progress directory-as-file fix. Both were repaired and
the combined final focused check passed eight tests. A frozen-source aggregate
rerun and native stage verification are in progress.

The frozen-source aggregate completed: **1,631 tests across 481 modules,
65 skipped, zero failures** (`tmp/full-tests-note-atlas-results-final-20260930.log`).
On binary `724328f4c571ba87cdee323594e36977b51d797c35c58bc5961e9ad25e507811`,
the repeated native results selection check passed: Satin Panties Nightmare's
`bf-car` selects BF, unknown identities always select BF, and requested Pico
variants select Pico. This supersedes the earlier results receipt's binary hash.
The full-stage danger-note callback probe also passed all 68 custom heads,
freeze/stun, frozen-hit penalty and score cancellation, harmless misses, and
alternating-input release without script errors
(`tmp/codename-note-types-native-20260930/receipt.json`). These checks do not
establish full-song parity. The normal-speed after-alias replay still places the
POV actor on camGame behind the HUD effect; first-person layering remains open.

Following the successful private danger-note check, a scoped live refresh added
only seven missing dependency/metadata files for the affected imported chart.
All **1,087** protected existing files, including settings and registries,
remain byte-identical. Backups, the full before-hash inventory, plan and receipt
are under `tmp/note-type-live-refresh-20260930/`. The new files came from the
production-helper preview; this does not clear the separate native scanner
crash. No donor content or existing imported chart was edited.

The first-person replay now **passes** on build
`239e71845478b8d307ce02baea8e69879ce7f64a17480f0e13ab481544235b8c`.
The remaining cause was XML stage-character injection shadowing live aliases.
Stage bindings now exclude registered live globals while preserving explicit
script-owned variables. Fifteen focused alias/stage/lifecycle checks passed.
In uninterrupted 1× offscreen playback, the authored grab advances from frame
2 to 31 at 88.0/89.2 seconds. At 91.5 seconds the visible swapped player is on
camHUD at member index 54, above the corner effect at index 53. Both screenshots
were visually inspected. There were no script errors and the native driver now
asserts animation advancement and shared-camera ordering, rather than treating
a successful process exit as evidence of this fix. Receipt and screenshots:
`tmp/codename-grab-native-20260930-stage-live-bindings/`. This covers the reported
transition, not full-song or all-FPS parity. The current full suite is running.

The scanner-core follow-up confirms that ordinary array-shape guards cannot
explain or repair a Dynamic object with the invalid `0x0101…` vtable. The old
receipt expects binary `25f68e…`, but its recorded executable path has since
been refreshed, so disassembly/locals from that mismatched binary were rejected
as evidence. A future diagnostic must retain the matching executable and trace
the exact nested array-check boundary in a reduced scan. No speculative
null-check workaround was added. Nightmare Vision's next native-host work is
mapped in `tmp/nmv-playstate-host-plan-20260930.md`; its parser/core evidence
still does not constitute gameplay integration.

The subsequent aggregate ran 1,631 tests across 481 modules with 65 skips;
480 modules passed and the mounted HXC count test exceeded its 300-second
subprocess wrapper. An isolated rerun passed in 241.1 seconds with unchanged
assertions (`tmp/hxc-mounted-counts-stage-live-recheck-20260930.log`). The full
run itself remains recorded as a timeout, not relabelled as green.

Source review of Codename `Stage.setStagesSprites` further narrowed the alias
guard: only native Character registrations colliding with live globals are
excluded. Real XML sprite props can intentionally reuse those names, and
explicit script assignments retain precedence. The new test executes the real
filter and covers both the swapped-character timer and these authored prop
collisions; all 15 focused tests pass. This refinement is awaiting its native
build/replay below.

### Direct chart owner initialization and second custom-note mechanism

The broader note check found a separate shared defect: native Freeplay/direct
chart launches did not activate the selected package's global constructor.
Source note scripts could therefore read unset owner-private option defaults
and hide player notes. The direct-load GunshotNote run failed its visibility
check; an explicit-owner control on the same pre-fix `239e718…` binary passed.
An intermediate control probe incorrectly read the legacy HScript FlxG save
wrapper; its null-access messages were fixture errors. The corrected probe
reads the note interpreter's own save facade.

`CodenameModRuntime.synchronizeChartOwner` now initializes globals before
characters and notes, retains successful same-owner sessions, releases foreign
owners, and permits failed constructors to retry. No option values are forced;
the unchanged source constructor supplies defaults through its owner save.
Eighteen focused global/alias/stage/lifecycle tests pass, including failed
selection and constructor recovery.

On current binary
`2d4ab706404ed2bdbed576c6c4f0a85e031307172da77bb9eba037824d636781`,
the direct-load GunshotNote probe passes without `--smoke-owner-root`: default
mechanics is true, active visible player/opponent notes use the source bullet
atlas, player animation is `singDOWN-dodge`, dad plays `shoot`, miss damage is
the authored 0.2 plus the normal 0.0475, and camera angles return from (1,2) to
(0,0). No script errors/diagnostics occurred. Receipt:
`tmp/codename-gunshot-direct-owner-sync-native-20260930/receipt.json`.

The ice-note probe also passes on this binary, now explicitly requiring all
68 heads to be enabled and visible by default as well as their atlas/type and
hit/miss/input behavior. Earlier callback-only evidence did not establish that
visibility/default-initialization requirement. Receipt:
`tmp/codename-note-types-native-20260930/receipt.json`.
The repeated normal-speed botplay grab/layering assertions pass on this build
(`tmp/codename-grab-native-20260930-owner-init/receipt.json`), but botplay hits
the newly enabled ice notes and leaves the authored freeze overlay visible.
An additional no-input practice replay is checking unobscured presentation;
neither replay is evidence of human input timing or full-song parity.

The no-input 1× replay also passes on `2d4ab706…`, with no script errors:
grab frames 3→31 and the visible POV player on camHUD at index 53 above the
effect at index 52. Screenshots were inspected, including the unobscured
first-person composition. Receipt:
`tmp/codename-grab-native-20260930-owner-init-no-input/receipt.json`.

After verifying both source note-script mechanisms, the remaining generated
tables/dependencies were refreshed for the same owner: **20 additional missing
files**, **1,094 existing files unchanged**. The original 1,087-file inventory
also still matches after all builds. Together with the first seven additions,
this installs the 27-file production-helper preview across its 20 songs/22
charts. This refresh still does not count as a successful native scanner run.
Receipt, backups, and transitive integrity summary:
`tmp/note-type-live-refresh-all-20260930/`. Temporary native test companions were
confirmed absent. Final focused global/alias/stage/lifecycle run: **18 passed**
(`tmp/codename-owner-final-focused-20260930.log`). Full package coverage, the
unexplained scanner corruption, and NMV gameplay integration remain open.

### 2026-09-30 — Nightmare Vision main gameplay host and native errors

The selected installed NMV owner now supplies the main gameplay script group:
stage/global/character/song initialization, live PlayState fields, source
character-parent assignment timing, update/step/beat/event callbacks, spawn,
pause/resume and ending gates, and destruction. Note generation follows the
source's song-script initialization phase. This advances the preceding
integration gap; it does not implement every NMV API or separate script group.

Stage metadata uses the source's four ordered JSON locations and exact template
fallback. Import repair adds missing stage JSON without replacing owned files.
Production-helper previews found 20 new-package and 21 old-package files. The
private new-package refresh added 20 files and preserved all 330 protected
files, including options, chart provenance and existing owner files. Evidence:
`tmp/nmv-stage-metadata-private-refresh-20260930/receipt.json`. No live NMV
installation was refreshed. The 36 named easing aliases are source-derived.

The native check exposed a separate interpreter defect: hxcpp's typed enum
catch could consume an Iris error as a control-flow signal, registering a
partly executed module without reporting the error. The compatibility
interpreter now checks the exact control enum identity in function returns,
loops and script try/catch. Unknown-variable modules are rejected; callback
errors remain attributable and later calls can recover. This change is confined
to the shared NMV interpreter and does not alter donor scripts or haxelibs.

Canonical build `tmp/nmv-native-error-control-build-20260930.log` passed.
Binary SHA256:
`7e4499df18170d84438ad5023253dc1d7e8d07ed47ec6958424c80967c8a796f`.
The offscreen, null-audio, isolated-save 1× native probe passes the unchanged
Events module's midpoint camera, authored offsets, lock/release, stage zoom
and easing tween; native-action-before-callback order; update/post/step/beat
dispatch; and mod-owned ending precedence. Receipt and full diagnostics:
`tmp/nmv-gameplay-host-native-20260930/`. The short smoke success marker is not
a natural-ending or full-song compatibility pass.

Known NMV gaps include ClientPrefs/Paths/shader/HUD bindings, Bopper and camera
utilities, plugins, stage-object rendering and character groups, separate
event/note-type groups, remaining gameplay hooks and multi-playfield behavior.
The native receipt retains these errors and import warnings with repetition
counts. There are 15 distinct unresolved source diagnostics. The six intentional
missing-variable test errors are recorded separately by probe module name. No playable inventory row is promoted to source-matching status.

### Codename scanner investigation: actual event-array fixture

The preserved ASan diagnostic binary `03b22f06…` traversed the unchanged
Soretro hard chart and event sidecar: 348 event rows, 322 event groups and five
authored event names, exit 0 in 3.449 seconds without an ASan error. Receipt:
`tmp/codename-event-walk-dsides-soretro-pathsentinel-20260930/receipt.json`.
A generated zero-byte Inst.ogg path sentinel satisfies discovery validation;
this fixture makes no audio/import/playability claim. The first fixture lacked
that path and discovered zero songs, so it provided no event-traversal evidence.
The diagnostic binary predates the current ModuleFunctions stage-metadata
changes; its source hashes are recorded. The historical native scanner
corruption remains unexplained and open.


The same native binary also passes direct error checks inside functions,
while/do/for loops, script catch, break/continue/return through catch blocks,
and a second successful call after a failed callback. One intermediate probe
incorrectly expected the group's CONTINUE value from a direct module call;
module calls return null after reporting errors. Its failed receipt is retained
as `receipt-probe-module-return-error.json`; the corrected check passes without
an engine change. Temporary chart companions were removed after both runs.

The first full integration run completed 1,640 tests across 487 modules in
319.6 seconds (65 skips), with eight failed modules. Failures were stale test
fixtures: missing extracted helper/binding dependencies and exact pause-gate
text matching. Their output is retained in
`tmp/full-tests-nmv-gameplay-host-20260930.log`; a repaired-suite result follows
when available. No failure in that run is being relabelled as a pass.


The same 1× native mechanism probe passes at configured 60, 240 and 480 FPS;
startup markers confirm both update/draw caps. Each observes nine step hooks
and two beat hooks over the same song-time window, while update/post counts
scale with rendered frames (90/90, 342/342, 601/601). Camera target/release,
easing completion, error recovery and ending ownership assertions pass at
all three caps. Private option bytes are restored after each run. Summary:
`tmp/nmv-host-fps-summary-20260930.json`; individual receipts are under
`tmp/nmv-gameplay-host-native-20260930-fps-{60,240,480}/`. This is timing
coverage for the newly connected main-group mechanism, not a sustained
480-FPS performance claim or full rendering/gameplay parity.


Next API work is source-audited in
`tmp/nmv-native-binding-next-batch-20260930.md`: ScriptConstants, NMV settings,
owner-scoped shader loading, then HUD/plugin surfaces. The release plugin API
differs from the supplied source version. Proposed preference mappings in that
audit are a plan, not implemented behavior: unsupported settings must retain
explicit gaps until their semantics are implemented. In particular, the local
Psych preference object, PluginManager and PlayState are not interchangeable
with the NMV ClientPrefs, PluginsManager and PsychHUD interfaces.


After all native runs, the original 330-file protected inventory still matches
byte-for-byte (`tmp/nmv-stage-metadata-private-refresh-20260930/post-native-integrity.json`).
Production source hashes for this build are saved with the native receipt in
`tmp/nmv-gameplay-host-native-20260930/source-hashes.json`.


Final integration rerun: **1,640 tests across 487 modules, 65 skips, zero
failed modules**, in 275.7 seconds. Log:
`tmp/full-tests-nmv-gameplay-host-repaired-20260930.log`. The eight fixture
repairs retain production method extraction; the pause test now additionally
checks NMV cancellation before pause flags change, and the character fixture
executes the real native-Character alias guard with a minimal test type. No
production behavior changed between the native checks and this suite pass.
This milestone closes the test-harness failures, not the remaining package
compatibility gaps or unexplained historical native crashes.


## 2026-09-30 — Nightmare Vision source APIs and asset retention

Shared importer/runtime changes retain the selected content tree plus its
explicit engine assets under an isolated `__nmv_core` subtree. Core-only
imports avoid duplicate script staging. Runtime lookup follows owner/core
precedence, including core-only calls and distinct core script identities.
Added source constants, color helpers, shader construction, camera-position
and snap helpers, and an owner-local ClientPrefs data view.

The canonical build completed (`tmp/nmv-source-apis-build-20260930.log`).
Focused NMV checks passed **43 tests in 20 modules**; the additional importer
integration checks passed **10 tests**. The full suite is running; its first
stale destination-variable assertion was repaired and its 19-test module
passed independently. Final aggregate evidence is recorded below when ready.

The private-only refresh added **1,940 files / 1,059,146,438 bytes**, with
**350 existing files unchanged**, including chart metadata and personal
settings. Every added file was checked against its donor hash. Preview,
backups, protected hashes, and receipt are retained in
`tmp/nmv-assets-private-refresh-20260930/`. The importer itself uses
non-overwriting copies. No live import or donor content was edited.

The native source-API probe completed on binary
`74352eab397440290e170b7d4735be50f01c4ce303fa24daf82189a12ee4c997`
and **failed its stage/shader assertions**. Stage `onLoad` stops at unsupported
`zIndex`, so the lighting sprite is never added. The separate shader check
incorrectly looked up a lexically scoped script variable in the globals map;
its null read does not establish a shader failure. The probe now reads the
actual camera filter shader for the next run, without rerunning this known
stage failure solely to repair the fixture.
The probe also retains unresolved PluginsManager, modManager, playHUD and
other source API diagnostics. No shader compile errors were reported, but the
failed initialization means this does not establish complete shader behavior.
See `tmp/nmv-source-apis-native-20260930/receipt.json`. No new chart/difficulty
is promoted to source-compatible by this implementation.
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
source count assertions remain unchanged. The targeted rerun passed all **20 tests**
in 195.583 seconds (`tmp/nmv-source-apis-suite-recheck-20260930.log`),
covering both previously failing modules. This resolves the two reported
failures; it is not a second full-suite run.

Post-build integrity: 349 protected files remain byte-identical. During the
desktop build/play session, live options gained `normalizeSongAudio:false`
where it was previously absent; all existing personal option values remain intact.
The live settings file was not restored over the user's session. See
`tmp/nmv-assets-private-refresh-20260930/post-build-integrity.json`.


## 2026-09-30 — Modchart sustain UV and camera regression work

Two shared defects explain the new Endless report independently of chart name:

- FunkinModchart 1.2.5 reads hold UV bounds using an obsolete Flixel field
  order; its rotated branch also advances eight floats while emitting twelve.
  The tracked compatibility helper fixes atlas selection and subdivision seams.
- Its camera fallback calls `getCameras()`, which already returns the global
  draw default. Plain-group notes therefore reach the gameplay camera outside
  their group's draw, while sprite-group receptors retain HUD cameras. Explicit
  sprite/container and playfield assignments now precede the adapter fallback;
  the native note group's assigned camera is retained.

**11 focused tests passed** (`tmp/modchart-uv-camera-focused-20260930.log`),
including interpreted asymmetric/rotated UV fixtures, camera precedence,
patch idempotence, and the existing modchart adapter/draw-ownership checks.
The canonical `./run.sh build` applied the patch successfully under the runtime lock.
The isolated normal-speed baseline now reproduces the small/offset note heads
in `tmp/endless-geometry-20260930/baseline-28s.png`, on binary
`74352eab397440290e170b7d4735be50f01c4ce303fa24daf82189a12ee4c997`.
Telemetry shows roughly equal note/receptor scale and frame size before their
draw-camera transforms. The corrected normal-speed replay passed on binary
`4b6825927623f9b7e76afedd638cf3fa79efe6d2394d286708de08e58c3ee6a6`:
`tmp/endless-geometry-20260930/after.result.json` records exit 0, runtime success,
no failure markers, and both requested screenshots. The 25-second image shows
a continuous, centered green sustain; the 28-second image shows correctly
sized incoming arrows aligned with their transformed receptor lanes. This
is a bounded presentation check, not full-song or 60/240/480 FPS parity.

The selected owner's default PNG/XML note atlas was missing from the previous
import. The production collector now retains default note/receptor atlases,
and creation events resolve the selected owner's default even when a script
leaves `game/notes/default` unchanged. Per-state owner caching avoids repeated
lookups. The private replay staged only the two donor-hash-verified files in
`tmp/codename-default-atlas-import-preview-20260930.json`. The subsequent runtime-only missing-file refresh added those two files;
all **1,034** preexisting owner files and **42** protected options/ownership/
provenance files stayed byte-identical. Receipt and backups:
`tmp/codename-default-atlas-refresh-20260930/applied/`. No partial repository
owner was created, and no chart or donor bytes were edited. Merely
retaining an Animate-format note atlas does not implement composite note
rendering; that format remains an explicit gap for plain note sprites.

The combined render/creation/pause focused check passed **15 tests** in
`tmp/codename-render-batch-focused-20260930.log`; the native build log is
`tmp/codename-render-batch-build-20260930.log`. The first Try Harder normal-speed replay also passed its runtime window:
`tmp/try-harder-scene-20260930/after.result.json`. `SCENE_ANIMATE` samples show
an actual 418-frame Animate timeline advancing at 24 frames/second, visible
through the lyric section and finished/hidden after the authored handoff at
about 161.578 seconds. Captures at 145, 151, 158 and 164 seconds show the
previously missing composite actor and its exit. An authored ice-note overlay
was unexpectedly active because the script-facing `player.cpu` flag omitted
demo botplay. That newly discovered shared flag defect is being corrected;
this first scene replay does not establish clean overall presentation.

The native pause/resume check passed (`tmp/codename-pause-native-20260930.json`):
one Escape/Return pair, music clock unchanged at 3,079 ms during pause, music
playing again after resume, and zero transition-update/transition-finish
markers. The source pause implementation issues callbacks without triggering
an automatic selected transition on either opening or closing.


### Follow-up native source API check

The Nightmare Vision-only `zIndex` property bridge now uses the existing
compatibility storage. The final canonical build is
`357392e762c1c1be7d136c7ba0a6998096d207a0fe769b7bd7371b6dd4e800b0`.
`tmp/nmv-source-apis-native-20260930-zindex-fixed/receipt.json` records
`NMV_HOST_NATIVE|PASS`, exit 0 and runtime success. The real stage now creates
its fourth overlay sprite. The corrected probe reads the shader attached to
`camGame` and confirms its `iTime` uniform advances; no shader compile
diagnostics were emitted. Camera event/tween behavior, preferences, callback
execution, interpreter error recovery, and the mod-owned ending gate also
pass this bounded check. Intentional error fixtures are recorded separately.

Twelve unresolved source/import diagnostics remain, including PluginsManager,
modManager, playHUD, Bopper, CameraUtil, FunkinAssets, WindowUtil, DiscordClient,
Difficulty, and the separately unsupported event-group scope. Passing this
API probe does not promote the song/package to full compatibility. No new
automatic stage sorting policy was introduced. Focused interpreter/group
coverage passed **3 tests** (`tmp/nmv-zindex-focused-rerun-20260930.log`).


### Final normal-speed scene verification

After fixing the effective CPU script view, the final **1x** replay passed on
binary `357392e762c1c1be7d136c7ba0a6998096d207a0fe769b7bd7371b6dd4e800b0`.
`tmp/try-harder-scene-20260930/final-scene-check.json` records 17 visible scene
samples, the 418-frame composite animation advancing, the authored handoff
back to gameplay, `playerCPU=true`, and `playerStunned=false`. All four capture
targets were obtained. The 151-second screenshot now contains the missing
actor during “SO WELCOME TO YOUR NEW EDITION!”; 158 seconds shows another
pose and 164 seconds shows gameplay restored. There are **zero tagged script
diagnostics or unexplained errors** in this bounded run. These captures do not
establish complete-song presentation or 60/240/480 FPS timing parity.

The CPU bridge's final focused run passed **10 tests**
(`tmp/codename-cpu-final-focused-20260930.log`). Native note ownership remains
based on the authored CPU field; script reads also reflect demo/autoplay.
Unsupported Animate note/receptor atlases now emit a deduplicated
`[codename-atlas-unsupported]` diagnostic before fallback, which strict native
checks treat as an unresolved compatibility issue.

The two-file refresh's **42 protected settings/ownership/provenance hashes**
remain unchanged after the final build; see
`tmp/codename-default-atlas-refresh-20260930/applied/post-final-build-integrity.json`.
Relevant final source/dependency hashes are recorded in
`tmp/codename-render-final-source-hashes-20260930.json`.


### Completion checks and integration results for this batch

Both selected Hard charts passed natural audio completion and returned to
Freeplay at **50x**, on final binary `357392e7…`:
`tmp/codename-render-completion-20260930.jsonl`. Endless dispatched **464/464**
due events; Try Harder dispatched **657/657** due events (its 658th chart event
lies after the instrumental end). Both receipts have zero interpreter/native
diagnostics and unchanged options. This verifies accelerated execution and
ending cleanup; normal-speed presentation is established only by the bounded
captures above. Temporary native capture installations were removed.

Two integration runs each executed **1,656 tests across 495 modules, 65 skips**:

- `tmp/full-tests-codename-render-20260930.log`: one module failed while its
  isolated Haxe classpath fixture was being updated. The corrected NMV
  interpreter/group rerun passed all **3 tests**.
- `tmp/full-tests-codename-render-final-20260930.log`: the corrected module
  passed; the only failure was the mounted counts scan reaching its internal
  300-second deadline during concurrent build/native/inventory work. With that
  work finished, the unchanged check passed in **205.618 seconds**:
  `tmp/mounted-import-diagnostics-final-rerun-20260930.log`. Neither its count
  assertions nor its native timeout were weakened. This is a full-suite run
  plus a successful isolated retry, not a single uninterrupted green run.

No known failure remains in these targeted presentation/lifecycle checks.
The wider compatibility goal is still incomplete: retained NMV plugin,
modifier and HUD APIs, unsupported formats, remaining package/difficulty
parity, and final 60/240/480 FPS validation still require work. A source audit
identified repeated sibling-directory enumeration in `DependencyInspector`
as a candidate for measurement; no unmeasured performance change or persistent
donor-result cache was introduced in this batch.


## 2026-09-30 — Nightmare Vision plugin/HUD/callback integration (in progress)

Shared source changes add a real persistent plugin runtime, owner save forwarding,
callback scheduling and a live HUD adapter. No donor/chart files were changed.
The callback fixture covers 60/240/480 FPS, BPM boundaries and seeking; this is
interpreter-level timing evidence, not native frame-rate/presentation validation.

The initial focused run passed **23 tests**:
`tmp/nmv-plugins-focused-20260930.log`. The HUD/plugin/gameplay run passed **7**:
`tmp/nmv-hud-focused-20260930.log`. These precede final review corrections and will
be superseded by the final focused run for this batch.

Build/native verification is pending while the desktop process holds the shared
runtime lock. The existing `357392e7…` native receipts belong to the preceding
Codename rendering batch and do not verify these new Nightmare Vision changes.
The isolated source-API probe was extended to verify real Utils plugin return
values and metadata reads, owner save initialization, existing HUD object
identity, live receptor arrays, and native one-shot callback execution.

Known remaining NMV gaps include menu entry points, imported engine utility
classes, event/note-type execution, modifier value/easing/rendering, and source HUD
judgement popups. Successful focused checks do not clear these diagnostics or
establish complete source parity for any song/difficulty.


### Integration/native evidence and alpha preparation

The integration suite completed with **1,667 tests across 501 modules, 65 skips,
0 failures** in 368.9 seconds:
`tmp/full-tests-nmv-plugin-hud-20260930.log`. Native typechecking then identified
a plugin-host static `active` field colliding with FlxBasic's instance field.
It was renamed `activeHost`, and the driver fixture now includes FlxBasic.active
so that collision is covered. The three plugin runtime tests passed again in
`tmp/nmv-plugin-host-native-type-fix-20260930.log`.

The canonical Linux build passed (`tmp/nmv-plugin-hud-alpha-final-build-20260930.log`).
Current binary SHA-256:
`83f6058e0296dbf07b7d243f1c4997c902d8a30b0a177b789f69c4aceeafea17`.
The extended 1x offscreen NMV probe passed its assertions and exited normally:
`tmp/nmv-source-apis-native-20260930-plugin-hud-alpha/receipt.json`.
It exercises actual Utils loading, source return values, metadata JSON reads,
typed owner saves, real HUD object identity, receptor arrays and one-shot callbacks.

This probe is **not a clean package-parity result**. Its receipt retains 15 unique
unresolved diagnostics: unavailable engine utility classes, a missing click sound,
unimplemented event execution, an unknown sanitize function, and dependent
callbacks. In particular, missing Mods context is reported from plugin onUpdate
on 955 frames; callback attempts have not been dropped to hide that dependency.
These failures require further shared compatibility work.

Alpha preparation changed app metadata to CammieEngine 0.0.1 and removed the old
menu version suffix. The offscreen native menu check passed with zero diagnostics;
`tmp/alpha-menu-20260930/main-menu.png` visibly reads **CammieEngine v0.0.1**.
The capture initially needed its private scratch directories created; the corrected
fixture passed and did not touch desktop input/audio. Default and live personal
options stayed byte-identical across builds:
`tmp/nmv-plugin-hud-build-settings-20260930.json`.

Git ignore rules now reject future local asset imports by path, including unknown
asset subtrees, while existing tracked bundled assets remain versioned. The audit
found exactly the 29 bundled chart directories and no additional tracked song
folders (`tmp/alpha-gitignore-audit-20260930.json`). A tracked generated dump was
removed from the index with its local file preserved. Five known 24-byte PNG test
fixtures were moved beneath tmp; their test now writes into its temporary directory
and its focused check passes. README was shortened for the alpha. No upload,
tag or GitHub release has been published by this work.


### Windows alpha release pipeline — 2026-09-30

Replaced the three obsolete Windows workflows with `windows-alpha.yml`. It builds
through `run.bat build` on Windows 2022, publishes downloadable Actions artifacts,
and attaches a ZIP/checksum to alpha-tag prereleases. No repository has been
pushed, tagged or published during this work.

The packager requires the executable, Lime native library, VLC libraries/plugin
cache/manifest, decoder and notices. Fixture tests verify library/plugin and Lime
manifest preservation, tracked bundled content, exclusion of untracked flat
imports, rejection of populated owner-import trees, the committed default options
seed instead of personal runtime settings, and the archive checksum. **5 focused
tests pass** (`tmp/windows-alpha-release-review-20260930.log`). The Windows launcher
now applies the shared compatibility patches, including hold UV/camera resolution,
and creates absent declared asset mount directories. The existing shared hold-UV
and camera suites also pass **6 tests**
(`tmp/windows-shared-render-patch-review-20260930.log`). `git diff --check` passes.

These are packaging/source checks, not a native Windows build or playback result.
The first GitHub Actions Windows build and a Windows launch/playback check remain
required before claiming that platform is verified. Example trigger tag:
`v0.0.1-alpha.1`; manual workflow runs produce downloadable development ZIPs.


### NMV source context and release-facing cleanup — 2026-09-30

The latest development pass binds owner-scoped Mods/Difficulty context, preserves
source difficulty spelling and maps selections by name, records the logical source
mod directory separately from the stable import identity, and exposes the source
Conductor timing names over native transport. Paths.sanitize and owner-scoped
FunkinAssets.exists now let the real Completion/UI modules continue. Missing
sounds use the source engine's embedded beep fallback with an explicit diagnostic.
The supplied package really lacks sounds/keys/keyClick6.ogg; neighboring donor and
installed keyClick5.ogg hashes agree. No donor changes or import refresh were used.

Focused checks pass: **22 tests** across context, timing/window, Paths, difficulty
metadata and ownership (`tmp/nmv-release-facing-focused-20260930.log`), plus **5
Windows packaging tests** (`tmp/alpha-branding-package-check-20260930.log`). The
canonical build passed (`tmp/alpha-release-facing-build-20260930.log`). Binary:
`d2e0df415798cfa69f5e3b7d77b09e91ac28a73265d6f0b044be9f40d81b056b`.

The first native probe exposed a real hxcpp issue: dynamically reflecting Lime's
inline window properties failed (title) or returned incorrect values (width).
The bridge now uses typed Lime access. The repeated 1x offscreen probe passes,
including live source transport, initial tempo mapping, source difficulty, owner
context, actual window width, last camera and real Completion initialization:
`tmp/nmv-source-apis-native-20260930-release-facing/receipt.json`. The prior `Mods` failure on every frame is gone.

This remains partial source-API verification. Six unresolved diagnostics remain:
Bopper and DiscordClient imports, dedicated Middle Camera event-script execution,
the missing donor click sound, and two ComposerIntro callbacks depending on
DiscordClient. Global Mods switching, advanced camera construction, source scale
mode changes and additional source utility/HUD APIs remain unfinished. No entry
has been promoted to complete compatibility from this check.

Release-facing cleanup updated native HUD/Discord/import-report/launcher labels,
credits and title-intro attribution, official download links in NOTICE, the bundled
player guide and the issue template. EngineBranding now reports app metadata
rather than Flixel's version, with a 0.0.1 fallback; VERSION also says 0.0.1.
The inherited LICENSE, executable filename and save/package identifiers remain.
Discord's inherited application ID still needs a project-owned replacement to
change its service-side application identity. No Git remote change or push was
performed. Static metadata/credit checks and `git diff --check` pass.

### Local Windows cross-build and loading checks — 2026-09-30

The repository's bundled LLVM MinGW toolchain built the Windows x64 executable
from Linux with `./build.sh windows`. The output includes the PE executable,
`lime.ndll`, VLC and LLVM runtime DLLs, and the ASTC decoder. The local release
packager produced `dist/CammieEngine-local-linux-cross-windows-x64.zip`
(1,144,444,693 bytes; SHA-256
`e8c7d5e1244f41599eec01ab444f0fd78fa221ed6227b31f0e60d49b1e7a7db2`).
Archive integrity and checksum verification passed. The archive excludes imported
mods and personal options; its settings file matches the repository seed.

The Windows alpha workflow now caches exact pinned toolchain and haxelib inputs.
The reported GitHub job spent about 20 minutes in its build step, but a new CI
run is needed to measure the cache benefit. The README documents the local
cross-build and package commands. This is a local alternative for building and
testing Windows releases; the GitHub runner remains available.

The missing or stationary scrolling notes on a fresh Windows save came from
using the absent legacy `scrollSpeed` save field as the travel-speed multiplier.
The shared gameplay path now uses `effectiveScrollSpeed`, retaining the existing
dynamic speed and strumline override precedence. The regression test executes
the extracted Haxe expression for a missing legacy field and explicit settings.

Cold imported-song loading had two verified shared costs. Native asset path
resolution made redundant OpenFL manifest and scope probes; a synthetic 1,000
path benchmark went from 97.9 ms and 3,000 manifest probes to 29.0 ms and none.
`NoteKeys` repeatedly parsed the same preset JSON for each note; a bounded,
per-song template cache now deep-clones presets for note isolation and resets at
song creation and import completion. Its 2,304-note Haxe benchmark went from
177–188 ms and 2,304 reads to 62–69 ms and one read. The representative
imported Codename chart's offscreen Wine note construction went from about
3.0 seconds to 0.252 seconds; PlayState readiness went from 8.057 to 5.299
seconds. The latest Linux run reached PlayState in 5.267 seconds. Bitmap
decoding still consumed about 2.5 seconds in the Wine run, so other large
imports can remain slow; no async image-loading claim is made.

Runtime Codename song metadata now re-derives generated fields from validated
source fields when loading a sidecar. Import-time generation still rejects an
inconsistent cache. This removed the null metadata errors found by the first
strict Wine replay without changing the donor or doing a bulk import refresh.

After these changes, `./run.sh build` and the local Windows cross-build passed.
The full test suite passed: **1,681 tests across 506 modules, 65 skipped, zero
failed** (`tmp/full-suite-note-cache-final.log`). A fresh private Wine prefix,
Xvfb, dummy video and null audio ran imported Codename Try Harder Hard for 12
seconds offscreen: `tmp/windows-note-cache-smoke-retry.json` reports success,
zero strict diagnostics and unchanged options. The load log records the first
and last note at 2.823 and 3.075 seconds and PlayState ready at 5.299 seconds.
The current run does not verify every difficulty, full song completion, visual
parity by screenshot, actual Windows hardware, or the reported slow loads for
other imported charts. The broader Example Mods completion goal remains open.

### Bundled Windows results screen — 2026-09-30

The previously packaged local Windows ZIP contained **zero** files under
`assets/imported_mods/`; the locally imported V-Slice-style Psych results pack
had been excluded along with personal imports. The clean release now carries a
fixed, engine-owned `bundled-vslice-results` provider (138 files, 43 MB of
source content). Its copied files match the supplied pack byte for byte. The
release packager includes only this fixed tree from the imported-mod namespace,
checks every packaged file against the source tree, excludes other imported
owners, and writes the committed settings seed rather than personal options.
`PsychGlobalPackImporter` uses a valid user-selected global provider first and
the bundled provider otherwise. A newly imported global pack can still become
the user's selected provider without modifying the bundled tree.

Windows `PsychScriptDiscovery` reports absolute script paths such as `C:/...`.
`PsychModSettingCompat` had treated every path not starting with `/` as relative
and rejected the drive colon. That removed the results script's validated
owner, so owner-scoped settings and media were unavailable. The shared path
validator now recognizes drive-absolute script origins while retaining the
traversal and drive-relative rejection checks. This is a Windows path rule,
not a chart or pack-name exception.

`./build-windows-release.sh local-results` completed the local LLVM-MinGW
build and package in one command. The generated ZIP passed SHA-256 and archive
integrity checks, contains all 138 results files and no other imported files,
and contains the committed options seed. The Windows executable then ran the
bundled provider against the packaged Tutorial Normal chart under isolated
offscreen Wine. Song end invoked the provider, it created and added results
sprites, and Return reached Freeplay with zero strict diagnostics. An Xvfb
capture, `tmp/windows-vslice-results-state.png`, shows the actual results UI,
character, score panel and title at 1280×720 (83.94% nonblack pixels). The
runtime log is `tmp/runtime-smoke/logs/windows-vslice-provider-results.log`.
The first private Wine prefix attempt stalled in `wineboot` before game launch;
the warmed-prefix replay completed. The runtime lock and personal settings
were preserved.

The CI Windows workflow still builds comparison artifacts, but no longer
automatically publishes them to a tagged prerelease. This prevents a later CI
run from replacing the verified local cross-build after it is uploaded. The
bundled pack is credited in NOTICE. Native Windows hardware, results for an
imported full-song ending, accurate real-play scores, and complete visual/audio
parity across all charts remain open checks. The supplied results pack has no
license file, so its redistribution terms also need explicit review before a
public release.

Previous local upload candidate (superseded by the scan fix below):
`dist/CammieEngine-v0.0.1-alpha.3-windows-x64.zip`
(1,185,036,152 bytes; SHA-256
`e80b9dd8262b34e84882f3ba1f00c1bbf2b5e8febfb925edab04540a54fe1c97`).
It uses the existing prerelease asset name; checksum and ZIP integrity checks
passed. It contains all 138 bundled results files, no other imported files,
the committed options seed, and the updated player guide. The final suite
passed **1,683 tests across 506 modules, 65 skipped, zero failed**
(`tmp/full-suite-bundled-results-final.log`). The prerelease asset has not been
uploaded; the checkout's changes and the new bundled files remain uncommitted.

### Windows import scan null listing — 2026-09-30

An offscreen Wine replay of the local Windows executable crashed while scanning
the Psych `Hey kid do you wanna weiner` package, before `scan_ready` and before
any import writes. The native fault was a read at `0x18` in hxcpp's array sort.
The scanner tested Codename markers for every candidate root; this Psych root
has no `data/config` directory, and Windows directory enumeration returned a
null listing for that probe (`tmp/windows-sequential-import-3.log`).
`ImportRootScanner.readDirectory` now checks that
the target is a directory and normalizes a null listing to an empty array
before sorting. This is a shared engine-detector fix; no donor or chart was
changed. The focused interpreter test covers missing directories, null native
listings, and deterministic case-insensitive ordering.

In one disposable runtime, the Codename `bully-mod` import completed first
with the original executable (1 song, 96 assets). The patched Windows
executable was then rebuilt locally and, in separate Wine processes using that
same runtime, imported the previously crashing Psych package (1 new song, 63
assets) and ModdingPoop `cursed pergation` (1 new song, 88 assets).
Both post-fix scans emitted `scan_ready` and both imports emitted `success`
with `failed=0`. A repeat Psych import skipped both detected candidates and
copied no assets, confirming that existing imported files were retained. The
logs are `tmp/windows-sequential-import-2.log` and
`tmp/windows-sequential-import-after-fix-{psych,third,repeat}.log`.

The Psych transaction still reports one nonfatal source-asset diagnostic:
`noteSkins/NOTE_assets` is absent from that donor. The separate import checks
establish scan and transaction stability under Wine; they do not establish
song-playthrough parity or a native Windows hardware result. The broader
Example Mods completion goal remains open.

The complete automated suite passed **1,684 tests across 506 modules, 65
skipped, zero failed** after this change.
Both `./run.sh build` and `./build-windows-release.sh v0.0.1-alpha.3` passed.
The rebuilt ZIP is 1,185,037,288 bytes with SHA-256
`871667c04a3ff5110aed1e8e44b2f130440f9de9fa35df7bf949d3fb1df3d8c7`.
Archive integrity and `SHA256SUMS.txt` passed; the ZIP's executable matches
the tested build, contains all 138 bundled results files, and contains no
other imported-mod files. It has not been uploaded.

### Character picker release roster — 2026-09-30

The global character registry can retain names from earlier imports even when
the release package excludes their media. `ChooseCharState` now derives its
roster on each entry from the shared `Song.resolveCharacterVisual` resolver and
lists only entries with a complete visual under their own asset name. A
character with installed media remains selectable; stale names and aliases
that only borrow another character's media are hidden. No chart or mod names
are checked. The focused Haxe interpreter fixture passes and covers a missing
visual, a borrowed alias, and refreshing the list after media becomes
available. The Linux and Windows release builds both passed with this code.

### Opt-in Windows release updater — 2026-09-30

Windows Settings now checks the published GitHub release list on request, so
alpha prereleases are included. It accepts only the matching Windows x64 ZIP
with a GitHub SHA-256 asset digest and a matching `SHA256SUMS.txt` entry. The
separate helper downloads and verifies the archive, checks its extraction
paths, waits for the game executable to close, then overlays the runtime. It
backs up replaced runtime files for rollback and commits `RELEASE_TAG` after
the copy. Existing files under `assets/`, `mods/`, and `imported_mods/` are
kept, including settings and owner imports. Because older releases have no
package ownership manifest, this also retains older static asset files; the
Settings prompt and README say a clean extraction is needed for static asset
changes. The updater is offered only on Windows while no Linux package
exists. The focused tests compile the Windows-only helper under Haxe
`--interp`, exercise release filtering and version ordering, and check the
generated helper contract. They pass; a live GitHub download and completed
in-app install on native Windows hardware remain untested.

The complete suite passed **1,687 tests across 508 modules, 65 skipped, zero
failed** (`tmp/settings-updater-full-suite.log`). `./run.sh build` passed
(`tmp/settings-updater-linux-build.log`). The local Windows cross-build passed
(`tmp/settings-updater-windows-build.log`) and produced
`dist/CammieEngine-v0.0.1-alpha.4-windows-x64.zip` (1,185,441,938 bytes;
SHA-256 `c8c0b3229dadba0be5933b6a06c7a79b4fe86b9b2053b924a95bd4931a6df5c6`).
ZIP integrity and `SHA256SUMS.txt` passed; its `RELEASE_TAG` is
`v0.0.1-alpha.4`, all 138 bundled results files are present, and no other
`assets/imported_mods` files are included. The packager now takes both release
log copies from current source, so the root log cannot be stale after a
cached runtime build. A 20-second offscreen, audio-disabled
Wine startup stayed alive through its timeout (`tmp/wine-smoke-1188611.log`).
The first sandboxed Wine attempt could not bind its local wineserver socket;
the isolated retry succeeded. The updated ZIP has not been uploaded.

### Windows tag rebuild removed — 2026-09-30

The `windows-alpha.yml` workflow was removed after its tag trigger started a
second Windows build while the locally built ZIP was being published. Release
packaging remains available through `build-windows-release.sh`; GitHub Actions
will no longer build on alpha tag pushes once this removal is pushed. The
already-running workflow was cancelled by the maintainer. The test contract
now checks that the old workflows are absent. The full Python suite passed
**1,687 tests across 508 modules, 65 skipped, zero failed** after the removal.

### Windows alpha.5 import and visual checks — 2026-09-30

The prior Wine HL17 scan crashed at `0x00000001412D7292` while
`KadeStageSource.playStateFiles` read the length of a null result from
`FileSystem.readDirectory`. The same offscreen scan on the rebuilt Windows
executable now finishes with three songs, zero scan errors, and no crash
(`tmp/wine-alpha5-hl17-scan-process.log`). The shared importer and Kade source
enumerators now handle null native listings. A Haxe fixture forces null
listings, and the focused compatibility tests pass (68 tests, two skips).

The Psych Weiner package does not contain its referenced stock stage images.
Owner-first image lookup now falls back to the engine's stock stage folder,
which includes the previously absent matching light. An offscreen Wine frame
from the imported chart shows its backdrop, front, and curtains
(`tmp/wine-alpha5-weiner-frames/frame-12.png`). The default Psych note skin
is supplied by the engine's normal UI atlas, so import no longer reports its
absence as a donor error.

Windows hxcpp parsed a full eight-digit Psych color as `7FFFFFFF`, making
the V-Slice results backdrop translucent despite sprite and camera alpha of
one. The shared color conversion now preserves the 32-bit ARGB value; an
offscreen Wine capture of the bundled results screen showed `FFFFFFFF` and
no gameplay scene beneath it (`tmp/wine-alpha5-results-frames/frame-18.png`).

A clean `v0.0.1-alpha.5` ZIP was extracted into a disposable runtime. In one
Wine process it imported Weiner with zero errors, immediately entered its
Hard chart, and reached song end at 50× demo speed. A second process used the
same disposable installation to import HL17 with zero errors (three songs,
242 copied assets) and immediately entered Linkinteen Parks for a 15-second
offscreen smoke. These checks cover the reported first-play sequence for two
imports, but the friend's unspecified crashing chart and native Windows
machine have not been reproduced, so that anecdote remains a follow-up case.

The locally built ZIP contains the bundled results pack and common stage light,
no personal imported owners, and `RELEASE_TAG=v0.0.1-alpha.5`. Its checksum
passes `sha256sum -c`. No GitHub Actions Windows build was used.
The final `./run.sh build` succeeded. The complete parallel suite passed
**1,691 tests across 509 modules, 65 skipped, zero failed**. The final ZIP
is 1,185,459,082 bytes with SHA-256
`96335c897480ab20c252194c33a0064fc75a1804a843e4862f6819561c0b3d86`.

### Windows alpha.6 updater and version — 2026-10-01

The Settings updater now starts a bundled Windows helper from a unique temporary
job directory, allowing an update to replace the installed helper itself after
the game exits. The same helper runs on Windows and under Wine; it no longer
needs PowerShell. The update check and asset downloads use Windows URLMon HTTPS
and certificate validation. A real Wine request downloaded the published
alpha.5 checksum and release-list JSON, parsed the three returned releases, and
rejected an expired-certificate test endpoint. This checks the network path but
does not claim a published alpha.6 update was installed.

An isolated Wine fixture installed a synthetic release, replacing the game,
helper, and release tag while preserving `assets/data/options.json` and a
personal imported chart. With a forced failure after two replacement files,
the installer restored the old game, helper, and tag, left personal files intact,
and removed the new asset. The helper verifies the ZIP checksum and archive
paths before installation. These tests cover self-replacement and rollback;
native Windows hardware and a full in-app update from GitHub remain to be
checked.

The runtime reads the installed `RELEASE_TAG` for user-facing version text, so
the packaged build displays `v0.0.1-alpha.6` where the engine version appears.
`Project.xml` keeps numeric `0.0.1` for Windows resource-compiler compatibility.
The Linux build passed, and the parallel suite passed **1,693 tests across 510
modules, 65 skipped, zero failed** (`tmp/wine-updater-full-suite-final.log`).
The final 29 focused updater/build tests passed. The locally built Windows ZIP
is 1,186,011,949 bytes with SHA-256
`f0fcb09612617c3a89b659d96e732678a4a807c6f666e2b8a338b10c1ed7058e`.
Its checksum and ZIP integrity passed; it contains `CammieUpdateHelper.exe` and
`RELEASE_TAG=v0.0.1-alpha.6`. The ZIP is local and has not been published. The
overall example-mod compatibility goal remains open; this evidence covers the
updater and version work only.

An additional 20-second offscreen Wine startup of the alpha.6 executable used
Xvfb and dummy audio, reached `TitleState`, and remained alive until the
intentional timeout (`tmp/alpha6-wine-startup.log`). The sandboxed first attempt
could not bind a wineserver socket; the permitted retry completed. The runtime
settings file was backed up and restored after the check.
