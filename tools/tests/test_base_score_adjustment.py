"""Script score edits go through one base function that owns the hits rule."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class BaseScoreAdjustmentTest(unittest.TestCase):
    def test_base_functions_edit_the_counter_that_owns_each_value(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = "\n".join((
            method(play, "\t@:keep public function scoreValue(field:String):Null<Int> {"),
            method(play, "\t@:keep public function adjustScore(field:String, value:Int, relative:Bool):Bool {"),
        ))
        fixture = r'''class PlayState {
 public static var misses:Int = 0;
 public static var sicks:Int = 1;
 public static var goods:Int = 2;
 public static var bads:Int = 3;
 public static var shits:Int = 4;
 public var songScore:Int = 0;
 public var songHits:Int = 0;
 public var psychHitsAdjustment:Int = 0;
 public var ledger:Bool = false;
 public var changes:Int = 0;
 public function new() {}
 public function sourceScoreLedgerActive():Bool return ledger;
 public function psychScoreChanged():Void changes++;
__METHODS__
}
class ScoreAdjustFixture {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  check(SourceScoreAdjust.apply(5, 3, true) == 8 && SourceScoreAdjust.apply(5, 3, false) == 3, 'add and set');
  check(SourceScoreAdjust.hitTotal(10, -4) == 6 && SourceScoreAdjust.hitAdjustment(6, 10) == -4, 'hits arithmetic');

  var state = new PlayState();
  check(state.adjustScore('score', 50, true) && state.adjustScore('score', 25, true), 'score is a counter');
  check(state.scoreValue('score') == 75 && state.songScore == 75, 'relative score');
  state.adjustScore('score', 10, false);
  check(state.songScore == 10, 'absolute score');
  state.adjustScore('misses', 2, true);
  state.adjustScore('misses', 3, true);
  check(PlayState.misses == 5 && state.scoreValue('misses') == 5, 'relative misses');
  state.adjustScore('misses', 1, false);
  check(PlayState.misses == 1, 'absolute misses');

  // Without the ledger the judgement counts (1+2+3+4) own the total, so the
  // edit is kept as the difference that makes the read-back come out right.
  check(state.scoreValue('hits') == 10, 'hits start at the judgement counts');
  state.adjustScore('hits', 3, true);
  check(state.scoreValue('hits') == 13 && state.psychHitsAdjustment == 3 && state.songHits == 0, 'relative hits');
  for (target in [0, 7, 10, 42]) {
   state.adjustScore('hits', target, false);
   check(state.scoreValue('hits') == target, 'set hits should read back as ' + target);
  }
  check(state.psychHitsAdjustment == 32 && state.songHits == 0, 'native set stores only the adjustment');

  // With the ledger active both edits act on its own hit counter.
  state.ledger = true;
  state.adjustScore('hits', 17, false);
  state.adjustScore('hits', 2, true);
  check(state.songHits == 19 && state.scoreValue('hits') == 19, 'ledger hits');
  check(state.psychHitsAdjustment == 32, 'ledger edits must leave the native adjustment alone');

  var before = state.changes;
  check(!state.adjustScore('combo', 4, false) && state.scoreValue('combo') == null, 'unknown counter');
  check(state.changes == before, 'a rejected edit should not announce a change');
  check(before == 13, 'each accepted edit announces exactly one change: ' + before);
  Sys.println('OK');
 }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(prefix="score-adjust-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "ScoreAdjustFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (scratch / "SourceScoreAdjust.hx").write_text(
                (ROOT / "source/SourceScoreAdjust.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "ScoreAdjustFixture"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_script_layer_only_forwards(self):
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        for name, field, relative in (("addScore", "score", "true"), ("setScore", "score", "false"),
                                      ("addMisses", "misses", "true"), ("setMisses", "misses", "false"),
                                      ("addHits", "hits", "true"), ("setHits", "hits", "false")):
            body = method(bindings, f"\tfunction {name}(")
            self.assertIn(f"host.adjustScore('{field}', value, {relative});", body)
        self.assertIn("return host.scoreValue(alias);", method(bindings, "\tfunction readScorePropertyAlias("))
        self.assertIn("return host.adjustScore(alias, number, false);",
                      method(bindings, "\tfunction writeScorePropertyAlias("))
        # The ledger choice and the counters themselves stay out of the script layer.
        self.assertNotIn("psychHitsAdjustment", bindings)
        self.assertNotIn("host.songHits", bindings)


if __name__ == "__main__":
    unittest.main()
