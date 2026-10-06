"""Executable ordered modifier bridge checks without a game or donor edits."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionModifierExecutionBridgeTest(unittest.TestCase):
    def test_live_order_vector_replacement_and_native_sprite_mutations(self):
        fixture = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTimeline;
class Main {
 static var centerCalls=0;
 static var expectedCenters=0;
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function near(a:Float,b:Float,label:String):Void check(Math.abs(a-b)<0.00001,label+":"+a+" != "+b);
 static function entry(?builtin:String,?path:Float->Float->Float->Float->NightmareVisionModchartVector->Int->Int->Dynamic->NightmareVisionModchartVector,
  ?update:Float->Dynamic->NightmareVisionModchartVector->Int->String->Void):NightmareVisionModifierExecution return {
   builtin:builtin,
   getPosition:path==null?function(t,d,td,b,p,data,player,obj)return p:path,
   updateObject:update==null?function(b,obj,p,player,kind){}:update
  };
 static function sprite(?sustain:Bool=false):Dynamic return {
  active:true,x:0.,y:0.,width:50.,height:100.,frameWidth:50.,frameHeight:100.,
  scale:{x:2.,y:2.},baseScale:{x:2.,y:2.},offset:{x:0.,y:0.},origin:{x:0.,y:0.},
  spriteOffset:{x:0.,y:0.},rgbGraphics:{alpha:1.,flash:0.},
  angle:0.,alpha:0.75,alphaMod:1.,multSpeed:1.,noteData:0,ID:0,
  strumTime:999.,sustainLength:124.,isSustainNote:sustain,isSustainEnd:false,wasGoodHit:false,
  antialiasing:false,animation:{curAnim:{name:sustain?"hold":"Scroll"}},
  marker:"untouched",centerOrigin:function(){centerCalls++;},centerOffsets:function(){}
 };
 static function main():Void {
  var registry=new NightmareVisionModifierRegistry(4);
  var transform=new NightmareVisionModchartTransform(registry);
  var context=new NightmareVisionModchartContext(1280,720,4,112,777,2.5);
  registry.setValue("reverse",1,0);registry.setValue("transformX",13,0);
  var names=["before","reverse","after","transformX","replace"];
  var entries:Map<String,NightmareVisionModifierExecution>=new Map();
  var calls=[];var replacement=new NightmareVisionModchartVector();
  entries.set("before",entry(null,function(t,d,td,b,p,data,player,obj){calls.push("before");p.y=900;return p;}));
  entries.set("reverse",entry("reverse"));entries.set("transformX",entry("transformX"));
  entries.set("after",entry(null,function(t,d,td,b,p,data,player,obj){calls.push("after");near(p.y,594,"reverse interleaved before custom");p.y+=5;return p;}));
  entries.set("replace",entry(null,function(t,d,td,b,p,data,player,obj){calls.push("replace");near(p.x,798,"transform interleaved before custom");near(t,999,"source note time");near(d,20,"visual delta");near(td,30,"time delta");near(b,2.5,"beat");replacement.x=p.x;replacement.y=p.y;replacement.z=3;return replacement;}));
  registry.executionNames=function(player)return names;registry.executionEntry=function(name)return entries.get(name);
  var object=new NightmareVisionModchartObject();object.strumTime=999;
  var result=transform.getPositionInto(context,object,20,30,2.5,new NightmareVisionModchartVector());
  check(result==replacement && calls.join(",")=="before,after,replace","ordered replacement identity");near(result.y,599,"after reverse mutation");
  calls=[];names=["before","reverse"];result=transform.getPositionInto(context,object,20,30,2.5,new NightmareVisionModchartVector(),["reverse"]);near(result.y,900,"name exclusion");
  var live=sprite();object.nativeObject=live;names=["append"];
  entries.set("append",entry(null,function(t,d,td,b,p,data,player,obj){names.push("disable");return p;}));
  entries.set("disable",entry(null,function(t,d,td,b,p,data,player,obj){calls.push("disable");obj.active=false;names.push("unreachable");return p;}));
  entries.set("unreachable",entry(null,function(t,d,td,b,p,data,player,obj){throw "inactive callback ran";return p;}));
  transform.getPositionInto(context,object,0,0,0,new NightmareVisionModchartVector());check(calls.indexOf("disable")>=0,"live appended entry executes");
  var untouched=new NightmareVisionModchartVector(2,3,4);check(transform.getPositionInto(context,object,0,0,0,untouched)==untouched && untouched.x==2 && untouched.z==4,"inactive object retains supplied vector");
  // Native renderer callbacks observe prior builtin changes and persist source edits.
  live.active=true;names=["early","mini","late"];
  registry.setValue("mini",0.5,0);entries.set("mini",entry("mini"));
  var kindCalls=[];var times=[];
  entries.set("early",entry(null,function(t,d,td,b,p,data,player,obj){times.push(t);check(obj==live,"actual native sprite argument");return p;},function(b,obj,p,player,kind){check(centerCalls==expectedCenters,"no early source centering");obj.scale.x=99;obj.angle=12;obj.marker="changed";}));
  entries.set("late",entry(null,null,function(b,obj,p,player,kind){check(centerCalls==expectedCenters,"intermediate flush must not center");near(obj.scale.x,1,"mini interleaved before live callback");kindCalls.push(kind);obj.scale.x=3;obj.angle=21;obj.x+=7;obj.alphaMod=0.35;obj.multSpeed=4;obj.rgbGraphics.flash=0.6;obj.alpha=0.2;}));
  var renderer=new NightmareVisionModchartRenderer(transform);
  renderer.updateNote(context,live,0,0,0,0,0,0);check(centerCalls==1,"final centering exactly once");
  near(live.scale.x,3,"custom scale retained");near(live.angle,21,"custom angle retained");near(live.alphaMod,0.35,"custom alphaMod retained");near(live.multSpeed,4,"custom speed retained");near(live.rgbGraphics.flash,0.6,"custom graphics retained");near(live.alpha,0.2,"unowned alpha retained");check(live.marker=="changed","arbitrary sprite mutation retained");
  for(kind in ["receptor","noteSplash","sustainSplash"]) {
   expectedCenters=centerCalls;live=sprite();if(kind=="receptor")renderer.updateReceptor(context,live,0);else renderer.updateSplash(context,live,kind,0,0);
   near(live.scale.x,3,"all callback kinds native scale");
  }
  check(kindCalls.join(",")=="note,receptor,noteSplash,sustainSplash","all object callback kinds");
  expectedCenters=centerCalls;live=sprite(true);times=[];renderer.updateNote(context,live,0,0,0,20,30,3.2);
  check(times.length==2 && times[0]==999 && times[1]==1123,"sustain endpoint source times");
  // Main returned vectors remain script-owned; the explicit source sustain endpoint is pooled.
  live=sprite();names=["retained"];
  var retainedHead:NightmareVisionModchartVector=null;var retainedTail:NightmareVisionModchartVector=null;
  entries.set("retained",entry(null,function(t,d,td,b,p,data,player,obj){
   var result=NightmareVisionModchartVector.get(p.x+9,p.y+4,2);
   if(t==999)retainedHead=result;else retainedTail=result;
   return result;
  },function(b,obj,p,player,kind){obj.baseScale.x=5;obj.baseScale.y=6;}));
  var liveState=renderer.updateNote(context,live,0,0,0,20,30,3.2);
  check(retainedHead.x!=0 && retainedHead.z==2,"note head replacement must not be put implicitly");
  near(liveState.baseScaleX,5,"live baseScale X retained in visual offsets");near(liveState.baseScaleY,6,"live baseScale Y retained in visual offsets");
  live=sprite();renderer.updateReceptor(context,live,0);check(retainedTail.x!=0 && retainedTail.z==2,"receptor replacement must not be put implicitly");
  live=sprite(true);renderer.updateNote(context,live,0,0,0,20,30,3.2);
  check(retainedHead.x!=0 && retainedTail.x==0 && retainedTail.y==0 && retainedTail.z==0,"only source sustain endpoint returned vector is put");
  // Source-facing manager methods share formulas but never overwrite an outer request snapshot.
  expectedCenters=centerCalls;live=sprite();names=["recursive","reverse"];
  var recursiveCalls=0;
  entries.set("recursive",entry(null,function(t,d,td,b,p,data,player,obj){
   recursiveCalls++;check(data==0,"outer data retained across recursive request");
   var nested=renderer.evaluatePosition(context,obj,"note",1,player,456,20,30,b,["recursive"],new NightmareVisionModchartVector());
   near(nested.x,897,"nested supplied direction");near(nested.y,594,"nested excluded source path");
   check(t==123 && data==0,"outer source arguments retained");return p;
  }));
  var supplied=new NightmareVisionModchartVector();var evaluated=renderer.evaluatePosition(context,live,"note",0,0,123,20,30,2.5,null,supplied);
  check(evaluated==supplied && recursiveCalls==1,"public position identity and finite recursion");
  renderer.applyObject(context,live,"note",0,2.5,evaluated);
  check(recursiveCalls==1,"public updateObject must not evaluate position again");
  near(live.x,760,"public source centering");
  // Source note map retains its builtin instance even when a same-name misc replaces global values.
  var duplicateRegistry=new NightmareVisionModifierRegistry(4);
  duplicateRegistry.valueBridge=function(name,player)return 0.;
  duplicateRegistry.executionNames=function(player)return ["reverse"];
  var noteReverse=entry("reverse");noteReverse.value=function(player)return 1.;noteReverse.subValue=function(name,player)return 0.;
  duplicateRegistry.executionEntry=function(name)return noteReverse;
  var duplicateTransform=new NightmareVisionModchartTransform(duplicateRegistry);
  near(duplicateTransform.getPosition(context,new NightmareVisionModchartObject(),20,30,0).y,594,"resolved builtin instance values beat global duplicate lookup");
  // Source follows the shared tail-state pointer, not the head's separate splash.
  names=[];live=sprite(true);live.wasGoodHit=true;
  var directSplash:Dynamic={angle:17.,alive:true};var sharedSplash:Dynamic={angle:23.,alive:false};
  live.sustainSplash=directSplash;live.tailState={splash:sharedSplash};live.playField={trackSustainSplashes:false};
  var tracked=renderer.updateNote(context,live,0,0,0,50,100,200,2.5,null);
  near(sharedSplash.angle,23,"source tracking disabled");near(directSplash.angle,17,"source head pointer independent");
  live.playField.trackSustainSplashes=true;
  tracked=renderer.updateNote(context,live,0,0,0,50,100,200,2.5,null);
  near(sharedSplash.angle,tracked.holdAngle,"source tail pointer follows even when not alive");near(directSplash.angle,17,"source head pointer still independent");
  live.tailState.splash=null;sharedSplash.angle=29;
  renderer.updateNote(context,live,0,0,0,50,100,200,2.5,null);near(directSplash.angle,17,"missing shared pointer does not invent link");
  renderer.release(live);renderer.destroy();
  // Dimension finalization preserves values and registry identity; timeline enrolls dynamically.
  var dimensions=new NightmareVisionModifierRegistry(1,1,false);dimensions.registerDefaultModifiers();dimensions.setValue("mini",0.3,0);dimensions.configureDimensions(3,4);
  near(dimensions.value("mini",0),0.3,"existing value preserved");near(dimensions.value("mini",3),0,"new lane initialized");check(dimensions.keys==3 && dimensions.players==4,"live dimensions");
  var source=new NightmareVisionModifierRegistry(1,1,false);var values:Map<String,Float>=new Map();values.set("custom",0);
  source.hasNameBridge=function(name)return values.exists(name);source.valueBridge=function(name,player)return values.get(name);source.setValueBridge=function(name,value,player)values.set(name,value);
  var timeline=new NightmareVisionModchartTimeline(source);timeline.registerName("custom");timeline.queueSet(2,"custom",0.7);timeline.registerName("custom");timeline.update(2);near(values.get("custom"),0.7,"dynamic timeline source bridge");timeline.destroy();
  trace("NV_MODIFIER_EXECUTION_BRIDGE_OK");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            work = Path(temp)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "-cp", str(ROOT / ".haxelib/flixel/6,1,2"), "-main", "Main", "--interp"], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_MODIFIER_EXECUTION_BRIDGE_OK", result.stdout)
