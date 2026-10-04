"""Execute actor-scoped queries and native game-over quote scheduling."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]


class HxcDeathQuoteHostTest(unittest.TestCase):
    def run_haxe(self, text):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(text, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', folder, '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_query_uses_original_actor_and_restores_temporary_binding(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(extract_method(source, marker) for marker in (
            'function hxcCharacterForScope(', 'function hxcCharacterScopeIsActive(',
            'function hxcCharacterRole(', 'function hxcCharacterForRole(',
            'function hxcCharacterMethodIsAuthored(', 'public function hxcCharacterDeathQuote('))
        self.run_haxe(r'''using StringTools;
class Character {
 public var curCharacter:String; public var frames:Dynamic={};
 public function new(id:String) curCharacter=id;
}
class Interp {public var variables:Map<String,Dynamic>=new Map(); public function new() {}}
class HxcScriptDiscovery {public static function normalizeToken(id:String):String return id;}
class Main {
 var hxcCharacterScopeNames:Map<String,String>=new Map();
 var hxcCharacterScopeRoles:Map<String,Array<String>>=new Map();
 var hscriptStates:Map<String,Interp>=new Map();
 var boyfriend:Character; var gf:Character; var dad:Character;
 var hxcGameOverCharacter:Character; var hxcCharacterCallbackActor:Character;
 var hxcCharacterCallbackRole:String=''; var calls:Array<String>=[];
 function new() {boyfriend=new Character('actor');dad=new Character('enemy');}
 function add(scope:String,id:String,role:String,method:Void->Dynamic):Interp {
  var interp=new Interp(); interp.variables.set('getDeathQuote',method);
  hxcCharacterScopeNames.set(scope,id);hxcCharacterScopeRoles.set(scope,[role]);
  hscriptStates.set(scope,interp);return interp;
 }
 function callHscript(name:String,args:Array<Dynamic>,scope:String,optional:Bool,values:Array<Dynamic>):Bool {
  calls.push(scope);var fn:Void->Dynamic=cast hscriptStates.get(scope).variables.get(name);
  values.push(fn());return true;
 }
''' + methods + r'''
 static function main() {
  var s=new Main();var original=s.boyfriend;
  s.hxcGameOverCharacter=new Character('actor');
  var closed=s.add('a-closed','actor','boyfriend',function() return 'wrong');
  closed.variables.set('__compatClosed',true);
  s.add('b-inactive','old','boyfriend',function() return 'wrong');
  s.add('c-foreign','enemy','dad',function() return 'wrong');
  var live=s.add('d-live','actor','boyfriend',function() {
   if(s.hxcCharacterForRole('boyfriend')!=original) throw 'query lost original actor';
   return 'owner/sounds/death.ogg';
  });
  if(!s.hxcCharacterScopeIsActive('d-live')
   || s.hxcCharacterForScope('d-live')[0]!=s.hxcGameOverCharacter) throw 'death actor lost authored scope';
  if(s.hxcCharacterDeathQuote(original)!='owner/sounds/death.ogg'
   || s.calls.join(',')!='d-live') throw 'query crossed actor ownership';
  if(s.hxcCharacterCallbackActor!=null || s.hxcCharacterCallbackRole!=''
   || s.hxcCharacterForRole('boyfriend')!=s.hxcGameOverCharacter) throw 'binding leaked';
  live.variables.set('getDeathQuote',function() return null);
  if(s.hxcCharacterDeathQuote(original)!=null) throw 'explicit null lost';
  live.variables.set('getDeathQuote',function() return 3);
  if(s.hxcCharacterDeathQuote(original)!=null || s.hxcCharacterCallbackActor!=null) throw 'invalid return or error leaked';
  var inherited=live.variables.get('getDeathQuote');
  live.variables.set('__hxcNativeCharacterMethods',['getDeathQuote'=>inherited]);
  var before=s.calls.length;
  if(s.hxcCharacterDeathQuote(original)!=null || s.calls.length!=before) throw 'inherited helper called as override';
  if(s.hxcCharacterDeathQuote(null)!=null || s.hxcCharacterDeathQuote(new Character('actor'))!=null) throw 'unowned query accepted';
 }
}''')

    def test_query_return_values_do_not_become_lifecycle_cancellation(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        begin = source.index('\t\t\tif (returnValues != null && (hxcPayloadStates.get(usehaxe)')
        end = source.index('\n\t\t\tHxcCompatRuntime.commitTallyCallback();', begin)
        capture = source[begin:end]
        self.run_haxe(r'''class Main {
 static function query(hxc:Bool,func_name:String):Array<Dynamic> {
  var hxcPayloadStates=['scope'=>hxc];var usehaxe='scope';
  var returnValues:Array<Dynamic>=[];var returned:Dynamic=true;
''' + capture + r'''
  return returnValues;
 }
 static function main() {
  for(name in ['getDeathQuote','getScreenPosition'])
   if(query(true,name).length!=1) throw 'query return discarded: '+name;
  for(name in ['onCreate','startCountdown','onNoteHit','onPause']) {
   if(query(true,name).length!=0) throw 'void HXC hook cancelled gate: '+name;
   if(query(false,name).length!=1) throw 'legacy/Psych return discarded';
  }
 }
}''')

    def test_gameover_queries_twice_only_when_animation_finishes(self):
        source = (ROOT / 'source/GameOverSubstate.hx').read_text()
        constructor = extract_method(source, 'public function new(')
        setup = extract_method(source, 'function setupDefaultGameOver(')
        self.assertLess(constructor.index('if (sourceMode != 0) return;'),
                        constructor.index('setupDefaultGameOver(player, daBf);'))
        self.assertLess(setup.index('if (codenameInitGameOverScript())'),
                        setup.index('HxcCompatRuntime.bindGameOverCharacter(bf);'))
        self.assertLess(setup.index('HxcCompatRuntime.bindGameOverCharacter(bf);'),
                        setup.index("bf.playAnim('firstDeath')"))
        method = extract_method(source, 'function updateGameoverAnimation(')
        update = extract_method(source, 'override function update(')
        self.assertLess(update.index('updateGameoverAnimation(currentAnim);'), update.rindex('super.update(elapsed);'))
        for marker in ('function endBullshit(', 'override public function destroy('):
            body = extract_method(source, marker)
            self.assertIn('deathquote', body.lower())
        self.run_haxe(r'''using StringTools;
class FlxAnimation {
 public var name='firstDeath-costume';public var curFrame=13;public var finished=false;
 public function new() {}
}
class Actor {
 public var animation:Dynamic={curAnim:new FlxAnimation()};
 public var queries=0;public var quotes:Array<Null<String>>=[];
 public function new() {}
 public function getDeathQuote():Null<String> {queries++;return quotes.length==0?null:quotes.shift();}
}
class Camera {public function new() {}public function follow(target:Dynamic,style:Dynamic,speed:Float):Void {}}
class FlxG {public static var camera=new Camera();}
class RuntimeSmokeHarness {public static function markGameOverPhase(p:String,d:Dynamic):Void {}}
class Main {
 var bf=new Actor();var quoteCharacter=new Actor();var isEnding=false;var gameoverStarted=false;
 var deathQuoteAttempted=false;var deathQuotePlayback:HxcDeathQuotePlayback;
 var camFollow:Dynamic={};var LOCKON=0;var events:Array<String>=[];
 function new() {
  deathQuotePlayback=new HxcDeathQuotePlayback({
   startLoopMusic:function(v:Float) {gameoverStarted=true;events.push('music:'+v);},
   playDeathLoop:function() {bf.animation.curAnim.name='deathLoop-costume';events.push('loop');},
   playQuote:function(path:String,done:Void->Void):Dynamic {events.push(path);return null;},
   canFadeLoopMusic:function() return true,
   fadeLoopMusic:function(a:Float,b:Float,c:Float) {},stopQuote:function(a:Dynamic) {}
  });
 }
 function startGameoverLoop():Void {gameoverStarted=true;events.push('normal');}
''' + method + r'''
 static function main() {
  var s=new Main();s.quoteCharacter.quotes=['gate-early','gate','playback'];
  s.updateGameoverAnimation(s.bf.animation.curAnim);
  if(s.quoteCharacter.queries!=1 || s.events.length!=0) throw 'early source query changed';
  s.bf.animation.curAnim.finished=true;s.updateGameoverAnimation(s.bf.animation.curAnim);
  if(s.quoteCharacter.queries!=3 || s.events.join(',')!='music:0.2,loop,playback') throw 'second query/order lost';
  s.updateGameoverAnimation(s.bf.animation.curAnim);if(s.quoteCharacter.queries!=3) throw 'started quote queried again';
  var n=new Main();n.bf.animation.curAnim.finished=true;n.updateGameoverAnimation(n.bf.animation.curAnim);
  if(n.quoteCharacter.queries!=1 || n.events.join(',')!='normal') throw 'null fallback changed';
  var r=new Main();r.bf.animation.curAnim.finished=true;r.quoteCharacter.quotes=['gate',null,'gate'];
  r.updateGameoverAnimation(r.bf.animation.curAnim);r.updateGameoverAnimation(r.bf.animation.curAnim);
  if(!r.deathQuoteAttempted || r.deathQuotePlayback.hasStarted || r.quoteCharacter.queries!=3
    || r.events.length!=0) throw 'second null did not latch attempt';
  var ending=new Main();ending.isEnding=true;ending.updateGameoverAnimation(ending.bf.animation.curAnim);
  if(ending.quoteCharacter.queries!=0) throw 'ending queried quote';
  var missing=new Main();missing.bf.animation.curAnim=null;missing.updateGameoverAnimation(missing.bf.animation.curAnim);
  if(missing.events.join(',')!='normal' || missing.quoteCharacter.queries!=1) throw 'missing animation fallback changed';
 }
}''')


    def test_custom_substate_order_and_animation_snapshot_are_preserved(self):
        source = (ROOT / 'source/GameOverSubstate.hx').read_text()
        method = extract_method(source, 'override function update(')
        self.run_haxe(r'''class FlxAnimation { public var name='firstDeath';public function new() {} }
class Actor {public var animation:Dynamic={curAnim:new FlxAnimation()};public function new() {}}
class Base {
 public var bf=new Actor();public var events:Array<String>=[];
 public function new() {}
 public function update(e:Float):Void {events.push('super');var next=new FlxAnimation();next.name='deathLoop';bf.animation.curAnim=next;}
}
class RuntimeSmokeHarness {public static var events:Array<String>;public static function tick(e:Float):Bool {events.push('tick');return false;}}
class FlxG {public static var sound:Dynamic={music:{playing:false,time:0.0,stop:function() {}}};}
class Conductor {public static var songPosition=0.0;}
class HxcCompatRuntime {public static function clearGameOverCharacter(a:Dynamic):Void {}}
class StoryMenuState {public function new() {}}
class FreeplayState {public function new() {}}
class LoadingState {public static function loadAndSwitchState(s:Dynamic):Void {}}
class PlayState {public static var isStoryMode=false;}
class Main extends Base {
 var sourceMode:Int=0;
 var codenameGameOverRuntime:Dynamic;
 var codenameGameOverCancelled=false;var isEnding=false;
 var controls:Dynamic={ACCEPT:false,BACK:false};
 function new(custom:Bool,cancelled:Bool) {
  super();RuntimeSmokeHarness.events=events;
  codenameGameOverCancelled=cancelled;
  if(custom) codenameGameOverRuntime={update:function(e:Float) {events.push('script:'+bf.animation.curAnim.name);}};
 }
 function endBullshit():Void {}
 function cancelDeathQuote():Void {}
 function hxcClearDeathOverlays():Void {}
 function dispatchSourceGameOverUpdateBeforeSuper(e:Float):Void {}
 function dispatchSourceGameOverUpdateAfterSuper(e:Float):Void {}
 function dispatchSourceGameOverUpdatePost(e:Float):Void {}
 function updateSourceGameOverInput():Void {}
 function updateGameoverAnimation(a:FlxAnimation):Void {events.push('gate:'+a.name);}
''' + method + r'''
 static function main() {
  var cancelled=new Main(true,true);cancelled.update(0.01);
  if(cancelled.events.join(',')!='super,tick,script:deathLoop') throw 'cancelled custom ABI changed';
  var custom=new Main(true,false);custom.update(0.01);
  if(custom.events.join(',')!='super,tick,script:deathLoop,gate:firstDeath') throw 'custom snapshot/order lost';
  var native=new Main(false,false);native.update(0.01);
  if(native.events.join(',')!='tick,gate:firstDeath,super') throw 'native quote gate advanced too late';
 }
}''')


if __name__ == '__main__':
    unittest.main()
