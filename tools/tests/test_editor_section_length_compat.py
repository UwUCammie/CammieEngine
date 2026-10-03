"""The chart editor accepts section lengths from supported chart formats."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


class EditorSectionLengthCompatTest(unittest.TestCase):
    def test_section_beats_and_legacy_steps(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        fixture = '''class EditorSectionLengthCompatFixture {
 static function main():Void {
  var sections:Array<Dynamic> = [
   {sectionBeats:4}, {sectionBeats:3.5}, {lengthInSteps:8, sectionBeats:4},
   {lengthInSteps:0, sectionBeats:2}, {}, {sectionBeats:-2}
  ];
  EditorSectionLengthCompat.normalize(sections);
  var expected = [16, 14, 8, 8, 16, 16];
  for (i in 0...sections.length)
   if (Reflect.field(sections[i], "lengthInSteps") != expected[i])
    throw 'section ' + i;
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'EditorSectionLengthCompatFixture.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-cp', str(ROOT / 'source'),
                 '--run', 'EditorSectionLengthCompatFixture'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
