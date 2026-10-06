"""Note exposes Psych/native rating scalars and live NMV descriptors."""
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


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


class NoteRatingShapeTest(unittest.TestCase):
    def test_rating_fields_and_runtime_descriptor_contract(self):
        source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "function get_ratingMod(",
                "function set_ratingMod(",
                "public function resetSourceRatingState(",
            )
        )
        self.assertIn("public var rating:Dynamic = \"miss\";", source)
        self.assertIn("public var ratingDisabled:Bool = false;", source)
        self.assertIn("ratingDisabled = prevNote.ratingDisabled;", source)

        fixture = '''
class NoteRatingShapeProbe {
  public var nightmareVisionTypeRuntime:Dynamic;
  public var sourceTimingMode:Int = 0;
  public var garbage:Bool = false;
  public var sustainSplash:Dynamic;
  public var noteSplash:Dynamic;
  public var noteSplashDisabled:Bool;
  public var parent:Dynamic;
  public var nightmareVisionTailState:Dynamic;
  public var rating:Dynamic = "miss";
  public var ratingDisabled:Bool = false;
  public var dontCountNote:Bool = false;
  var storedRatingMod:Float = 0;
  public var ratingMod(get, set):Float;
  public function new() {}
__METHODS__
}

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;

  static function main():Void {
    var note = new NoteRatingShapeProbe();
    check(note.rating == "miss" && !note.ratingDisabled && note.ratingMod == 0,
      "native/Psych defaults should be a miss string, enabled rating, and mod zero");
    note.ratingDisabled = true;
    check(!note.dontCountNote && note.ratingDisabled,
      "ratingDisabled must remain independent from dontCountNote");
    note.ratingMod = 0.42;
    check(note.ratingMod == 0.42, "native/Psych ratingMod should store a scalar");

    note.rating = "good";
    note.resetSourceRatingState();
    check(note.rating == "miss" && !note.ratingDisabled && note.ratingMod == 0,
      "native reset should restore the donor defaults");

    note.nightmareVisionTypeRuntime = {};
    note.sourceTimingMode = 2;
    note.garbage = true;
    note.rating = new SourceRating("good");
    check(note.ratingMod == 0.7, "NMV ratingMod should reflect the live descriptor");
    note.rating.ratingMod = 0.25;
    check(note.ratingMod == 0.25, "NMV ratingMod should observe descriptor mutations");
    note.rating.ratingMod = 9;
    check(note.ratingMod == -1, "the source sentinel ratingMod 9 should normalize to -1");

    note.ratingDisabled = true;
    note.sustainSplash = {}; note.noteSplash={}; note.noteSplashDisabled=true; note.nightmareVisionTailState = {splash:{}};
    note.resetSourceRatingState();
    check(note.sustainSplash == null && note.noteSplash == null && note.noteSplashDisabled && note.nightmareVisionTailState.splash == null, "independent fresh source splash pointers reset");
    check(!note.garbage, "fresh NV reset clears source garbage marker");
    check(note.rating == null && !note.ratingDisabled && note.ratingMod == -1,
      "NMV reset should clear its live rating and expose the unset mod sentinel");
    var rejected = false;
    try note.ratingMod = 0.5 catch (_:Dynamic) rejected = true;
    check(rejected, "NMV ratingMod writes should direct scripts to rating.ratingMod");
  }
}
'''.replace("__METHODS__", methods)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
