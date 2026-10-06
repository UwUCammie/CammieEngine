# Nightmare Vision NoteSplash field integration

Development 0.0.15. Pinned donor `733165c42ca71eb0961a70e4173b2d81ba4a29ea`: PlayField constructor, hit caller at 418-427, public spawnSplash at 555-579, changeSkin alive effect updates, PlayState tracked effect pass, and Note reset/pointers. No donor, chart, mod or asset edits. Integrated acceptance is recorded below.

Source field tap groups now contain actual NightmareVisionNoteSplash instances, including the inert alpha-zero constructor seed whose fourth argument is the source field.player (unlike the sustain seed fixed at zero). Public grpNoteSplashes remains writable, and changing that pointer does not rewrite the existing layer child or captured display reference. Internally owned original layer cleanup and borrowed replacement ownership remain as established by the sustain package. Native, Psych and Codename generic pools retain their existing paths.

Public field.spawnSplash delegates to the owner implementation. It uses only donor preference, nonnull note, hazard/sustain/disabled flags, field.noteSplashes and the nullable skin-enabled expression. The complete pinned method is compiled alongside the host method; null skin passes the enabled default and subsequently fails on source texture access. Null notes short-circuit. No host global splash option, line showNotesplash, absolute direction normalization or rating requirement is added to this public method. Direction indexes the note's own field through typed members access, independently from the spawning field. This preserves the previous C++ getter correction and supports wider banks.

The actual pinned Flixel recycle/add methods prove retained sprite alpha, revive and no duplicate membership. Setup uses the spawning field's skin texture, real note RGB and field metadata. The onSpawnNoteSplash callback sees group membership before the new note.noteSplash pointer is assigned. Source NOTE fields noteSplash and sustainSplash remain independent from shared tailState.splash; fresh NV reset clears the tap pointer. The separate source noteSplashDisabled Bool starts false on construction but is preserved by donor _reset, so this reset likewise leaves the authored flag untouched. The Psych noteSplashData table remains separate.

The successful-hit caller owns rating gating: field.noteSplashes admits opponent/automatic field hits regardless of rating, while playerControls requires ratingMod >= 1 after judging. The public direct method permits low-rating notes. Accepted tap publication precedes sustain spawning and note-type/general hit callbacks through the existing hit pipeline.

Gameplay bindings expose actual NoteSplash class identity for bare and fully qualified imports, with the four source constructor arguments and owner factory injected as the fifth host argument. An actual Iris probe executes the extracted PlayState binding against a minimal constructor shape to verify defaults, arguments and current owner identity; the sprite owner's full-class donor comparisons separately establish actual sprite semantics. Arbitrary scripted subclasses remain a separate interpreter contract.

Alive current public tap-group members receive changeSkin scale/baseScale and coloring-enabled changes without texture reload, alpha reset or selected skin replacement. trackNoteSplashes gates only the modchart pass; false keeps the source setup's receptor-centered placement. The manager identifies the real type as noteSplash. PlayState applies its actual RGB state and returns before generic offset addition, because the dedicated sprite owns animation/sprite offsets. The shared sprite helper is a narrow verified extraction, not a complete inherited FunkinSprite API claim.

## Focused verification

Commands: `.tools/python/python.exe tools/run_tests.py --pattern <module> --jobs 1`.

- test_nv_note_splash_field.py: 3 passed in 1.2s, no skips. Complete pinned public spawn expression and actual field hook/hit caller, real Flixel recycle/add, note-owned getter/wider directions, preference and flag matrix, null note/receptor/skin behavior, low-rating direct calls, callback publication and retained alpha. Static C++ generation asserts typed get_members rather than dynamic lookup. Actual Iris constructor/import binding and owner identity. Extracted alive current-group skin update executes and generates C++ with nonnullable Float scales.
- test_nv_sustain_splash_field.py: 3 passed, 0.6s, no skips; fixture seed type updated, existing source pool/layer/ownership and static C++ checks retained.
- test_note_rating_shape.py: 1 passed, 0.2s; independent tap pointer/disabled flag reset coverage.
- test_nv_hit_order.py: 3 passed, 0.4s.
- test_nightmare_vision_note_skin_runtime.py: 1 passed, 0.7s.
- test_nv_receptor_generation_lifecycle.py: 5 passed, 0.5s.
- test_nv_field_mutation_contract.py: 2 passed, 0.4s.
- test_nightmare_vision_playfield_contract.py: 2 passed, 0.2s.

Owner total: 20 passed across 8 modules, zero skips/failures. C++ focused checks use no-compilation generation only. Sprite/helper/source atlas comparison evidence is recorded separately in nv-note-splash-contracts.md. Full global stack, broader Note reset/NoteUtil APIs, arbitrary skin visual parity and Psych splash config/copy semantics remain separate gaps.

## Integrated acceptance

Accepted bounded NoteSplash checkpoint, development 0.0.15. Canonical Windows build passed (`tmp/nv-tap-build.log`). The full eight-worker suite passed 2,268 tests across 738 modules in 179.0 seconds, with 345 reported platform/corpus skips and zero failures (`tmp/nv-tap-full-tests.log`). Existing compiler PATH was supplied so compiler-dependent fixtures ran.

Muted native checks passed two visits at 60 FPS (psych-pass-darnell--nightmare-vision-54e1fc6dd6-1db0a8fd, 141.176 seconds) and unlimited FPS (psych-pass-darnell--nightmare-vision-54e1fc6dd6-003d5dd8, 143.675 seconds). All four markers appeared twice: actual hit/public spawn and atlas frames, callback-before-pointer publication, animation retirement and pool reuse. Root inspected all four gameplay captures, including normal and pixel reference effects. The normal effect uses the retained imported atlas; pixel references use immutable private donor copies. Frozen references establish frame rendering, not complete live modifier/global draw-stack parity. The first probe incorrectly wrote read-only ratingMod; correcting only the probe to rating.ratingMod made the source-shaped check pass.

A further two-visit 60 FPS SustainSplash native regression (psych-pass-darnell--nightmare-vision-54e1fc6dd6-39d71f9f, 141.052 seconds) passed all four hold lifecycle markers twice after shared helper extraction, with both captures reviewed. Every run preserved seventy protected files and removed temporary probes. Donor source checkouts remained clean. Executable SHA256: `CF5E9D804424E8339C2AC8A64DC9C79E5C34E2BFE732B8A90CA204B52B6A1821`. Receipt: `tmp/nv-tap-checkpoint.json`.

Phase 2 remains unfinished. Next proposed shared package is the actual Psych/NV three-sprite Bar API and HUD identity (`tmp/source-bar-next-proposal.md`). Broader inherited sprite/Note APIs, full quad skew/global draw stack and Psych-specific splash behavior remain open. No donor/mod/chart modifications or release publication.
