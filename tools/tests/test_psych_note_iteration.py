"""Psych live cursor orders match the pinned donor and real Flixel mutations."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]
FLIXEL = ROOT / '.haxelib/flixel/6,1,2/flixel'


class PsychNoteIterationTest(unittest.TestCase):
    def test_live_cursor_matches_donor_mutations_and_explicit_guards(self):
        play = (ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
        method = extract_method(play, 'function forEachLiveGameplayNote(').replace('function ', 'public function ', 1)
        self.assertIn('forEachLiveGameplayNote(function(daNote:Note)', play)
        helper = (ROOT/'source/PsychNoteIteration.hx').read_text(encoding='utf-8')
        self.assertNotIn('indexOf(', extract_method(helper, 'public function run('))
        self.assertNotIn('.copy()', helper)
        group_source = (FLIXEL/'group/FlxGroup.hx').read_text(encoding='utf-8')
        group_methods = '\n'.join(extract_method(group_source, marker) for marker in (
            'public function add(', 'public function insert(', 'public function getFirstNull(',
            'public function remove(', 'public function replace(', 'public function clear(',
            'function onMemberAdd(', 'function onMemberRemove(',
            'function get_memberAdded(', 'function get_memberRemoved(',
            'override public function destroy('))
        destroy = (FLIXEL/'util/FlxDestroyUtil.hx').read_text(encoding='utf-8')
        destroy_methods = '\n'.join(extract_method(destroy, marker) for marker in (
            'public static function destroy<', 'public static function destroyArray<'))
        group = r'''package flixel.group;
import Note;
import flixel.util.FlxSignal.FlxTypedSignal;
import flixel.util.FlxDestroyUtil;
class FlxG {public static var log={warn:function(message:String):Void {}};}
class GroupBase {public function new() {} public function destroy():Void {}}
class FlxArrayUtil {public static function clearArray<T>(array:Array<T>):Void array.resize(0);}
class FlxTypedGroup<T:Note> extends GroupBase {
 public var members:Array<T>; public var length:Int; public var maxSize:Int=0;
 public var memberAdded(get,never):FlxTypedSignal<T->Void>;
 public var memberRemoved(get,never):FlxTypedSignal<T->Void>;
 var _memberAdded:FlxTypedSignal<T->Void>; var _memberRemoved:FlxTypedSignal<T->Void>;
 public function new(members:Array<T>) {super();this.members=members;length=members.length;}
 // All membership mutations below are exact pinned methods.
 public function forEachAlive(callback:T->Void):Void
  for(note in members)if(note!=null && note.exists && note.alive)callback(note);
 __GROUP_METHODS__
}
'''.replace('__GROUP_METHODS__', group_methods)
        donor = (ROOT/'../fnf_sources/FNF-PsychEngine/source/states/PlayState.hx').read_text(encoding='utf-8')
        cursor_start = donor.index('var i:Int = 0;', donor.index('if(notes.length > 0)'))
        cursor_prefix = donor[cursor_start:donor.index('var strumGroup:',cursor_start)]
        cursor_tail = 'if(daNote.exists) i++;'
        self.assertIn(cursor_tail, donor[cursor_start:])
        reference = cursor_prefix.replace('notes.', 'owner.notes.') + 'callback(daNote);\n' + cursor_tail + '\n}'
        fixture = r'''import flixel.group.FlxGroup.FlxTypedGroup;
class PlayState {
 public var nightmareVisionScripts:Dynamic=null; public var mode:Int=1;
 public var inCutscene:Bool=false; public var startedCountdown:Bool=true;
 public var notes:FlxTypedGroup<Note>; public var psychNoteIteration=new PsychNoteIteration();
 public function new(members:Array<Note>) notes=new FlxTypedGroup<Note>(members);
 public function sourceNoteTimingMode():Int return mode;
 __METHOD__
}
@:access(PsychNoteIteration)
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function reference(owner:PlayState,callback:Note->Void):Void { __REFERENCE__ }
 static function order(which:Int,donor:Bool):String {
  var a=new Note(1),b=new Note(2),c=new Note(3),d=new Note(4);
  var game=new PlayState([a,b,c]);var seen:Array<Int>=[];var mutated=false;
  if(which==20)b.alive=false;
  if(which==16)game.notes.memberRemoved.add(function(n){if(n==b)game.notes.add(b);});
  if(which==17)game.notes.memberAdded.add(function(n){if(n==d)game.notes.remove(d,true);});
  var callback=function(n:Note):Void {
   seen.push(n.id);check(seen.length<100,'finite fixture unexpectedly loops');
   if(which==21 && n==d)game.notes.add(new Note(5));
   if(n!=a || mutated)return;mutated=true;
   switch(which) {
    case 0: game.notes.add(d);
    case 1: game.notes.insert(2,d);
    case 2: game.notes.insert(0,d);
    case 3: game.notes.remove(b,true);
    case 4: a.kill();game.notes.remove(a,true);
    case 5: game.notes.remove(a,true);
    case 6: game.notes.replace(b,d);
    case 7: game.notes.replace(a,d);
    case 8: game.notes.members.reverse();
    case 9: game.notes.members.sort(function(x,y)return y.id-x.id);
    case 10: game.notes.members[1]=d;
    case 11: game.notes.members.splice(1,1);game.notes.length--;
    case 12: game.notes.members.push(d);
    case 13: game.notes.members.push(d);game.notes.length++;
    case 14: game.notes=new FlxTypedGroup<Note>([d,new Note(5),new Note(6)]);
    case 15: game.notes.clear();
    case 16: game.notes.remove(b,true);
    case 17: game.notes.add(d);
    case 18: a.kill();game.notes.members.splice(0,1);game.notes.length--;
    case 19: game.notes.members[0]=c;game.notes.members[2]=a;
    case 21: game.notes.add(d);
    case 22: game.notes.members=[a,c,b];
    case 23: a.kill();game.notes=new FlxTypedGroup<Note>([d,new Note(5)]);
    case 24: game.notes.clear();game.notes.add(d);
    default:
   }
  };
  if(donor)reference(game,callback);else game.forEachLiveGameplayNote(callback);
  check(!game.psychNoteIteration.active,'live pass remains active');return seen.join(',');
 }
 static function main():Void {
  for(which in 0...25)check(order(which,false)==order(which,true),'donor visit order '+which);
  check(order(0,false)=='1,2,3,4','same-frame append deferred');
  check(order(2,false)=='1,1,2,3','insert-before must revisit current and skip prior new slot');
  check(order(5,false)=='1,3','donor live-current detach cursor was substituted');
  check(order(8,false)=='1,2,1','reorder must use live indices');
  check(order(12,false)=='1,2,3' && order(13,false)=='1,2,3,4','raw push must honor group.length');
  check(order(14,false)=='1,5,6' && order(23,false)=='1,4,5','replacement group must inherit cursor');
  check(order(20,false)=='1,2,3','exists=true alive=false was incorrectly filtered');
  var a=new Note(1),b=new Note(2),c=new Note(3);var game=new PlayState([a,null,b,c]);var seen=[];
  game.forEachLiveGameplayNote(function(n){seen.push(n.id);if(n==a)game.notes.remove(b,false);});
  check(seen.join(',')=='1,3','null/nonsplice hole must make progress');
  a=new Note(1);b=new Note(2);game=new PlayState([a,b]);seen=[];
  game.forEachLiveGameplayNote(function(n){seen.push(n.id);if(n==a)n.kill();});
  check(seen.join(',')=='1,2','retained killed current must make progress');
  a=new Note(1);b=new Note(2);c=new Note(3);game=new PlayState([a,b,c]);seen=[];
  game.forEachLiveGameplayNote(function(n){seen.push(n.id);if(n==a)game.notes.members.splice(1,1);});
  check(seen.join(',')=='1,3','raw shrink must stop at actual array bounds');
  a=new Note(1);b=new Note(2);game=new PlayState([a,b]);seen=[];
  game.forEachLiveGameplayNote(function(n){seen.push(n.id);game.notes.destroy();});
  check(seen.join(',')=='1' && !game.psychNoteIteration.active,'destroyed group guard');
  game=new PlayState([new Note(1)]);var thrown:Dynamic=null;
  try game.forEachLiveGameplayNote(function(n)throw 'callback-sentinel')catch(e:Dynamic)thrown=e;
  check(thrown=='callback-sentinel' && !game.psychNoteIteration.active,'throw cleanup changed error');
  game.forEachLiveGameplayNote(function(n)n.visited++);check(game.notes.members[0].visited==1,'next pass after throw');
  var rejected=false;game=new PlayState([new Note(1),new Note(2)]);
  game.forEachLiveGameplayNote(function(n){n.visited++;if(n.id==1){try game.forEachLiveGameplayNote(function(_)throw 'nested')catch(e:Dynamic)rejected=Std.string(e).indexOf('reenter')>=0;}});
  check(rejected && game.notes.members[1].visited==1 && !game.psychNoteIteration.active,'reentry damaged outer pass');
  a=new Note(1);b=new Note(2);game=new PlayState([a,b]);game.inCutscene=true;
  game.forEachLiveGameplayNote(function(n)n.visited++);
  check(a.visited==0 && b.visited==0 && a.canBeHit && a.wasGoodHit,'cutscene source gate');
  game.inCutscene=false;game.startedCountdown=false;b.alive=false;
  game.forEachLiveGameplayNote(function(n)n.visited++);
  check(a.visited==0 && !a.canBeHit && !a.wasGoodHit && b.canBeHit && b.wasGoodHit,'precountdown source alive reset gate');
  for(mode in [0,1]) {
   a=new Note(1);b=new Note(2);c=new Note(3);game=new PlayState([a,b,c]);game.mode=mode;if(mode==1)game.nightmareVisionScripts={};
   game.forEachLiveGameplayNote(function(n){n.visited++;if(n==a){n.kill();game.notes.remove(n,true);}});
   check(b.visited==0 && c.visited==1,'native/NV iteration changed');
  }
 }
}
'''.replace('__METHOD__', method).replace('__REFERENCE__',reference)
        files = {
            'Main.hx': 'import flixel.group.FlxGroup.FlxTypedGroup;\n' + fixture[fixture.index('@:access(PsychNoteIteration)'):],
            'Note.hx': 'class Note {public var exists=true;public var alive=true;public var id:Int;public var visited=0;public var canBeHit=true;public var wasGoodHit=true;public function new(id:Int)this.id=id;public function kill():Void{exists=false;alive=false;}public function revive():Void{exists=true;alive=true;}public function destroy():Void{exists=false;alive=false;}}',
            'PlayState.hx': fixture[:fixture.index('@:access(PsychNoteIteration)')],
            'PsychNoteIteration.hx': helper,
            'flixel/group/FlxGroup.hx': group,
            'flixel/util/FlxSignal.hx': (FLIXEL/'util/FlxSignal.hx').read_text(encoding='utf-8'),
            'flixel/util/FlxDestroyUtil.hx': 'package flixel.util; interface IFlxDestroyable {function destroy():Void;} class FlxDestroyUtil {' + destroy_methods + '}',
        }
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            for name,text in files.items():
                path=Path(folder)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
