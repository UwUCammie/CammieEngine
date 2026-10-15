"""A stage's private FlxTweenManager field keeps its constructor.

`var tweens:FlxTweenManager = new FlxTweenManager();` was dropped to a bare
`var tweens;`, so every `tweens.tween(...)` and `tweens.update(elapsed)` hit
a null object and the stage's animation never ran.
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

DONOR = r'''import flixel.tweens.FlxTweenManager;
import funkin.play.stage.Stage;

class SwingStage extends Stage {
    var swing:FlxTweenManager = new FlxTweenManager();
    var other:FlxTweenManager = new FlxTweenManager(somethingElse);
    public function new() { super('swing'); }
    public function onCreate(event) {
        super.onCreate(event);
        swing.tween(getNamedProp("ship"), {angle: 3}, 2, {type: 4});
    }
    public function onUpdate(event) { swing.update(event.elapsed); }
}
'''

MAIN = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var generated = HxcCompat.analyze(%s, "scripts/stages/swing.hxc").generatedHscript;
    if (generated.indexOf("var swing = new FlxTweenManager();") < 0) fail("tween manager field lost its constructor: " + generated);
    if (generated.indexOf("somethingElse") >= 0) fail("only the plain constructor is kept: " + generated);
    Sys.println("tween-field-ok");
  }
}
'''


class HxcTweenManagerFieldTest(unittest.TestCase):
    def test_private_tween_manager_field_is_constructed(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(DONOR), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('tween-field-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
