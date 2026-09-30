"""Keep ignored Codename HScript null accesses attributable to a callback."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameNullDiagnosticTest(unittest.TestCase):
    def test_null_access_names_owning_script(self):
        source = (ROOT / 'source/CodenameScriptInterp.hx').read_text()
        match = re.search(r'\toverride function nullAccessDiagnose\(', source)
        self.assertIsNotNone(match)
        brace = source.index('{', match.start())
        depth = 0
        end = None
        for at in range(brace, len(source)):
            depth += (source[at] == '{') - (source[at] == '}')
            if depth == 0:
                end = at + 1
                break
        self.assertIsNotNone(end)
        method = source[match.start():end]
        fixture = '''class Main extends hscript.Interp {
 var codenameNullAccessSeen:Map<String,Bool>=new Map();
''' + method + '''
 static function main():Void {
  var script=new Main();
  script.variables.set('__compatDiagnosticSource','songs/ui.hx');
  script.variables.set('__compatDiagnosticCallback','onPostNoteHit');
  script.execute(new hscript.Parser().parseString('var note = null; note.strumLine; note.strumLine;'));
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', work, '--run', 'Main'], cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.count('[hscript-null-access]'), 1, result.stdout)
            self.assertIn('(songs/ui.hx#onPostNoteHit)', result.stdout)


if __name__ == '__main__':
    unittest.main()
