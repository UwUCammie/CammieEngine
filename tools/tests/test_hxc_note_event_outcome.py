"""Note events show the real judgement numbers and take script changes back."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

NOTE_KIND = '''
class HeavyNote extends ScriptedNoteKind {
    function new() { super("heavy", "Heavy note"); }
    override function onNoteHit(event) {
        event.healthChange = -0.1;
        event.doesNotesplash = false;
        event.isComboBreak = true;
        event.score = event.score + 50;
    }
    override function onNoteMiss(event) {
        event.healthChange = event.healthChange * 2;
        event.playSound = false;
    }
    override function onNoteGhostMiss(event) {
        event.playAnim = false;
        event.playSound = false;
        event.scoreChange = 0;
        event.healthChange = Constants.HEALTH_MISS_PENALTY * -0.5;
    }
}
'''


class HxcNoteEventOutcomeTest(unittest.TestCase):
    def run_fixture(self, body):
        fixture = f'''import hscript.Interp;
import hscript.Parser;
class NoteOutcomeFixture {{
    static function fail(message:String):Void throw message;
    static function near(a:Float, b:Float):Bool return Math.abs(a - b) < 0.000001;
    static function main() {{
        var note:Dynamic = {{strumTime: 1000.0, noteData: 2, rating: "sick", isSustainNote: false,
            mustPress: true, alive: true}};
        {body}
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "NoteOutcomeFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "NoteOutcomeFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_untouched_event_reads_real_numbers_and_changes_nothing(self):
        self.run_fixture('''
        var outcome = NoteJudgementOutcome.hit(0.023, 350, "sick", false, true, -12.5, 41);
        var payload = EngineCompat.hxcNoteCallbackPayload([true, note, false], "noteHit");
        if (payload.healthChange != 0) fail("an event without an outcome keeps the old placeholder");
        EngineCompat.hxcSeedNoteOutcome(payload, outcome);
        if (!near(payload.healthChange, 0.023) || payload.score != 350 || payload.judgement != "sick"
            || payload.isComboBreak != false || payload.doesNotesplash != true
            || !near(payload.hitDiff, -12.5) || payload.comboCount != 41)
            fail("seeded fields");
        EngineCompat.hxcApplyNoteOutcome(payload, outcome);
        if (outcome.anyChanged()) fail("reading an event must not change the outcome");
        if (!near(outcome.healthChange, 0.023) || outcome.score != 350) fail("values drifted");
        // No outcome at all is fine too.
        EngineCompat.hxcSeedNoteOutcome(payload, null);
        EngineCompat.hxcApplyNoteOutcome(payload, null);
        EngineCompat.hxcApplyNoteOutcome(null, outcome);
        ''')

    def test_translated_note_kind_writes_reach_the_outcome(self):
        self.run_fixture(f'''
        var result = HxcCompat.analyze({json.dumps(NOTE_KIND)}, "scripts/notes/heavy.hxc");
        for (name in ["noteHit", "noteMiss", "noteGhostMiss"])
            if (result.canonicalCallbacks.indexOf(name) < 0) fail("callback not routed: " + name);
        for (finding in (cast result.diagnostics:Array<Dynamic>))
            if (finding.code == "unsupported-hxc-payload-field" || finding.code == "unsupported-hxc-api")
                fail("outcome field diagnosed: " + finding.message);
        var interp = new Interp();
        interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
        interp.variables.set("hxcAssetRoot", "assets");
        interp.execute(new Parser().parseString(result.generatedHscript));
        function call(name:String, payload:Dynamic):Void
            Reflect.callMethod(null, interp.variables.get(name), [payload]);

        var hit = NoteJudgementOutcome.hit(0.023, 350, "sick", false, true, 4.0, 10);
        var hitEvent = EngineCompat.hxcNoteCallbackPayload([true, note, false], "noteHit");
        EngineCompat.hxcSeedNoteOutcome(hitEvent, hit);
        call("noteHit", hitEvent);
        EngineCompat.hxcApplyNoteOutcome(hitEvent, hit);
        if (!hit.healthChanged() || !near(hit.healthChange, -0.1)) fail("hit health write");
        if (!hit.notesplashChanged() || hit.doesNotesplash) fail("hit splash write");
        if (!hit.comboBreakChanged() || !hit.isComboBreak) fail("hit combo break write");
        if (!hit.scoreChanged() || hit.score != 400 || hit.scoreDelta() != 50) fail("hit score write");
        if (hit.judgementChanged()) fail("judgement was not written");

        var miss = NoteJudgementOutcome.miss(-0.04, -5, true, true, 10);
        var missEvent = EngineCompat.hxcNoteCallbackPayload([note, true, 2], "noteMiss");
        EngineCompat.hxcSeedNoteOutcome(missEvent, miss);
        call("noteMiss", missEvent);
        EngineCompat.hxcApplyNoteOutcome(missEvent, miss);
        if (!near(miss.healthChange, -0.08) || miss.playSound || miss.scoreChanged() || !miss.isComboBreak)
            fail("miss writes");

        var ghost = NoteJudgementOutcome.miss(-0.04, -5, true, true, 0);
        var ghostEvent = EngineCompat.hxcNoteCallbackPayload([null, true, 3], "noteGhostMiss");
        EngineCompat.hxcSeedNoteOutcome(ghostEvent, ghost);
        if (ghostEvent.scoreChange != -5 || ghostEvent.playAnim != true) fail("ghost seed");
        call("noteGhostMiss", ghostEvent);
        EngineCompat.hxcApplyNoteOutcome(ghostEvent, ghost);
        if (ghost.playAnim || ghost.playSound) fail("ghost animation and sound round trip");
        if (!ghost.scoreChanged() || ghost.score != 0) fail("ghost scoreChange spelling");
        if (!near(ghost.healthChange, -0.02)) fail("ghost health from the constants table");
        ''')

    def test_wrong_typed_writes_are_refused(self):
        self.run_fixture('''
        var outcome = NoteJudgementOutcome.hit(0.023, 350, "good", false, false, 0, 3);
        var payload:Dynamic = EngineCompat.hxcNoteCallbackPayload([true, note, false], "noteHit");
        EngineCompat.hxcSeedNoteOutcome(payload, outcome);
        payload.healthChange = "lots";
        payload.score = Math.NaN;
        payload.scoreChange = "more";
        payload.isComboBreak = 1;
        payload.doesNotesplash = "yes";
        payload.playSound = null;
        payload.judgement = "legendary";
        EngineCompat.hxcApplyNoteOutcome(payload, outcome);
        if (outcome.anyChanged()) fail("a wrong-typed write changed the outcome");
        payload.healthChange = Math.POSITIVE_INFINITY;
        EngineCompat.hxcApplyNoteOutcome(payload, outcome);
        if (outcome.healthChanged()) fail("a non-finite health was accepted");
        // A real rating name is taken, in any case, and the bot-only name maps down.
        payload.healthChange = 0.023;
        payload.judgement = "Sick";
        EngineCompat.hxcApplyNoteOutcome(payload, outcome);
        if (!outcome.judgementChanged() || outcome.judgement != "sick") fail("rating rename");
        if (NoteJudgementOutcome.acceptedJudgement("perfect") != "sick"
            || NoteJudgementOutcome.acceptedJudgement("miss") != null)
            fail("accepted rating names");
        ''')

    def test_constants_facade_quotes_the_game_table(self):
        self.run_fixture('''
        var constants = HxcCompatRuntime.constantsForRoot("assets");
        if (constants.HEALTH_MAX != GameplayConstants.HEALTH_MAX || constants.HEALTH_MAX != 2
            || constants.HEALTH_MIN != 0 || constants.HEALTH_STARTING != 1)
            fail("health bounds");
        if (!near(constants.HEALTH_MISS_PENALTY, GameplayConstants.HEALTH_MISS_PENALTY)
            || !near(constants.HEALTH_GHOST_MISS_PENALTY, 0.04)
            || !near(constants.HEALTH_SICK_BONUS, 0.07))
            fail("health amounts");
        if (constants.MS_PER_SEC != 1000 || constants.STEPS_PER_BEAT != 4) fail("timing constants");
        ''')

    def test_playstate_applies_the_outcome_on_the_native_judgement_only(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        wanted = source[source.index("function noteOutcomeWanted("):
            source.index("function proposeHitOutcome(")]
        self.assertIn("!sourceScoreLedgerActive()", wanted)
        # Every script has an entry in the table, so "any entry" would turn
        # outcomes on for songs with no event-object script at all.
        self.assertIn("hasEventObjectScope()", wanted)
        self.assertNotIn("hxcPayloadStates.iterator().hasNext()", source)
        scope = source[source.index("function hasEventObjectScope("):
            source.index("function proposeHitOutcome(")]
        self.assertIn("for (wanted in hxcPayloadStates)", scope)
        self.assertIn("if (wanted)", scope)

        hit = source[source.index("function goodNoteHit("):source.index("function dispatchHitCausesMiss(")]
        seeded = hit.index("EngineCompat.hxcSeedNoteOutcome(hxcHitEvent, hitOutcome);")
        dispatched = hit.index('callHxcNoteHScript("noteHit"')
        read_back = hit.index("EngineCompat.hxcApplyNoteOutcome(hxcHitEvent, hitOutcome);")
        scored = hit.index("popUpScore(note.strumTime, note, playerOne);")
        applied = hit.index("applyHitOutcomeChanges(note, playerOne, hitOutcome);")
        self.assertLess(seeded, dispatched)
        self.assertLess(dispatched, read_back)
        self.assertLess(read_back, scored)
        self.assertLess(scored, applied)
        self.assertIn("hitOutcome.comboBreakChanged()", hit)

        apply = source[source.index("function applyHitOutcomeChanges("):source.index("function shouldShowNoteSplash(")]
        self.assertIn("if (outcome == null || !outcome.anyChanged())", apply)
        # A hit re-rated to the top rating is splashed by the popup, not twice.
        self.assertIn("&& (note.rating != 'sick' || note.mineNote))", apply)

        miss = source[source.index("function noteMissCore("):source.index("function badNoteCheck(")]
        for line in [
            "EngineCompat.hxcSeedNoteOutcome(hxcGhostEvent, missOutcome);",
            "EngineCompat.hxcApplyNoteOutcome(hxcGhostEvent, missOutcome);",
            "if (EngineCompat.hxcPayloadCanceled(hxcGhostEvent))",
            "EngineCompat.hxcApplyNoteOutcome(hxcMissEvent, missOutcome);",
            "if (missOutcome != null && missOutcome.healthChanged()) healthBonus = missOutcome.healthChange;",
            "if (countsMiss && (missOutcome == null || missOutcome.isComboBreak)) combo = 0;",
            "if (missOutcome != null) playMissSound = missOutcome.playSound;",
            "(missOutcome == null || missOutcome.playAnim)",
        ]:
            self.assertIn(line, miss)


if __name__ == "__main__":
    unittest.main()
