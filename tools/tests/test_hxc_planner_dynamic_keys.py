"""The HXC asset planner lists only lookups that run with a literal key."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r'''class Lines extends Module {
  // snd = FunkinSound.load(Paths.sound('commentedLine'), true);
  /* FunkinSound.playOnce(Paths.sound("blockLine"));
     Paths.image('blockArt'); */
  var pattern = ~/a\/\/b/g;
  function line(lang:String, index:Int) {
    FunkinSound.playOnce(Paths.sound('voice/$lang/line-$index'));
    FunkinSound.playOnce(Paths.sound('voice/${lang}/end'));
    FunkinSound.playOnce(Paths.sound("gameplay/hit")); // trailing note Paths.sound('trailing')
    var url = "http://example.invalid/" + Paths.image('realArt');
    Paths.music('price$5');
  }
}
'''

MAIN = '''class Main {
 static function main() {
  var keys = [for (reference in HxcAssetPlanner.literalReferences(%s)) reference.kind + ':' + reference.key];
  for (wanted in ['sound:gameplay/hit', 'image:realArt', 'music:price$5'])
   if (keys.indexOf(wanted) < 0) throw 'lost ' + wanted + ' from ' + keys;
  for (key in keys)
   if (key.indexOf('commented') >= 0 || key.indexOf('block') >= 0 || key.indexOf('trailing') >= 0)
    throw 'a commented lookup became a dependency: ' + keys;
   else if (key.indexOf('voice/') >= 0)
    throw 'an interpolated key became a literal dependency: ' + keys;
 }
}
'''


class HxcPlannerDynamicKeysTest(unittest.TestCase):
    def test_comments_and_interpolated_keys_are_not_dependencies(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(SCRIPT), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
