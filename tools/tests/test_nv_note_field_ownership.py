"""Execute source-note membership writes and host field teardown ownership."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvNoteFieldOwnershipTest(unittest.TestCase):
    def test_membership_setter_and_field_teardown_leave_native_note_cleanup_owned(self):
        setter = method((ROOT / 'source/Note.hx').read_text(), 'function set_playField(')
        teardown = method((ROOT / 'source/PlayState.hx').read_text(),
                          'function nightmareVisionDestroyFieldView(')
        fixture = r'''
class Note {
 public var playField(default,set):Dynamic=null;
 public var destroys:Int=0;
 public function new() {}
 public function destroy():Void destroys++;
 __SETTER__
}
class NightmareVisionPlayFieldView {
 public var notes:Array<Dynamic>=[];
 public var adds:Int=0;public var removes:Int=0;
 public function new() {}
 public function addNote(note:Dynamic):Void {adds++;notes.push(note);}
 public function removeNote(note:Dynamic):Void {removes++;notes.remove(note);}
}
class NativeNotes {
 public var members:Array<Note>=[];
 public function new() {}
 public function destroy():Void {for(note in members)note.destroy();members.resize(0);}
}
class Fields {
 public var members:Array<NightmareVisionPlayFieldView>=[];
 public function new() {}
 public function remove(field:NightmareVisionPlayFieldView,splice:Bool):Void members.remove(field);
}
class Renderer {
 public var destroys:Int=0;
 public function new() {}
 public function destroy():Void destroys++;
}
class Main {
 public var nightmareVisionRenderers:haxe.ds.ObjectMap<NightmareVisionPlayFieldView,Renderer>=new haxe.ds.ObjectMap();
 public var playFields:Fields=new Fields();
 public var notes:NativeNotes=new NativeNotes();
 public var detached:Int=0;
 public function new() {}
 function destroyNightmareVisionFieldSplashes(field:NightmareVisionPlayFieldView):Void {}
 function detachNightmareVisionPlayField(field:NightmareVisionPlayFieldView):Void detached++;
 __TEARDOWN__
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main() {
  var host=new Main(), a=new NightmareVisionPlayFieldView(), b=new NightmareVisionPlayFieldView();
  var note=new Note();
  note.playField=a;
  check(a.notes[0]==note && a.adds==1 && note.playField==a,'new membership');
  note.playField=a;
  check(a.adds==1 && a.removes==0,'same field does not duplicate membership');
  note.playField=b;
  check(a.notes.length==0 && a.removes==1 && b.notes[0]==note,'transfer membership');
  note.playField=null;
  check(b.notes.length==0 && b.removes==1,'detach membership');
  b.addNote(note);
  note.playField=b;
  check(b.adds==2 && b.notes.length==1,'existing membership not re-added');
  host.notes.members.push(note);host.playFields.members.push(b);
  var renderer=new Renderer();host.nightmareVisionRenderers.set(b,renderer);
  host.detachNightmareVisionPlayField(b);
  check(host.nightmareVisionRenderers.get(b)==renderer && renderer.destroys==0,'plain detach retains live renderer');
  host.detached=0;
  host.nightmareVisionDestroyFieldView(b);
  check(!host.nightmareVisionRenderers.exists(b) && renderer.destroys==1,'destroyed field releases renderer');
  check(host.playFields.members.length==0 && b.removes==1,'field teardown does not remove notes');
  check(host.notes.members[0]==note && note.destroys==0,'native group retains cleanup ownership');
  host.notes.destroy();
  check(note.destroys==1,'base scene destroys retained note once');
  host.nightmareVisionDestroyFieldView(b);
  check(host.detached==1 && note.destroys==1,'detached field cleanup does not repeat note disposal');
  check(renderer.destroys==1,'renderer destroyed only once');
 }
}
'''.replace('__SETTER__', setter).replace('__TEARDOWN__', teardown)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
