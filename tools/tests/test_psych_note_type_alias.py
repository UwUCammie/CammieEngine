"""Psych Lua noteType reads use the authored chart label."""
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


class PsychNoteTypeAliasTest(unittest.TestCase):
    def test_group_property_reflection_reads_and_updates_source_kind(self):
        source = (ROOT / "source/Note.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "function set_sourceKind(", "function applyPsychNoteAnimationType(",
            "function get_noteType(", "function set_noteType(",
        ))
        fixture = '''
class PsychNoteTypeAliasFixture {
  public var sourceKind(default, set):Null<String> = null;
  public var noAnimation:Bool = false;
  public var noMissAnimation:Bool = false;
  public var noteType(get, set):String;
  public var refreshes:Int = 0;
  public function new() {}
  function refreshPsychNoteType():Void refreshes++;
__METHODS__
  static function main():Void {
    var note = new PsychNoteTypeAliasFixture();
    note.sourceKind = 'Hotdog_Note';
    if (Reflect.getProperty(note, 'noteType') != 'Hotdog_Note')
      throw 'Psych script cannot read the authored note label';
    Reflect.setProperty(note, 'noteType', 'Other_Note');
    if (note.sourceKind != 'Other_Note' || note.refreshes != 2)
      throw 'Psych note type write did not refresh the authored kind';
  }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychNoteTypeAliasFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychNoteTypeAliasFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
