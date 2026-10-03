"""HXC NoteKind callbacks are owned by authored note identity."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


class HxcNoteKindDispatchTest(unittest.TestCase):
    def test_false_payload_scopes_use_legacy_arguments_and_stay_in_broadcast(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction callAllHScript(")
        end = source.index("\n\t/** A NoteKind interpreter", start)
        dispatch = source[start:end]
        dispatch = dispatch.replace("function callAllHScript(", "public function callAllHScript(", 1)
        dispatch = dispatch.replace("function callHxcNoteHScript(", "public function callHxcNoteHScript(", 1)
        self.assertIn("hxcPayloadStates.get(usehaxe) == true", source)
        fixture = '''class EngineCompat {
  public static function callbackArguments(name:String, selected:String,
      args:Array<Dynamic>, hxc:Bool):Array<Dynamic> return [hxc ? 'hxc' : 'legacy'];
}
class State {
  public var hscriptStates:Map<String,Bool> = [];
  public var hxcPayloadStates:Map<String,Bool> = [];
  public var defaultPsychGlobalScopes:Array<String> = [];
  public var hxcCharacterScopeNames:Map<String,String> = [];
  public var hxcNoteKindScopes:Map<String,String> = [];
  public var received:Array<String> = [];
  public function new() {}
  function hxcCharacterScopeOwnsNote(scope:String,args:Array<Dynamic>):Bool return true;
  function hxcNoteKindScopeOwnsNote(scope:String,args:Array<Dynamic>):Bool return true;
  function callHscript(name:String,args:Array<Dynamic>,usehaxe:String,
      optional:Bool,?returnValues:Array<Dynamic>):Void {
    var selectedName = name;
    var callArgs = EngineCompat.callbackArguments(name, selectedName, args,
      hxcPayloadStates.get(usehaxe) == true);
    received.push(usehaxe + ':' + callArgs[0]);
  }
''' + dispatch + '''
}
class Main {
  static function main() {
    var state = new State();
    state.hscriptStates.set('psych', true);
    state.hscriptStates.set('hxc', true);
    state.hxcPayloadStates.set('psych', false);
    state.hxcPayloadStates.set('hxc', true);
    state.callAllHScript('noteMiss', [null], true);
    if (state.received.length != 1 || state.received[0] != 'psych:legacy')
      throw 'false payload scope skipped or given HXC arguments';
    state.received = [];
    state.callHxcNoteHScript('noteHit', [null]);
    if (state.received.length != 1 || state.received[0] != 'hxc:hxc')
      throw 'non-HXC scope entered early HXC dispatch';
  }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", tmp,
                "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mixed_normal_and_custom_notes_route_only_to_matching_kind(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction hxcNoteKindScopeOwnsNote(")
        end = source.index("\n\t/**", start + 1)
        method = source[start:end].replace("function hxcNoteKindScopeOwnsNote(",
                                           "public function hxcNoteKindScopeOwnsNote(", 1)
        fixture = '''using StringTools;
class Note {
  public var sourceKind:String;
  public var classes:Array<String> = [];
  public var coolId:String;
  public function new(?sourceKind:String, ?classes:Array<String>, ?coolId:String) {
    this.sourceKind = sourceKind;
    if (classes != null) this.classes = classes;
    this.coolId = coolId;
  }
}
class HxcScriptDiscovery {
  public static function normalizeToken(value:String):String {
    if (value == null) return '';
    var out = new StringBuf();
    for (i in 0...value.length) {
      var char = value.charAt(i).toLowerCase();
      if (~/^[a-z0-9]$/.match(char)) out.add(char);
    }
    return out.toString();
  }
}
class State {
  public var hxcNoteKindScopes:Map<String,String> = [];
  public function new() {}
''' + method + '''
}
class Main {
  static function main() {
    var state = new State();
    state.hxcNoteKindScopes.set('hell', 'trickyhell');
    state.hxcNoteKindScopes.set('death', 'trickydeath');
    state.hxcNoteKindScopes.set('unknown', '');
    var normal = new Note();
    var hell = new Note('Tricky Hell', ['vslice', 'vslice-kind:trickyhell'], 'vslice:trickyhell:0');
    var death = new Note('trickydeath', ['vslice-kind:trickydeath'], 'vslice:trickydeath:1');
    var classOnly = new Note(null, ['vslice-kind:trickyhell']);
    var idOnly = new Note(null, [], 'vslice:trickyhell:0');
    var conflicting = new Note('trickydeath', ['vslice-kind:trickyhell'], 'vslice:trickyhell:0');
    if (state.hxcNoteKindScopeOwnsNote('hell', [normal])
      || state.hxcNoteKindScopeOwnsNote('hell', [death])
      || state.hxcNoteKindScopeOwnsNote('unknown', [hell])
      || state.hxcNoteKindScopeOwnsNote('hell', [null, true, 2]))
      throw 'unowned note reached NoteKind';
    if (!state.hxcNoteKindScopeOwnsNote('hell', [true, hell, false, {note:hell}])
      || !state.hxcNoteKindScopeOwnsNote('death', [death])
      || !state.hxcNoteKindScopeOwnsNote('hell', [classOnly])
      || !state.hxcNoteKindScopeOwnsNote('hell', [idOnly]))
      throw 'matching note kind not dispatched';
    if (state.hxcNoteKindScopeOwnsNote('hell', [conflicting]))
      throw 'sourceKind must win over stale fallback marker';
  }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", tmp,
                "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scope_registration_and_ghost_miss_boundary(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("hxcNoteKindScopes.set(scope, HxcScriptDiscovery.normalizeToken(translatedCompat.identifier))", source)
        self.assertIn("&& (!hxcNoteKindScopes.exists(key) || hxcNoteKindScopeOwnsNote(key, args))", source)
        miss = source[source.index("\tfunction noteMiss("):source.index("\n\tfunction badNoteCheck(")]
        self.assertLess(miss.index("callHxcNoteHScript('noteGhostMiss'"),
                        miss.index("if (note != null) {\n\t\t\t\thxcMissEvent"))
        self.assertIn('callAllHScript("noteMiss", [note, playerOne, direction, hxcMissEvent], true)', miss)


if __name__ == "__main__":
    unittest.main()
