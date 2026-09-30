"""Camera note offsets tolerate characters whose imported animation failed."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
SOURCE = ROOT / 'source/PlayState.hx'


class CameraNoteAnimationTest(unittest.TestCase):
    def test_missing_current_animation_has_empty_safe_name(self):
        source = SOURCE.read_text()
        start = source.index('\tpublic static function characterAnimationName(')
        end = source.index('\n\tpublic static function hscriptSoundNeedsRebuild(', start)
        helper = source[start:end].replace('public static function', 'static function')
        fixture = f'''class Anim {{
\tpublic var name:String;
\tpublic function new(name:String) this.name = name;
}}
class Controller {{
\tpublic var curAnim:Anim;
\tpublic function new(curAnim:Anim) this.curAnim = curAnim;
}}
class Character {{
	public var animation:Controller;
	public function new(animation:Controller) this.animation = animation;
	public static function animationName(character:Character):String {{
		return character != null && character.animation != null && character.animation.curAnim != null ? character.animation.curAnim.name : '';
	}}
}}
class Test {{
{helper}
\tstatic function main() {{
\t\tif (characterAnimationName(null) != "") throw "null character";
\t\tif (characterAnimationName(new Character(null)) != "") throw "null controller";
\t\tif (characterAnimationName(new Character(new Controller(null))) != "") throw "null animation";
\t\tif (characterAnimationName(new Character(new Controller(new Anim("singUP-alt")))) != "singUP-alt") throw "live animation";
\t}}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Test.hx'
            path.write_text(fixture)
            result = subprocess.run([str(HAXE), '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_offsets_use_safe_animation_name(self):
        source = SOURCE.read_text()
        camera = source[source.index('\t\tif (camNotes) {'):source.index('\n\t\tif (endingSong)', source.index('\t\tif (camNotes) {'))]
        self.assertIn('characterAnimationName(dad)', camera)
        self.assertIn('characterAnimationName(boyfriend)', camera)
        self.assertNotIn('dad.animation.curAnim.name', camera)
        self.assertNotIn('boyfriend.animation.curAnim.name', camera)


if __name__ == '__main__':
    unittest.main()
