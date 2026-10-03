"""Incoming HXC notes must route to the live actor, including native properties."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HxcCharacterNoteOwnershipTest(unittest.TestCase):
    def test_native_property_contract_and_source_owner_precedence(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = source.split('\tfunction hxcCharacterScopeOwnsNote(', 1)[1].split(
            '\n\t/** Execute one generated character method', 1)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text('''
class Character { public function new() {} }
class NoteView {
 public var strumTime(get,never):Float;
 public var mustPress(get,never):Bool;
 public var sourcePlayfieldPlayerControlled(get,never):Null<Bool>;
 public var forceGfSing(get,never):Bool;
 public var owner:Null<Bool> = null;
 public var player:Bool;
 public var girlfriend:Bool = false;
 public function new(player:Bool) this.player = player;
 function get_strumTime():Float return 0;
 function get_mustPress():Bool return player;
 function get_sourcePlayfieldPlayerControlled():Null<Bool> return owner;
 function get_forceGfSing():Bool return girlfriend;
}
class Host {
 public var boyfriend = new Character();
 public var dad = new Character();
 public var gf = new Character();
 var hxcCharacterScopeNames = ['bf'=>'bf', 'dad'=>'dad', 'gf'=>'gf', 'both'=>'shared'];
 public function new() {}
 function hxcCharacterForRole(role:String):Character return boyfriend;
 function getOpponentSinger():Character return dad;
 function hxcCharacterForScope(scope:String):Array<Character> {
  return switch(scope) { case 'bf':[boyfriend]; case 'dad':[dad]; case 'gf':[gf];
   case 'both':[boyfriend,dad]; default:[]; }
 }
 public function hxcCharacterScopeOwnsNote(''' + method + '''
 public function check(args:Array<Dynamic>, owner:String):Void {
  for (scope in ['bf','dad','gf'])
   if (hxcCharacterScopeOwnsNote(scope,args) != (scope == owner))
    throw 'wrong owner: expected ' + owner + ' for ' + scope;
 }
}
class Main {
 static function main() {
  var host = new Host();
  var note = new NoteView(false);
  var payload = {note:note, nativeNote:note, eventData:{}};
  if (Reflect.hasField(note,'strumTime')) throw 'fixture must exercise property access';
  host.check([null, note, payload], 'dad');
  note.player = true;
  host.check([note, payload], 'bf');
  note.owner = false;
  host.check([note, payload], 'dad'); // Explicit source owner wins mustPress.
  note.player = false; note.owner = true;
  host.check([note, payload], 'bf');
  host.check([note, false, 0, payload], 'dad'); // Explicit hit/miss bool wins source owner.
  note.owner = false;
  host.check([note, true, false, payload], 'bf'); // First explicit bool wins.
  note.owner = null; note.girlfriend = true;
  host.check([note, payload], 'gf');
  host.check([note, true, payload], 'bf');
  host.gf = null;
  host.check([note, payload], 'dad'); // Match native singer fallback when GF is absent.
  host.check([null, false, 0, payload], 'dad');
  host.check([null, true, 0, payload], 'bf');
  if (!host.hxcCharacterScopeOwnsNote('global', [note,payload]))
   throw 'non-character callback was filtered';
  if (!host.hxcCharacterScopeOwnsNote('both', [note,payload]))
   throw 'a script shared by roles lost its owner';
  host.dad = null;
  host.check([note,payload], ''); // No actor: do not dispatch to a null role.
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work),
                                     '--main', 'Main', '--interp'], cwd=work,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
