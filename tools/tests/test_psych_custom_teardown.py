"""Parent teardown owns mounted children and abandoned Flixel queued targets."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import ROOT, HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method

class PsychCustomTeardownTest(unittest.TestCase):
 def test_source_close_order_and_pending_ownership(self):
  host=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  method=extract_method(host, 'function destroyPsychCustomSubstates()')
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/states/PlayState.hx'],text=True)
  source=extract_method(extract_method(donor,'override function destroy()'), 'if (psychlua.CustomSubstate.instance != null)')
  source=source.replace('psychlua.CustomSubstate.instance','PsychCustomSubstate.instance')
  destroy=extract_method(host,'override public function destroy()')
  self.assertLess(destroy.index('destroyPsychCustomSubstates();'),destroy.index('psychVideoHostDestroyed = true'))
  self.assertLess(destroy.index('destroyPsychCustomSubstates();'),destroy.index("callAllHScript('destroy'"))
  files={
   'Base.hx':"class Base {public var subState:PsychCustomSubstate;public var _requestedSubState:PsychCustomSubstate;public function new(){}public function openSubState(s:PsychCustomSubstate):Void {_requestedSubState=s;}public function closeSubState():Void Main.log.push('close');public function resetSubState():Void {Main.log.push('reset');if(subState!=null)subState.destroy();subState=_requestedSubState;_requestedSubState=null;}}",
   'PsychCustomSubstate.hx':"class PsychCustomSubstate {public static var instance:PsychCustomSubstate;public var sourceLifecycle:Bool;public var lifecycleCreated:Bool;public var id:String;public var disposed:Bool=false;public var notified:Bool=false;public function new(i:String,s:Bool,c:Bool){id=i;sourceLifecycle=s;lifecycleCreated=c;}public function notifyBeforeParentDestroy():Void {if(!notified){notified=true;Main.log.push('notify:'+id);}}public function cancelBeforeCreate():Void {if(disposed)throw 'double destroy';disposed=true;Main.log.push('cancel:'+id);}public function destroy():Void {notifyBeforeParentDestroy();disposed=true;instance=null;Main.log.push('destroy:'+id);}}",
   'PlayState.hx':'class PlayState extends Base {public var compatCustomSubstate:PsychCustomSubstate;public function new(){super();}public function psychCustomSubstateFinished(s:PsychCustomSubstate):Void {if(compatCustomSubstate==s)compatCustomSubstate=null;}public '+method+' public function donor():Void {'+source+'}}',
   'Main.hx':r"""class Main {public static var log:Array<String>;static function check(b:Bool,m:String):Void if(!b)throw m;static function run(donor:Bool):String {log=[];var p=new PlayState();p.subState=new PsychCustomSubstate('mounted',true,true);p.compatCustomSubstate=p.subState;PsychCustomSubstate.instance=p.subState;if(donor)p.donor();else p.destroyPsychCustomSubstates();return log.join('|');}static function main(){check(run(true)==run(false),'pinned normal parent close order');for(source in [false,true])for(queuedOnly in [false,true])for(direct in [false,true]){log=[];var p=new PlayState();var mounted=new PsychCustomSubstate('mounted',source,true);var queued=new PsychCustomSubstate('queued',source,false);p.subState=queuedOnly?null:mounted;PsychCustomSubstate.instance=p.subState;p._requestedSubState=queued;p.compatCustomSubstate=direct?null:queued;p.destroyPsychCustomSubstates();check(queued.disposed&&!queued.lifecycleCreated,'abandoned queue lifetime');check(p.compatCustomSubstate==null&&p._requestedSubState==null,'pending references');if(!queuedOnly){check(mounted.notified,'mounted callback');check(mounted.disposed==source,'source closes before script release; historical native disposal remains deferred');}check(log.filter(function(s)return s=='cancel:queued').length==1,'one cancellation');}trace('custom-teardown:9');}}"""
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,data in files.items():(work/name).write_text(data,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'--run','Main'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('custom-teardown:9',result.stdout)
