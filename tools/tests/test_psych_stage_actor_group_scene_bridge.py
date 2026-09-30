"""Psych actor-group views unwrap to their native actors at scene boundaries."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


class PsychStageActorGroupSceneBridgeTest(unittest.TestCase):
    def test_create_layer_and_actor_group_reordering_use_native_actor_members(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            owner = base / "owner"
            stage = owner / "source/demo/ReorderStage.hx"
            stage.parent.mkdir(parents=True)
            stage.write_text(
                """package demo;
import backend.BaseStage;
import flixel.FlxBasic;
class ReorderStage extends BaseStage {
 override public function create():Void {
  add(new FlxBasic());
  remove(dadGroup, true);
  addBehindBF(dadGroup);
 }
}
""",
                encoding="utf-8",
            )
            (base / "PsychStageActorGroupSceneProbe.hx").write_text(
                r'''import flixel.FlxBasic;
class PsychStageActorGroupSceneProbe {
 static function main():Void {
  var owner = Sys.args()[0];
  var gf = new FlxBasic();
  var dad = new FlxBasic();
  var boyfriend = new FlxBasic();
  var members:Array<Dynamic> = [gf, dad, boyfriend];
  var insertIndices:Array<Int> = [];
  var removed:Array<Dynamic> = [];
  var host:Dynamic = {
   gf:gf,
   dad:dad,
   boyfriend:boyfriend,
   members:members,
   add:function(value:Dynamic):Dynamic { members.push(value); return value; },
   insert:function(index:Int, value:Dynamic):Dynamic {
    insertIndices.push(index);
    members.insert(index, value);
    return value;
   },
   remove:function(value:Dynamic, splice:Bool = false):Dynamic {
    removed.push(value);
    members.remove(value);
    return value;
   }
  };
  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('flixel.FlxBasic', FlxBasic);
  bindings.set('FlxBasic', FlxBasic);
  bindings.set('backend.BaseStage', PsychBaseStageCompat);
  bindings.set('BaseStage', PsychBaseStageCompat);
  var runtime = new PsychCompiledStageRuntime(owner, 'demo.ReorderStage', host, bindings);
  if (!runtime.create() || !runtime.active)
   throw 'Psych actor-group scene stage failed: ' + runtime.diagnostics;
  if (removed.length != 1 || removed[0] != dad)
   throw 'remove(dadGroup) did not remove the native dad actor';
  if (insertIndices.length != 2 || insertIndices[0] != 0 || insertIndices[1] != 2)
   throw 'background or addBehindBF chose the wrong actor layer: ' + insertIndices;
  if (members.length != 4 || members[1] != gf || members[2] != dad || members[3] != boyfriend)
   throw 'actor-group reordering inserted a facade instead of the native actor';
  runtime.destroy();
 }
}''',
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 *FLIXEL_ARGS, "--run", "PsychStageActorGroupSceneProbe", str(owner)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
