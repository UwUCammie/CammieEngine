"""Note.getHealth takes its default amounts from GameplayConstants.

The table is what the game quotes to scripts, so the native judgement and the
table must give the same numbers for an ordinary note.
"""
from haxe_test_support import HAXE_COMMAND

import os
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
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
    raise AssertionError(f"unterminated method: {marker}")


FIXTURE = '''
class OptionsHandler {
  public static var options = {useKadeHealth: false};
}
class PlayState {
  public static var healthGainMultiplier:Float = 1;
  public static var healthLossMultiplier:Float = 1;
}
class NoteHealthTableFixture {
  public var mineNote = false;
  public var nukeNote = false;
  public var consistentHealth = false;
  public var healCutoff:Null<String> = null;
  public var damageAmount:Null<Float> = null;
  public var healAmount:Null<Float> = null;
  public var damageMultiplier:Float = 1;
  public var healMultiplier:Float = 1;
  public var ignoreHealthMods = false;
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  public function new() {}
__METHOD__
  static function near(a:Float, b:Float):Bool return Math.abs(a - b) < 0.000001;
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function main():Void {
    var note = new NoteHealthTableFixture();
    // Default cutoff: the signed bonuses scripts are given.
    check(near(note.getHealth('sick'), GameplayConstants.HEALTH_SICK_BONUS), 'sick');
    check(near(note.getHealth('good'), GameplayConstants.HEALTH_GOOD_BONUS), 'good');
    check(near(note.getHealth('bad'), GameplayConstants.HEALTH_BAD_BONUS), 'bad');
    check(near(note.getHealth('shit'), GameplayConstants.HEALTH_SHIT_BONUS), 'shit');
    check(near(note.getHealth('miss'), -GameplayConstants.HEALTH_MISS_PENALTY), 'miss');
    // The values themselves are unchanged from the old literals.
    check(near(note.getHealth('sick'), 0.07) && near(note.getHealth('good'), 0.03)
      && near(note.getHealth('bad'), -0.03) && near(note.getHealth('shit'), -0.06)
      && near(note.getHealth('miss'), -0.04), 'default amounts moved');
    // A bad hit loses health at the default cutoff, so the table's bonus is negative.
    check(GameplayConstants.HEALTH_BAD_BONUS < 0, 'bad bonus sign');
    // The cutoff still picks the sign of each amount.
    note.healCutoff = 'shit';
    check(near(note.getHealth('bad'), GameplayConstants.HEALTH_BAD_AMOUNT), 'shit cutoff heals bad');
    note.healCutoff = 'sick';
    check(near(note.getHealth('sick'), -GameplayConstants.HEALTH_SICK_AMOUNT), 'sick cutoff hurts sick');
    note.healCutoff = null;
    // Kade amounts.
    OptionsHandler.options.useKadeHealth = true;
    check(near(note.getHealth('sick'), 0.1) && near(note.getHealth('good'), 0.04)
      && near(note.getHealth('bad'), -0.06) && near(note.getHealth('shit'), -0.2), 'kade amounts');
    check(near(note.getHealth('sick'), GameplayConstants.KADE_HEALTH_SICK_AMOUNT), 'kade sick from table');
    OptionsHandler.options.useKadeHealth = false;
    // Consistent health steps scale with the type multipliers.
    note.consistentHealth = true;
    note.damageMultiplier = 2;
    note.healMultiplier = 3;
    check(near(note.getHealth('miss'), -2 * GameplayConstants.HEALTH_CONSISTENT_STEP), 'consistent loss');
    check(near(note.getHealth('sick'), 3 * GameplayConstants.HEALTH_CONSISTENT_STEP), 'consistent gain');
    note.consistentHealth = false;
    // Mines and nukes hurt only when hit.
    note.mineNote = true;
    check(near(note.getHealth('sick'), -0.45) && note.getHealth('miss') == 0, 'mine');
    note.mineNote = false;
    note.nukeNote = true;
    check(note.getHealth('good') == -GameplayConstants.HEALTH_NUKE_PENALTY && note.getHealth('miss') == 0, 'nuke');
    check(-GameplayConstants.HEALTH_NUKE_PENALTY < -GameplayConstants.HEALTH_MAX, 'nuke always kills');
    Sys.println('ok');
  }
}
'''


class NoteHealthTableTest(unittest.TestCase):
    def test_get_health_reads_the_shared_table(self):
        note_source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        method = extract_method(note_source, "public function getHealth(")
        # No per-rating literal is left in the judgement itself.
        for literal in ("0.07", "0.06", "0.03", "0.04", "0.45", "-69"):
            self.assertNotIn(literal, method, literal)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "NoteHealthTableFixture.hx").write_text(
                FIXTURE.replace("__METHOD__", method), newline="\n")
            Path(folder, "GameplayConstants.hx").write_text(
                (ROOT / "source/GameplayConstants.hx").read_text(encoding="utf-8"), newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "NoteHealthTableFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
