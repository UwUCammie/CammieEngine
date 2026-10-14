"""Psych owner metadata remains available alongside optional compiled stages."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


class PsychStageJsonOnlyMetadataTest(unittest.TestCase):
    def test_authored_girlfriend_visibility_preserves_required_actor(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        apply = extract_method(play, 'function applyPsychStageJson(').replace('function ', 'public function ', 1)
        fixture = r'''class FNFAssets {
 public static var data:Dynamic;
 public static function exists(path:String):Bool return true;
 public static function getText(path:String):String return haxe.Json.stringify(data);
}
class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}
class PsychOwnerAssetPath {public static function cleanId(s:String):String return s;}
class Actor {
 public var visible:Bool=true;public var likeGf:Bool=false;
 public function new(){}public function setPosition(x:Float,y:Float):Void {}
}
class Probe {
 public var gf:Actor=new Actor();public var dad:Actor=null;public var boyfriend:Actor=null;
 var psychStageLibrary:String;var curStage:Dynamic={defaultZoom:1.0};var defaultCamZoom:Float=1;
 var swapOffsetsBeforePsychStage:Array<Float>;var swapOffsets:Array<Float>=[];var psychStageCharacterRoot:String;
 var psychStageObjectsBuilt:Bool=false;
 function applySourceStageMetadata(meta:SourceStageMetadata,profile:Dynamic):Void {}
 function buildSourceStageObjects(meta:SourceStageMetadata,owner:String):Void {}
 function rememberPsychStagePoint(key:String,point:Array<Float>):Void {}
 function stageCharacterOffset(actor:Actor,role:String):Array<Float> return [0,0];
 function refreshPsychStageCameraTarget():Void {}
 public function new(){}
 __APPLY__
 static function main():Void {
  var p=new Probe();var actor=p.gf;
  FNFAssets.data={hide_girlfriend:true};p.applyPsychStageJson('stage.json','owner');
  if(p.gf!=actor || p.gf.visible)throw 'authored hidden role was exposed or destroyed';
  FNFAssets.data={hide_girlfriend:false};p.applyPsychStageJson('stage.json','owner');
  if(p.gf.visible)throw 'stage forced a script-hidden role visible';
  var visible=new Probe();FNFAssets.data={};visible.applyPsychStageJson('stage.json','owner');
  if(!visible.gf.visible)throw 'missing flag hid a visible role';
  p.gf=null;FNFAssets.data={hide_girlfriend:true};p.applyPsychStageJson('stage.json','owner');
 }
}'''.replace('__APPLY__',apply)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Probe.hx').write_text(fixture, newline='\n')
            (Path(folder) / 'SourceStageMetadata.hx').write_text(
                (ROOT / 'source/SourceStageMetadata.hx').read_text(), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Probe', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('psych-stage-json-error', result.stdout)

    @unittest.skipIf(os.name == 'nt', 'requires a case-sensitive filesystem fixture')
    def test_finds_owner_json_and_executes_compiled_source_when_resolved(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play, "function psychStageMetadataPath(")
        self.assertIn("for (directory in ['stages', 'shared/stages'])", method)
        self.assertIn("entry.toLowerCase() != wanted", method)
        self.assertIn("if (match != null)\n\t\t\t\t\treturn null;", method)

        source_resolver = extract_method(play, "function psychCompiledStageSourceForCurrentSong(")
        self.assertIn("selectedPsychSkinRoot()", source_resolver)
        self.assertIn("PsychSourceStageCompat.resolve(ownerRoot, Std.string(SONG.stage))", source_resolver)

        stage_start = extract_method(play, "function startPsychCompiledStage(")
        self.assertIn("new PsychCompiledStageRuntime(ownerRoot, source.modulePath", stage_start)
        self.assertIn("if (!psychCompiledStageRuntime.create())", stage_start)
        self.assertIn("[psych-stage-runtime] executing", stage_start)

        stage_setup_start = play.index("var psychCompiledStageOwner = selectedPsychSkinRoot();")
        stage_setup_end = play.index("setAllHaxeVar('stage', curStage);", stage_setup_start)
        stage_setup = play[stage_setup_start:stage_setup_end]
        self.assertIn("psychCompiledStageOwner != null && psychCompiledStageSource != null", stage_setup)
        self.assertIn("psychCompiledStageCreated = startPsychCompiledStage", stage_setup)
        self.assertIn("if (psychCompiledStageCreated)", stage_setup)
        self.assertIn("applyOwnedPsychStageMetadataOnly(psychCompiledStageOwner)", stage_setup)
        self.assertIn("curStage.applyNativeFallback(SONG.stage, missingStageDiagnostic)", stage_setup)

        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class Probe {{
{method}
  public function new() {{}}
  static function main():Void {{
    var root = Sys.args()[0];
    var probe = new Probe();
    var expected = Path.join([root, 'shared/stages/alphaStage.json']);
    if (probe.psychStageMetadataPath(root, 'ALPHASTAGE') != expected)
      throw 'shared stage JSON was not resolved case-insensitively';
    if (probe.psychStageMetadataPath(root, '../alphaStage') != null)
      throw 'unsafe stage ids must not become filesystem paths';
    if (probe.psychStageMetadataPath(root, 'no-stage') != null)
      throw 'an absent stage JSON was reported as present';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner = work / "owner"
            stage_root = owner / "shared/stages"
            stage_root.mkdir(parents=True)
            (stage_root / "alphaStage.json").write_text('{"defaultZoom":0.77}', newline='\n')
            (work / "Probe.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Probe", str(owner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("applyOwnedPsychStageMetadataOnly();", play)


if __name__ == "__main__":
    unittest.main()
