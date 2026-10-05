"""Psych notes follow receptor alpha without compounding or crossing modes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychNoteAlphaTest(unittest.TestCase):
    def test_receptor_alpha_copy_is_live_opt_out_and_mode_scoped(self):
        source = (ROOT / "source/Note.hx").read_text()
        self.assertRegex(source, r"@:keep public var copyAlpha:Bool = true;")
        self.assertRegex(source, r"@:keep public var multAlpha:Float = 1\.0;")
        self.assertRegex(source, r"if \(isSustainNote && prevNote != null\)\s*\{\s*noteScore \* 0\.2;\s*alpha = 0\.6;\s*multAlpha = 0\.6;")
        method = extract_method(source, "public function applyPsychReceptorAlpha(")

        fixture = f'''class NoteAlpha {{
 public var sourceTimingMode:Int=1;
 public var codenameInputLine:Dynamic=null;
 public var copyAlpha:Bool=true;
 public var multAlpha:Float=1.0;
 public var alpha:Float=1.0;
 public function new() {{}}
 {method}
}}
class Main {{
 static function check(actual:Float,expected:Float,message:String):Void {{
  if (Math.abs(actual-expected)>0.00001) throw message+": "+actual;
 }}
 static function main():Void {{
  var note=new NoteAlpha();
  note.applyPsychReceptorAlpha(0);
  check(note.alpha,0,"hidden receptor did not hide chart note");
  note.applyPsychReceptorAlpha(0.25);
  check(note.alpha,0.25,"partial receptor alpha did not copy");
  note.applyPsychReceptorAlpha(1);
  check(note.alpha,1,"restored receptor did not restore chart note");

  var sustain=new NoteAlpha(); sustain.alpha=0.6; sustain.multAlpha=0.6;
  sustain.applyPsychReceptorAlpha(0);
  check(sustain.alpha,0,"hidden receptor did not hide sustain");
  sustain.applyPsychReceptorAlpha(0.8);
  check(sustain.alpha,0.48,"sustain multiplier was not applied from source alpha");
  sustain.applyPsychReceptorAlpha(0.5);
  check(sustain.alpha,0.3,"sustain multiplier compounded across frames");

  note.alpha=0.37; note.copyAlpha=false;
  note.applyPsychReceptorAlpha(0);
  check(note.alpha,0.37,"copyAlpha=false overwrote a script-set note alpha");
  note.copyAlpha=true; note.applyPsychReceptorAlpha(0.5);
  check(note.alpha,0.5,"copyAlpha could not be re-enabled");

  note.sourceTimingMode=0; note.alpha=0.22;
  note.applyPsychReceptorAlpha(0);
  check(note.alpha,0.22,"base note alpha was changed");
  note.sourceTimingMode=2; note.alpha=0.43;
  note.applyPsychReceptorAlpha(0);
  check(note.alpha,0.43,"Nightmare Vision note alpha was changed");
  note.sourceTimingMode=1; note.codenameInputLine={{}}; note.alpha=0.56;
  note.applyPsychReceptorAlpha(0);
  check(note.alpha,0.56,"Codename note alpha was changed");
 }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
