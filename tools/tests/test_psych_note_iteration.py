"""Psych live-note mutation cannot skip neighboring travel/hit/lifetime work."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychNoteIterationTest(unittest.TestCase):
    def test_splice_safe_pass_reuses_storage_and_skips_destroyed_notes(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = extract_method(source, 'function forEachLiveGameplayNote(').replace('function ', 'public function ', 1)
        self.assertIn('forEachLiveGameplayNote(function(daNote:Note)', source)
        self.assertNotIn('.copy()', method)
        fixture = r'''
class Note {
 public var exists:Bool=true; public var alive:Bool=true; public var id:Int;
 public var visited:Int=0; public var updated:Bool=false;
 public function new(id:Int) this.id=id;
 public function kill():Void { exists=false; alive=false; }
}
class Group {
 public var members:Array<Note>; public function new(members:Array<Note>) this.members=members;
 // Pinned Flixel iterates the mutable members array in forEachAlive.
 public function forEachAlive(callback:Note->Void):Void
  for (note in members) if (note!=null && note.exists && note.alive) callback(note);
 public function remove(note:Note):Void { var index=members.indexOf(note); if (index>=0) members.splice(index,1); note.kill(); }
}
class PlayState {
 public var nightmareVisionScripts:Dynamic=null; public var mode:Int=1;
 public var notes:Group; public var psychNoteUpdateScratch:Array<Note>=[];
 public function new(members:Array<Note>) notes=new Group(members);
 public function sourceNoteTimingMode():Int return mode;
 __METHOD__
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var first=new Note(1); var neighbor=new Note(2); var third=new Note(3);
  var legacy=new PlayState([first,neighbor,third]); legacy.mode=0;
  legacy.forEachLiveGameplayNote(function(note) { note.visited++; if(note==first) legacy.notes.remove(note); });
  check(first.visited==1 && neighbor.visited==0 && third.visited==1,'fixture must reproduce Flixel live-array skip');
  first=new Note(1); neighbor=new Note(2); third=new Note(3);
  var game=new PlayState([first,neighbor,third]); var storage=game.psychNoteUpdateScratch;
  game.forEachLiveGameplayNote(function(note) {
   note.visited++; note.updated=true;
   // Adjacent due notes both retire; their surviving neighbor still follows.
   if(note==first || note==neighbor) game.notes.remove(note);
  });
  check(first.visited==1 && neighbor.visited==1 && third.visited==1 && third.updated,'adjacent retirement skipped surviving note');
  check(game.psychNoteUpdateScratch==storage && storage.length==0,'iteration allocates or retains dead entries');
  first=new Note(1); neighbor=new Note(2); third=new Note(3); var last=new Note(4);
  game=new PlayState([first,neighbor,third,last]); storage=game.psychNoteUpdateScratch;
  game.forEachLiveGameplayNote(function(note) {
   note.visited++;
   if(note==first) game.notes.remove(third);
   if(note==neighbor) { game.notes.remove(first); game.notes.remove(neighbor); }
  });
  check(first.visited==1 && neighbor.visited==1 && third.visited==0 && last.visited==1,'callback removals skipped survivor or updated destroyed note');
  check(storage==game.psychNoteUpdateScratch && storage.length==0,'scratch was not reusable');
  var added=new Note(5); game=new PlayState([new Note(1)]);
  game.forEachLiveGameplayNote(function(note) { note.visited++; game.notes.members.push(added); });
  check(added.visited==0,'new callback insertion should enter the next pass');
  game.forEachLiveGameplayNote(function(note) note.visited++);
  check(added.visited==1,'callback insertion lost on next pass');
  game=new PlayState([new Note(1),new Note(2),new Note(3)]); game.nightmareVisionScripts={};
  game.forEachLiveGameplayNote(function(note) { note.visited++; if(note.id==1) game.notes.remove(note); });
  check(game.notes.members[0].visited==0 && game.notes.members[1].visited==1,'NV iteration behavior changed');
 }
}
'''.replace('__METHOD__', method)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
