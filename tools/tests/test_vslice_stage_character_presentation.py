"""Native stage role metadata survives fresh HXC actor construction and old imports."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class VSliceStageCharacterPresentationTest(unittest.TestCase):
    def run_haxe(self, fixture: str) -> None:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = folder
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_actors_use_their_own_base_scale_and_authored_stage_data(self):
        stage = (ROOT / "source/StageHelper.hx").read_text()
        setter = method(stage, "\tpublic function setVSliceCharacterPresentation(")
        apply = method(stage, "\tpublic function applyVSliceCharacterPresentation(")
        self.run_haxe("""
class FakePoint {
  public var x:Float;
  public var y:Float;
  public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
  public function set(x:Float, y:Float):Void { this.x = x; this.y = y; }
}
class Character {
  public var stageBaseScaleX:Float = 0.9;
  public var stageBaseScaleY:Float = 0.9;
  public var stageBaseFlipX:Bool = false;
  public var flipX:Bool = false;
  public var scale = new FakePoint(0.9, 0.9);
  public var scrollFactor = new FakePoint(1, 1);
  public var cameraFocusPoint = new FakePoint();
  public var x:Float = 0;
  public var y:Float = 0;
  public var width:Float = 100;
  public var height:Float = 200;
  public var alpha:Float = 1;
  public var angle:Float = 0;
  public var playerOffsetX:Int = 12;
  public var playerOffsetY:Int = -8;
  public var enemyOffsetX:Int = 0;
  public var enemyOffsetY:Int = 0;
  public var gfOffsetX:Int = 0;
  public var gfOffsetY:Int = 0;
  public var vSliceCamOffsetX:Int = 5;
  public var vSliceCamOffsetY:Int = -7;
  public var followCamX:Int = 150;
  public var followCamY:Int = -100;
  public var camOffsetX:Int = 0;
  public var camOffsetY:Int = 0;
  public var authoredCamOffsets:Bool = false;
  public var synced:Bool = false;
  public function new() {}
  public function updateHitbox():Void { width = 100 * scale.x; height = 200 * scale.y; }
  public function syncHxcPosition():Void synced = true;
}
typedef VSliceStageCharacterPresentation = {
  var feetX:Float; var feetY:Float; var scaleX:Float; var scaleY:Float;
  var scrollX:Float; var scrollY:Float; var alpha:Float; var angle:Float;
  var cameraX:Int; var cameraY:Int;
}
class StageHelper {
  var vSliceCharacterPresentation:Map<String, VSliceStageCharacterPresentation> = [];
  public var presentedCharacters:Map<Character, String> = [];
  public var zIndexes:Map<Character, Int> = [];
  public function new() {}
  static function normalizeCharacterRole(role:String):String
    return role == 'bf' ? 'boyfriend' : role;
""" + setter + "\n" + apply + """
}
class Main {
  static function near(actual:Float, expected:Float):Void
    if (Math.abs(actual - expected) > 0.00001) throw actual + ' != ' + expected;
  static function main() {
    var first = new StageHelper();
    first.setVSliceCharacterPresentation('bf', 500, 700, 1.05, 1.05,
      0.8, 0.9, 0.7, 12, -60, 30);
    var old = new Character();
    if (!first.applyVSliceCharacterPresentation('bf', old)) throw 'first role missing';
    near(old.scale.x, 0.945);
    if (!old.flipX) throw 'BF stage orientation not restored';
    if (!first.applyVSliceCharacterPresentation('bf', old)) throw 'same actor was rejected';
    near(old.scale.x, 0.945); // A second callback must not compound scale.
    near(old.x, 500 - old.width / 2 + 12);
    near(old.y, 700 - old.height - 8);
    near(old.scrollFactor.x, 0.8);
    near(old.alpha, 0.7);
    near(old.angle, 12);
    if (old.followCamX != -55 || old.followCamY != 23 || !old.authoredCamOffsets || !old.synced)
      throw 'camera or original position not restored';
    var second = new StageHelper();
    second.setVSliceCharacterPresentation('bf', 900, 800, 0.85, 0.85,
      1, 1, 1, 0, 10, -20);
    var fresh = new Character();
    if (!second.applyVSliceCharacterPresentation('boyfriend', fresh)) throw 'second role missing';
    near(fresh.scale.x, 0.765); // Own 0.9 base * 0.85, not old 0.945 * 0.85.
    near(fresh.x, 900 - fresh.width / 2 + 12);
    near(fresh.y, 800 - fresh.height - 8);
    if (fresh.followCamX != 15 || fresh.followCamY != -27) throw 'stage camera not replaced';
    if (!second.applyVSliceCharacterPresentation('bf', old)) throw 'cached actor failed on second stage';
    near(old.scale.x, 0.765); // Reused actor also starts from definition scale.
    if (!old.flipX) throw 'reused BF orientation changed';
    if (second.presentedCharacters.exists(fresh)) throw 'outgoing actor was retained';
    if (second.applyVSliceCharacterPresentation('other', new Character()))
      throw 'unknown role was applied';
  }
}
""")

    def test_native_change_character_rebinds_stage_presentation_and_depth(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        swap = method(play_state, "\tfunction switchCharacter(charTo:String, charState:String)")
        for role in ("boyfriend", "dad", "gf"):
            self.assertIn(
                f"curStage.applyVSliceCharacterPresentation('{role}', {role})",
                swap,
            )
        self.assertIn("curStage.rebindCharacterZ(charState, previousStageActor, stageActor)", swap)
        self.assertIn("stageRoleInfo.zIndex != -69", swap)
        self.assertIn("curStage.refresh()", swap)
        self.assertLess(swap.index("curStage.rebindCharacterZ"), swap.index("curStage.refresh()"))

    def test_new_imports_emit_raw_role_data_before_actor_transforms(self):
        self.run_haxe(r'''
import haxe.Json;
class Main {
 static function main() {
  var data=Json.parse('{"name":"synthetic-stage","cameraZoom":0.75,"characters":'
   +'{"bf":{"position":[900,800],"scale":0.85,"scroll":[0.8,0.9],'
   +'"alpha":0.7,"angle":12,"cameraOffsets":[-60,30]}},"props":[]}');
  var converted=VSliceImporter.convertStage(data,'/donor/visuals');
  var raw='stage.setVSliceCharacterPresentation("bf", 900, 800, 0.85, 0.85, 0.8, 0.9, 0.7, 12, -60, 30);';
  var declaration=converted.hscript.indexOf(raw);
  var transform=converted.hscript.indexOf('boyfriend.scale.set(');
  if (declaration<0 || transform<0 || declaration>transform)
    throw 'raw stage role data was not registered before live actor transform';
 }
}
''')

    def test_old_generated_stage_registers_raw_role_data_in_memory_only(self):
        self.run_haxe(r'''
class Main {
 static function check(value:Bool, detail:String):Void if (!value) throw detail;
 static function main() {
  var owner=CompatScriptManifest.create('/donor/visuals',ImportEngine.V_SLICE);
  var other=CompatScriptManifest.create('/donor/visuals',ImportEngine.PSYCH);
  var old='function start(song) {\n'
   +'    setDefaultZoom(0.75);\n'
   +'    boyfriend.scale.set(boyfriend.scale.x * 0.85, boyfriend.scale.y * 0.85);\n'
   +'    boyfriend.updateHitbox();\n'
   +'    stage.setOffsets("bf", 900 - boyfriend.width / 2 + boyfriend.playerOffsetX, 800 - boyfriend.height + boyfriend.playerOffsetY, false);\n'
   +'    boyfriend.x = 900 - boyfriend.width / 2 + boyfriend.playerOffsetX;\n'
   +'    boyfriend.y = 800 - boyfriend.height + boyfriend.playerOffsetY;\n'
   +'    boyfriend.followCamX = 0;\n    boyfriend.followCamY = 0;\n'
   +'    stage.setCamOffsets("bf", -60, 30, false);\n'
   +'    stage.setCharacterZ("bf", 300);\n'
   +'    boyfriend.alpha = 0.7;\n    boyfriend.angle = 12;\n}\n';
  check(VSliceStageCompat.normalizeGeneratedCharacterPresentation(old,other,true)==old,'other engine');
  check(VSliceStageCompat.normalizeGeneratedCharacterPresentation(old,owner,false)==old,'other scope');
  var fixed=VSliceStageCompat.normalizeGeneratedCharacterPresentation(old,owner,true);
  check(fixed.indexOf('stage.setVSliceCharacterPresentation("bf", 900, 800, 0.85, 0.85, 1, 1, 0.7, 12, -60, 30);')>=0,
    'old role data missing: '+fixed);
  check(VSliceStageCompat.normalizeGeneratedCharacterPresentation(fixed,owner,true)==fixed,'not idempotent');
  var computed=StringTools.replace(old, 'boyfriend.scale.x * 0.85', 'boyfriend.scale.x * dynamicScale()');
  check(VSliceStageCompat.normalizeGeneratedCharacterPresentation(computed,owner,true)==computed,'computed stage mutated');
  var computedPos=StringTools.replace(old,'900 - boyfriend.width / 2','computeX() - boyfriend.width / 2');
  check(VSliceStageCompat.normalizeGeneratedCharacterPresentation(computedPos,owner,true)==computedPos,'computed position mutated');
 }
}
''')


if __name__ == "__main__":
    unittest.main()
