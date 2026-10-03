from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HxcStrumlineNoteSurfaceTest(unittest.TestCase):
    def test_hscript_reads_live_notes_and_hold_members(self):
        files = {
            'Strumline.hx': '''class Strumline {
              public var notes(get,never):HxcStrumlineNoteList;
              public var holdNotes(get,never):HxcStrumlineNoteList;
              function get_notes():HxcStrumlineNoteList return new HxcStrumlineNoteList(this,false);
              function get_holdNotes():HxcStrumlineNoteList return new HxcStrumlineNoteList(this,true);
              public function new() {}
            }''',
            'PlayState.hx': '''class PlayState {
              public static var instance:PlayState;
              public var playerStrumline:Strumline=new Strumline();
              public function new(){instance=this;}
              public function hxcStrumlineMembers(line:Strumline,holds:Bool):Array<Dynamic>
               return line==playerStrumline ? (holds ? [{kind:"hold"}] : [{kind:"head"}]) : [];
            }''',
            'Main.hx': '''import hscript.Parser; import hscript.Interp;
            class Main {static function main():Void {
              var state=new PlayState(); var interp=new Interp();
              interp.variables.set("state",state);
              var holds:Dynamic=interp.execute(new Parser().parseString(
               "state.playerStrumline.holdNotes.members"));
              if(holds.length!=1||holds[0].kind!="hold") throw "HScript lost live holds";
              var heads:Dynamic=interp.execute(new Parser().parseString(
               "state.playerStrumline.notes.members"));
              if(heads.length!=1||heads[0].kind!="head") throw "HScript lost live heads";
            }}''',
        }
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, body in files.items():
                (Path(folder) / name).write_text(body, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', folder,
                 '-main', 'Main', '--interp'], cwd=folder,
                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hold_state_survives_native_segment_retirement(self):
        files = {
            'Conductor.hx': '''class Conductor {public static var songPosition:Float=0;}''',
            'Note.hx': '''class Note {
              public var strumTime:Float; public var sustainLength:Float;
              public var mustPress:Bool; public var isSustainNote:Bool;
              public var prevNote:Note; public var alive:Bool=true;
              public var kind:String; public var noteData:Int;
              public function new(t:Float, len:Float, player:Bool, sustain:Bool,
               kind:String, ?previous:Note) {
                strumTime=t; sustainLength=len; mustPress=player;
                isSustainNote=sustain; this.kind=kind; prevNote=previous; noteData=2;
              }
            }''',
            'EngineCompat.hx': '''class EngineCompat {
              public static function hxcNoteView(note:Note):Dynamic
               return {noteData:{kind:note.kind, data:note.noteData,
                getDirection:function():Int return note.noteData}};
            }''',
            'Main.hx': '''class Main {
              static function check(ok:Bool, label:String):Void if(!ok) throw label;
              static function main():Void {
                var head=new Note(1000,500,true,false,"hurt");
                var part=new Note(1125,0,true,true,"hurt",head);
                var part2=new Note(1250,0,true,true,"hurt",part);
                var other=new Note(1200,400,false,false,"markov");
                var tap=new Note(950,0,true,false,"mom");
                var surface=new HxcStrumlineNoteSurface([head,part,part2,other,tap]);
                check(surface.holdMembers(true).length==0,"unspawned hold leaked");
                surface.spawn(head); surface.spawn(other); surface.spawn(tap);
                Conductor.songPosition=900;
                var player=surface.holdMembers(true);
                check(player.length==1 && !player[0].hitNote && !player[0].missedNote,
                 "pending hold state");
                check(player[0].noteData.kind=="hurt",
                 "authored kind: "+player[0].noteData.kind);
                check(player[0].sustainLength==600,
                 "authored duration: "+player[0].sustainLength);
                check(surface.noteMembers(true,[head,part,tap,other]).length==2,
                 "live heads and taps filtered by side");
                surface.hit(head); head.alive=false;
                Conductor.songPosition=1250;
                player=surface.holdMembers(true);
                check(player.length==1 && player[0].hitNote && !player[0].missedNote,
                 "head hit did not survive retirement");
                check(player[0].sustainLength==250,"remaining hold duration");
                surface.hit(part2); part2.alive=false;
                check(surface.holdMembers(true)[0].hitNote,"segment hit changed head state");
                // A canceled miss never calls the accepted miss hook.
                check(!surface.holdMembers(false)[0].missedNote,"opponent miss was fabricated");
                surface.miss(part2);
                check(surface.holdMembers(true)[0].missedNote,"accepted segment miss not retained");
                Conductor.songPosition=1500;
                check(surface.holdMembers(true).length==0,"expired hold remained alive");
                check(surface.holdMembers(false).length==1,"other side was retired early");
                var newHead=new Note(1600,300,true,false,"alternate");
                surface.replaceSide(true,[newHead]);
                check(surface.holdMembers(true).length==0,"old side hold survived replacement");
                check(surface.holdMembers(false).length==1,"opposite side lost its hold");
                surface.spawn(newHead);
                check(surface.holdMembers(true).length==1
                 && surface.holdMembers(true)[0].noteData.kind=="alternate",
                 "replacement hold did not become live");
              }
            }''',
        }
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, body in files.items():
                (Path(folder) / name).write_text(body, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', folder, '-main', 'Main', '--interp'],
                cwd=folder, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
