"""Execute source-line initialization, mode controls, note binding and swaps."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    markers = (
        "\tfunction " + name + "(",
        "\tpublic function " + name + "(",
        "\t@:keep public function " + name + "(",
    )
    starts = [(source.find(marker), marker) for marker in markers]
    starts = [(start, marker) for start, marker in starts if start >= 0]
    if not starts:
        raise AssertionError(name)
    start, _ = min(starts)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameInputInitializationTest(unittest.TestCase):
    def test_mode_banks_origin_binding_and_script_preserving_swap(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(method(source, name) for name in (
            'initializeCodenameInputLines', 'captureCodenameNoteReceptorOffsets',
            'captureCodenameNoteReceptorOffset', 'codenameLineVisibilityHandler',
            'initializeCodenameStrumlines', 'configureCodenameStrumline',
            'getCodenameLineMembers', 'getCodenameLineStrumline', 'codenameNoteLane',
            'bindCodenameNoteLine', 'rebindCodenameInputActor'))
        note_source = (ROOT / 'source/Note.hx').read_text()
        note_scale = method(note_source, 'applyCodenameSourceStrumScale')
        fixture = r'''
enum KeyboardScheme {Solo(keys:Int);Duo(first:Bool);}
class Controls {
 public var scheme:KeyboardScheme=null;
 public function new() {}
 public function setKeyboardScheme(value:KeyboardScheme):Void scheme=value;
}
class Character {public var name:String;public function new(n:String)name=n;}
class CodenameActorPlan {public var lines:Array<Dynamic>;public function new(lines) this.lines=lines;}
class FlxG {public static var width:Float=1280;}
class Receptor {
 public var x:Float;public var visible=true;
 public function new(x:Float) this.x=x;
}
class Strumline {
 public var x:Float;public var y:Float;public var visible=true;
 public var cameras:Array<Dynamic>=[];
 public var members:Array<Receptor>=[];
 public var onMiss=new flixel.util.FlxSignal.FlxTypedSignal<Dynamic->Void>();
 public var noteHoldCovers:Dynamic={cameras:[]};
 public var spacing:Float=1;public var sourceStrumScale:Float=1;
 public function new(x:Float,y:Float,_type:String) {
  this.x=x;this.y=y;
  for(i in 0...Note.NOTE_AMOUNT) members.push(new Receptor(x+i*Note.swagWidth));
 }
 public function setNoteSpacing(value:Float):Void {spacing=value;resetReceptors();}
 public function setSourceStrumScale(value:Float):Void {sourceStrumScale=value;resetReceptors();}
 public function bindCodenameInputLine(_line:CodenameInputLine<Character>):Void {}
 function resetReceptors():Void for(i in 0...members.length)
  members[i].x=x+i*Note.swagWidth*spacing*sourceStrumScale;
}
class Point {
 public var x:Float;public var y:Float;
 public function new(x:Float,y:Float){this.x=x;this.y=y;}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Note {
 public static var NOTE_AMOUNT=4;
 public static var swagWidth:Float=112;
 public var codenameOrigin:Dynamic;
 public var codenameInputLine:CodenameInputLine<Character>=null;
 public var forceGfSing=false;
 public var codenameLineConfigured=false;
 public var codenameCreationScaleSet=false;
 public var codenameReceptorXOffset:Null<Float>=null;
 public var codenameGeneratedX:Null<Float>=null;
 public var codenameSourceStrumScale:Float=1;
 public var mustPress:Bool;public var noteData:Int;public var x:Float;
 public var scale=new Point(2,2);public var hitboxUpdates=0;
 public function new(index:Int,side:Int,?x:Float=0) {
  codenameOrigin={lineIndex:index,nativeSide:side};
  mustPress=side==0;noteData=index;this.x=x;
 }
 public function updateHitbox():Void hitboxUpdates++;
''' + note_scale + r'''
}
class Main {
 var codenameInputLines:Array<CodenameInputLine<Character>>=[];
 var codenameStrumlines:Array<Strumline>=[];
 var playerStrums:Strumline;var enemyStrums:Strumline;
 var opponentPlayer=false;var duoMode=false;var demoMode=false;
 public var ghostTapping=false;
 var controls=new Controls();var controlsPlayerTwo=new Controls();
 var unspawnNotes:Array<Note>=[];var notes:{members:Array<Note>}={members:[]};
 var plan:CodenameActorPlan;var actors:Array<Character>=[new Character('a'),new Character('b'),new Character('gf')];
 var strumLine:Dynamic={y:50};var SONG:Dynamic={uiType:'normal'};
 var camHUD:Dynamic={};var grpNoteSplashes:Dynamic={};var healthBarBG:Dynamic={};
 var members:Array<Dynamic>=[];
 function new() {
  playerStrums=new Strumline(100,50,'normal');enemyStrums=new Strumline(400,50,'normal');
  members=[playerStrums,enemyStrums,notes,grpNoteSplashes,healthBarBG];
  plan=new CodenameActorPlan([
   {type:1,role:'player',visible:true,keyCount:4,strumLinePos:0.75,strumPos:[0,50],strumScale:1,strumSpacing:1},
   {type:0,role:'opponent',visible:true,keyCount:4,strumLinePos:0.25,strumPos:[0,50],strumScale:1,strumSpacing:1},
   {type:1,role:'player',visible:true,keyCount:4,strumLinePos:0.65,strumPos:[0,60],strumScale:1,strumSpacing:1},
   {type:2,role:'gf',visible:true,keyCount:4,strumLinePos:0.4,strumPos:[123,77],strumScale:1.5,strumSpacing:1.25},
   {type:3,role:'extra',visible:false,keyCount:2,strumLinePos:0.55,strumPos:[0,88],strumScale:0.75,strumSpacing:1.1}
  ]);
 }
 function getCodenameActorPlan():CodenameActorPlan return plan;
 function getCodenameLineNotes(_lineIndex:Int):Array<Dynamic> return [];
 function getCodenameLineActorSlots(index:Int):Array<Null<Character>>
  return index==2||index>=4?[]:[actors[index==3?2:index]];
 function getCodenameLineCharacters(index:Int):Array<Character> return index==2||index>=4?[]:[actors[index==3?2:index]];
 function add(value:Dynamic):Dynamic {members.push(value);return value;}
 function insert(index:Int,value:Dynamic):Dynamic {members.insert(index,value);return value;}
 static function check(ok:Bool,s:String):Void if(!ok)throw s;
''' + methods + r'''
 static function main():Void {
  for(opp in [false,true]) for(coop in [false,true]) {
   var state=new Main();state.opponentPlayer=opp;state.duoMode=coop;
   var head=new Note(0,0,125),wrongSide=new Note(0,1),opponent=new Note(1,1,530),empty=new Note(2,0);
   head.codenameGeneratedX=113;
   var girlfriend=new Note(3,1,740),wrongGfSide=new Note(3,0);
   var foreign=new Note(99,0);var legacy=new Note(0,0);legacy.codenameOrigin=null;
   state.unspawnNotes=[head,wrongSide,foreign,legacy,empty,girlfriend,wrongGfSide];state.notes.members=[opponent];
   state.initializeCodenameInputLines(state.plan);
   check(state.codenameInputLines.length==5,'empty/extra source line dropped');
   var a=state.codenameInputLines[0],b=state.codenameInputLines[1];
   check(a.members==state.playerStrums.members
    && b.members==state.enemyStrums.members
    && state.codenameInputLines[2].members!=state.playerStrums.members
    && state.codenameInputLines[3].members!=state.enemyStrums.members
    && state.codenameInputLines[4].members!=null,
    'source lines did not expose distinct native receptor groups');
   check(state.codenameInputLines[2].members!=state.codenameInputLines[3].members
    && state.codenameInputLines[3].members!=state.codenameInputLines[4].members,
    'additional source lines aliased one another');
   check(state.getCodenameLineStrumline(2)!=state.getCodenameLineStrumline(0)
    && state.getCodenameLineStrumline(-1)==null && state.getCodenameLineStrumline(5)==null,
    'source-index strumline lookup did not preserve distinct bounds');
   var gfLine=state.codenameInputLines[3],extraLine=state.codenameInputLines[4];
   check(gfLine.strumLinePos==0.4 && gfLine.strumPos[0]==123
    && gfLine.strumScale==1.5 && gfLine.strumSpacing==1.25
    && state.getCodenameLineStrumline(3).x==123 && state.getCodenameLineStrumline(3).y==77
    && state.getCodenameLineStrumline(3).sourceStrumScale==1.5
    && extraLine.keyCount==2 && !extraLine.visible
    && !state.getCodenameLineStrumline(4).visible
    && !state.getCodenameLineStrumline(4).members[2].visible,
    'authored line geometry, scaling, key count or visibility was lost');
   extraLine.visible=true;
   check(state.getCodenameLineStrumline(4).visible,
    'source-line visibility change did not reach its native receptor group');
   extraLine.visible=false;
   state.ghostTapping=true;
   check(a.ghostTapping&&b.ghostTapping,'line fallback did not follow game setting');
   a.ghostTapping=false;
   check(!a.ghostTapping&&b.ghostTapping,'line override leaked to sibling');
   check(head.codenameInputLine==a&&opponent.codenameInputLine==b,'generated/live notes not bound');
   check(girlfriend.codenameInputLine==state.codenameInputLines[3]&&girlfriend.forceGfSing
    &&girlfriend.codenameInputLine.cpu&&girlfriend.codenameInputLine.characters[0]==state.actors[2]
    && girlfriend.codenameSourceStrumScale==1.5 && girlfriend.scale.x==3
    && girlfriend.scale.y==3 && girlfriend.hitboxUpdates==1,
    'girlfriend source line did not retain CPU and singer');
   check(head.codenameReceptorXOffset==12 && opponent.codenameReceptorXOffset==18
    && girlfriend.codenameReceptorXOffset==4,
    'generated note padding or script-authored receptor offsets were lost before line binding');
   check(wrongGfSide.codenameInputLine==null&&!wrongGfSide.forceGfSing,'wrong-side girlfriend note bound');
   check(wrongSide.codenameInputLine==null&&foreign.codenameInputLine==null&&legacy.codenameInputLine==null,'invalid/native binding');
   check(empty.codenameInputLine==state.codenameInputLines[2]
    && empty.codenameInputLine.characters.length==0
    && empty.codenameInputLine.members==state.getCodenameLineStrumline(2).members,
    'empty line did not retain its own receptor group');
   if(coop) {
    check(state.controls.scheme.equals(Duo(true))&&state.controlsPlayerTwo.scheme.equals(Duo(false)),'coop banks not configured');
    check(a.controls==(opp?state.controlsPlayerTwo:state.controls),'coop player controls reversed incorrectly');
    check(b.controls==(opp?state.controls:state.controlsPlayerTwo),'coop opponent controls reversed incorrectly');
   } else {
    var solo=opp?state.controlsPlayerTwo:state.controls;
    check(solo.scheme.equals(Solo(4)),'solo bank not configured');
    check(a.controls==solo&&b.controls==solo,'solo source controls differ');
   }
   var added=new Character('script'),replacement=new Character('new');
   b.characters.push(added);a.characters.push(added);
   var saved=b.characters;
   state.rebindCodenameInputActor(state.actors[0],replacement);
   check(a.characters[0]==replacement&&a.characters[1]==added,'swap discarded script actor');
   check(b.characters==saved&&b.characters[1]==added,'swap recreated unrelated script array');
   state.initializeCodenameInputLines(state.plan);
   check(state.codenameInputLines[0]==a,'repeated init replaced stable view');
  }
  var skipped=new Main();
  skipped.plan=new CodenameActorPlan([null,{type:1,role:'player'}]);
  var skippedNote=new Note(0,0),laterNote=new Note(1,0);
  skipped.unspawnNotes=[skippedNote,laterNote];
  skipped.initializeCodenameInputLines(skipped.plan);
  check(skipped.codenameInputLines.length==2 && skipped.codenameInputLines[0]==null
   && skipped.codenameInputLines[1].lineIndex==1 && skippedNote.codenameInputLine==null
   && laterNote.codenameInputLine==skipped.codenameInputLines[1]
   && skipped.codenameInputLines[1].members==skipped.playerStrums.members
   && skipped.getCodenameLineStrumline(0)==null
   && skipped.getCodenameLineStrumline(1)==skipped.playerStrums,
   'null source line must leave a hole in the input array');
  skipped.rebindCodenameInputActor(skipped.actors[1],new Character('replacement'));
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            folder = Path(work)
            (folder / 'Main.hx').write_text(fixture, newline='\n')
            # initializeCodenameInputLines supplies a live song-position
            # callback. Put this module beside the fixture so its single clock
            # value avoids Conductor's unrelated Song/Flixel dependency graph.
            (folder / 'Conductor.hx').write_text('''class Conductor {
 public static var songPosition:Float=0;
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'tools/tests/haxe_stubs'),
                                     '-cp', str(ROOT / 'source'), '-cp', str(folder), '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
