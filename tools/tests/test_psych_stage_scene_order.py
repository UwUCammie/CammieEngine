"""Psych stage construction order on the native PlayState member list."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class PsychStageSceneOrderTest(unittest.TestCase):
    def test_create_props_draw_behind_actors_and_create_post_props_append(self):
        source = (ROOT / "source/PsychBaseStageCompat.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public function add(object:Dynamic):Dynamic {",
            "function firstActorMemberIndex():Int {",
        ))
        methods += "\n\tpublic function beginPostCreate():Void creatingBackground = false;"
        runtime = (ROOT / "source/PsychCompiledStageRuntime.hx").read_text()
        post_gate = runtime.index("if (name == 'createPost') {")
        self.assertLess(post_gate, runtime.index("baseStage.beginPostCreate();", post_gate))
        self.assertLess(
            runtime.index("baseStage.beginPostCreate();", post_gate),
            runtime.index("stageClass.callFunction(name", post_gate),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text("""class Main {
 static function main():Void {
  var scene=new StageProbe();
  scene.add('sky');
  scene.add('road');
  if(scene.members.join(',')!='base,sky,road,gf,dad,bf,hud')
   throw 'create props covered native actors: '+scene.members;
  scene.beginPostCreate();
  scene.add('can');
  if(scene.members.join(',')!='base,sky,road,gf,dad,bf,hud,can')
   throw 'createPost prop lost authored foreground order: '+scene.members;
 }
}
class StageProbe {
 public var creatingBackground:Bool=true;
 public var members:Array<Dynamic>=['base','gf','dad','bf','hud'];
 public function new() {}
 function readField(name:String):Dynamic return switch(name) {
  case 'gf','dad','boyfriend': name=='boyfriend' ? 'bf' : name;
  default: null;
 };
 function sceneObject(value:Dynamic,_adding:Bool):Dynamic return value;
 function callHost(name:String,args:Array<Dynamic>):Dynamic {
  if(name=='insert') members.insert(args[0],args[1]);
  else if(name=='add') members.push(args[0]);
  return args[args.length-1];
 }
""" + methods + "\n}\n", encoding="utf-8", newline='\n')
            env = dict(os.environ)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
