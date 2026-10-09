"""Execute source sustain speed setters and authored event/tween routing."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychSustainSpeedTest(unittest.TestCase):
    def test_active_queue_dedup_caps_multipliers_and_fixed_target(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        note = (ROOT / 'source/Note.hx').read_text()
        methods = '\n'.join(extract_method(play, marker) for marker in (
            'function set_scrollSpeed(', 'function resizePsychSustains(',
            'function refreshNightmareVisionNoteKillOffset(',
            '@:keep public function tweenScrollSpeed('))
        methods = methods.replace('FlxTween.tween(PlayState,', 'FlxTween.tween(Main,')
        methods += '\nfunction set_songSpeed(value:Float):Float return scrollSpeed = value;'
        resize = extract_method(note, 'public function resizeByRatio(')
        multiplier = extract_method(note, 'function set_multSpeed(')
        predicate = extract_method(play, 'function isPsychReceptorNote(')
        fixture = r'''using StringTools;
class Conductor {
 public static var stepCrochet:Float=125;
 public static function stepsToTime(value:Float):Float return value * stepCrochet;
}
class FlxEase {public static function linear(t:Float):Float return t;}
class FlxTween {
 public static var target:Dynamic; public static var props:Dynamic; public static var opts:Dynamic;
 public static function tween(t:Dynamic,p:Dynamic,duration:Float,o:Dynamic):Void {target=t;props=p;opts=o;}
 public static function tick(value:Float):Void {
  if (Reflect.hasField(props,'songSpeed')) Reflect.setProperty(target,'songSpeed',value);
  else Reflect.setField(target,'daScrollSpeed',value);
  if (Reflect.hasField(opts,'onUpdate')) opts.onUpdate(null);
 }
}
class AnimFrame {public var name:String='bluehold'; public function new() {}}
class Anim {public var curAnim:AnimFrame=new AnimFrame(); public function new() {}}
class Note {
 public var nightmareVisionLegacyGeometry=false; public var noteData=0; public var baseScaleY=10.;
 public var sourceTimingMode:Int=1; public var codenameInputLine:Dynamic=null;
 public var isSustainNote:Bool=true; public var animation:Anim=new Anim();
 public var scale:Dynamic={y:10.0}; public var updates:Int=0;
 public var multSpeed(default,set):Float=1;
 public function new() {} public function updateHitbox():Void updates++;
 __RESIZE__
 __MULTIPLIER__
}
class Main {
 public static var daScrollSpeed:Float=2;
 public static var dynamicScrollTarget:Float=0;
 public static var effectiveScrollSpeed(get,never):Float;
 static function get_effectiveScrollSpeed():Float return dynamicScrollTarget>0 ? dynamicScrollTarget : daScrollSpeed;
 public var scrollSpeed(get,set):Float;
 function get_scrollSpeed():Float return daScrollSpeed;
 public var songSpeed(get,set):Float;
 function get_songSpeed():Float return daScrollSpeed;
 public var nightmareVisionScripts:Dynamic=null;
 public var nightmareVisionLegacyFieldCameras=false; public var generatedMusic=true;
 public var sourceMode:Int=1; function sourceNoteTimingMode():Int return sourceMode;
 public var notes:{members:Array<Note>}={members:[]}; public var unspawnNotes:Array<Note>=[];
 public var noteKillOffset:Float=350; public var playbackRate:Float=1;
 public static var SONG={speed:2.0};
 function tweenVSliceScrollSpeed(a:Dynamic,b:Dynamic,c:Dynamic,d:Dynamic):Void {}
 __PREDICATE__
 __METHODS__
 public function new() {}
 static function near(a:Float,b:Float,label:String):Void if(Math.abs(a-b)>0.00001)throw label+': '+a+' != '+b;
 static function check(value:Bool,label:String):Void if(!value)throw label;
 static function main():Void {
  var game=new Main(); var body=new Note(); var queued=new Note(); var cap=new Note();
  cap.animation.curAnim.name='blueholdend'; var tap=new Note(); tap.isSustainNote=false;
  var native=new Note(); native.sourceTimingMode=0; var codename=new Note(); codename.codenameInputLine={};
  game.notes.members=[null,body,cap,tap,native,codename]; game.unspawnNotes=[body,queued,null];
  body.multSpeed=1.5; near(body.scale.y,15,'per-note initial multiplier');
  game.songSpeed=4;
  near(body.scale.y,30,'active deduplicated'); near(queued.scale.y,20,'unspawn resize');
  near(cap.scale.y,10,'cap unchanged'); near(tap.scale.y,10,'tap unchanged');
  near(native.scale.y,10,'native unchanged'); near(codename.scale.y,10,'Codename unchanged');
  check(body.updates==2 && queued.updates==1,'one resize per queue entry');
  body.multSpeed=2; near(body.scale.y,40,'multSpeed composes');
  game.songSpeed=4; check(body.updates==3,'same speed no repeat');
  game.tweenScrollSpeed({scroll:3.,absolute:true,duration:0.});
  near(body.scale.y,30,'instant source event'); near(queued.scale.y,15,'instant unspawn');
  game.tweenScrollSpeed({scroll:6.,absolute:true,duration:4.});
  check(FlxTween.target==game && Reflect.hasField(FlxTween.props,'songSpeed'),'source tween uses setter');
  FlxTween.tick(4.5); near(body.scale.y,45,'intermediate tween');
  FlxTween.tick(6); near(body.scale.y,60,'final tween'); near(queued.scale.y,30,'queued tween');
  near(cap.scale.y,10,'tween leaves cap');
  dynamicScrollTarget=2.5; var updates=body.updates;
  game.songSpeed=9; near(daScrollSpeed,9,'fixed mode retains authored speed');
  near(body.scale.y,60,'fixed target setter no stretch'); check(body.updates==updates,'fixed target no update');
  game.tweenScrollSpeed({scroll:12.,absolute:true,duration:4.}); FlxTween.tick(10);
  near(body.scale.y,60,'fixed target tween no stretch'); near(daScrollSpeed,10,'fixed target tween retains authored speed');
  dynamicScrollTarget=0;
  game.nightmareVisionScripts={}; game.songSpeed=20; near(body.scale.y,60,'NV exclusion');
  game.nightmareVisionLegacyFieldCameras=true; body.nightmareVisionLegacyGeometry=true;
  game.songSpeed=40; near(body.scale.y,120,'historical body shared speed resizing');near(body.baseScaleY,120,'historical raw baseline');
  near(cap.scale.y,10,'historical cap remains unchanged');
  game.generatedMusic=false;game.songSpeed=80;near(body.scale.y,120,'historical generation gate');game.generatedMusic=true;
  game.nightmareVisionLegacyFieldCameras=false;
  game.nightmareVisionScripts=null; game.sourceMode=0; game.songSpeed=30; near(body.scale.y,120,'native setter exclusion');
  game.tweenScrollSpeed({scroll:40.,absolute:true,duration:4.});
  check(FlxTween.target==Main && Reflect.hasField(FlxTween.props,'daScrollSpeed'),'native tween unchanged');
 }
}
'''
        fixture = fixture.replace('__METHODS__', methods).replace('__PREDICATE__', predicate)
        fixture = fixture.replace('__RESIZE__', resize).replace('__MULTIPLIER__', multiplier)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            (Path(folder)/'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        event = play[play.index("case 'Change Scroll Speed':"):play.index("case 'Set Camera Bop':")]
        self.assertIn('tweenScrollSpeed({scroll: parseF(e.v1), duration: secs * 1000 / Conductor.stepCrochet});', event)


if __name__ == '__main__':
    unittest.main()
