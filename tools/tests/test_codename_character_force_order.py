"""Run extracted Character animation methods across nullable Codename event dispatch."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    if name == "playAnim":
        start = source.index("\tpublic function " + name + "(")
    elif name == "codenamePlayAnim":
        start = source.index("\t@:keep public function " + name + "(")
    else:
        start = source.index("\tfunction " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for at in range(brace, len(source)):
        depth += (source[at] == "{") - (source[at] == "}")
        if depth == 0:
            return source[start:at + 1]
    raise AssertionError(name)


class CodenameCharacterForceOrderTest(unittest.TestCase):
    def test_nullable_force_resolves_after_mutable_animation_event(self):
        source = (ROOT / "source/Character.hx").read_text()
        methods = "\n".join(method(source, name) for name in (
            "playAnim", "codenameApplyGlobalOffset", "codenamePlayAnim",
            "codenameAdvanceLoop", "codenameUpdateAfterSuper"))
        methods = methods.replace("[AnimName, Force, false, Reversed]",
                                  "[cast AnimName, Force, false, Reversed]")
        update = source.index("\t\tif (codenameLiveDefinition != null) {", source.index("\toverride function update("))
        self.assertLess(source.index("super.update(elapsed);", update),
                        source.index("codenameUpdateAfterSuper(elapsed);", update))
        construction = source.index("codenameRuntime = codename.createRuntime(this);")
        self.assertLess(source.index("codenameVisualBuilding = true;", construction),
                        source.index("codenameRuntime.call('create', []);", construction))
        self.assertLess(source.index("codenameRuntime.event('onCharacterXMLParsed', event);", construction),
                        source.index("CodenameCharacterVisual.build(this", construction))
        self.assertLess(source.index("codenameLiveDefinition = builtCodenameDefinition;", construction),
                        source.index("codenameRuntime.call('postCreate', []);", construction))
        self.assertIn("codenameBuildingAnimations = null;\n\t\t\t\tif (codenameRuntime != null) codenameRuntime.destroy();", source)
        fixture = '''class FakePoint {
 public var x:Float=0; public var y:Float=0;
 public function new() {}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class FakeAnimation {
 public var curAnim:Dynamic=null;
 public var name:String=null;
 public var nullLoopAvailable=false;
 public var calls:Array<Dynamic>=[];
 public function new() {}
 public function exists(name:String):Bool return name=='plain' || name=='forced' || name=='plain-loop'
  || (name=='null-loop' && nullLoopAvailable);
 public function play(name:String,force:Bool,reversed:Bool,frame:Int):Void {
  calls.push({name:name,force:force,reversed:reversed,frame:frame});
  this.name=name;
  curAnim={name:name,finished:false};
 }
}
class CodenameCharacterEvent {
 public var animName:String; public var force:Null<Bool>; public var reverse:Bool;
 public var startingFrame:Int=0; public var context:Dynamic; public var cancelled=false;
 public function new() {}
}
class Conductor { public static var songPosition:Float=123; }
class PlayState { public static var instance:Dynamic=null; }
class Character {
 public var codenameLiveDefinition:Dynamic={animations:[{name:'plain',forced:false},
  {name:'forced',forced:true}]};
 var codenameVisualBuilding=false;
 var codenameBuildingAnimations:Array<Dynamic>=null;
 public var codenameRuntime:Dynamic;
 public var hook:CodenameCharacterEvent->Void=null;
 public var seen:Array<Dynamic>=[];
 public var seenContexts:Array<Dynamic>=[];
 public var log:Array<String>=[];
 public var animation=new FakeAnimation();
 public var offset=new FakePoint();
 public var frameOffset=new FakePoint();
 public var globalOffset=new FakePoint();
 public var isPlayer=false; public var playerOffsets=false;
 public var animOffsets:Map<String,Array<Dynamic>>=[];
 public var vSliceBaseFrames:Dynamic=null;
 public var isDie=false; public var likeGf=false; public var danced=false;
 public var stunned=false; var codenameStunnedTime:Float=0;
 public var debugMode=false;
 public var lastAnimContext:Dynamic=null; public var lastHit:Float=0;
 var codenameAnimationContext:Dynamic;
 public var codenameAnimationLock=false;
 var codenamePendingForce:Null<Bool>;
 var codenameHasPendingForce=false;
 public function new() {
  var self=this;
  codenameRuntime={event:function(_name:String,e:CodenameCharacterEvent):Dynamic {
   self.log.push('onPlayAnim:' + e.animName);
   self.seen.push(e.force);
   self.seenContexts.push(e.context);
   if(self.hook!=null) self.hook(e);
   return e;
  },call:function(name:String,_args:Array<Dynamic>):Bool {
   self.log.push(name); return true;
  }};
 }
 function applyVSliceAnimationAsset(_name:String):Void {}
 function codenameTryDance():Void log.push('tryDance');
''' + methods + '''
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function last(actor:Character):Dynamic return actor.animation.calls[actor.animation.calls.length-1];
 static function main():Void {
  var actor=new Character();
  actor.animOffsets.set('plain',[2,3]);
  actor.animOffsets.set('forced',[-5,9]);
  actor.hook=function(e) e.animName='forced';
  actor.codenamePlayAnim('plain',null,'DANCE');
  check(actor.seen[0]==null && last(actor).name=='forced' && last(actor).force,
   'null force resolved before renamed animation');
  check(!actor.codenameAnimationLock,'script animation granted input lock');
  check(actor.frameOffset.x==-5 && actor.frameOffset.y==9,
   'renamed animation did not set its distinct frame offset');
  actor.hook=function(e) e.animName='plain';
  actor.codenamePlayAnim('forced',null,'DANCE');
  check(actor.seen[1]==null && last(actor).name=='plain' && !last(actor).force,
   'renamed non-forced animation retained old forced flag');
  check(actor.frameOffset.x==2 && actor.frameOffset.y==3,
   'successive animation did not replace frame offset');
  actor.hook=function(e) e.animName='forced';
  actor.codenamePlayAnim('plain',false,'DANCE');
  check(actor.seen[2]==false && !last(actor).force,'explicit false changed');
  actor.hook=function(e) e.animName='plain';
  actor.codenamePlayAnim('forced',true,'DANCE');
  check(actor.seen[3]==true && last(actor).force,'explicit true changed');
  actor.hook=function(e) {e.animName='plain';e.force=null;};
  actor.codenamePlayAnim('forced',true,'DANCE');
  check(actor.seen[4]==true && !last(actor).force,'callback null reset ignored');
  var before=actor.animation.calls.length;
  actor.hook=function(e) e.cancelled=true;
  actor.codenamePlayAnim('plain',null,'DANCE');
  check(actor.seen[5]==null && actor.animation.calls.length==before,
   'cancelled event played native animation');
  actor.hook=null;
  actor.playAnim('forced',false);
  check(actor.seen[6]==false && !last(actor).force,'direct Bool API changed');
  actor.codenameLiveDefinition=null;
  before=actor.seen.length;
  actor.playAnim('plain',true);
  check(actor.seen.length==before && last(actor).force,'non-Codename API changed');
  actor.codenameLiveDefinition={animations:[{name:'plain',forced:false},
   {name:'forced',forced:true}]};
  var nested=false;
  actor.hook=function(e) {
   if(!nested) {
    nested=true;
    actor.codenamePlayAnim('forced',true,'INNER');
   }
  };
  before=actor.seen.length;
  actor.codenamePlayAnim('plain',null,'OUTER');
  check(actor.seen[before]==null && actor.seen[before+1]==true
   && actor.seenContexts[before]=='OUTER' && actor.seenContexts[before+1]=='INNER',
   'nested dispatch lost nullable force or context');
  check(last(actor).name=='plain' && !last(actor).force,
   'outer default force changed after nested dispatch');
  actor.hook=function(_e) throw 'callback error';
  var threw=false;
  try actor.codenamePlayAnim('plain',null,'THROW') catch (_:Dynamic) threw=true;
  check(threw,'throwing callback was swallowed by fixture');
  actor.hook=null;
  before=actor.seen.length;
  actor.playAnim('forced',false);
  check(actor.seen[before]==false && actor.seenContexts[before]==null
   && !last(actor).force,'thrown callback leaked pending force/context');
  actor.playAnim('plain',true);
  var current=actor.animation.curAnim;
  before=actor.animation.calls.length;
  actor.lastAnimContext='DANCE'; actor.lastHit=0; actor.codenameAnimationLock=false;
  actor.globalOffset.set(11,13); actor.offset.set(7,8);
  var previousFrameX=actor.frameOffset.x; var previousFrameY=actor.frameOffset.y;
  actor.hook=function(e) e.animName='missing';
  actor.codenamePlayAnim('plain',null,'SING');
  check(actor.animation.calls.length==before && actor.animation.curAnim==current
   && actor.lastAnimContext=='DANCE' && actor.lastHit==Conductor.songPosition
   && !actor.codenameAnimationLock && actor.offset.x==-11 && actor.offset.y==-13
   && actor.frameOffset.x==previousFrameX && actor.frameOffset.y==previousFrameY,
   'missing post-callback name changed animation/context or lost global offset/timestamp');
  actor.hook=function(e) e.animName=null;
  actor.lastHit=0;
  actor.codenamePlayAnim('plain',null,'MISS');
  check(actor.animation.calls.length==before && actor.animation.curAnim==current
   && actor.lastAnimContext=='DANCE' && actor.lastHit==Conductor.songPosition
   && actor.frameOffset.x==previousFrameX && actor.frameOffset.y==previousFrameY,
   'null post-callback name changed animation/context or lost miss timestamp');
  actor.hook=null; actor.isPlayer=true; actor.playerOffsets=false;
  actor.codenamePlayAnim('plain',true,'DANCE');
  check(actor.offset.x==11 && actor.offset.y==-13 && actor.frameOffset.x==2,
   'player mismatch global sign or frame offset');
  actor.playerOffsets=true;
  actor.codenamePlayAnim('plain',true,'DANCE');
  check(actor.offset.x==-11 && actor.offset.y==-13 && actor.frameOffset.x==2,
   'matching playerOffsets global sign');
  actor.isPlayer=false; actor.playerOffsets=false;
  actor.hook=function(e) { e.animName='plain'; e.cancelled=true; };
  before=actor.animation.calls.length;
  actor.lastHit=0;
  actor.codenamePlayAnim('plain',null,'SING');
  check(actor.animation.calls.length==before && actor.lastHit==0,
   'cancelled callback changed timestamp or animation');
  actor.hook=null;
  actor.log.resize(0);
  actor.lastAnimContext='DANCE';
  current=actor.animation.curAnim;
  current.finished=true;
  @:privateAccess actor.codenameUpdateAfterSuper(0.1);
  check(actor.log.join(',')=='onPlayAnim:plain-loop,update'
   && last(actor).name=='plain-loop' && actor.lastAnimContext=='DANCE'
   && actor.seen[actor.seen.length-1]==null && !actor.codenameAnimationLock,
   'finished -loop successor did not precede update with nullable force/context');
  actor.log.resize(0);
  actor.animation.curAnim={name:'forced',finished:true};
  actor.animation.name='forced';
  before=actor.animation.calls.length;
  @:privateAccess actor.codenameUpdateAfterSuper(0.1);
  check(actor.log.join(',')=='update' && actor.animation.calls.length==before,
   'missing successor changed animation');
  actor.log.resize(0);
  actor.animation.curAnim={name:'plain',finished:true};
  actor.animation.name='plain';
  actor.debugMode=true;
  @:privateAccess actor.codenameUpdateAfterSuper(0.1);
  check(actor.log.join(',')=='update' && actor.animation.calls.length==before,
   'debug mode advanced successor');
  actor.debugMode=false;
  actor.hook=null;
  actor.log.resize(0);
  actor.animation.curAnim=null; actor.animation.name=null;
  actor.animation.nullLoopAvailable=true;
  @:privateAccess actor.codenameUpdateAfterSuper(0.1);
  check(actor.log.join(',')=='onPlayAnim:null-loop,update'
   && last(actor).name=='null-loop',
   'no-current-animation null-loop successor differs from donor');
  actor.animation.nullLoopAvailable=false;
  actor.log.resize(0);
  actor.hook=function(e) e.animName='missing';
  actor.debugMode=true;
  actor.codenamePlayAnim('plain',null,'LOCK');
  check(last(actor).name=='missing' && actor.lastAnimContext=='LOCK'
   && actor.frameOffset.x==0 && actor.frameOffset.y==0,
   'debug mode did not retain donor missing-animation attempt');
  actor.hook=function(e) e.animName=null;
  before=actor.animation.calls.length;
  actor.codenamePlayAnim('plain',null,'SING');
  check(actor.animation.calls.length==before && actor.lastAnimContext=='LOCK',
   'null name changed animation context in debug mode');
  // During XML construction, callbacks still take the Codename path while
  // the completed public definition stays unavailable.
  actor.debugMode=false;
  actor.codenameLiveDefinition=null;
  @:privateAccess actor.codenameVisualBuilding=true;
  @:privateAccess actor.codenameBuildingAnimations=[];
  actor.hook=function(e) e.force=null;
  before=actor.seen.length;
  actor.codenamePlayAnim('plain',true,null);
  check(actor.seen[before]==true && actor.seenContexts[before]==null
   && !last(actor).force && actor.codenameLiveDefinition==null,
   'construction callback did not use source path or saw current descriptor early');
  @:privateAccess actor.codenameBuildingAnimations.push({name:'plain',forced:true});
  actor.codenamePlayAnim('plain',false,null);
  check(last(actor).force,'previous duplicate descriptor unavailable during next LOOP play');
  @:privateAccess actor.codenameBuildingAnimations.push({name:'plain',forced:false});
  actor.codenamePlayAnim('plain',true,null);
  check(!last(actor).force,'later duplicate descriptor did not replace prior map value');
  @:privateAccess actor.codenameVisualBuilding=false;
  @:privateAccess actor.codenameBuildingAnimations=null;
  actor.hook=null;
  before=actor.seen.length;
  actor.playAnim('plain',true);
  check(actor.seen.length==before && last(actor).force,
   'construction route leaked after cleanup');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                 '-cp', work, '--run', 'Main'], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
