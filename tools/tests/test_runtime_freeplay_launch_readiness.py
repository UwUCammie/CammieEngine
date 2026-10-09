"""Real Freeplay smoke observations must respect the menu's readiness gate."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_nightmare_vision_psych_audio_getter import extract_method

ROOT = Path(__file__).resolve().parents[2]

class RuntimeFreeplayLaunchReadinessTest(unittest.TestCase):
    def test_list_rebuild_starts_a_new_bounded_search(self):
        method=extract_method((ROOT / "source/RuntimeSmokeHarness.hx").read_text(), "static function freeplayTargetSearchExpired(")
        main='class Main {static var freeplayTargetMissingSince:Float=-1;'+method+"""
        static function main(){
          if(freeplayTargetSearchExpired("target",false,false,0))throw "initial search";
          if(freeplayTargetSearchExpired("target",false,false,19999))throw "early failure";
          if(!freeplayTargetSearchExpired("target",false,false,20000))throw "missing target must time out";
          if(freeplayTargetSearchExpired("target",true,false,500000))throw "found while locked";
          if(freeplayTargetSearchExpired("target",false,false,500001))throw "refresh cannot consume new search window";
          if(freeplayTargetSearchExpired("target",true,false,500500))throw "reselected target";
          if(freeplayTargetSearchExpired("target",false,false,500501))throw "second rebuild";
          if(!freeplayTargetSearchExpired("target",false,false,520501))throw "removed target stays bounded";
          if(freeplayTargetSearchExpired("target",false,true,600000))throw "accepted target";
          if(freeplayTargetSearchExpired("",false,false,700000))throw "ordinary browsing";
        }}"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work=Path(directory);(work/"Main.hx").write_text(main,encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",directory,"--main","Main","--interp"],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_import_wait_does_not_extend_gameplay_sample(self):
        method=extract_method((ROOT / "source/RuntimeSmokeHarness.hx").read_text(), "static function initialWindowMs():Int")
        main='class Main {static var cfg:{durationMs:Int,freeplay:Bool,freeplayAcceptSong:String,freeplayWaitMs:Int}; static function config() return cfg;'+method+'''
        static function main(){
          cfg={durationMs:20000,freeplay:true,freeplayAcceptSong:"target",freeplayWaitMs:1800000};
          if(initialWindowMs()!=1800000||config().durationMs!=20000)throw "separate import/gameplay windows";
          cfg.freeplayAcceptSong="";if(initialWindowMs()!=20000)throw "ordinary menu timing changed";
          cfg.freeplayAcceptSong="target";cfg.freeplay=false;if(initialWindowMs()!=20000)throw "direct gameplay timing changed";
          cfg.freeplay=true;cfg.freeplayWaitMs=0;if(initialWindowMs()!=20000)throw "default timing changed";
        }}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work=Path(directory);(work/"Main.hx").write_text(main,encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",directory,"--main","Main","--interp"],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_observes_authoritative_row_and_waits_before_single_confirmation(self):
        source = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        observation = extract_method(source, "static function acceptObservation():Dynamic")
        start = source.index("var selectionReady = observation.availability")
        end = source.index("\n\t\t\tif (cfg.freeplayLeaveMs", start)
        gate = source[start:end]
        main = r'''
class FlxG {public static var state:Dynamic;}
class DifficultyManager {public static function getDiffName(i:Int):String return "normal";}
class FakeState {
 public static var curSelected=0;public static var curDifficulty=1;
 public var songs:Array<Dynamic>=[{songName:"generated",displayTitle:"Generated",sourceLabel:"Owner"}];
 public var hxcConfirmToken=0;public var queries=0;
 public var decision:Dynamic={ready:false,state:"checking",reason:"Inspecting receipt"};
 public function new(){}
 public function rowAvailabilityDecision(index:Int):Dynamic {if(index!=0)throw "wrong row";queries++;return decision;}
}
class Main {
 static var acceptInitiated=false;static var accepts=0;static var emitted=0;
 static function emit(name:String,data:Dynamic){emitted++;}
 static function simulateAccept(){accepts++;}
 OBSERVATION
 static function tick(observation:Dynamic,acceptDue:Bool,popup:Dynamic){GATE}
 static function check(value:Bool,message:String){if(!value)throw message;}
 static function main(){
  var state=new FakeState();FlxG.state=state;
  var pending=acceptObservation();
  check(pending.availability==state.decision&&state.queries==1,"actual row decision is observed without a substitute gate");
  check(pending.song=="generated"&&pending.difficultyName=="normal","selection context retained");
  tick(pending,true,null);check(accepts==0&&!acceptInitiated,"pending import cannot consume the only accept");
  state.decision={ready:true,state:"ready",reason:""};var ready=acceptObservation();
  tick(ready,false,null);tick(ready,true,{});tick({},true,null);
  check(accepts==0,"not due, popup or unknown readiness cannot accept");
  tick(ready,true,null);tick(ready,true,null);
  check(accepts==1&&emitted==1&&acceptInitiated,"ready row confirmed exactly once");
 }
}
'''.replace("OBSERVATION", observation).replace("GATE", gate)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work=Path(directory)
            (work / "Main.hx").write_text(main,encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",str(work),"--main","Main","--interp"],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == "__main__":
    unittest.main()
