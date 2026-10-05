"""Execute the extracted source GameOver constructor/setup/audio paths."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE, HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source" / "GameOverSubstate.hx"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.find("{", start)
    terminator = source.find(";", start)
    if terminator >= 0 and (opening < 0 or terminator < opening):
        return source[start : terminator + 1]
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and nxt == "/":
            line_comment = True
            index += 1
        elif char == "/" and nxt == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"Unclosed method: {marker}")


def run_fixture(fixture: str) -> subprocess.CompletedProcess:
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="source-gameover-setup-", dir=ROOT / "tmp") as scratch:
        folder = Path(scratch)
        (folder / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
        sound_package = folder / "openfl" / "media"
        sound_package.mkdir(parents=True)
        (sound_package / "Sound.hx").write_text(
            "package openfl.media;\ntypedef Sound = Dynamic;\n", encoding="utf-8", newline="\n"
        )
        flixel_system = folder / "flixel" / "system"
        flixel_system.mkdir(parents=True)
        (flixel_system / "FlxAssets.hx").write_text(
            "package flixel.system;\nclass FlxAssets { public static function getSound(path:String):Dynamic return path; }\n",
            encoding="utf-8",
            newline="\n",
        )
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder), "--main", "Main", "--interp"],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": scratch},
            capture_output=True,
            text=True,
            timeout=60,
        )


def source_methods() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    markers = (
        "static function get_characterName():Null<String>",
        "static function set_characterName(value:Null<String>):Null<String>",
        "static function get_deathSoundName():Null<String>",
        "static function set_deathSoundName(value:Null<String>):Null<String>",
        "static function get_loopSoundName():Null<String>",
        "static function set_loopSoundName(value:Null<String>):Null<String>",
        "static function get_endSoundName():Null<String>",
        "static function set_endSoundName(value:Null<String>):Null<String>",
        "static function get_deathDelay():Float",
        "static function set_deathDelay(value:Float):Float",
        "public static function resetVariables():Void",
        "static function sourceSettingsForActiveOwner():SourceGameOverSettings",
        "public function new(player:Character)",
        "function setupSourceGameOver(player:Character",
        "static function sourcePositionValue(",
        "function psychGameOverAntialiasing():Bool",
        "function psychGameOverAtlas(key:String):Dynamic",
        "function psychGameOverSound(name:String):openfl.media.Sound",
        "function playPsychTankGameOverVoice():Void",
        "function cancelDeathQuote():Void",
        "override function create():Void",
        "function sourceDeathCharacterName():Null<String>",
        "function preloadPsychGameOverLoop():Void",
        "function setupPsychPicoOverlay():Void",
        "function playDeathAnimation(name:String):Void",
        "function endBullshit():Void",
        "function notifySourceGameOverConfirmed():Void",
        "public function coolStartDeath(?volume:Float = 1):Void",
        "function updateGameoverAnimation(currentAnim:FlxAnimation):Void",
        "function startGameoverLoop(?volume:Float = 1)",
        "function playGameoverMusic(volume:Float = 1)",
        "override public function destroy():Void",
    )
    return "\n".join(extract_method(source, marker) for marker in markers)


FIXTURE = r'''import SourceGameOverSettings;
using StringTools;

class Trace {
 public static var events:Array<String> = [];
 public static function add(value:String):Void events.push(value);
 public static function reset():Void events = [];
 public static function has(value:String):Bool return events.indexOf(value) >= 0;
 public static function index(value:String):Int return events.indexOf(value);
 public static function countPrefix(prefix:String):Int {
  var count=0;
  for (event in events) if(StringTools.startsWith(event,prefix)) count++;
  return count;
 }
}

class FlxPoint {
 public var x:Float;
 public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public static function get(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):Void { this.x=x; this.y=y; Trace.add('camera.scroll.set'); }
 public function put():Void Trace.add('point.put');
}

class FlxObject {
 public var x:Float; public var y:Float;
 public function new(x:Float,y:Float,w:Float,h:Float) { this.x=x; this.y=y; }
 public function destroy():Void Trace.add('camera.destroy');
}

class FlxAnimation {
 public var name:String;
 public var curFrame:Int;
 public var finished:Bool;
 public function new(name:String,curFrame:Int,finished:Bool) {
  this.name=name; this.curFrame=curFrame; this.finished=finished;
 }
}

class CharacterAnimation {
 public var curAnim:FlxAnimation;
 public var callback:String->Int->Int->Void;
 public function new() curAnim=new FlxAnimation('idle',0,false);
}

class SpriteAnimation {
 public var finishCallback:String->Void;
 var names:Array<String>=[];
 public function new() {}
 public function addByPrefix(name:String,prefix:String,fps:Int,looped:Bool):Void {
  names.push(name); Trace.add('sprite.anim.add:'+name+':'+prefix);
 }
 public function exists(name:String):Bool return names.indexOf(name)>=0;
 public function play(name:String,force:Bool=false):Void Trace.add('sprite.anim.play:'+name);
}

class FlxSprite {
 public var x:Float; public var y:Float;
 public var frames:Dynamic;
 public var antialiasing:Bool=false;
 public var visible:Bool=true;
 public var animation:SpriteAnimation=new SpriteAnimation();
 public var offset:FlxPoint=new FlxPoint();
 public function new(x:Float=0,y:Float=0) {
  this.x=x; this.y=y; Trace.add('sprite.new:'+x+':'+y);
 }
 public function destroy():Void Trace.add('sprite.destroy:'+x+':'+y);
}

class Character {
 public static var created:Array<String>=[];
 public static var exactSourceVisuals:Map<String,Bool>=new Map();
 public static function animationName(character:Character):String
  return character.animation.curAnim == null ? '' : character.animation.curAnim.name;

 public var curCharacter:String;
 public var visualCharacterId:String;
 public var x:Float; public var y:Float;
 public var screenX:Float; public var screenY:Float;
 public var positionArray:Array<Float>;
 public var cameraPosition:Array<Float>;
 public var animation:CharacterAnimation=new CharacterAnimation();
 public var beingControlled:Bool=false;
 public var skipDance:Bool=false;
 public var deathSound:String='fnf_loss_sfx.ogg';
 public var gameoverMusic:String='gameOver.ogg';
 public var gameoverMusicEnd:String='gameOverEnd.ogg';
 public var deathCameraZoom:Float=0;
 public var isPixel:Bool=false;
 public var destroyed:Bool=false;
 public var playerOffsetX:Float=0; public var playerOffsetY:Float=0;
 public var gameoverCharacter:Null<String>;
 public var gameoverInitialDeathSound:Null<String>;
 public var gameoverLoopDeathSound:Null<String>;
 public var gameoverConfirmDeathSound:Null<String>;
 public function new(x:Float,y:Float,curCharacter:String,isPlayer:Bool) {
  this.x=x; this.y=y; this.screenX=x; this.screenY=y; this.curCharacter=curCharacter;
  visualCharacterId=curCharacter;
  if (PlayState.instance != null && PlayState.instance.sourceGameOverMode() != 0
   && StringTools.endsWith(curCharacter,'-dead') && !exactSourceVisuals.exists(curCharacter))
   visualCharacterId='bf';
  if (curCharacter == 'psych-dead' || curCharacter == 'nv-dead') {
   positionArray=[40,70]; cameraPosition=[8,14];
  } else { positionArray=[12,20]; cameraPosition=[2,4]; }
  created.push(curCharacter);
  Trace.add('actor.new:'+curCharacter+':'+x+':'+y);
 }
 public function getScreenPosition():FlxPoint return new FlxPoint(screenX,screenY);
 public function getMidpoint():FlxPoint {
  Trace.add('actor.midpoint:'+animation.curAnim.name);
  return new FlxPoint(x+50,y+60);
 }
 public function getGraphicMidpoint():FlxPoint {
  Trace.add('actor.graphicMidpoint:'+animation.curAnim.name);
  var animationOffset = animation.curAnim.name == 'firstDeath' ? 7 : 0;
  return new FlxPoint(x+50+animationOffset,y+60+animationOffset+2);
 }
 public var hasDeathConfirm:Bool=true;
 public var hasDeathLoop:Bool=true;
 public function hasAnimation(name:String):Bool
  return name == 'deathConfirm' ? hasDeathConfirm : name == 'deathLoop' ? hasDeathLoop : true;
 public function playAnim(name:String,force:Bool=false):Void {
  animation.curAnim=new FlxAnimation(name,0,false); Trace.add('actor.anim:'+name);
 }
 public function getDeathQuote():Null<String> return null;
 public function destroy():Void { destroyed=true; Trace.add('actor.destroy:'+curCharacter); }
}

class FakeSound {
 public var volume:Float=0;
 public var resource:Dynamic=null;
 public var playing:Bool=false;
 public function new() {}
 public function loadEmbedded(sound:Dynamic,loop:Bool):Void {
  resource=sound; Trace.add('music.load:'+Std.string(sound)+':'+loop);
 }
 public function play(restart:Bool=false):Void { playing=true; Trace.add('music.play:'+restart); }
 public function stop():Void { playing=false; Trace.add('music.stop'); }
 public function fadeIn(from:Float,to:Float,duration:Float):Void Trace.add('music.fadeIn:'+from+':'+to+':'+duration);
}

class SoundFrontEnd {
 public var music:FakeSound=new FakeSound();
 public function new() {}
 public function play(sound:Dynamic,volume:Float=1,looped:Bool=false,?group:Dynamic,
  autoDestroy:Bool=true,?onComplete:Void->Void):Dynamic {
  Trace.add('sound.play:'+Std.string(sound)+':'+volume+':'+looped); return sound;
 }
 public function playMusic(sound:Dynamic,volume:Float=1,looped:Bool=true):FakeSound {
  music=new FakeSound(); music.resource=sound; music.volume=volume; music.playing=true;
  Trace.add('music.start:'+Std.string(sound)+':'+volume+':'+looped); return music;
 }
}

class FakeCamera {
 public var scroll:FlxPoint=new FlxPoint(22,33);
 public var target:Dynamic='old-target';
 public var width:Float=800; public var height:Float=600;
 public var zoom:Float=1;
 public function new() {}
 public function focusOn(point:FlxPoint):Void Trace.add('camera.focus:'+point.x+':'+point.y);
 public function follow(point:FlxObject,style:Int,lerp:Float):Void
  Trace.add('camera.follow:'+point.x+':'+point.y+':'+lerp);
 public function fade(color:Int,duration:Float,fadeIn:Bool,done:Void->Void):Void Trace.add('camera.fade');
}

class FlxG {
 public static var sound:SoundFrontEnd=new SoundFrontEnd();
 public static var camera:FakeCamera=new FakeCamera();
 public static var random:FakeRandom=new FakeRandom();
}
class FakeRandom {
 public function new() {}
 public function int(min:Int,max:Int,?exclude:Array<Int>):Int {
  Trace.add('random.int:'+min+':'+max); return 7;
 }
}

class FlxTimer {
 public function new() {}
 public function start(time:Float,callback:FlxTimer->Void):FlxTimer {
  Trace.add('timer.start:'+time); return this;
 }
}
class FlxColor { public static inline var BLACK:Int=0; }
class LoadingState {
 public static function loadAndSwitchState(value:Dynamic):Void Trace.add('state.switch');
}
class Paths {
 public static function music(value:String):String return value;
}

class Conductor { public static var songPosition:Float=99; }
class RuntimeSmokeHarness {
 public static function markGameOverPhase(name:String,data:Dynamic):Void Trace.add('phase:'+name);
}
class HxcCompatRuntime {
 public static function clearGameOverCharacter(character:Dynamic):Void Trace.add('hxc.clear');
 public static function resolveGameOverTrack(value:String,root:String,pixel:Bool,end:Bool=false):String return value;
}
class FNFAssets {
 public static function getSound(path:String):Dynamic return path;
 public static function exists(path:String):Bool return true;
}
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:String='NV_STOP'; }
class ScriptCallbackResult { public static inline var STOP:String='PSY_STOP'; }

class PlayState {
 public static var instance:PlayState;
 public static var isStoryMode:Bool=false;
 public static var SONG:Dynamic=null;
 public var sourceGameOverSettings:SourceGameOverSettings;
 public var psychClientPrefs:Dynamic={data:{antialiasing:false}};
 public var startResult:Dynamic=null;
 public var mutateCharacterOnStart:Null<String>=null;
 public var psychPathOwner:String='psych-assets';
 public var psychPathLibrary:String='shared';
 public var camFollow:FlxObject=new FlxObject(400,300,1,1);
 public var gf:Dynamic=null;
 public function new(?settings:SourceGameOverSettings) {
  sourceGameOverSettings=settings; if(settings!=null) instance=this;
 }
 public function sourceGameOverMode():Int return sourceGameOverSettings.mode;
 public function psychGameOverCharacterName():Null<String> return sourceGameOverSettings.characterName;
 public function sourceGameOverPsychPaths():Dynamic {
  if (sourceGameOverSettings == null || sourceGameOverSettings.mode != SourceGameOverSettings.PSYCH)
   throw 'Psych owner Paths requested for a non-Psych owner';
  var owner=psychPathOwner; var library=psychPathLibrary;
  Trace.add('paths.owner:'+owner+':'+library);
  return {getSparrowAtlas:function(key:String):Dynamic {
   Trace.add('atlas:'+owner+':'+library+':'+key); return owner+'/'+library+'/'+key;
  }, sound:function(key:String):Dynamic {
   Trace.add('sound.path:'+owner+':'+library+':'+key); return owner+'/'+library+'/sounds/'+key+'.ogg';
  }};
 }
 public function sourceGameOverSetInGameOver(value:Bool):Void Trace.add('inGameOver:'+value);
 public function sourceGameOverCall(hook:String,args:Array<Dynamic>):Dynamic {
  Trace.add('call:'+hook+':'+args.length+(args.length>0 ? ':'+Std.string(args[0]) : ''));
  if (hook=='deathAnimStart' && GameOverSubstate.instance!=null)
   Trace.add('startedDeathAtCallback:'+GameOverSubstate.instance.startedDeath);
  if (hook=='onGameOverStart' && mutateCharacterOnStart!=null)
   sourceGameOverSettings.write('characterName',mutateCharacterOnStart);
  return hook=='onGameOverStart' ? startResult : null;
 }
 public function psychGameOverSoundPath(property:String,preferSounds:Bool):Null<String> return null;
 public function sourceGameOverSound(property:String,preferSounds:Bool):Dynamic {
  var key = property == 'deathSoundName' ? 'deathSoundName' : property;
  var name:Dynamic=sourceGameOverSettings.read(key);
  Trace.add('sound.resolve:'+property+':'+preferSounds+':'+Std.string(name));
  return name==null ? null : (preferSounds ? 'sound:'+name : 'music:'+name);
 }
}

class MusicBeatSubstate {
 public var members:Array<Dynamic>=[];
 public function new() {}
 public function add(value:Dynamic):Dynamic {
  members.push(value);
  if (Std.isOfType(value,Character)) Trace.add('add.actor:'+cast(value,Character).curCharacter);
  else if (Std.isOfType(value,FlxSprite)) Trace.add('add.sprite');
  else Trace.add('add.camera');
  return value;
 }
 public function remove(value:Dynamic,splice:Bool=false):Dynamic {
  members.remove(value); Trace.add('remove:'+splice);
  return value;
 }
 public function insert(position:Int,value:Dynamic):Dynamic return add(value);
 public function create():Void Trace.add('super.create');
 public function destroy():Void {
  Trace.add('super.destroy');
  for (value in members.copy())
   if (Reflect.hasField(value,'destroy')) Reflect.callMethod(value,Reflect.field(value,'destroy'),[]);
  members=[];
 }
}

class GameOverSubstate extends MusicBeatSubstate {
 public static inline var LOCKON:Int=1;
 public static var instance:GameOverSubstate;
 public static var characterName(get,set):Null<String>;
 public static var deathSoundName(get,set):Null<String>;
 public static var loopSoundName(get,set):Null<String>;
 public static var endSoundName(get,set):Null<String>;
 public static var deathDelay(get,set):Float;
 var bf:Character;
 var sourceOwner:PlayState;
 var sourceMode:Int=0;
 var sourceStartStopped:Bool=false;
 var sourceDeathAnimNotified:Bool=false;
 var sourceSettings:SourceGameOverSettings;
 var sourceSetupCharacterName:Null<String>;
 var sourceReusedGameplayActor:Bool=false;
 var psychLoopPreloaded:Bool=false;
 var quoteCharacter:Character;
 var deathQuotePlayback:Dynamic=null;
 var codenameGameOverRuntime:Dynamic=null;
 var gameoverLoopMusic:FakeSound;
 var gameoverStarted:Bool=false;
 public var startedDeath:Bool=false;
 var isEnding:Bool=false;
 var deathQuoteAttempted:Bool=false;
 var camFollow:FlxObject;
 var psychRetryOverlay:Dynamic=null;
 var psychNeneKnife:Dynamic=null;
 var psychRetryAnimationCallback:String->Int->Int->Void;
 var psychPreviousAnimationCallback:String->Int->Int->Void;
 var psychRetryConfirmOffsets:FlxPoint=FlxPoint.get(250,200);
 function setupDefaultGameOver(player:Character,name:String,resetSongPosition:Bool=true):Void
  Trace.add('native.setup:'+name);
 function restorePsychRetryAnimationCallback():Void Trace.add('retry.callback.restore');
''' + source_methods() + r'''
 function hxcClearDeathOverlays():Void Trace.add('hxc.overlays.clear');
 public function actor():Character return bf;
 public function wasReused():Bool return sourceReusedGameplayActor;
 public function runCreate():Void create();
 public function runAnimation(animation:FlxAnimation):Void updateGameoverAnimation(animation);
 public function runEnd():Void endBullshit();
 public function runCoolStartDeath(volume:Float):Void coolStartDeath(volume);
 public function runPsychAntialiasing():Bool return psychGameOverAntialiasing();
 public function runPsychOverlaySetup():Void setupPsychPicoOverlay();
 public function overlayAntialiasing():Bool return psychRetryOverlay.antialiasing;
 public function knifeAntialiasing():Bool return psychNeneKnife.antialiasing;
 public function loopVolume():Float return gameoverLoopMusic.volume;
 public function runDestroy():Void destroy();
 public function isPsychLoopPreloaded():Bool return psychLoopPreloaded;
}

class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function index(event:String):Int return Trace.index(event);
 static function main():Void {
  var psychSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,
   {gameOverChar:'psych-dead',gameOverSound:'psych-loss',gameOverLoop:'psych-loop'});
  Character.exactSourceVisuals.set('psych-dead',true);
  var psychOwner=new PlayState(psychSettings);
  psychOwner.mutateCharacterOnStart='too-late-dead';
  var psychPlayer=new Character(0,0,'bf',true);
  psychPlayer.screenX=310; psychPlayer.screenY=420;
  Character.created=[]; Trace.reset();
  var psych=new GameOverSubstate(psychPlayer);
  psych.runCreate();
  check(psych.actor().curCharacter=='psych-dead','Psych chart character was not used');
  check(psych.actor().x==338 && psych.actor().y==470,
   'Psych actor did not apply source positionArray delta: '+psych.actor().x+','+psych.actor().y);
  check(psych.actor().skipDance,'source actor must skip dance during game over');
  check(psychSettings.characterName=='too-late-dead','Psych start callback mutation was not live');
  check(index('add.actor:psych-dead') < index('call:onGameOverStart:0'),
   'Psych must build default actor before onGameOverStart');
  check(index('call:onGameOverStart:0') < index('music.load:music:psych-loop:true'),
   'Psych must preload loop after onGameOverStart');
  check(!Trace.has('music.start:music:psych-loop:1:true') && !Trace.has('music.play:true'),
   'Psych loop must preload without starting before firstDeath finishes');
  check(Trace.has('sound.play:sound:psych-loss:1:false'),'Psych initial sound was not resolved through source audio');
  check(Trace.has('camera.focus:400:300'),'Psych camera did not focus on screen center after reset');
  check(index('actor.anim:firstDeath') < index('actor.graphicMidpoint:firstDeath'),
   'Psych donor computes getGraphicMidpoint after firstDeath starts');
  check(index('actor.graphicMidpoint:firstDeath') < index('camera.follow:403:553:0.01'),
   'Psych camera uses the post-animation graphic midpoint plus cameraPosition');
  check(Trace.countPrefix('camera.follow:')==1,
   'Psych donor follows once during setup, after its death animation starts');
  check(!Trace.has('actor.midpoint:firstDeath'),'Psych uses graphic midpoint, not NV getMidpoint');
  check(!psych.runPsychAntialiasing(),
   'Psych retry antialiasing must read the active Psych owner preference');
  psychOwner.psychClientPrefs.data.antialiasing=true;
  check(psych.runPsychAntialiasing(),
   'Psych retry antialiasing should observe live writes to its owner preference data');
  check(index('inGameOver:true') > index('add.camera'),
   'Psych inGameOver must be set after default setup');
  GameOverSubstate.characterName='psych-static-dead';
  GameOverSubstate.deathDelay=0.15;
  check(psychSettings.characterName=='psych-static-dead' && psychSettings.deathDelay==0.15,
   'Psych GameOverSubstate static properties must write through to the active source settings');
  psych.runAnimation(new FlxAnimation('firstDeath',0,false));
  check(!Trace.has('music.play:true'),'Psych loop started before the death animation completed');
  psych.runAnimation(new FlxAnimation('firstDeath',12,false));
  check(Trace.countPrefix('camera.follow:')==1,
   'Psych frame-12 update must not issue a second camera follow');
  psych.runAnimation(new FlxAnimation('firstDeath',40,true));
  check(Trace.has('music.play:true'),'Psych did not start the preloaded loop at death completion');
  check(Trace.countPrefix('camera.follow:')==1,
   'Psych loop start must not reissue the setup camera follow');
  check(!Trace.has('music.start:music:psych-loop:1:true'),
   'Psych should play the preloaded music handle instead of loading a second loop');
  psych.runDestroy();
  check(psych.actor().destroyed,'owned source death actor should be destroyed with its substate');

  // GameOver setup passes the authored death ID to Character. The extracted
  // Character identity fixture separately executes the production constructor
  // resolution and verifies that a missing source visual keeps this ID while
  // selecting the donor DEFAULT_CHARACTER visual (`bf`).
  var psychFallbackSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,
   {gameOverChar:'authored-dead'});
  new PlayState(psychFallbackSettings);
  Character.exactSourceVisuals.remove('authored-dead');
  var psychFallback=new GameOverSubstate(new Character(0,0,'bf',true));
  Trace.reset();
  psychFallback.runCreate();
  check(psychFallback.actor().curCharacter=='authored-dead'
   && psychFallback.actor().visualCharacterId=='bf',
   'Psych GameOver must retain the requested death ID while falling back to the donor bf visual');
  psychFallback.runDestroy();

  var nvSettings=new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,null);
  var nvOwner=new PlayState(nvSettings);
  nvOwner.mutateCharacterOnStart='nv-dead';
  var nvPlayer=new Character(0,0,'bf',true);
  nvPlayer.screenX=310; nvPlayer.screenY=420;
  nvPlayer.gameoverCharacter='old-dead';
  Character.exactSourceVisuals.set('nv-dead',true);
  nvPlayer.gameoverInitialDeathSound=null;
  nvPlayer.gameoverLoopDeathSound='nv-loop';
  nvSettings.write('deathSoundName',null);
  Character.created=[]; Trace.reset();
  var nv=new GameOverSubstate(nvPlayer);
  check(nvSettings.characterName=='old-dead','NV constructor did not apply character metadata before create');
  check(GameOverSubstate.characterName=='old-dead','NV GameOverSubstate.characterName did not read shared metadata settings');
  nvOwner.psychClientPrefs.data.antialiasing=true;
  check(nv.runPsychAntialiasing(),
   'a substate must retain its owner preference view after another owner becomes active');
  GameOverSubstate.loopSoundName='nv-loop-static';
  check(nvSettings.loopSoundName=='nv-loop-static','NV static loop write did not update settings used by the substate');
  nv.runCreate();
  check(nv.actor().curCharacter=='nv-dead','NV start callback setting did not affect default setup');
  check(nv.actor().x==338 && nv.actor().y==470,'NV actor positionArray delta changed');
  check(nv.actor().skipDance,'NV actor must skip dance');
  check(index('call:onGameOverStart:0') < index('actor.new:nv-dead:310:420'),
   'NV must call Start before constructing default actor');
  check(index('actor.midpoint:idle') < index('actor.anim:firstDeath'),
   'NV donor computes getMidpoint before starting firstDeath');
  check(index('actor.midpoint:idle') < index('camera.follow:280:444:0'),
   'NV camera uses getMidpoint minus cameraPosition.x and the donor 100px offset');
  check(!Trace.has('actor.graphicMidpoint:firstDeath'),'NV camera uses getMidpoint, not Psych getGraphicMidpoint');
  check(!Trace.has('sound.play:sound:fnf_loss_sfx:1:false'),'NV null initial sound should not invent a fallback');
  check(!Trace.has('music.load:music:nv-loop-static:true') && !Trace.has('music.start:music:nv-loop-static:1:true'),
   'NV loop must not be loaded or played during setup');
  check(Trace.has('call:onGameOverPost:0'),'NV post-create callback was skipped');
  nv.runAnimation(new FlxAnimation('firstDeath',0,false));
  check(!Trace.has('music.start:music:nv-loop-static:1:true'),'NV loop started before firstDeath completed');
  nv.runAnimation(new FlxAnimation('firstDeath',40,true));
  check(Trace.has('music.start:music:nv-loop-static:1:true'),'NV loop did not load/play after firstDeath completion');
  check(Trace.has('call:deathAnimStart:1:1'),'NV deathAnimStart must follow delayed loop start');
  check(index('music.start:music:nv-loop-static:1:true') < index('call:deathAnimStart:1:1'),
   'NV deathAnimStart ran before loop playback');
  check(Trace.has('startedDeathAtCallback:false'),
   'automatic NV deathAnimStart must run before startedDeath flips true');
  Trace.reset();
  nv.runCoolStartDeath(0.4);
  nv.runCoolStartDeath(0.7);
  check(Trace.index('call:deathAnimStart:1:0.4') >= 0 && Trace.index('call:deathAnimStart:1:0.7') >= 0,
   'direct NV coolStartDeath calls preserve their volume and each notify');
  check(Trace.index('call:deathAnimStart:1:0.4') < Trace.index('call:deathAnimStart:1:0.7'),
   'repeated direct NV coolStartDeath calls were coalesced');

  var noLoopSettings=new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,null);
  noLoopSettings.write('loopSoundName',null);
  var noLoopOwner=new PlayState(noLoopSettings);
  var noLoopPlayer=new Character(0,0,'no-loop-bf',true);
  noLoopPlayer.gameoverCharacter='different-dead';
  Character.created=[]; Trace.reset();
  var noLoop=new GameOverSubstate(noLoopPlayer);
  noLoop.runCreate();
  noLoop.runAnimation(new FlxAnimation('firstDeath',40,true));
  check(!Trace.has('music.start:music:null:1:true'),'NV null loop must not use fallback music');
  check(Trace.has('call:deathAnimStart:1:1'),'NV deathAnimStart remains after nullable loop attempt');

  var psychConfirmSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,
   {gameOverChar:'psych-no-confirm'});
  new PlayState(psychConfirmSettings);
  Trace.reset();
  var psychConfirm=new GameOverSubstate(new Character(0,0,'bf',true));
  psychConfirm.runCreate();
  psychConfirm.actor().hasDeathConfirm=false;
  psychConfirm.runEnd();
  check(Trace.has('actor.anim:deathLoop'),
   'Psych confirmation falls back to deathLoop when deathConfirm is absent');
  check(!Trace.has('actor.anim:deathConfirm'),
   'Psych attempted unavailable deathConfirm instead of donor fallback');

  var nvConfirmSettings=new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,null);
  new PlayState(nvConfirmSettings);
  Trace.reset();
  var nvConfirm=new GameOverSubstate(new Character(0,0,'bf',true));
  nvConfirm.runCreate();
  nvConfirm.actor().hasDeathConfirm=false;
  nvConfirm.runEnd();
  check(Trace.has('actor.anim:deathConfirm') && !Trace.has('actor.anim:deathLoop'),
   'NV donor always requests deathConfirm regardless of animation availability');

  var pathSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,
   {gameOverChar:'psych-other'});
  var pathOwner=new PlayState(pathSettings);
  pathOwner.psychPathOwner='selected-song-owner';
  pathOwner.psychPathLibrary='tank';
  pathOwner.psychClientPrefs.data.antialiasing=true;
  pathOwner.mutateCharacterOnStart='pico-dead';
  pathOwner.gf={curCharacter:'nene'};
  var pathGameOver=new GameOverSubstate(new Character(0,0,'bf',true));
  var replacementSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,null);
  var replacementOwner=new PlayState(replacementSettings);
  replacementOwner.psychPathOwner='wrong-current-owner';
  replacementOwner.psychPathLibrary='shared';
  Trace.reset();
  pathGameOver.runCreate();
  check(pathGameOver.actor().curCharacter=='psych-other' && pathSettings.characterName=='pico-dead',
   'Psych Start mutation should select overlays without replacing the already-created actor');
  check(Trace.has('atlas:selected-song-owner:tank:Pico_Death_Retry'),
   'Pico retry overlay atlas must resolve through its captured Psych owner and stage library');
  check(Trace.has('atlas:selected-song-owner:tank:NeneKnifeToss'),
   'Nene knife atlas must resolve through the same captured Psych owner and stage library');
  check(!Trace.has('atlas:wrong-current-owner:shared:Pico_Death_Retry'),
   'GameOver atlas resolution followed a later global PlayState owner');
  check(pathGameOver.overlayAntialiasing() && pathGameOver.knifeAntialiasing(),
   'overlay and Nene effect antialiasing must read captured owner preferences');
  check(index('call:onGameOverStart:0') < index('paths.owner:selected-song-owner:tank'),
   'Psych effect assets should resolve after onGameOverStart');
  PlayState.SONG={stage:'tank'};
  Trace.reset();
  pathGameOver.runAnimation(new FlxAnimation('firstDeath',40,true));
  var musicPlayCount=0;
  for (event in Trace.events) if (event=='music.play:true') musicPlayCount++;
  check(musicPlayCount==1 && pathGameOver.loopVolume()==0.2,
   'Psych tank death must start its preloaded loop once at volume 0.2');
  check(index('music.play:true') < index('sound.path:selected-song-owner:tank:jeffGameover/jeffGameover-7'),
   'Psych tank voice must resolve from the owner Paths after the death loop starts');
  check(Trace.has('sound.play:selected-song-owner/tank/sounds/jeffGameover/jeffGameover-7.ogg:1:false'),
   'Psych tank voice should play the owner-resolved Jeff death sound');
  PlayState.SONG=null;
  pathGameOver.runDestroy();

  var reuseSettings=new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,null);
  var reuseOwner=new PlayState(reuseSettings);
  var borrowed=new Character(1,2,'same-death',true);
  borrowed.screenX=310; borrowed.screenY=420;
  borrowed.gameoverCharacter='same-death';
  var createdBefore=Character.created.length;
  Trace.reset();
  var reuse=new GameOverSubstate(borrowed);
  check(reuse.wasReused() && reuse.actor()==borrowed,
   'NV matching configured actor should borrow the live gameplay character');
  reuse.runCreate();
  check(Character.created.length==createdBefore,'matching actor created a duplicate death Character');
  check(Trace.has('add.actor:same-death'),'borrowed actor was not attached to substate');
  reuse.runDestroy();
  check(!borrowed.destroyed,'destroying source GameOverSubstate destroyed the borrowed PlayState actor');
  check(index('remove:true') < index('super.destroy'),
   'borrowed actor must be detached before FlxSubState destroys its members');

  var nvFallbackSettings=new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,null);
  new PlayState(nvFallbackSettings);
  var nvFallbackPlayer=new Character(0,0,'nv-player',true);
  nvFallbackPlayer.gameoverCharacter='nv-authored-dead';
  Character.exactSourceVisuals.remove('nv-authored-dead');
  Trace.reset();
  var nvFallback=new GameOverSubstate(nvFallbackPlayer);
  nvFallback.runCreate();
  check(nvFallback.actor().curCharacter=='nv-authored-dead'
   && nvFallback.actor().visualCharacterId=='bf',
   'NV GameOver must retain the requested death ID while falling back to the donor bf visual');
  nvFallback.runDestroy();

  var psychReuseSettings=new SourceGameOverSettings(SourceGameOverSettings.PSYCH,
   {gameOverChar:'same-psych-player'});
  new PlayState(psychReuseSettings);
  var psychBorrowed=new Character(3,4,'same-psych-player',true);
  var beforePsychReuse=Character.created.length;
  Trace.reset();
  var psychReuse=new GameOverSubstate(psychBorrowed);
  check(psychReuse.wasReused() && psychReuse.actor()==psychBorrowed,
   'Psych matching chart character should borrow the live gameplay character');
  psychReuse.runCreate();
  check(Character.created.length==beforePsychReuse,'Psych matching actor created a duplicate death Character');
  psychReuse.runDestroy();
  check(!psychBorrowed.destroyed,'Psych substate destroyed its borrowed gameplay Character');

  PlayState.instance=null;
  var nativePlayer=new Character(0,0,'native-bf',true);
  Trace.reset();
  var native=new GameOverSubstate(nativePlayer);
  native.runCreate();
  check(Trace.has('native.setup:native-bf-dead') && Trace.has('super.create'),
   'native constructor/create path no longer delegates to its existing setup');
  check(!Trace.has('inGameOver:true') && !Trace.has('call:onGameOverStart:0'),
   'source-only hooks leaked into native game-over setup');
 }
}
'''


class SourceGameOverSetupTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_extracted_setup_audio_camera_and_borrowed_actor_lifetime(self):
        result = run_fixture(FIXTURE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
