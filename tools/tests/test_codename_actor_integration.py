"""Run the PlayState actor integration methods with lightweight Haxe actors."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    start = source.index("\tfunction " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        depth += (source[i] == "{") - (source[i] == "}")
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError(name)


class CodenameActorIntegrationTest(unittest.TestCase):
    def test_current_stage_baseline_and_exact_primary(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(method(source, name) for name in (
            "rememberCodenameActor", "placeCodenameRuntimeActor",
            "codenameActorPlacementModel", "codenameStageIdentityMatches",
            "initializeCodenameActors", "reapplyCodenameActors"))
        fixture = r'''
import haxe.ds.ObjectMap;
import CodenameStagePlacement.CodenameStagePlacementData;
class EngineCompat {
 public static function resolveStageAlias(name:String):String
  return name != null && name.toLowerCase()=="halloween" ? "spooky" : name;
}
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float=1,y:Float=1) {this.x=x;this.y=y;}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Character {
 public var curCharacter:String; public var isPlayer:Bool;
 public var x:Float=0; public var y:Float=0;
 public var alpha:Float=1; public var angle:Float=5;
 public var scale=new Point(2,3); public var skew=new Point(1,2);
 public var scrollFactor=new Point(); public var cameraPosition:Array<Float>=[7,8];
 public var characterType:String=""; public var cameras:Array<Dynamic>=[];
 public var codenameLiveDefinition:Dynamic=null;
 public var globalOffset=new Point(0,0); public var cameraOffset=new Point(7,8); public var playerOffsets:Bool=false;
 public static var sourceActors=false;
 public var destroyed=false;
 public function new(x:Float,y:Float,name:String,isPlayer:Bool,?construction:Dynamic) {
  this.curCharacter=name; this.isPlayer=isPlayer;
  if(sourceActors) { codenameLiveDefinition={}; globalOffset.set(4,6); }
  setPosition(x,y);
 }
 public static function characterExists(name:String):Bool return name!="missing";
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
 public function syncHxcPosition():Void {}
 public function destroy():Void destroyed=true;
}
class Song {
 public static function characterVisualRegistryEntryInManifest(name:String,root:String):Dynamic
  return {codenameCharacter:{x:4.0,y:6.0,playerOffsets:false}};
}
class StageHelper {
 public var model:CodenameStagePlacement.CodenameStagePlacementData;
 public var authoredName:String="stage";
 public var placed:Array<String>=[];
 public function new(model) this.model=model;
 public function getCodenamePlacement() return model;
 public function placeCodenameActor(actor:Character,key:String):Void
  placed.push(actor.curCharacter+":"+key+":"+actor.x);
}
class Main {
 static var SONG:Dynamic={stage:"owned-stage"};
 var curStage:StageHelper;
 var codenameActors:CodenameActorRuntime<Character>=null;
 var unspawnNotes:Array<Dynamic>=[];
 var notes:Dynamic=null;
 var codenameActorBaselines=new ObjectMap<Character,Dynamic>();
 var boyfriend:Character; var dad:Character; var gf:Character;
 var camGame:Dynamic={};
 var plan:CodenameActorPlan;
 var runtimeSmokeOwnedDestroyCalls:Int=0;
 function runtimeSmokeActorTracking():Bool return false;
 function bindCodenameNoteLine(note:Dynamic):Void {}
 var added:Array<Character>=[];
 var initializedInputPlan:CodenameActorPlan=null;
 function initializeCodenameInputLines(value:CodenameActorPlan):Void {
  if(codenameActors==null || codenameActors.lineCharacters(0).length!=2)
   throw "input initialized before actor materialization";
  initializedInputPlan=value;
 }
 public function new(plan:CodenameActorPlan,stage:StageHelper,bfName:String="hero") {
  this.plan=plan; curStage=stage;
  boyfriend=new Character(0,0,bfName,false);
  dad=new Character(0,0,"foe",false);
  gf=new Character(0,0,"gf",false);
 }
 function codenameSelectedRoot():String return "owner";
 function getCodenameActorPlan():CodenameActorPlan return plan;
 function codenameCharacterConstruction(_record:Dynamic):Dynamic return null;
 function add(actor:Character):Character {added.push(actor);return actor;}
 function remove(actor:Character,splice:Bool):Character {added.remove(actor);return actor;}
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
''' + methods + r'''
 static function main():Void {
  var first=CodenameStagePlacement.parse(
   '<stage><char name="hero" x="10" spacingx="35" camxoffset="11" camyoffset="13" flip="false" scale="2" alpha="0.5"/>'
   +'<char name="Bambino" x="330"/>'
   +'<dad x="50"/><girlfriend x="90"/></stage>');
  var second=CodenameStagePlacement.parse(
   '<stage><char name="hero" x="100" spacingx="20" camxoffset="-5" camyoffset="-7" flip="false" scale="3" alpha="0.25"/>'
   +'<dad x="60"/><girlfriend x="95"/></stage>');
  var entry:Dynamic={stagePlacement:CodenameStagePlacement.toData(first),nativeCharacters:{},lines:[
   {role:"player",type:1,position:null,characters:["hero","hero"]},
   {role:"opponent",type:0,position:null,characters:["foe"]},
   {role:"gf",type:2,position:null,characters:["gf"]}]};
  Reflect.setField(entry.nativeCharacters,"hero","hero");
  Reflect.setField(entry.nativeCharacters,"foe","foe");
  Reflect.setField(entry.nativeCharacters,"gf","gf");
  var plan=new CodenameActorPlan(entry);
  var state=new Main(plan,new StageHelper(second));
  state.initializeCodenameActors();
  check(state.codenameActors!=null && state.added.length==1,"only extra constructed");
  check(state.initializedInputPlan==plan,"input plan not initialized");
  var chars=state.codenameActors.lineCharacters(0);
  check(chars.length==2 && chars[0]==state.boyfriend && chars[1]!=chars[0],
   "exact primary alias and duplicate instance");
  var gfChars=state.codenameActors.lineCharacters(2);
  check(gfChars.length==1 && gfChars[0]==state.gf
   && !state.codenameActors.find(2,0).owned,
   "type-2 GF line did not borrow the exact native girlfriend primary");
  check(chars[0].x==104 && chars[1].x==124,"current stage placement and occurrence spacing");
  check(chars[1].scale.x==6 && chars[1].alpha==0.25 && chars[1].angle==5,
   "presentation composed from constructor baseline");
  state.reapplyCodenameActors();
  check(chars[1].x==124 && chars[1].scale.x==6 && chars[1].alpha==0.25,
   "reapply does not accumulate presentation");
  state.curStage=new StageHelper(first); state.reapplyCodenameActors();
  check(chars[0].x==14 && chars[1].x==49 && chars[1].scale.x==4
   && chars[1].alpha==0.5,"replacement uses its stage model, not initial snapshot");
  state.curStage=new StageHelper(null); state.reapplyCodenameActors();
  check(chars[1].x==49 && chars[1].scale.x==4,
   "missing replacement placement retains actor without initial fallback");
  Character.sourceActors=true;
  var live=new Main(plan,new StageHelper(first));
  live.initializeCodenameActors();
  var liveChars=live.codenameActors.lineCharacters(0);
  check(liveChars[0].x==10 && liveChars[1].x==45 && liveChars[1].y==0,
   "live source world position included draw offsets");
  check(liveChars[1].cameraOffset.x==18 && liveChars[1].cameraOffset.y==21,
   "live source stage camera offset missing");
  live.reapplyCodenameActors();
  check(liveChars[1].cameraOffset.x==18 && liveChars[1].cameraOffset.y==21,
   "live stage camera offsets accumulated");
  live.curStage=new StageHelper(second); live.reapplyCodenameActors();
  check(liveChars[1].x==120 && liveChars[1].cameraOffset.x==2 && liveChars[1].cameraOffset.y==1,
   "replacement retained old stage camera/world offsets");
  live.curStage=new StageHelper(first); live.reapplyCodenameActors();
  check(liveChars[1].x==45 && liveChars[1].cameraOffset.x==18 && liveChars[1].cameraOffset.y==21,
   "A/B/A source camera baseline drifted");
  Character.sourceActors=false;
  var mismatch=new Main(plan,new StageHelper(first),"edited-hero");
  mismatch.initializeCodenameActors();
  check(mismatch.codenameActors==null && mismatch.added.length==0,
   "edited primary mismatch forbids extra construction");
  var unsupported=CodenameStagePlacement.fromData(CodenameStagePlacement.toData(first));
  unsupported.unsupported.push("stage-script");
  var guarded=new Main(plan,new StageHelper(unsupported));
  guarded.initializeCodenameActors();
  check(guarded.codenameActors!=null && guarded.initializedInputPlan==plan,
   "unresolved placement must not suppress source-line initialization");
  check(guarded.added.length==0,
   "unresolved current stage cannot leave an extra actor at origin");
  var guardedChars=guarded.codenameActors.lineCharacters(0);
  check(guardedChars.length==2 && guardedChars[0]==guarded.boyfriend && guardedChars[1]==null,
   "unsupported placement keeps the exact primary and leaves unsafe extras absent");
  check(unsupported.unsupported.indexOf("stage-script")>=0
   && guarded.codenameActors.diagnostics.join(",").indexOf("placement-failed:0:1")>=0,
   "unsupported placement remains diagnosed after source lines initialize");

  var fallbackEntry:Dynamic={stage:"owned-stage",nativeStage:"owned-stage",
   stagePlacement:CodenameStagePlacement.toData(first),nativeCharacters:{},lines:[
    {role:"player",type:1,position:null,characters:["hero","hero"]},
    {role:"opponent",type:0,position:null,characters:["foe"]},
    {role:"gf",type:2,position:null,characters:["gf"]},
    {role:"extra",type:3,position:null,characters:["Bambino"]}]};
  for(id in ["hero","foe","gf","Bambino"])
   Reflect.setField(fallbackEntry.nativeCharacters,id,id.toLowerCase());
  var fallbackPlan=new CodenameActorPlan(fallbackEntry,
   "function postCreate(){ dad.alpha = 0; }");
  check(fallbackPlan.staticXmlPlacementForExtras,
   "primary actor script writes should preserve unrelated XML slots");
  var noStageModel=new Main(fallbackPlan,new StageHelper(null));
  noStageModel.curStage.authoredName="owned-stage";
  check(noStageModel.codenameActorPlacementModel(fallbackPlan)==fallbackPlan.stagePlacement,
   "the selected owner XML model should serve its matching stage without a live model");
  noStageModel.initializeCodenameActors();
  var extra=noStageModel.codenameActors.lineCharacters(3);
  check(extra.length==1 && extra[0]!=null && extra[0].curCharacter=="bambino"
   && extra[0].x==334,
   "a no-model initial stage should materialize its verified XML extra actor in the authored line");
  noStageModel.curStage.authoredName="later-stage";
  check(noStageModel.codenameActorPlacementModel(fallbackPlan)==null,
   "selected owner XML placement must not leak onto a different stage");
 }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", str(ROOT / "source"),
                "-cp", str(folder), "--run", "Main"], cwd=ROOT,
                env={**os.environ, "TMPDIR": work}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
