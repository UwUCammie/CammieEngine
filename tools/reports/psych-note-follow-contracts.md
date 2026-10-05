# Psych receptor follow integration - scoped contract verification complete

Reference: `../fnf_sources/FNF-PsychEngine`, revision `5c67ced49e5a98535298a6daa3f8f4ec79ac8399` (pinned Psych 1.0.4). Donor contracts are `source/objects/Note.hx` (`followStrumNote`, `clipToStrumNote`, constructor and `reloadNote`) and `source/states/PlayState.hx` (sustain generation, live note loop, songSpeed setter).

## Implemented scope

Source Psych notes (`sourceTimingMode == 1`, no Codename input line, no NV session) use receptor direction/downScroll, independent copyX/copyY/copyAngle, offsets, multSpeed, correctionOffset, clipping and publicly reflected signed distance. Native Y travel, snap X/angle, and spatial lifetime/visibility passes bypass this route. Host line speed overrides and selected speed/drunk/snake/vanish modifiers retain their effect while independent source copy flags keep ownership of script-controlled properties.

Generated source sustains receive the donor head-height correction (zero for nonpixel global downscroll). Psych retirement uses the donor time threshold and preserves host auto/ignore/dontCount/ending miss gates. Due automatic hits run before retirement, including accepted-sustain early returns. NV and Codename retain their existing routes. StrumNote already exposed sustainReduce; it was not added again.

Focused evidence: `python -m unittest discover -s tools/tests -p test_psych_note_follow*.py` passed 7 tests after integration review. A further 5 affected tests pass (`test_dynamic_scroll_speed`, `test_nightmare_vision_note_kill_offset`, `test_codename_snap_geometry`, `test_psych_note_alpha`), for 12 focused checks total. After native investigation, `test_psych_note_iteration` adds one passing executable check, for 13 focused checks total. Probes exercise follow/copy flags, multSpeed, clipping, resolved receptor parameters, native/NV/Codename exclusions, sustain correction, exact time threshold, offscreen/onscreen retirement, and source miss suppression. These tests establish focused behavior, not full source Note parity.

## Native investigation and iteration stabilization

The first 60 FPS runner completed both visits and all six markers twice, but failed its strict script-error gate: sporadic ordinary-Y mismatches were approximately one frame of travel. The pinned Flixel `forEachAlive` directly iterates `members`; host hit/retirement removal splices that same array, so removing the current note skips its following neighbor until the next frame. An executable probe reproduces that behavior and verifies the engine correction.

The source Psych live pass now reuses one scratch array containing its entry set. It updates each surviving entry once and skips entries destroyed by earlier callbacks, so adjacent retirement/hit removal cannot omit their surviving neighbor. Storage is reused and references are cleared after the pass. Native/NV retain existing iteration. **Mutation difference retained:** a note inserted during a hit callback enters the next host pass; donor live-index iteration can process such additions immediately. A script that detaches a still-alive Note without killing it can leave that object in the entry-set pass once; engine hit/retirement paths kill before removal. These are bounded stabilization semantics, not a claim of exact callback-mutation parity.

The native geometry assertions and 0.05 tolerance remained unchanged. Final canonical and native reruns of the stabilized source pass passed; receipts follow.

## Final acceptance evidence

Scoped receptor-follow, alpha, clipping integration, time retirement and neighboring-note iteration verification passed against the final integrated files. This status does not establish complete source Note/sustain visual parity.

- Canonical Windows build succeeded. `tmp/psych-follow-underlay-tests-verified.log` records 2,226 tests across 721 modules in 130.8 seconds: 345 skipped, 0 failed. Skips remain unverified coverage, not passing donor evidence.
- `tmp/psych-follow-native-60-verified.log`: run `psych-pass-swag-messiah-8883983e`, exit 0, 94.204 seconds, 60 FPS, two visits.
- `tmp/psych-follow-native-unlimited-verified.log`: run `psych-pass-swag-messiah-926d7e01`, exit 0, 88.407 seconds, unlimited FPS, two visits.
- Both muted private-fixture native runs passed the strict script-error gate and all six markers exactly twice: ordinary tap geometry; ordinary sustain geometry; manual axes and spatial lifetime; independent flags and offset recovery; time retirement; hitch opponent hit before retirement. The protected baseline remained unchanged at 70 files in both runs.
- Runner `tmp/test-psych-note-follow-native.ps1` removes its private probe in finally and verifies the protected baseline before/after. Formula tolerance remained 0.05; the initial runtime iteration failure was repaired in the engine rather than relaxed in the probe.
- Primary agent inspected the 60 FPS second-visit introductory screenshot: authored hidden HUD and visible source actors were correct. A later gameplay capture showing visible sustains and a pinned-donor visual comparison remain outstanding. Numerical geometry checks alone cannot establish skin-dependent sustain alignment or complete visual parity.
- Review repair is included in this verified build: receptor-alpha copying runs before hit callbacks and accepted-sustain early returns; copyAlpha and the host vanish preference remain effective; no late duplicate overwrites callback alpha mutations.

## Broader Note parity gaps retained for follow-up

The subsequent sustain package now implements and verifies the first three items below within its scoped canonical/native checkpoint. See `psych-sustain-contracts.md`; the earlier successful follow checkpoint receipts do not verify these newer geometry/generation changes.

1. Pixel sustain reload offsets: donor `reloadNote` tracks `_lastNoteOffX`, restores the prior contribution and recalculates `(width - 7) * (daPixelZoom / 2)` when loading pixel ENDS. Host skin reload has no matching source offset bookkeeping. Constructor +30 alone does not prove reload alignment.
2. Sustain stretch: host Note constructor keeps its native `stepCrochet / 100 * 1.5 * effectiveScrollSpeed` previous-piece stretch. Donor uses `1.05 * songSpeed`, pixel `1.19`/height correction, and PlayState generation applies SUSTAIN_SIZE/frameHeight and playbackRate/local-step corrections. Those transformations are not implemented by this follow-route integration; multSpeed ratio resizing is only one portion of the contract.
3. Sustain segment placement/count: host normalized native generation uses ceil steps and first piece at head + one step; pinned donor rounds local-BPM hold steps and starts the piece sequence at spawnTime. Source-specific generation parity remains open.
4. General arbitrary skin/frame size and pixel/nonpixel switching require native comparison and regression fixtures. This package must not be recorded as complete source Note/sustain visual parity.

No donor/chart/mod content was edited. This receptor-follow integration has passed its scoped canonical/native checks; the broader gaps and visible-sustain/donor comparison remain open.

Final-build visible gameplay review: `tmp/psych-follow-gameplay-visual.log` records muted 60 FPS run `psych-pass-swag-messiah-da1fc110`, exit 0 in 69.920 seconds. Root inspected its 35-second-song-position PNG: ordinary notes, a visible sustain, actors and restored HUD render together; no script errors were detected, and the 70 protected hashes were rechecked unchanged. This visual sanity check does not establish exact donor sustain length/cap alignment; the source-generation gaps above remain open.
