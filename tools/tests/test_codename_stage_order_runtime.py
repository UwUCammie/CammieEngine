"""Execute StageHelper's real anchor insertion and actor-rebinding methods."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from test_difficulty_visual_fallback import extract_method

ROOT = Path(__file__).resolve().parents[2]


class CodenameStageOrderRuntimeTest(unittest.TestCase):
    def test_duplicate_anchors_occurrences_and_replacements_keep_ownership(self):
        source = (ROOT / "source/StageHelper.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public function setCodenamePlacement(", "public function getCodenamePlacement(",
            "public function addCodenameAnchor(", "public function addCodenameProp(",
            "function insertCodenameActor(", "public function placeCodenameActor(",
            "public function rebindCodenameActor(", "public function clearStage("))
        fields = "\n".join(line.strip() for line in source.splitlines()
                           if "var codename" in line)
        fixture = """import haxe.Json;
import CodenameStagePlacement.CodenameStagePlacementData;
class FlxSprite {
 public var name:String;
 public var visible:Bool = true;
 public var active:Bool = true;
 public var destroyCount:Int = 0;
 public function new(name:String='anchor') this.name=name;
 public function destroy() destroyCount++;
}
class FlxGroup extends FlxSprite {
 public var children:Array<FlxSprite> = [];
 public function forEach(callback:FlxSprite->Void) { for(child in children) callback(child); }
}
class PlayState {
 public static var instance:PlayState;
 public var curStage:StageHarness;
 public var members:Array<FlxSprite> = [];
 public function new() {}
 public function add(sprite:FlxSprite) { if(members.indexOf(sprite)<0) members.push(sprite); }
 public function remove(sprite:FlxSprite, splice:Bool=false) { members.remove(sprite); }
 public function insert(index:Int, sprite:FlxSprite) { members.insert(index,sprite); }
 public function detachStageMember(sprite:FlxSprite) { remove(sprite,true); }
}
class StageHarness {
 public var members:Array<FlxSprite> = [];
 public var elements:Map<String,Dynamic> = [];
 public var functions:Map<String,Dynamic> = [];
 public var presentedCharacters:Map<String,Dynamic> = [];
 public var vSliceCharacterPresentation:Map<String,Dynamic> = [];
 public var characterPoses:Map<String,Dynamic> = [];
 public var group:{clear:Void->Void};
 public function new() { group={clear:function(){members.resize(0);}}; }
 public function add(sprite:FlxSprite) {
  if(members.indexOf(sprite)<0) members.push(sprite);
  if(PlayState.instance.curStage==this) PlayState.instance.add(sprite);
 }
 public function remove(sprite:FlxSprite, splice:Bool=false) {
  members.remove(sprite);
  if(PlayState.instance.curStage==this) PlayState.instance.remove(sprite,true);
 }
""" + fields + methods + """
}
class Main {
 static function assertOrder(expected:Array<FlxSprite>) {
  var live=PlayState.instance.members;
  if(live.length!=expected.length) throw 'member count changed';
  for(i in 0...expected.length) if(live[i]!=expected[i]) throw 'order differs at '+i;
 }
 static function main() {
  var state=new PlayState(); PlayState.instance=state;
  var stage=new StageHarness(); state.curStage=stage;
  if(stage.getCodenamePlacement()!=null) throw 'legacy stage acquired placement';
  var placement=CodenameStagePlacement.toData(CodenameStagePlacement.parse(
   '<stage><character name="special" x="37" camxoffset="12" camyoffset="-7"/><dad x="19"/></stage>'));
  stage.setCodenamePlacement(Json.stringify(placement));
  var installed=stage.getCodenamePlacement();
  if(installed==null || !installed.slots.exists('special')
    || installed.slots.get('dad').x!=19) throw 'stage placement publication failed';
  var pose=stage.characterPoses.get('special');
  if(pose==null || pose.camxoffset!=12 || pose.camyoffset!=-7)
   throw 'stage pose offsets were not published for source scripts';
  var rejected=false;
  try stage.setCodenamePlacement('{}') catch(_:Dynamic) rejected=true;
  if(!rejected || stage.getCodenamePlacement()!=installed)
   throw 'invalid publication replaced current placement';
  var dad=new FlxSprite('dad'); var bf=new FlxSprite('bf'); var gf=new FlxSprite('gf');
  var hud=new FlxSprite('hud');
  for(actor in [gf,dad,bf,hud]) state.add(actor);
  var p0=new FlxSprite('p0'); var p2=new FlxSprite('p2'); var p4=new FlxSprite('p4');
  stage.addCodenameProp(p0,0); var oldAnchor=stage.addCodenameAnchor('same',1);
  stage.addCodenameProp(p2,2); var bfAnchor=stage.addCodenameAnchor('boyfriend',3);
  stage.addCodenameProp(p4,4); var lastAnchor=stage.addCodenameAnchor('same',5);
  var gfAnchor=stage.addCodenameAnchor('girlfriend',6);
  stage.placeCodenameActor(dad,'same'); stage.placeCodenameActor(bf,'boyfriend');
  stage.placeCodenameActor(gf,'girlfriend');
  var extraA=new FlxSprite('repeat'); var extraB=new FlxSprite('repeat');
  stage.placeCodenameActor(extraA,'same'); stage.placeCodenameActor(extraB,'same');
  assertOrder([hud,p0,oldAnchor,p2,bf,bfAnchor,p4,dad,extraA,extraB,lastAnchor,gf,gfAnchor]);
  if(stage.codenameOrderNodes.length!=7 || oldAnchor==lastAnchor
    || oldAnchor.visible || lastAnchor.active) throw 'anchor identity/presentation changed';
  for(actor in [dad,bf,gf,extraA,extraB]) if(stage.members.indexOf(actor)>=0)
    throw 'actor became stage-owned';
  // Native swaps also re-add the other role; restore every bound occurrence.
  state.remove(dad,true); var replacement=new FlxSprite('new-dad'); state.add(replacement);
  state.remove(bf,true); state.add(bf);
  stage.rebindCodenameActor(dad,replacement);
  assertOrder([hud,p0,oldAnchor,p2,bf,bfAnchor,p4,replacement,extraA,extraB,lastAnchor,gf,gfAnchor]);
  if(stage.members.indexOf(replacement)>=0) throw 'replacement became stage-owned';
  state.remove(bf,true); state.add(bf);
  stage.rebindCodenameActor(bf,bf);
  assertOrder([hud,p0,oldAnchor,p2,bf,bfAnchor,p4,replacement,extraA,extraB,lastAnchor,gf,gfAnchor]);
  var unknown=new FlxSprite('unknown'); stage.placeCodenameActor(unknown,'missing-slot');
  if(state.members[state.members.length-1]!=unknown) throw 'unknown slot did not append';
  if(stage.members.indexOf(unknown)>=0) throw 'unbound actor became stage-owned';
  // Removal is reversible, but the stage's ownership ledger must still clean
  // detached unnamed nodes once. Actors and unrelated HUD members survive.
  stage.addCodenameProp(p0,7);
  stage.remove(p0,true);
  stage.clearStage();
  for(sprite in [p0,p2,p4,oldAnchor,bfAnchor,lastAnchor,gfAnchor])
   if(sprite.destroyCount!=1) throw 'stage node was leaked or destroyed twice';
  for(actor in [replacement,bf,gf,extraA,extraB,unknown,hud])
   if(actor.destroyCount!=0 || state.members.indexOf(actor)<0) throw 'stage teardown destroyed actor/HUD';
  if(stage.codenameOrderNodes.length!=0 || stage.members.length!=0) throw 'stage ledger was retained';
  if(stage.getCodenamePlacement()!=null) throw 'stage placement survived cleanup';
  if(stage.characterPoses.exists('special')) throw 'stage pose survived cleanup';
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "--run", "Main"], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
