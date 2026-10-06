"""Live EventTimeline comparisons against the pinned donor implementation."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / "fnf_sources/NightmareVision/source/funkin/game/modchart/EventTimeline.hx"


class NightmareVisionEventTimelineContractTest(unittest.TestCase):
    def test_live_public_queues_match_executable_donor(self):
        if not DONOR.is_file():
            self.skipTest("pinned Nightmare Vision donor unavailable")
        donor = re.sub(r"^(package|import)[^\n]*\n", "", DONOR.read_text(), flags=re.M)
        donor = donor.replace("class EventTimeline", "class DonorTimeline")
        fixture = r'''
class NamedEvent extends NightmareVisionBaseEvent {
 public var label:String;public var action:NamedEvent->Float->Void;public var calls=0;
 public function new(label:String,step:Float,?action:NamedEvent->Float->Void){super(step,null);this.label=label;this.action=action;}
 public override function run(step:Float){calls++;if(action!=null)action(this,step);else finished=true;}
}
class NamedMod extends NightmareVisionModEvent {
 public var label:String;public var action:NamedMod->Float->Void;
 public function new(name:String,label:String,step:Float,?action:NamedMod->Float->Void){super(step,name,0,0,null);this.label=label;this.action=action;}
 public override function run(step:Float){if(action!=null)action(this,step);else finished=true;}
}
typedef TimelineSurface={var modEvents:Map<String,Array<NightmareVisionModEvent>>;var events:Array<NightmareVisionBaseEvent>;function addMod(name:String):Void;function addEvent(event:NightmareVisionBaseEvent):Void;function update(step:Float):Void;}
class Main {
 static function check(v:Bool,s:String)if(!v)throw s;
 static function make(host:Bool):TimelineSurface return host?cast new NightmareVisionEventTimeline():cast new DonorTimeline();
 static function labels(list:Array<NightmareVisionBaseEvent>):String return [for(e in list)Std.isOfType(e,NamedEvent)?cast(e,NamedEvent).label:Std.isOfType(e,NamedMod)?cast(e,NamedMod).label:"base"].join(",");
 static function snapshot(t:Dynamic):String {var map:Map<String,Array<NightmareVisionModEvent>>=t.modEvents;var keys=[for(k in map.keys())k];keys.sort(Reflect.compare);return labels(t.events)+"|"+[for(k in keys)k+":"+labels(cast map.get(k))].join(";");}
 static function scenario(host:Bool,which:Int):String {
  var t=make(host);var log:Array<String>=[];
  function event(label:String,step:Float):NamedEvent return new NamedEvent(label,step,function(e,s){log.push(label+"@"+s);e.finished=true;});
  switch(which){
   case 0:
    t.addMod("x");var old:Dynamic=t.modEvents.get("x");t.addEvent(new NamedMod("x","discarded",1));t.addMod("x");check(old.length==1&&t.modEvents.get("x")!=old,"addMod resets by replacement");
    var one=event("one",2);t.addEvent(one);t.addEvent(one);t.addEvent(event("fraction",2.4));t.addEvent(event("fractionEarlier",2.1));t.addEvent(event("late",6));log.push(snapshot(t));t.update(2.2);log.push(snapshot(t));t.update(10);t.update(0);log.push(snapshot(t));
   case 1:
    var mod=new NamedMod("new","mod",3,function(e,s){log.push("mod-before-callback");e.finished=true;});t.addEvent(mod);t.addEvent(mod);t.addEvent(event("callback",3));check(t.modEvents.get("new")[0]==mod,"mod routing identity");t.update(3);log.push(snapshot(t));
    var base=new NightmareVisionBaseEvent(0,null);t.addEvent(base);t.update(5);check(t.events[0]==base&&!base.finished,"base virtual noop retained");
   case 2:
    var ignored=event("ignored",0);ignored.ignoreExecution=true;var done=event("already-finished",0);done.finished=true;t.addEvent(ignored);t.addEvent(done);t.addEvent(event("due",1));t.update(4);ignored.ignoreExecution=false;t.update(4);log.push(snapshot(t));
   case 3:
    // Raw arrays, current property replacement, and current map keys are authoritative.
    t.events=[event("replacement",0)];var map:Map<String,Array<NightmareVisionModEvent>>=[];map.set("raw",[new NamedMod("raw","rawmod",0,function(e,s){log.push("rawmod");e.finished=true;})]);t.modEvents=map;t.update(1);log.push(snapshot(t));
    t.addEvent(event("removed",2));t.events.remove(t.events[0]);t.events.push(event("raw-insert",0));t.update(3);log.push(snapshot(t));
   case 4:
    var outer=new NamedEvent("outer",5,function(e,s){log.push("outer");t.addEvent(event("nested-earlier",0));e.finished=true;});t.addEvent(outer);t.addEvent(event("after",5));t.update(5);log.push(snapshot(t));
   case 5:
    // Repeat sees source cursor changes. Finite callback eventually retires.
    var repeat=new NamedEvent("repeat",2,function(e,s){log.push("repeat"+e.calls);if(e.calls==1)t.events.insert(0,event("inserted",0));else e.finished=true;});t.addEvent(repeat);t.addEvent(event("after",2));t.update(2);log.push(snapshot(t));t.update(2);log.push(snapshot(t));
   case 6:
    var self=new NamedEvent("self-remove",0,function(e,s){log.push("self");t.events.remove(e);e.finished=true;});t.addEvent(self);t.addEvent(event("neighbor",0));t.update(0);log.push(snapshot(t));
   case 7:
    var nested=false;var repeat=new NamedEvent("recursive",0,function(e,s){log.push("recursive"+e.calls);if(!nested){nested=true;t.update(s);}e.finished=true;});t.addEvent(repeat);t.addEvent(event("neighbor",0));t.update(0);log.push(snapshot(t));
   case 8:
    var original:Array<NightmareVisionBaseEvent>=t.events;t.addEvent(new NamedEvent("replace",0,function(e,s){log.push("replace");t.events=[event("new-array",0)];e.finished=true;}));t.addEvent(event("old-array-tail",0));t.update(0);log.push("old="+labels(original));log.push(snapshot(t));t.update(0);log.push(snapshot(t));
   case 9:
    var mod=new NamedMod("x","move-name",0,function(e,s){log.push(e.modName);e.finished=true;});t.addEvent(mod);mod.modName="y";t.update(0);log.push(snapshot(t));
   case 10:
    var event=new NamedEvent("throw",0,function(e,s){log.push("throw");throw "source-error";});t.addEvent(event);t.addEvent(new NamedEvent("blocked",0,function(e,s){log.push("blocked");e.finished=true;}));var error="";try t.update(0)catch(e:Dynamic)error=Std.string(e);check(error=="source-error"&&!event.finished,"default exception propagated without finishing");log.push(snapshot(t));
   case 11:
    var mod=new NamedMod("x","raw-remove",0,function(e,s){log.push("removed-bucket");t.modEvents.remove("x");e.finished=true;});t.addEvent(mod);t.addEvent(event("callback",0));t.update(0);log.push(snapshot(t));
  }
  return log.join("|");
 }
 static function main(){
  for(i in 0...12){var expected=scenario(false,i),actual=scenario(true,i);check(expected==actual,"scenario"+i+":"+actual+" != "+expected);}
  var reports=0;var t=new NightmareVisionEventTimeline(function(e,error){reports++;throw "reporter-error";});var failed=new NightmareVisionCallbackEvent(0,function(e,s){throw "callback-error";},null);var after=new NamedEvent("after",0);t.addEvent(failed);t.addEvent(after);t.update(0);check(reports==1&&failed.finished&&after.finished,"explicit callback-only containment");t.update(1);check(reports==1,"error does not repeat");
  var base=new NamedEvent("base-failure",0,function(e,s){throw "base-error";});t.addEvent(base);var threw=false;try t.update(0)catch(e:Dynamic)threw=Std.string(e)=="base-error";check(threw&&!base.finished,"base exceptions are not contained");
  var mod=new NamedMod("x","mod-failure",0,function(e,s){throw "mod-error";});t=new NightmareVisionEventTimeline(function(e,error){reports++;});t.addEvent(mod);threw=false;try t.update(0)catch(e:Dynamic)threw=Std.string(e)=="mod-error";check(threw&&!mod.finished&&reports==1,"modifier exceptions are not contained");
  var heldEvents=t.events;var heldMap=t.modEvents;var heldBucket=t.modEvents.get("x");var callback=new NightmareVisionCallbackEvent(100,function(e,s){throw "disposed";},null);t.addEvent(callback);t.destroy();t.destroy();check(callback.finished&&mod.finished&&heldEvents.length==0&&heldBucket.length==0&&!heldMap.keys().hasNext(),"destroy releases externally held containers");t.update(200);threw=false;try t.addMod("later")catch(e:Dynamic)threw=true;check(threw,"destroy rejects new buckets");threw=false;try t.addEvent(callback)catch(e:Dynamic)threw=true;check(threw,"destroy rejects new events");
 }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / "DonorTimeline.hx").write_text("typedef BaseEvent=NightmareVisionBaseEvent;\ntypedef ModEvent=NightmareVisionModEvent;\n" + donor)
            (temp / "NightmareVisionBaseEvent.hx").write_text("class NightmareVisionBaseEvent {public var manager:Dynamic;public var executionStep:Float;public var finished=false;public var ignoreExecution=false;public function new(step:Float,manager:Dynamic){executionStep=step;this.manager=manager;}public function run(step:Float):Void{}}")
            (temp / "NightmareVisionModEvent.hx").write_text("class NightmareVisionModEvent extends NightmareVisionBaseEvent {public var modName:String;public function new(step:Float,name:String,value:Float,player:Int,manager:Dynamic){super(step,manager);modName=name;}}")
            (temp / "NightmareVisionCallbackEvent.hx").write_text("class NightmareVisionCallbackEvent extends NightmareVisionBaseEvent {public var callback:Dynamic;public function new(step:Float,callback:Dynamic,manager:Dynamic){super(step,manager);this.callback=callback;}override public function run(step:Float):Void{Reflect.callMethod(null,callback,[this,step]);finished=true;}}")
            (temp / "Main.hx").write_text(fixture)
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", directory, "-main", "Main", "--interp"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-10000:])
