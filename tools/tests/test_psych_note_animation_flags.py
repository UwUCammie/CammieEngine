"""Psych per-note animation flags reach the shared hit and miss paths."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class PsychNoteAnimationFlagsTest(unittest.TestCase):
    def test_psych_flags_gate_shared_animation_routes(self):
        note_source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        play_source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        setter = extract_method(note_source, "function set_sourceKind(")
        note_miss = extract_method(play_source, "function noteMissCore(")
        good_hit = extract_method(play_source, "function goodNoteHit(")

        self.assertIn("public var noAnimation:Bool = false;", note_source)
        self.assertIn("public var noMissAnimation:Bool = false;", note_source)
        self.assertIn("applyPsychNoteAnimationType(value);", setter)
        self.assertIn("note == null || note.allowsAnimation(true)", note_miss)
        self.assertIn("if (note.allowsAnimation())", good_hit)

    def test_note_type_defaults_and_live_script_writes(self):
        note_source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(note_source, marker)
            for marker in (
                "function set_sourceKind(",
                "function applyPsychNoteAnimationType(",
                "public function allowsAnimation(",
            )
        )
        fixture = '''
import hscript.Interp;
import hscript.Parser;
class PsychNoteAnimationProbe {
  public var sourceKind(default, set):Null<String> = null;
  public var sourceTimingMode:Int = 0;
  public var hitPriority:Int = 1;
  public var noAnimation:Bool = false;
  public var noMissAnimation:Bool = false;
  public var refreshes:Int = 0;
  public function new() {}
  function refreshPsychNoteType():Void refreshes++;
  function applySourceHurtNoteSemantics():Void {}
__METHODS__
  static function main():Void {
    var note = new PsychNoteAnimationProbe();
    if (note.hitPriority != 1 || !note.allowsAnimation() || !note.allowsAnimation(true))
      throw 'ordinary notes should keep both animation paths';
    note.sourceKind = 'No Animation';
    if (note.hitPriority != 1 || !note.noAnimation || !note.noMissAnimation
      || note.allowsAnimation() || note.allowsAnimation(true))
      throw 'Psych No Animation did not suppress both animation paths';
    note.noAnimation = false;
    if (!note.allowsAnimation() || note.allowsAnimation(true))
      throw 'hit and miss animation flags were not independent';
    note.sourceKind = 'Hurt Note';
    if (note.hitPriority != 0)
      throw 'Hurt Note did not receive Nightmare Vision hit priority';
    note.hitPriority = 7;
    note.sourceKind = 'Alt Animation';
    if (note.hitPriority != 7 || note.noAnimation || !note.noMissAnimation || note.allowsAnimation(true))
      throw 'changing note type unexpectedly cleared an authored miss flag';
    var interp = new Interp();
    interp.variables.set('note', note);
    interp.execute(new Parser().parseString('note.noAnimation = true; note.noMissAnimation = false;'));
    if (note.allowsAnimation() || !note.allowsAnimation(true))
      throw 'script writes to live note animation flags were ignored';
  }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychNoteAnimationProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "PsychNoteAnimationProbe"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
