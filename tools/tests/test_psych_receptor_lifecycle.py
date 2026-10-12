"""Script fades own their receptor property; rebuilt groups keep live references."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, ROOT
from test_source_event_preparation import extract_method

class PsychReceptorLifecycleTest(unittest.TestCase):
    def test_intro_takeover_and_rebuilt_index(self):
        strums = (ROOT / 'source/Strumline.hx').read_text(encoding='utf-8')
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        intro = '\n'.join(extract_method(strums, 'public function ' + name + '(')
                          for name in ['startIntroTween', 'cancelIntroTween'])
        index = extract_method(play, 'public function refreshPsychStrumIndex(')
        begin = extract_method(play, 'function beginPsychCountdownReceptors(').replace('function ', 'public function ', 1)
        defaults = '\n'.join(extract_method(play, 'function ' + name + '(').replace('function ', 'public function ', 1) for name in ['captureLuaDefaultStrums', 'publishPsychDefaultStrums'])
        countdown = extract_method(play, 'public function startCountdown(')
        self.assertLess(countdown.index('if (sourceCountdownStopped)'), countdown.index('beginPsychCountdownReceptors();'))
        self.assertLess(countdown.index('beginPsychCountdownReceptors();'), countdown.index('notifySourceCountdownStarted();'))
        self.assertEqual(play.count('SONG.uiType, false, nightmareVisionScripts == null && !(sourceScoreOwner && !sourceScoreNightmare)'), 2)
        self.assertIn('PlayState.instance.refreshPsychStrumIndex()', extract_method(strums, 'public function changeType('))
        self.assertIn('.cancelIntroTween(field)', extract_method(play, 'function compatTweenObject('))
        fixture = r'''class Note {public static var NOTE_AMOUNT=1;}
class Script {public var variables:Map<String,Dynamic>=[];public function new(){}}
class FlxEase {public static function circOut(v:Float):Float return v;}
class FlxTween {
 public var cancelled:Bool=false; public var props:Dynamic; public var options:Dynamic;
 public function new(p:Dynamic,o:Dynamic){props=p;options=o;}
 public static function tween(target:Dynamic,p:Dynamic,d:Float,o:Dynamic):FlxTween return new FlxTween(p,o);
 public function cancel():Void cancelled=true;
}
class Receptor {
 public var alpha:Float=1;public var y:Float=100;public var x:Float=300;
 public var introAlphaTween:FlxTween;public var introYTween:FlxTween;
 public function new(){}
 __INTRO__
}
class Group {
 public var members:Array<Receptor>=[];
 public function new(){}
 public var type:String="fixture";public var transitions:Int=0;
 public function changeType(t:String,transition:Bool,preserve:Bool):Void {members=[new Receptor()];}
 public function transIn():Void transitions++;
 public function clear():Void members=[];
 public function add(v:Receptor):Void members.push(v);
}
class State {
 public var sourceScoreOwner=true;public var sourceScoreNightmare=false;public var skipCountdown=false;
 public function comboBreakThingies(side:Int):Void {}
 public function configurePsychStrumSkins():Void {}
 public var strumLineNotes:Group=new Group();public var enemyStrums:Group=new Group();public var playerStrums:Group=new Group();
 public var hscriptStates:Map<String,Script>=[];
 public var luaDefaultStrumX:Array<Float>=[];public var luaDefaultStrumY:Array<Float>=[];
 public var luaDefaultOpponentStrumX:Array<Float>=[];public var luaDefaultOpponentStrumY:Array<Float>=[];
 public var luaDefaultPlayerStrumX:Array<Float>=[];public var luaDefaultPlayerStrumY:Array<Float>=[];
 public var luaDefaultStrumsCaptured=false;
 public function new(){}
 __DEFAULTS__
 __INDEX__
 __BEGIN__
}
class Main {
 static function check(v:Bool,msg:String):Void if(!v)throw msg;
 static function main():Void {
  var r=new Receptor();r.startIntroTween(1.1);
  var entranceAlpha=r.introAlphaTween;var entranceY=r.introYTween;
  check(r.alpha==0 && r.y==90,'entrance initial position');
  check(entranceAlpha.props.alpha==1 && entranceAlpha.options.startDelay==1.1,'entrance timing');
  r.cancelIntroTween('alpha');
  check(entranceAlpha.cancelled && !entranceY.cancelled,'script alpha must not cancel movement');
  r.cancelIntroTween('alpha');r.cancelIntroTween('x');
  check(!entranceY.cancelled,'unrelated property cancelled');
  r.cancelIntroTween('y');check(entranceY.cancelled,'script movement must supersede entrance');
  var introState=new State();
  introState.refreshPsychStrumIndex();check(introState.strumLineNotes.members.length==0,'intro exposed receptors');
  introState.captureLuaDefaultStrums();
  check(!introState.luaDefaultStrumsCaptured,'empty groups froze default coordinates');
  var script=new Script();var globals:Map<String,Dynamic>=['objects'=>"authored"];
  script.variables.set('luaSetScriptGlobal',function(k:String,v:Dynamic){globals.set(k,v);return true;});
  introState.hscriptStates.set('stage',script);
  introState.skipCountdown=true;introState.beginPsychCountdownReceptors();
  check(introState.strumLineNotes.members.length==2,'accepted countdown has no receptors');
  check(introState.luaDefaultPlayerStrumX[0]==300 && introState.luaDefaultOpponentStrumY[0]==100,'defaults not captured');
  check(globals.get('defaultPlayerStrumX0')==300 && globals.get('defaultOpponentStrumY0')==100,'computed Lua global missing');
  check(script.variables.get('defaultPlayerStrumY0')==100 && globals.get('objects')=='authored','private state replaced');
  introState.playerStrums.members[0].x=400;introState.captureLuaDefaultStrums();
  check(introState.luaDefaultPlayerStrumX[0]==300,'immutable baseline changed');
  check(introState.playerStrums.transitions==0 && introState.playerStrums.members[0].alpha==1,'skipped countdown animated arrows');
  var regular=new State();regular.beginPsychCountdownReceptors();
  check(regular.playerStrums.transitions==1 && regular.enemyStrums.transitions==1,'regular entrance missing');
  var nv=new State();nv.sourceScoreNightmare=true;nv.beginPsychCountdownReceptors();
  check(nv.strumLineNotes.members.length==0,'Psych created NV receptors');
  var s=new State();var old=new Receptor();var player=new Receptor();
  s.enemyStrums.add(old);s.playerStrums.add(player);s.refreshPsychStrumIndex();
  check(s.strumLineNotes.members[0]==old && s.strumLineNotes.members[1]==player,'side ordering');
  var replacement=new Receptor();s.enemyStrums.members=[replacement];s.refreshPsychStrumIndex();
  check(s.strumLineNotes.members.length==2 && s.strumLineNotes.members[0]==replacement,'stale rebuilt receptor');
  s.strumLineNotes.members[1].alpha=0;check(player.alpha==0,'index must share live objects');
  s.sourceScoreNightmare=true;s.enemyStrums.members=[];s.refreshPsychStrumIndex();
  check(s.strumLineNotes.members.length==2,'NV owns its receptor index');
  s.sourceScoreNightmare=false;s.sourceScoreOwner=false;s.refreshPsychStrumIndex();
  check(s.strumLineNotes.members.length==2,'native index changed');
  s.sourceScoreOwner=true;s.strumLineNotes=null;s.refreshPsychStrumIndex();
 }
}'''.replace('__INTRO__',intro).replace('__INDEX__',index).replace('__BEGIN__',begin).replace('__DEFAULTS__',defaults)
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'Main.hx').write_text(fixture, encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',temp,'-main','Main','--interp'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
