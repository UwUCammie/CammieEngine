"""Character update tolerates imported characters with no active animation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


class CharacterUpdateAnimationTest(unittest.TestCase):
    def test_animation_name_handles_missing_animation_state(self):
        source = (ROOT / 'source/Character.hx').read_text()
        start = source.index('\tpublic static function animationName(')
        helper = source[start:source.index('\n\t}', start) + 3]
        fixture = '''class Animation { public var curAnim:Anim; public function new(curAnim) this.curAnim=curAnim; }
class Anim { public var name:String; public function new(name) this.name=name; }
class Character {
 public var animation:Animation;
 public function new(animation) this.animation=animation;
''' + helper + '''
 static function main() {
  var missingCharacter:Character=null;
  if(animationName(missingCharacter)!="") throw "null character";
  var missingController=new Character(null);
  if(animationName(missingController)!="") throw "null controller";
  var missingAnim=new Character(new Animation(null));
  if(animationName(missingAnim)!="") throw "null animation";
  var singing=new Character(new Animation(new Anim("singLEFT")));
  if(animationName(singing)!="singLEFT") throw "animation name lost";
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'Character.hx').write_text(fixture)
            result = subprocess.run([str(HAXE), '-cp', folder, '-main', 'Character', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_controlled_update_checks_active_animation(self):
        source = (ROOT / 'source/Character.hx').read_text()
        start = source.index('\toverride function update(elapsed:Float)')
        update = source[start:source.index('\n\tprivate var danced:', start)]
        self.assertIn('var currentAnim = animationName(this);', update)
        self.assertNotIn('animation.curAnim.name.startsWith', update)
        self.assertNotIn('animation.curAnim.name.endsWith', update)


if __name__ == '__main__':
    unittest.main()
