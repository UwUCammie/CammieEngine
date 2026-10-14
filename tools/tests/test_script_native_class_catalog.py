"""The shared script class catalogue, and the layers that seed from it before their adapters."""
import re
import subprocess
import tempfile
import unittest

from base_helper_fixtures import extract_block
from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

# Every class the catalogue names gets a tiny stand-in, so the real catalogue
# source compiles under the interpreter without Flixel.
STUB_CLASSES = {
    'flixel/FlxObject': 'class FlxObject {}',
    'flixel/math/FlxMath': 'class FlxMath {}',
    'flixel/math/FlxAngle': 'class FlxAngle {}',
    'flixel/math/FlxRect': 'class FlxRect {}',
    'flixel/util/FlxTimer': 'class FlxTimer {}',
    'flixel/util/FlxSort': 'class FlxSort {}',
    'flixel/util/FlxStringUtil': 'class FlxStringUtil {}',
    'flixel/util/FlxSpriteUtil': 'class FlxSpriteUtil {}',
    'flixel/tweens/FlxTween': 'class FlxTween {}',
    'flixel/tweens/FlxEase': 'class FlxEase {}',
    'flixel/effects/FlxFlicker': 'class FlxFlicker {}',
    'flixel/effects/particles/FlxEmitter': 'class FlxTypedEmitter<T> {}',
    'flixel/ui/FlxBar': 'class FlxBar {}\nenum FlxBarFillDirection { LEFT_TO_RIGHT; }',
    'flixel/addons/display/FlxBackdrop': 'class FlxBackdrop {}',
    'flixel/addons/display/FlxTiledSprite': 'class FlxTiledSprite {}',
    'flixel/addons/effects/FlxTrail': 'class FlxTrail {}',
    'openfl/filters/ShaderFilter': 'class ShaderFilter {}',
    'animate/internal/elements/FlxSpriteElement': 'class FlxSpriteElement {}',
}

MAIN = r'''class Main {
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function main():Void {
  var names=new Map<String,Dynamic>();
  var paths=new Map<String,Dynamic>();
  ScriptNativeClasses.seed(function(n, v) names.set(n, v), function(p, v) paths.set(p, v));
  var all=ScriptNativeClasses.all();
  check(all == ScriptNativeClasses.all(), 'the catalogue is built once');
  for (item in all) {
   check(item.value != null, 'catalogue entry ' + item.name + ' has a class');
   check(names.get(item.name) == item.value, 'bare name seeded for ' + item.name);
   if (item.path != item.name) check(paths.get(item.path) == item.value, 'qualified path seeded for ' + item.path);
   check(item.path.split('.').pop() == item.name || item.path.indexOf(item.name) >= 0,
    'qualified path ' + item.path + ' names the same class as ' + item.name);
  }
  check(names.get('FlxSpriteElement') == animate.internal.elements.FlxSpriteElement
   && paths.get('animate.internal.elements.FlxSpriteElement') == animate.internal.elements.FlxSpriteElement,
   'texture atlas sprite elements are shared under both spellings');
  check(names.get('FlxFlicker') == flixel.effects.FlxFlicker && paths.get('flixel.effects.FlxFlicker') == flixel.effects.FlxFlicker,
   'FlxFlicker is shared under both spellings');
  var onlyNames=new Map<String,Dynamic>();
  ScriptNativeClasses.seed(function(n, v) onlyNames.set(n, v));
  check(onlyNames.exists('FlxSort'), 'a layer without import paths still gets the bare names');
 }
}
'''


class ScriptNativeClassCatalogTest(unittest.TestCase):
    def test_catalogue_seeds_bare_and_qualified_names(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            for relative, body in STUB_CLASSES.items():
                target = work / (relative + '.hx')
                target.parent.mkdir(parents=True, exist_ok=True)
                package = '.'.join(relative.split('/')[:-1])
                target.write_text('package ' + package + ';\n' + body + '\n', encoding='utf-8')
            (work / 'ScriptNativeClasses.hx').write_text(
                (ROOT / 'source/ScriptNativeClasses.hx').read_text(encoding='utf-8'), encoding='utf-8')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_layers_seed_the_catalogue_before_their_own_adapters(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        preset = extract_block(play, 'public static function seedNightmareVisionCommon(')
        seed = preset.index('ScriptNativeClasses.seed(')
        self.assertLess(seed, preset.index('for (name => value in preset) interp.variables.set(name, value);'),
                        'the NV preset must seed shared classes before its owner adapters')
        plugin = (ROOT / 'source/PluginManager.hx').read_text(encoding='utf-8')
        body = extract_block(plugin, 'public static function addVarsToInterp<')
        self.assertLess(body.index('ScriptNativeClasses.seed('), body.index('interp.variables.set("FlxSprite"'),
                        'the base interpreter must seed shared classes before its adapters')

    def test_catalogue_stays_free_of_adapted_classes(self):
        source = (ROOT / 'source/ScriptNativeClasses.hx').read_text(encoding='utf-8')
        names = set(re.findall(r"entry\('([A-Za-z]+)'", source))
        # These are always replaced by a layer's own adapter; listing them here
        # would hand a raw class to any layer that forgot to override it.
        for adapted in ('FlxSprite', 'FlxG', 'FlxColor', 'FlxPoint', 'FlxSound', 'Paths', 'FlxRuntimeShader'):
            self.assertNotIn(adapted, names)


if __name__ == '__main__':
    unittest.main()
