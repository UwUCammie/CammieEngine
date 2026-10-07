"""A detached StageHelper group must forward owned members to PlayState once."""
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
                return source[start : index + 1]
    raise AssertionError(marker)


class StageGroupForwardingTest(unittest.TestCase):
    def test_add_remove_refresh_and_stage_swap_own_each_sprite_once(self):
        stage = (ROOT / "source/StageHelper.hx").read_text()
        play = (ROOT / "source/PlayState.hx").read_text()
        stage_methods = "\n".join(
            extract_method(stage, marker)
            for marker in (
                "\toverride public function add(",
                "\toverride public function remove(",
                "\tpublic function setZIndex(",
                "\tfunction sortByZIndex(",
                "\tpublic function refresh()",
                "\tpublic function clearStage(",
            )
        ).replace("FlxSprite", "FakeSprite").replace("FlxBasic", "FakeSprite").replace("PlayState", "FakeState").replace("flixel.FlxCamera", "Dynamic")
        state_methods = "\n".join(
            extract_method(play, marker)
            for marker in (
                "\tpublic function attachStageMember(",
                "\tpublic function detachStageMember(",
            )
        ).replace("FlxSprite", "FakeSprite").replace("FlxBasic", "FakeSprite")
        fixture = """
class FakeSprite {
  public var z:Int;
  public var destroyed:Int = 0;
  public var _cameras:Array<Dynamic> = null;
  public var cameras(get, set):Array<Dynamic>;
  function get_cameras():Array<Dynamic> return _cameras;
  function set_cameras(value:Array<Dynamic>):Array<Dynamic> return _cameras = value;
  public function new(z:Int) this.z = z;
  public function destroy():Void destroyed++;
}
class FlxGroup {
  public var children:Array<FakeSprite> = [];
  public function new() {}
  public function forEach(callback:FakeSprite->Void):Void for (sprite in children) callback(sprite);
  public function destroy():Void for (sprite in children) sprite.destroy();
}
class FlxSort {
  public static inline var ASCENDING:Int = 1;
  public static function byValues(order:Int, a:Null<Int>, b:Null<Int>):Int
    return order * Reflect.compare(a == null ? 0 : a, b == null ? 0 : b);
}
class FakeGroup {
  public var members:Array<FakeSprite> = [];
  public var group:FakeGroup;
  public function new() group = this;
  public function add(sprite:FakeSprite):FakeSprite { members.push(sprite); return sprite; }
  public function remove(sprite:FakeSprite, splice:Bool = false):FakeSprite {
    members.remove(sprite); sprite.cameras = null; return sprite;
  }
  public function sort(compare:Int->FakeSprite->FakeSprite->Int, order:Int):Void {
    members.sort(function(a, b) return compare(order, a, b));
  }
  public function clear():Void members.resize(0);
}
class FakeStage extends FakeGroup {
  public var codenamePlacement:Dynamic = {marker:true};
  public var zIndexes:Map<FakeSprite, Int> = [];
  public var presentedCharacters:Map<FakeSprite, String> = [];
  public var vSliceCharacterPresentation:Map<String, Dynamic> = [];
  public var characterPoses:Map<String, Dynamic> = [];
  public var elements:Map<String, Dynamic> = [];
  public var functions:Map<String, Dynamic> = [];
  var highestZ:Int = 0;
  public var codenameOrderNodes:Array<{kind:String, ordinal:Int, key:String, sprite:FakeSprite}> = [];
  var codenameAnchors:Map<String, FakeSprite> = [];
  var codenameActorBindings:Array<{actor:FakeSprite, key:String}> = [];
  public function getElement(name:String):Dynamic return elements.get(name);
""" + stage_methods + """
}
class FakeState {
  public static var instance:FakeState;
  public var curStage:FakeStage;
  public var stage:FakeStage; // Actual NV container is a separate route.
  public var nightmareVisionScripts:Dynamic = null;
  public var nightmareVisionRoleGroups:Array<FakeSprite>=[];
  function isNightmareVisionRoleGroup(sprite:Dynamic):Bool return false;
  public function preserveNightmareVisionStageMember(sprite:Dynamic):Bool return false;
  function nightmareVisionStageGroups():Array<PsychSceneGroupOrdering.PsychSceneGroup<FakeSprite>> return [];
  public function insert(index:Int, sprite:FakeSprite):FakeSprite {members.insert(index, sprite); return sprite;}
  public var members:Array<FakeSprite> = [];
  public var stageSprites:Array<FakeSprite> = [];
  public var camGame:Dynamic = 'game';
  public function new() {}
  public function add(sprite:FakeSprite):FakeSprite { members.push(sprite); return sprite; }
  public function remove(sprite:FakeSprite):FakeSprite { members.remove(sprite); return sprite; }
  public function refresh():Void {
    members.sort(function(a, b) return Reflect.compare(a.z, b.z));
  }
  function protectedStageObject(sprite:FakeSprite):Bool return false;
  function registerStageSprite(sprite:FakeSprite):Void {
    if (stageSprites.indexOf(sprite) < 0) stageSprites.push(sprite);
  }
  function isStageOwnedSprite(sprite:FakeSprite):Bool return stageSprites.indexOf(sprite) >= 0;
  function hasExplicitCameras(sprite:FakeSprite):Bool return sprite.cameras != null;
""" + state_methods + """
  static function main() {
    var state = new FakeState(); FakeState.instance = state;
    var first = new FakeStage(); state.curStage = first;
    var back = new FakeSprite(10); var front = new FakeSprite(30);
    first.zIndexes.set(back, 10); first.zIndexes.set(front, 30);
    first.add(front); first.add(back); first.add(back);
    if (first.members.length != 2 || state.members.length != 2 || state.stageSprites.length != 2)
      throw 'stage.add mounted a duplicate or failed to own a member';
    if (back.cameras == null || back.cameras[0] != 'game')
      throw 'stage.add did not bind the gameplay camera';
    first.refresh();
    if (state.members[0] != back || state.members[1] != front)
      throw 'stage.refresh did not sort the displayed members';
    first.remove(back);
    if (state.members.indexOf(back) >= 0 || state.stageSprites.indexOf(back) >= 0)
      throw 'stage.remove left a displayed or owned member';
    var hud = new FakeSprite(40); hud.cameras = ['hud']; first.add(hud);
    first.remove(hud); first.add(hud);
    if (hud.cameras == null || hud.cameras[0] != 'hud')
      throw 'stage.remove/add lost an explicitly assigned camera';
    // A native addSprite call may have mounted the prop before addElement.
    var registered = new FakeSprite(20); state.add(registered);
    first.add(registered);
    if (state.members.filter(function(x) return x == registered).length != 1)
      throw 'addElement duplicated an already displayed prop';
    // Stage replacement removes the old owner's remaining props and starts fresh.
    first.remove(front); first.remove(registered); first.remove(hud);
    var second = new FakeStage(); state.curStage = second;
    var next = new FakeSprite(15); second.add(next);
    if (state.members.length != 1 || state.members[0] != next || state.stageSprites.length != 1)
      throw 'old stage props survived stage replacement';
    second.clearStage(false);
    if (second.codenamePlacement != null) throw "stage placement survived cleanup";
    if (second.members.length != 0 || state.members.length != 0 || next.destroyed != 0)
      throw 'stage.clearStage(false) retained or destroyed a direct add member';
    var third = new FakeStage(); state.curStage = third;
    var last = new FakeSprite(10); third.add(last); third.clearStage(true);
    if (last.destroyed != 1 || state.members.length != 0 || third.members.length != 0)
      throw 'stage.clearStage(true) did not destroy a direct member exactly once';
  }
}
"""
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "FakeState.hx"
            path.write_text(fixture, newline='\n')
            Path(folder, "PsychSceneGroupOrdering.hx").write_text((ROOT / "source/PsychSceneGroupOrdering.hx").read_text(), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "FakeState", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
                env={**os.environ, "TMPDIR": folder},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cleanup = play[play.index("\tfunction clearRuntimeStage():Void"):]
        self.assertIn("for (sprite in stageSprites)", cleanup)
        self.assertIn("try oldStage.clearStage(false) catch", cleanup)
        self.assertIn("nightmareVisionStageCleanup = false;throw error", cleanup)


if __name__ == "__main__":
    unittest.main()
