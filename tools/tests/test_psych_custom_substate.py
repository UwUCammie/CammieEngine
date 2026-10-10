"""Exercise the real script substate lifecycle with a small Flixel clock stub."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychCustomSubstateTest(unittest.TestCase):
    def test_callbacks_are_ordered_once_and_queued_open_has_no_callbacks(self):
        files = {
            'flixel/FlxG.hx': r'''
package flixel;
class FlxG {
 public static var camera={followLerp:1.0};public static var sound:{music:Dynamic}={music:null};
 public static var cameras:{list:Array<Dynamic>}={list:['game','hud']};
}
''',
            'flixel/FlxSubState.hx': r'''
package flixel;
class FlxSubState {
 public var bgColor:Int;
 public var cameras:Array<Dynamic>;
 public var destroyed:Bool=false;
 public function new() {}
 public function add(o:Dynamic):Dynamic return o;public function insert(p:Int,o:Dynamic):Dynamic return o;
 public function create():Void { Main.order.push('superCreate'); }
 public function update(elapsed:Float):Void { Main.order.push('superUpdate:'+elapsed); }
 public function destroy():Void {
  if (destroyed) throw 'super destroy twice';
  destroyed=true;
  Main.order.push('superDestroy');
 }
}
''',
            'MusicBeatSubstate.hx': 'class MusicBeatSubstate extends flixel.FlxSubState {public function new(){super();}}',
            'PsychRuntimeBindings.hx': "class PsychRuntimeBindings {public static function publish(h:PlayState,n:String,v:Dynamic,f:String):Void h.setAllHaxeVar(n,v);public static function dispatch(h:PlayState,n:String,a:Array<Dynamic>):Void h.callAllHScript(n,a);}",
            'MusicBeatState.hx': 'class MusicBeatState {public static function getVariables():Map<String,Dynamic> return [];}',
            'flixel/FlxObject.hx': 'package flixel; class FlxObject {public function new(){}}',
            'PlayState.hx': r'''
class PlayState {
 public static var instance:PlayState;public var persistentUpdate:Bool;public var persistentDraw:Bool;public var paused:Bool;public function pauseVocals():Void{}public function closeSubState():Void{}public function compatOpenCustomSubstate(n:String,p:Bool,s:Bool):Void{}public function setAllHaxeVar(n:String,v:Dynamic):Void{}public function callAllHScript(n:String,a:Array<Dynamic>):Void{}public function psychCustomSubstateFinished(s:PsychCustomSubstate):Void{}
 public function new() {}
 public function psychCustomSubstateCreate(s:PsychCustomSubstate):Void {if(PsychCustomSubstate.instance!=s)throw 'create publication order';Main.order.push('create:'+s.customName);}
 public function psychCustomSubstateCreatePost(s:PsychCustomSubstate):Void Main.order.push('createPost:'+s.customName);
 public function psychCustomSubstateUpdate(s:PsychCustomSubstate,e:Float):Void Main.order.push('update:'+e);
 public function psychCustomSubstateUpdatePost(s:PsychCustomSubstate,e:Float):Void Main.order.push('updatePost:'+e);
 public function psychCustomSubstateDestroy(s:PsychCustomSubstate):Void {if(PsychCustomSubstate.instance!=s)throw 'destroy publication order';Main.order.push('destroy:'+s.customName);}
}
''',
            'Main.hx': r'''
class Main {
 public static var order:Array<String>=[];
 static function check(ok:Bool, why:String):Void if(!ok) throw why;
 static function main():Void {
  var owner=new PlayState();
  var queued=new PsychCustomSubstate('queued',owner,true,false);
  check(queued.cameras.length==1 && queued.cameras[0]=='hud','substate camera');
  check(PsychCustomSubstate.instance==null,'queued substate published too early');
  queued.cancelBeforeCreate();
  check(order.join(',')=='superDestroy','queued open dispatched source callbacks');
  order=[];
  var s=new PsychCustomSubstate('pause',owner,true,false);
  s.create();check(PsychCustomSubstate.instance==s,'created substate not published');s.update(.25);s.notifyBeforeParentDestroy();s.destroy();check(PsychCustomSubstate.instance==null,'destroyed substate still published');
  check(order.join(',')=='create:pause,superCreate,createPost:pause,update:0.25,superUpdate:0.25,updatePost:0.25,destroy:pause,superDestroy',
   'callback order or duplicate destroy: '+order.join(','));
  order=[];
  var old=new PsychCustomSubstate('old',owner,false,false);
  old.create();old.destroy();
  var next=new PsychCustomSubstate('next',owner,false,false);
  next.create();next.destroy();
  check(order.join(',')=='create:old,superCreate,createPost:old,destroy:old,superDestroy,create:next,superCreate,createPost:next,destroy:next,superDestroy',
   'replacement lifecycle: '+order.join(','));
 }
}
''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            folder = Path(work)
            for name, data in files.items():
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(data, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder), '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_dispatch_is_owned_by_substate_clock(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        bridge = (ROOT / 'source/EngineCompat.hx').read_text()
        self.assertIn("callAllHScript('customSubstateUpdatePost', [state.customName, elapsed])", source)
        self.assertNotIn("callAllHScript('customSubstateUpdate', [compatCustomSubstateName", source)
        self.assertIn("case 'oncustomsubstateupdatepost' | 'customsubstateupdatepost'", bridge)
        self.assertRegex(source, r'if \(compatCustomSubstateOpen\) \{\s*updateNightmareVisionScreenUnderlay\(\);\s*dispatchNightmareVisionUpdatePost\(sourceBatch\);\s*return;')
        self.assertIn('resumePsychCustomTimeline();', source)
        self.assertIn('subState == compatCustomSubstate && !compatCustomSubstate.sourceLifecycle', source)
        self.assertIn('if (!psychSourcePause && !resumePsychCustom && startTimer != null && !startTimer.finished)', source)
        self.assertIn('super.openSubState(null);', source)


if __name__ == '__main__':
    unittest.main()
