"""Menu confirmation preserves source frames and selection ownership."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method

ROOT = Path(__file__).resolve().parents[2]

class ConfirmationTest(unittest.TestCase):
    def test_authored_animation_fallbacks_and_elapsed_selection_lifecycle(self):
        sprite = r"""package flixel;
class FlxSprite {
 public var frames:{frames:Array<{name:String}>};
 public var animation = new Animations();
 public function new(names:Array<String>) frames={frames:[for(name in names) {name:name}]};
}
class Clip {
 public var frames:Array<Int>; public var name:String; public var frameRate:Int;
 public var numFrames:Int; public var curFrame:Int=0; public var finished:Bool=false;
 public function new(name:String,frames:Array<Int>,rate:Int) {this.name=name;this.frames=frames;frameRate=rate;numFrames=frames.length;}
}
class Animations {
 public var curAnim:Clip; var clips:Map<String,Clip>=[];
 public function new() {}
 public function add(name:String,frames:Array<Int>,rate:Int,loop:Bool) clips.set(name,new Clip(name,frames,rate));
 public function exists(name:String):Bool return clips.exists(name);
 public function getByName(name:String):Clip return clips.get(name);
 public function play(name:String,force:Bool=false) {curAnim=clips.get(name);curAnim.curFrame=0;curAnim.finished=false;}
 public function pause() {}
}
"""
        main = r"""class Main {
 static function check(ok:Bool,message:String) {if(!ok) throw message;}
 static function main() {
  var icon=new flixel.FlxSprite(['confirm-hold0000','confirm0001','idle0000','confirm0000','idle0001']);
  FreeplayIconPresentation.configureAtlas(icon,true);
  FreeplayIconPresentation.reset(icon,true);
  check(icon.animation.curAnim.name=='icon' && icon.animation.curAnim.frames.join(',')=='2,4','browsing shows atlas or confirmation instead of idle');
  FreeplayIconPresentation.confirm(icon,true);
  check(icon.animation.curAnim.frames.join(',')=='3,1','confirmation mixed in hold frames or wrong source order');
  icon.animation.curAnim.finished=true;FreeplayIconPresentation.update(icon);
  check(icon.animation.curAnim.name=='confirm-hold','finished confirmation did not hold');
  FreeplayIconPresentation.reset(icon,true);
  check(icon.animation.curAnim.name=='icon','cancel did not restore idle');
  var strip=new flixel.FlxSprite([]);strip.animation.add('icon',[0,1,1,0],0,false);
  FreeplayIconPresentation.confirm(strip,false);
  check(strip.animation.curAnim.curFrame==1,'two-face strip did not choose losing fallback');
  strip.animation.add('icon',[0,1,2,3],0,false);FreeplayIconPresentation.confirm(strip,false);
  check(strip.animation.curAnim.curFrame==3,'authored winning face not preferred');
  strip.animation.add('icon',[0,0,0,0],0,false);FreeplayIconPresentation.confirm(strip,false);
  check(strip.animation.curAnim.curFrame==0,'single-face strip escaped its neutral cell');
  strip.animation.add('dying',[4,5],24,true);strip.animation.add('winning',[6,7],24,true);
  FreeplayIconPresentation.confirm(strip,true);check(strip.animation.curAnim.name=='winning','atlas winning not preferred');
  var numbered=new flixel.FlxSprite(['confirm10.png','confirm2.png','confirm-hold0.png']);
  FreeplayIconPresentation.configureAtlas(numbered,true);FreeplayIconPresentation.confirm(numbered,true);
  check(numbered.animation.curAnim.frames.join(',')=='1,0','numeric frame order or extension support lost');
  var lone=new flixel.FlxSprite(['confirm0000']);FreeplayIconPresentation.configureAtlas(lone,true);FreeplayIconPresentation.reset(lone,true);
  check(lone.animation.curAnim.numFrames==1,'missing idle exposes full atlas');
  for(fps in [30,60,480,2000]) {
   var action=new FreeplayConfirmAction();action.start('owner/song:hard',9,0.6);
   var seconds=0.0;var fired=false;
   while(!fired && seconds<1) {seconds+=1.0/fps;fired=action.advance('owner/song:hard',9,1.0/fps);}
   check(fired && Math.abs(seconds-0.6)<=1.0/fps+0.0001,'confirmation depends on frame count');
   check(!action.advance('owner/song:hard',9,1),'confirmation replayed');
  }
  var action=new FreeplayConfirmAction();action.start('one',1,1);
  check(!action.advance('two',1,0.01) && !action.active,'selection change did not cancel immediately');
  action.start('one',1,1);check(!action.advance('one',2,0.01) && !action.active,'generation change did not cancel immediately');
  action.start('one',1,1);action.cancel();check(!action.advance('one',1,2),'cancel still launched');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            folder=Path(temp); (folder/'flixel').mkdir()
            (folder/'flixel/FlxSprite.hx').write_text(sprite)
            (folder/'Main.hx').write_text(main)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_menu_cancel_and_fresh_readiness_before_shared_launch(self):
        source=(ROOT/'source/FreeplayState.hx').read_text()
        # Expression-bodied selection key is supplied below; extract actual action methods.
        methods='\n'.join(extract_method(source, marker) for marker in [
            'function cancelBrowserConfirm(', 'function beginBrowserConfirm(',
            'function updateBrowserConfirm(', 'function launchSelection(',
            'function availabilityAllowsLaunch('])
        harness=r"""class Harness {
 public var browserConfirm=new FreeplayConfirmAction();
 public var browserConfirmIndex=-1; public var browserConfirmDifficulty=-1;
 public var browserConfirmIcon:Icon; public var iconArray=[new Icon(),new Icon()];
 public var curSelected=0;public var curDifficulty=2;public var hxcSelectionGeneration=1;
 public var songs=[{songName:'first'},{songName:'second'}];
 public var previewTimer:Float=1;public var previewGen=0;public var soundTest=false;
 public var ready=true;public var freshReady=true;public var chartPresent=true;
 public var controls={BACK:false,UP_MENU:false,DOWN_MENU:false,LEFT_MENU:false,RIGHT_MENU:false,ACCEPT:false};
 static inline var BACK=6;
 public function new() {}
 function browserSelectionKey():String return songs[curSelected].songName+':'+curDifficulty;
 function songMatches(index:Int):Bool return true;
 function availabilityAllowsSelection(index:Int,fresh=false):Bool return fresh?freshReady:ready;
 function selectionHasChart(song:String,difficulty:Int):Bool return chartPresent;
 function refreshAvailabilityForInteraction() {}
 function updateRenderedRowAvailability(index:Int) {}
 function stopPreviewSound() {}
"""+methods+"\n}"
        main=r"""@:access(Harness) class Main {
 static function check(ok:Bool,message:String) {if(!ok) throw message;}
 static function main() {
  var menu=new Harness();menu.beginBrowserConfirm(0,2);menu.controls.BACK=true;
  check(menu.updateBrowserConfirm(1) && !menu.browserConfirm.active && Song.reads==0,'Back did not cancel without launch');
  check(menu.iconArray[0].resets>0,'cancel did not restore icon');
  menu.controls.BACK=false;menu.beginBrowserConfirm(0,2);menu.controls.DOWN_MENU=true;
  check(!menu.updateBrowserConfirm(1) && !menu.browserConfirm.active,'navigation was swallowed or kept pending action');
  menu.controls.DOWN_MENU=false;menu.beginBrowserConfirm(0,2);menu.curDifficulty=1;menu.updateBrowserConfirm(1);
  check(Song.reads==0 && !menu.browserConfirm.active,'difficulty change launched stale chart');
  menu.beginBrowserConfirm(0,1);menu.ready=false;menu.updateBrowserConfirm(1);
  check(Song.reads==0 && !menu.browserConfirm.active,'pending package was launched');
  menu.ready=true;menu.beginBrowserConfirm(0,1);menu.freshReady=false;menu.updateBrowserConfirm(1);
  check(Song.reads==0 && RuntimeFreeplayDifficultyProbe.rejections==1,'final fresh readiness was bypassed');
  menu.freshReady=true;menu.beginBrowserConfirm(0,1);menu.chartPresent=false;menu.updateBrowserConfirm(1);
  check(Song.reads==0,'removed chart was loaded');
  menu.chartPresent=true;menu.beginBrowserConfirm(1,1);menu.updateBrowserConfirm(1);menu.updateBrowserConfirm(1);
  check(Song.reads==1 && LoadingState.launches==1 && PlayState.SONG.song=='second' && Song.attached=='second','resolved random target lost or launched twice');
 }
}
class Icon {public var resets=0;public function new(){} public function confirm():Float return 0.35;public function resetConfirmation(){resets++;}}
class FlxG {public static var keys={firstJustPressed:function(){return -1;}};public static var gamepads={anyJustPressed:function(key:Int){return false;}};public static var sound={music:{stop:function(){}}};}
class Song {public static var reads=0;public static var attached='';public static function loadFromJson(chart:String,song:String):Dynamic {reads++;return {song:song};}public static function attachFreeplayScoreSongId(song:Dynamic,name:String){attached=name;}}
class DifficultyIcons {public static function getEndingFP(diff:Int):String return '-'+diff;}
class RuntimeFreeplayDifficultyProbe {public static var rejections=0;public static function ordinaryRejectedSelection(song:String,diff:Int){rejections++;}}
class PlayState {public static var SONG:Dynamic;public static var isStoryMode=false;public static var balls=0;public static var watchedCutscene=false;public static var storyDifficulty=0;public function new(){}}
class ModifierState {public static var isStoryMode=false;public function new(){}}
class OptionsHandler {public static var options={skipModifierMenu:true};}
class LoadingState {public static function prepareSongTransition(song:String,prepare:Void->Void):Bool {prepare();return true;}public static var launches=0;public static function loadAndSwitchState(state:Dynamic){launches++;}}
"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            folder=Path(temp);(folder/'Main.hx').write_text(main+'\n'+harness)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
