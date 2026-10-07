"""Exercise the NMV shader import through the real script interpreter and lifecycle."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionShadowShaderImportTest(unittest.TestCase):
    def test_shader_import_allows_setup_and_repeated_effect_decay(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        seed = source.split('function seedNightmareVisionCommon', 1)[1].split(
            "interp.bindImport('funkin.game.shaders.HSLColorSwap'", 1)[1]
        binding = next(line.strip() for line in seed.splitlines()
                       if "interp.bindImport('funkin.game.shaders.DropShadowShader'" in line)
        main = r'''
import crowplexus.hscript.Parser;
class Main {
 static var errors:Array<String> = [];
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function run(hostHz:Int, bound:Bool):Float {
  var group = new NightmareVisionScriptGroup(null, function(name, phase, error):Void {
   errors.push(phase + ':' + Std.string(error));
  });
  var parser = new Parser(); parser.allowTypes = true; parser.allowMetadata = true;
  var script = group.load('stage', parser.parseString('
   import funkin.game.shaders.DropShadowShader;
   var shader;
   var blur = 0.0;
   function onLoad() {
    shader = new DropShadowShader();
    shader.distance = 15;
    shader.angle = 90;
    shader.color = 0xDF2F68;
    overlay = {alpha:0.0};
   }
   function onUpdate(elapsed) {
    overlay.alpha = 0.125;
    blur += (1 - blur) * elapsed * 3;
   }
   function onBeatHit() blur += 3;
   function readBlur() return blur;
   function readOverlay() return overlay;
   function readShader() return shader;
  '), function(interp):Void {
   if (bound) {
__BINDING__
   }
  });
  var clock = new CompatScriptClock();
  var ticks = 0;
  for (frame in 0...hostHz * 30) {
   var batch = clock.advance(1.0 / hostHz);
   batch.dispatchUpdate(function(index, elapsed):Void {
    if (ticks % 30 == 0) group.call('onBeatHit', []);
    group.call('onUpdate', [elapsed]);
    ticks++;
   });
  }
  var blur:Float = script.callValue('readBlur');
  if (bound) {
   check(errors.length == 0, 'import or callback failed: ' + errors);
   check(ticks == 1800, 'source callback cadence changed');
   check(script.callValue('readOverlay').alpha == .125, 'setup stopped before overlay');
   var shader:shaders.DropShadowShader = script.callValue('readShader');
   check(shader.distance == 15 && shader.angle == 90 && shader.color == 0xDF2F68,
    'source shader properties were lost');
   check(blur >= 1 && blur < 5, 'beat blur accumulates instead of decaying: ' + blur);
  } else {
   check(errors.length > 0 && errors[0].indexOf('onLoad:') == 0,
    'negative control should fail during stage setup');
   check(blur == 180, 'negative control should reproduce runaway beat blur: ' + blur);
  }
  group.destroy(); return blur;
 }
 static function main():Void {
  run(60, false); errors = [];
  var reference = run(60, true);
  for (hz in [30, 144, 480, 2400]) {
   var value = run(hz, true);
   check(Math.abs(value - reference) < .000001, 'render FPS changes effect decay');
  }
 }
}
'''.replace('__BINDING__', binding)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'shaders').mkdir()
            (work / 'shaders/DropShadowShader.hx').write_text('''package shaders;
class DropShadowShader {
 public var distance:Float = 0;
 public var angle:Float = 0;
 public var color:Int = 0;
 public function new() {}
}
''', encoding='utf-8')
            (work / 'Main.hx').write_text(main, encoding='utf-8')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work),
                '--main', 'Main', '--interp'], cwd=work,
                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
