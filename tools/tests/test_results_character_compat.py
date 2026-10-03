"""Default results use declared animation families and a deterministic BF fallback."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ResultsCharacterCompatTest(unittest.TestCase):
    def test_families_assets_aliases_and_unknown_fallback(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            owner = work / 'owner'
            for family in ('bf', 'pico'):
                atlas = owner / 'images' / ('results-' + family)
                atlas.mkdir(parents=True)
                (atlas / 'idle.png').write_bytes(b'fixture')
                (atlas / 'idle.xml').write_text('<TextureAtlas/>', newline='\n')
            (owner / 'images/extra.png').write_bytes(b'fixture')
            (owner / 'pack.json').write_text(json.dumps({'resultsCharacterFamilies': {
                'nene': {'characterIds': ['nene', 'custom-player'], 'requiredAssets': ['images/extra.png']},
                'missing': {'characterIds': ['bad-assets'], 'requiredAssets': ['images/missing.png']},
                'escape': {'characterIds': ['escape'], 'requiredAssets': ['../outside.png']},
            }}), newline='\n')
            (work / 'Main.hx').write_text(r'''
class Main {
 static function check(actual:String, expected:String) {
  if(actual != expected) throw actual + ' != ' + expected;
 }
 static function main() {
  var owner=Sys.args()[0];
  var choices=new ResultsCharacterCompat(owner);
  for (id in [null,'','unknown','not-pico','picobogus','abfthing','bf-car','boyfriend-pixel'])
   check(choices.resolve(id),'bf');
  check(choices.resolve('PICO'),'pico');
  check(choices.resolve('pico-speaker'),'pico');
  check(choices.resolve('custom-player'),'nene');
  check(choices.resolve('bad-assets'),'bf');
  check(choices.resolve('escape'),'bf');
  for(i in 0...100) check(choices.resolve('unknown'),'bf');
  sys.FileSystem.deleteFile(owner+'/images/results-pico/idle.xml');
  check(new ResultsCharacterCompat(owner).resolve('pico'),'bf');
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(work), '--run', 'Main', str(owner)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_only_default_provider_reads_presentation_identity(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('if (resultsObserver) {')
        end = source.index("interp.variables.set('setPropertyFromGroup'", start)
        binding = source[start:end]
        self.assertIn('new ResultsCharacterCompat(psychScriptOwner)', binding)
        self.assertIn('actor.requestedCharacter', binding)
        self.assertIn('codenameScriptCharacterAtLine(1)', binding)
        self.assertIn("else interp.variables.set('getProperty', compatGetProperty)", binding)
        self.assertNotIn('boyfriend.curCharacter =', binding)


if __name__ == '__main__':
    unittest.main()
