"""Translated HXC must parse with the game's HScript parser, which lacks some Haxe syntax."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / '.haxelib/hscript/2,5,0'
HSCRIPT_EX = ROOT / '.haxelib/hscript-ex/git/src'

# Each body is a statement list inside a song callback; `expect` must appear in the output.
CASES = [
    ('var a = cast PlayState.instance.dad;', 'var a = PlayState.instance.dad;'),
    ('currentShader = cast this.shader;', 'currentShader = shader;'),
    ('var w = cast(q, FlxSprite).x;', 'var w = (q).x;'),
    ('for (z in (cast list:Array<Dynamic>)) trace(z);', 'for (z in (list)) trace(z);'),
    ('var s = "cast me: (a:Int)"; /* cast b */ trace(s);', '"cast me: (a:Int)"'),
    ('var t = flag ? (x) : y;', 'flag ? (x) : y'),
    ('FlxTween.tween(a, {"scale.x": 1.5, angle: 2}, 1);', 'HxcCompatRuntime.objectOf(["scale.x", 1.5, "angle", 2])'),
    ('var o = {inner: {"a b": 1}};', '{inner: HxcCompatRuntime.objectOf(["a b", 1])}'),
    ('hpGremlin.zIndex = (a?.b()?.c + 1) ?? 110;', 'function() { return 110; }), "=");'),
    ('if (list[i].id.startsWith("m")) trace(1);', 'HxcCompatRuntime.stringStartsWith(list[i].id, "m")'),
    ('if (x) { y(); } else P.i.s.g("p")?.animation.play("s");',
     'else hxcOptionalField(function() { return P.i.s.g("p"); }, "animation")'),
    # The parser requires the type in a catch clause, so it must survive the type-check lowering.
    ('try { a(); } catch (e:Dynamic) { trace(e); }', 'catch (e:Dynamic)'),
    # Long scripts: rewrites late in the file still happen after hundreds of untouched brackets.
    ('trace(1); ' * 600 + 'var q = (w:FlxSprite);', 'var q = (w);'),
    ('if (a) { b(); } ' * 600 + 'var o = {"k.x": 1};', 'var o = HxcCompatRuntime.objectOf(["k.x", 1]);'),
]

MAIN = '''class Main {
 static function main() {
  var cases:Array<Array<String>> = %s;
  for (entry in cases) {
   var source = "class S extends Song { function new() { super('s'); } override function onCreate(event) { " + entry[0] + " } }";
   var code:String = HxcCompat.analyze(source, 'scripts/songs/s.hxc').generatedHscript;
   if (code.indexOf(entry[1]) < 0) throw 'expected ' + entry[1] + ' for ' + entry[0] + ' in ' + code;
   try new hscript.ParserEx().parseString(code) catch (error:Dynamic) throw 'parse failed (' + error + ') for ' + entry[0] + ': ' + code;
  }
  // Import aliases are spelled out in code and interpolation, not in plain strings or field names.
  var aliased = "import funkin.ui.FullScreenScaleMode as FSSM;
import flixel.FlxG in G;
class S extends Song { function new() { super('s'); } override function onCreate(event) { var w = 936 * FSSM.wideScale.x; trace('FSSM ${FSSM.wideScale.y} $FSSM'); trace(\\"FSSM\\"); var q = other.FSSM; G.camera.zoom = 1; } }";
  var expanded = HxcScriptSyntaxLowering.expandImportAliases(aliased);
  for (wanted in ['import funkin.ui.FullScreenScaleMode;', '936 * FullScreenScaleMode.wideScale.x', "'FSSM ${FullScreenScaleMode.wideScale.y} $FullScreenScaleMode'",
   'trace(\"FSSM\")', 'other.FSSM', 'FlxG.camera.zoom'])
   if (expanded.indexOf(wanted) < 0) throw 'alias expansion lost ' + wanted + ' in ' + expanded;
  var translated:String = HxcCompat.analyze(aliased, 'scripts/songs/s.hxc').generatedHscript;
  if (translated.indexOf('FSSM.') >= 0) throw 'the alias reached generated code: ' + translated;
  // The runtime half: quoted keys survive as fields, and nested tween paths are found.
  var object:Dynamic = HxcCompatRuntime.objectOf(["scale.x", 1.5, "angle", 2]);
  if (Reflect.field(object, "scale.x") != 1.5 || Reflect.field(object, "angle") != 2) throw 'objectOf lost a field';
  var target = {scale: {x: 1.0}, angle: 0.0};
  if (@:privateAccess HxcCompatRuntime.tweenFieldValue(target, "scale.x") != 1.0) throw 'nested tween path not found';
  if (@:privateAccess HxcCompatRuntime.tweenFieldValue(target, "scale.z") != null) throw 'a missing nested path was found';
 }
}
'''


class HxcParserSyntaxGapsTest(unittest.TestCase):
    def test_translations_parse_and_keep_meaning(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps([list(case) for case in CASES]), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
                '-cp', str(HSCRIPT_EX), '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-4000:])


if __name__ == '__main__':
    unittest.main()
