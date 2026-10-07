# Psych automatic note animation suppression

This development 0.0.16 correction honors the existing per-note noAnimation flag on automatic successful hits. It uses shared engine behavior and contains no song, mod, character-name or note-type-name branch.

## Evidence and scope

The immutable Shadow Wizard custom note scripts under `../fnf_example_mods/psych/shadow_wizard_money_gang_we_love_casting_spells/Shadow Wizard Money Gang, We Love Casting Spells/custom_notetypes/` set matching unspawnNotes.noAnimation to true: Green-Wiz Sing uses onCreatePost, while Yellow-Wiz Sing uses onCreate. The original successful-hit script then animates its extra actor from opponentNoteHit. No original script or chart was edited.

The retained Psych source `../fnf_sources/FNF-PsychEngine/source/states/PlayState.hx`, opponentNoteHit, gates its ordinary default-character animation with `else if(!note.noAnimation)`. Receptor/vocal effects and stage/Lua/HScript post-hit callbacks occur afterward, outside that gate. The host Note already owns writable noAnimation and noMissAnimation Bool fields; its existing allowsAnimation method reads the corresponding flag. The ordinary goodNoteHit route already uses this method.

The host update's separate automatic opponent and player singing blocks tested only the legacy aiShouldHit/shouldBeSung disjunction. They could therefore animate the default actor and reset its holdTimer even when an authored custom note script had suppressed animation. The generic custom-actor callback subsequently ran as well, producing both actors' singing.

## Change and focused verification

Only those two automatic singing conditions now additionally require daNote.allowsAnimation(). The legacy aiShouldHit/shouldBeSung distinction remains unchanged. Animation, associated native crossfade and default holdTimer reset stay inside the guard. Hit callbacks, receptors, vocals, judgement and head/sustain lifetime remain outside it. There is no global exclusive-speaker state, forced idle, or importer/content rewrite.

`test_psych_auto_note_animation.py` compiles the actual extracted opponent and player automatic-hit blocks, actual Note.allowsAnimation and actual numeric-loop helper. A translated generic Lua custom type writes the live Bool through group properties, and the real PsychNoteCallbacks helper invokes a translated custom-actor callback. Its 32-case matrix covers both sides, heads/sustains, both legacy sing-request values, forced AI, and suppression enabled/disabled. It asserts that the default actor's sing request, holdTimer reset and crossfade respect the flag, while the custom actor callback, receptor/vocal effects and source note retirement remain intact. A retained-donor check pins the post callback outside the source animation gate.

The focused automatic-note-animation, existing note-animation-flags and shared note-callback modules passed seven cases in 1.072 seconds, with no skips or failures. These are executable extracted-route tests rather than a simulation of full asset rendering. Existing tests retain independent hit/miss flags and typed native callback payload evidence.

## Acceptance boundary

The canonical Windows build passed (`tmp/source-exclusive-popup-draw-build.log`), executable SHA256 4F92060611BC3732068E5F2B949749915BFBCD479B182652EB95CA8C4111213B. Muted, strict opening checks passed at 60 FPS (`shadow-speaker-7aeff95c`,49.493 seconds) and unlimited (`shadow-speaker-ee6509c8`,48.822 seconds), with both reviewed framebuffer captures. Both observed 217 live custom notes carrying the suppression flag, correct alternate directional animations/icons/subtitles, and purple idle in green and yellow custom-only passages. Seventy protected inputs and the current user options snapshot remained unchanged; the older options baseline differed from user changes before this build. Twenty-five retained private inputs and immutable originals were checked/restored by each runner.

Failed private checks remain recorded: a fixed 450ms deadline preceded the previous ordinary note's authored 6.1-step hold expiry; a second attempt read a legacy native holdTime rather than that retained metadata. Final probe timing derives from the unchanged donor BPM and sing_duration plus 100ms margin. The production engine does not force idle, change holds or inspect song/character IDs to enforce exclusivity.

The integrated suite passed 2,327 cases/764 modules in 160.3 seconds, with 344 existing platform/corpus skips and zero failures; required donor audit and 23 policy checks passed. Receipt: `tmp/source-exclusive-popup-checkpoint.json`. The fixtures do not claim full custom-note loader lifecycle, all source note-type behavior or whole Character parity. Native, Psych and other engines retain their existing per-note flag semantics; this patch only connects the previously missing checks in the two shared automatic singing routes.
