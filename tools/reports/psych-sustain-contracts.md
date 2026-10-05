# Psych 1.0.4 sustain layout and skin geometry - verified scoped checkpoint

Reference revision: `5c67ced49e5a98535298a6daa3f8f4ec79ac8399` in `../fnf_sources/FNF-PsychEngine`.

## Source contracts and implementation

Donor `states/PlayState.hx:1338-1421` establishes section-local BPM, rounded sustain count, first segment at head time, parent/tail ownership, correctionOffset and final body-frame/rate/local-step corrections. Donor `objects/Note.hx:96,280-323,354-420` establishes SUSTAIN_SIZE 44, constructor body stretch, pixel cap ordering, originalHeight and pixel reload offset replacement.

`source/PsychSustainLayout.hx` separates source Psych hold rules from native tap-sentinel/ceil generation and NV's rounded-plus-one layout. It preserves finite positive authored lengths, including one-step and tiny nonzero durations; counts round(length/localStep), and segment time is headTime + index*localStep. BPM changes carry across later sections. Its bodyStretchRatio and generationStretchRatio match the two source geometry stages.

`source/PlayState.hx` applies these rules only to source Psych notes without Codename ownership or an NV session. Finalization runs after source skin configuration, before the segment enters the queue and later spawn callbacks. Existing head/tail linking remains in place. Native and NV generation retain their previous duration/count/timestamp rules. The native receptor hold normalizer is bypassed by a source-only sustain2 return, so short source hold metadata survives hits.

`source/Note.hx` and `source/PsychSkinRuntime.hx` were implemented by the coordinated Note/skin owner. Source sustain construction defers offset/body/pixel-cap geometry until the final source frames exist; finalizePsychSustainSegment applies correction and stretch once. Source constructor paths bypass native 1.5 stretching. Pixel reload retains scale/animation, records originalHeight, replaces the prior pixel width offset contribution without accumulating it, and keeps failed reloads atomic. Note.SUSTAIN_SIZE remains reflected as 44.

The receptor confirmation contract is specific to pinned Psych 1.0.4: donor PlayState:3013/3086/3471 uses Conductor.stepCrochet*1.25/1000/playbackRate for autoplay. The source sustain2 branch now sets that resetAnim value; manual confirmation sets resetAnim zero and relies on the existing source key release path. StrumNote.psychSourceTiming opts source receptors into resetAnim updates. Native and NV confirmation/timer behavior is unchanged.

## Focused evidence

22 cases ran across `test_psych_sustain*.py`, `test_psych_note_follow*.py`, `test_sustain_normalization`, `test_dynamic_scroll_speed`, `test_nightmare_vision_sustain_layout` and `test_sustain_trail_alignment`: 21 passed, 1 unavailable native chart fixture skipped.

New tests include:

- `test_psych_sustain_layout`: executable pure formulas and extracted real PlayState generation expressions for zero/half/one-step holds, local BPM/count/time, carry-forward BPM, metadata preservation, alternate body/cap dimensions and rate correction; native sentinel/ceil/+step and NV count/time exclusions; source skin-finalization order checks.
- `test_psych_sustain_confirmation`: executable production sustain2, StrumNote.update and source release methods. Verifies short hold metadata, auto countdown at live BPM/rate, manual confirmation persistence/release, absence of native timers on source hits, and unchanged native/NV cases.
- Coordinated Note/skin tests verify deferred geometry, finalization once, pixel reload metadata/offset replacement, animation/scale retention and failed reload behavior.

An additional 24 focused cases ran after adding live speed propagation and repairing fixture stubs: 23 passed and 1 unavailable fixture skipped. Commands used `.tools/python/python.exe -m unittest discover -s tools/tests -p <pattern>` with test_psych_sustain*.py, test_psych_note_follow*.py, test_dynamic_scroll_speed.py, test_nightmare_vision_note_kill_offset.py, test_vslice_scroll_speed_api.py, test_codename_note_core.py and test_strumline_compat.py. The first integrated build passed; its two full-suite failures were missing source predicate/receptor fixture fields and are repaired. The final integrated gate and scoped native checks passed as recorded below.

## Import/runtime scope and remaining acceptance

Read-only importer inspection found no sustain-duration normalization in Psych authored rows: ModuleFunctions retains chart row values, while the two relevant host mutations were chart generation and sustain2. No donor, chart or mod files were edited. V-Slice hxcApplyStrumlineNoteData is explicitly guarded by its HXC surface and retains its own runtime replacement generation; it is not a Psych API path.

Native runner `tmp/test-psych-sustain-native.ps1` was syntax-validated and executed successfully at 60/unlimited FPS. It builds only a private alternate chart and private source-skin copies, expects six markers twice, checks the protected 70-file baseline plus eight donor/copy hashes, removes its temporary artifacts in finally, and requests a 35-second gameplay capture during each 50-second visit.

## Integrated and native acceptance

- Canonical Windows build passed. `tmp/psych-sustain-release-gate.log` records 2,236 tests across 726 modules in 135.1 seconds: 345 skipped, zero failed.
- Muted 60 FPS run `psych-pass-swag-messiah-5e9bcfa4` exited 0 in 140.123 seconds; receipt `tmp/psych-sustain-native-60-accepted.log`.
- Muted unlimited FPS run `psych-pass-swag-messiah-4ce54023` exited 0 in 139.286 seconds; receipt `tmp/psych-sustain-native-unlimited-accepted.log`.
- Each run passed six strict markers exactly twice: authored zero/half/one-step and local-BPM chains; real normal/pixel body/cap geometry; real pixel A-B-A reload state/offsets; source speed event with queued bodies, cap preservation and multSpeed; source auto confirmation/manual release; visible HUD proof readiness. The script-error gate found no errors. Native speed checks use the real instant event/setter roundtrip; intermediate tween updates and fixed-target semantics also have executable focused coverage.
- The protected 70-file baseline and all eight original/copied donor skin hashes remained unchanged. Private scripts, chart and copied skins were removed in finally; original charts, mods and donor assets were untouched.
- Root inspected all four accepted 60/unlimited gameplay PNGs: normal and pixel proof bodies/caps, authored gameplay and HUD rendered together correctly as a visual sanity check. These native probes use real pinned source sheets, including the future preference postfix variant. Arbitrary skin dimensions, broader pixel/nonpixel switching and exact donor screenshot comparisons remain unverified; this does not establish full visual parity.

Initial runner failures were private fixture issues: broad note windows overlapped original notes; copied skins initially used an invalid owner path; the future pixel preference-postfix variant was initially requested as a standalone key; exact note lookup initially omitted the retained 300 ms source timing offset. Final checks use disjoint exact authored timestamps plus sourceChartNoteOffset, an allowed private imported owner, and the real postfix reload API. No production changes or relaxed assertions were used to resolve those probe errors.

Live songSpeed resize propagation is implemented for active and unspawned source sustain bodies, with deduplication for transient queue overlap. It uses the effective rendered speed ratio, leaves end caps unchanged, and composes with per-note multSpeed. Source event/tween writes use the source setter; fixed dynamic scroll targets preserve authored speed without stretching bodies. Native/NV setter and tween behavior is retained. The executable test_psych_sustain_speed fixture covers these behaviors. Variable-rate transport is not implemented by formula-level rate tests. Existing source-pass snapshot mutation differences (same-frame callback additions/detachment) remain separate gaps documented in psych-note-follow-contracts.md. No full source Note/sustain parity claim is made by this implementation record.
