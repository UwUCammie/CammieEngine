"""HScript-ex method arguments stay local when a class field has the same name."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class HscriptClassParameterShadowingTest(unittest.TestCase):
    def test_native_field_survives_shadowed_constructor_and_nested_method_args(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "FlxSound.hx").write_text(
                """class FlxSound {
 public var path:String = '';
 public var playing:Bool = false;
 public function new() {}
 public function loadEmbedded(value:String):FlxSound {
  path=value;
  return this;
 }
 public function play(looped:Bool):FlxSound {
  playing=true;
  return this;
 }
}
""",
                encoding="utf-8",
            )
            owner_script = base / "PhillyTrain.hx"
            owner_script.write_text(
                """class PhillyTrain {
 public var sound:FlxSound;
 public function new(sound:String='train_passes') {
  this.sound = new FlxSound().loadEmbedded(sound);
 }
 public function start():String {
  if (!sound.playing) {
   sound.play(true);
  }
  if (sound.playing) return 'playing';
  return 'stopped';
 }
 public function soundPath():String {
  return sound.path;
 }
 public function replaceSound(sound:String):Void {
  this.sound = new FlxSound().loadEmbedded(sound);
 }
 public function nestedRead(label:String):String {
  this.replaceSound(label);
  return label + ':' + sound.path;
 }
}
""",
                encoding="utf-8",
            )
            (base / "PsychClassParameterProbe.hx").write_text(
                r'''import hscript.ParserEx;
import hscript.ScriptClassScope;
import sys.io.File;

class PsychClassParameterProbe {
 static function main():Void {
  var scope=new ScriptClassScope();
  scope.seed('FlxSound',FlxSound);
  scope.registerModule(new ParserEx().parseModule(File.getContent(Sys.args()[0])));
  var train=scope.createInstance('PhillyTrain');
  if(train==null) throw 'owner class did not instantiate';
  if(train.callFunction('soundPath')!='train_passes')
   throw 'constructor parameter restore erased the same-named native field';
  if(train.callFunction('start')!='playing')
   throw 'PhillyTrain-style sound.playing read did not reach the native sound';
  if(train.callFunction('nestedRead',['second_pass'])!='second_pass:second_pass')
   throw 'nested method call did not preserve its caller local and updated field';
  if(train.callFunction('soundPath')!='second_pass')
   throw 'same-named nested parameter did not leave the native field updated';
  scope.release();
 }
}''',
                encoding="utf-8",
            )
            command = [
                str(ROOT / ".tools/haxe/haxe"),
                "-cp", str(base),
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                "--run", "PsychClassParameterProbe", str(owner_script),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
