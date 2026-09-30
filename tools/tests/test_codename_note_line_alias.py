"""Verify the real Note.strumLine export used by Codename note callbacks."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameNoteLineAliasTest(unittest.TestCase):
    def test_hscript_reads_bound_line(self):
        source = (ROOT / 'source/Note.hx').read_text()
        declaration = re.search(
            r'\t@:keep public var strumLine\(get, never\):CodenameInputLine<Character>;\n'
            r'\tfunction get_strumLine\(\):CodenameInputLine<Character> return codenameInputLine;',
            source,
        )
        self.assertIsNotNone(declaration)
        fixture = '''class Character {}
class CodenameInputLine<T> {
 public var cpu:Bool;
 public function new(cpu:Bool) this.cpu=cpu;
}
class Note {
 public function new() {}
 public var codenameInputLine:CodenameInputLine<Character>=null;
''' + declaration.group(0) + '''\n}
class Main {
 static function main():Void {
  var note=new Note();
  var line=new CodenameInputLine<Character>(false);
  note.codenameInputLine=line;
  var script=new hscript.Interp();
  script.variables.set("note",note);
  script.execute(new hscript.Parser().parseString("if (note.strumLine.cpu != false) throw 'bad line'; note.strumLine.cpu = true;"));
  if(!line.cpu || note.strumLine!=line) throw 'line identity lost';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', work, '--run', 'Main'], cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
