"""Exercise PlayState's owner-bound Psych note-input routing."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
PLAY_STATE = ROOT / "source/PlayState.hx"


def extract_method(source: str, marker: str) -> str:
    """Extract one Haxe method while ignoring braces in strings and comments."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


MAIN = r'''import haxe.ds.StringMap;

class Note {
 public static var NOTE_AMOUNT:Int = 4;
}

class NativeInput {
 public function new() {}
 public var CTRLA_P:Bool=false; public var CTRLB_P:Bool=false; public var CTRLC_P:Bool=false;
 public var CTRLD_P:Bool=false; public var CTRLE_P:Bool=false; public var CTRLF_P:Bool=false;
 public var CTRLG_P:Bool=false; public var CTRLH_P:Bool=false; public var CTRLI_P:Bool=false;
 public var CTRLA_R:Bool=false; public var CTRLB_R:Bool=false; public var CTRLC_R:Bool=false;
 public var CTRLD_R:Bool=false; public var CTRLE_R:Bool=false; public var CTRLF_R:Bool=false;
 public var CTRLG_R:Bool=false; public var CTRLH_R:Bool=false; public var CTRLI_R:Bool=false;
}

class OwnerControls {
 public var keyArrays:Array<Array<Int>>=[];
 public var keyboardResults:Map<String,Bool>=new Map();
 public var gamepadResults:Map<String,Bool>=new Map();
 public var calls:Array<String>=[];
 public var observedArrays:Array<Array<Int>>=[];
 public function new() {}
 function keyIndex(keys:Array<Int>):Int {
  for (i in 0...keyArrays.length) if (keyArrays[i]==keys) return i;
  return -1;
 }
 public function queryKeyboard(keys:Array<Int>,phase:String):Bool {
  var lane=keyIndex(keys);
  calls.push('keyboard:'+lane+':'+phase);
  observedArrays.push(keys);
  return keyboardResults.get(lane+':'+phase)==true;
 }
 public function queryGamepad(action:String,phase:String):Bool {
  calls.push('gamepad:'+action+':'+phase);
  return gamepadResults.get(action+':'+phase)==true;
 }
}

class PlayState {
 public var psychControls:OwnerControls;
 public var keysArray:Array<Array<Int>>=[];
 public var controls:NativeInput=new NativeInput();
 public var controlsPlayerTwo:NativeInput=new NativeInput();
 public var duoMode:Bool=false;
 public var opponentPlayer:Bool=false;
 public var disableKeys:Bool=false;
 public var compatEventVideoControlsDisabled:Bool=false;
 public var hxcVideoControlsDisabled:Bool=false;
 public var events:Array<String>=[];

 public function new() {}
 public function psychSourceKeyPressed(key:Int,playerOne:Bool):Void events.push('press:'+key+':'+playerOne);
 public function psychSourceKeyReleased(key:Int,playerOne:Bool):Void events.push('release:'+key+':'+playerOne);
__EXTRACTED_METHODS__
}

class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function newHost():PlayState {
  var host=new PlayState();
  host.keysArray=[[10],[11],[12],[13]];
  host.psychControls=new OwnerControls();
  host.psychControls.keyArrays=host.keysArray.copy();
  return host;
 }
 static function main():Void {
  var owner=newHost();
  var originalLeft=owner.keysArray[0];
  owner.psychControls.keyboardResults.set('0:justPressed',true);
  owner.psychControls.keyboardResults.set('0:justReleased',true);
  owner.psychControls.gamepadResults.set('note_down:justPressed',true);
  owner.psychControls.gamepadResults.set('note_down:justReleased',true);
  owner.psychControls.keyboardResults.set('2:justReleased',true);
  owner.dispatchPsychInputEdges();
  check(owner.events.join('|')=='press:0:true|release:0:true|press:1:true|release:1:true|release:2:true',
   'owner press and release edges were not dispatched independently');
  check(owner.psychControls.observedArrays[0]==originalLeft
   && owner.psychControls.calls.contains('gamepad:note_down:justPressed')
   && owner.psychControls.calls.contains('keyboard:2:justReleased'),
   'owner polling did not use captured keyboard arrays and named gamepad actions');

  // The PlayState captures each binding array at owner initialization. Replacing
  // a map entry later must not replace that captured keyboard edge source.
  var replacement:Array<Int>=[99];
  var liveMap=new StringMap<Array<Int>>();
  liveMap.set('note_left',originalLeft); liveMap.set('note_down',owner.keysArray[1]);
  liveMap.set('note_up',owner.keysArray[2]); liveMap.set('note_right',owner.keysArray[3]);
  owner.keysArray=[for(name in ['note_left','note_down','note_up','note_right']) liveMap.get(name)];
  owner.psychControls.keyArrays=owner.keysArray.copy();
  var capturedAtInit=owner.keysArray[0];
  liveMap.set('note_left',replacement);
  owner.psychControls.observedArrays=[];
  owner.psychControls.calls=[];
  owner.psychControls.keyboardResults.set('0:justPressed',true);
  owner.psychControls.keyboardResults.set('0:justReleased',false);
  owner.psychControls.gamepadResults=new Map();
  owner.events=[];
  owner.dispatchPsychInputEdges();
  check(owner.psychControls.observedArrays.length==8
   && owner.psychControls.observedArrays[0]==capturedAtInit
   && owner.psychControls.observedArrays[0]!=replacement,
   'replacing a preference map entry changed the captured keyboard array');

  check(owner.usesPsychOwnerControls(true) && !owner.usesPsychOwnerControls(false),
   'four-lane normal play should bind the source owner only to player one');
  owner.controls.CTRLI_P=true;
  owner.controls.CTRLI_R=true;
  owner.psychControls=null;
  owner.events=[];
  owner.dispatchPsychInputEdges();
  check(owner.events.join('|')=='press:8:true|release:8:true',
   'without an owner facade the nine-lane native input path should remain active');

  var extended=newHost();
  Note.NOTE_AMOUNT=9;
  check(!extended.usesPsychOwnerControls(true), 'extended mania must keep the native nine-lane route');
  extended.controls.CTRLI_P=true;
  extended.dispatchPsychInputEdges();
  check(extended.events.join('|')=='press:8:true', 'extended mania did not use the nine-lane fallback');
  Note.NOTE_AMOUNT=4;

  var duo=newHost();
  duo.duoMode=true;
  duo.controls.CTRLH_P=true;
  duo.controlsPlayerTwo.CTRLI_P=true;
  check(!duo.usesPsychOwnerControls(true) && !duo.usesPsychOwnerControls(false),
   'duo play must not claim the single-owner four-lane route');
  duo.dispatchPsychInputEdges();
  check(duo.events.join('|')=='press:7:true|press:8:false',
   'duo mode should preserve both native nine-action input banks');

  var opponent=newHost();
  opponent.opponentPlayer=true;
  opponent.controls.CTRLC_P=true;
  opponent.controlsPlayerTwo.CTRLD_P=true;
  check(!opponent.usesPsychOwnerControls(true) && !opponent.usesPsychOwnerControls(false),
   'opponent-player mode must keep its existing second-bank route');
  opponent.dispatchPsychInputEdges();
  check(opponent.events.join('|')=='press:3:false',
   'opponent-player mode should dispatch only the configured second bank');
 }
}'''


class PsychOwnerControlsWiringTest(unittest.TestCase):
    def test_extracted_owner_and_native_input_routes(self):
        play = PLAY_STATE.read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(play, marker)
            for marker in (
                "function dispatchPsychInputEdges():Void",
                "function usesPsychOwnerControls(playerOne:Bool):Bool",
                "static function psychNoteAction(key:Int):String",
            )
        )
        methods = methods.replace("function dispatchPsychInputEdges", "public function dispatchPsychInputEdges", 1)
        methods = methods.replace("function usesPsychOwnerControls", "public function usesPsychOwnerControls", 1)
        if not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="psych-owner-controls-", dir=ROOT / "tmp") as directory:
            base = FixturePath(directory)
            source = base / "Main.hx"
            source.write_text(MAIN.replace("__EXTRACTED_METHODS__", methods), encoding="utf-8", newline="\n")
            # The raw fixture is assembled by replacing its one splice marker.
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_bindings_reach_scripts_stages_and_release_with_the_scene(self):
        play = PLAY_STATE.read_text(encoding="utf-8")
        base_stage = (ROOT / "source/PsychBaseStageCompat.hx").read_text(encoding="utf-8")
        initialize = extract_method(play, "function initializePsychClientPrefs(ownerRoot:String):Void")
        compat_root = extract_method(play, "function compatPropertyRoot(name:String):Dynamic")
        destroy = extract_method(play, "override public function destroy()")
        self.assertIn("psychControls = new PsychControlsCompat(null, psychClientPrefs);", initialize)
        self.assertIn("keysArray = [for (name in ['note_left', 'note_down', 'note_up', 'note_right'])", initialize)
        self.assertIn("cast psychClientPrefs.keyBinds.get(name)", initialize)
        self.assertIn("case 'controls':", compat_root)
        self.assertIn("return psychControls == null ? cast controls : psychControls;", compat_root)
        self.assertIn("interp.variables.set('controls', psychControls == null ? cast controls : psychControls);", play)
        self.assertIn("var sourceControls = readField('psychControls');", base_stage)
        self.assertIn("return sourceControls == null ? readField('controls') : sourceControls;", base_stage)
        self.assertIn("if (psychControls != null) psychControls.release();", destroy)
        self.assertIn("keysArray = [];", destroy)
        self.assertIn("keysPressed = [];", destroy)


if __name__ == "__main__":
    unittest.main()
