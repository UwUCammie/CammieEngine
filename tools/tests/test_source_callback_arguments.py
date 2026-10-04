"""Exercise the real host callback boundary with source-prepared arguments."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = block_comment = escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char in "\r\n":
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
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


PLAY_STATE_STUB = r'''package;
import hscript.Interp;
class PlayState {
 public var hscriptStates:Map<String,Interp>=[];
 public var hxcPayloadStates:Map<String,Bool>=[];
 public var psychFlashEventScopes:Map<String,Bool>=[];
 public var hxcCharacterScopeNames:Map<String,Bool>=[];
 public var notes:Dynamic=null;
 public function new() {}

 public function psychFlashCallbackSuppressed(_flashing:Bool,_psych:Bool,_event:String):Bool return false;
 public function hxcCharacterScopeIsActive(_scope:String):Bool return true;
 public function refreshPsychScoreGlobals(_interp:Interp):Void {}

 __EXTRACTED_METHOD__
}
'''


FIXTURE = r'''package;
import hscript.Interp;

class SourceCallbackArgumentsFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;

 static function main():Void {
  var host=new PlayState();
  var sourceScope='psych-source';
  var source=new Interp();
  source.variables.set('__psychPlainHscript',true);
  host.hscriptStates.set(sourceScope,source);
  var liveNote:Dynamic={ID:41,noteData:-2,coolId:'Authored Hurt Type',isSustainNote:true};
  var received:Dynamic=null;
  source.variables.set('noteMiss',function(note:Dynamic):Void received=note);
  check(host.callHscript('noteMiss',[liveNote],sourceScope,true,null,true),
   'source HScript callback did not execute');
  check(received==liveNote,
   'source HScript callback received a projected scalar list instead of the live Note');

  var payload:Dynamic={name:'authored payload',nested:{keep:true}};
  var raw:Array<Dynamic>=[payload,'tail'];
  var rawFirst:Dynamic=null;
  var rawSecond:Dynamic=null;
  source.variables.set('customSourceHook',function(first:Dynamic,second:Dynamic):Void {
   rawFirst=first;rawSecond=second;
  });
  check(host.callHscript('customSourceHook',raw,sourceScope,true,null,true),
   'raw source caller payload did not execute');
  check(rawFirst==payload&&rawSecond=='tail'&&raw.length==2&&raw[0]==payload,
   'source callback changed or copied the caller payload values');

  var lua=new LuaCompatInterp();
  host.hscriptStates.set('psych-lua',lua);
  var luaSlot=-1;
  var luaLane=0;
  var luaKind:String=null;
  var luaSustain=false;
  lua.variables.set('noteMiss',function(slot:Int,lane:Int,kind:String,sustain:Bool):Void {
   luaSlot=slot;luaLane=lane;luaKind=kind;luaSustain=sustain;
  });
  check(host.callHscript('noteMiss',[17,-3,'Literal authored note type',true],
   'psych-lua',true,null,true),'prepared Lua callback did not execute');
  check(luaSlot==17&&luaLane==-3&&luaKind=='Literal authored note type'&&luaSustain,
   'source dispatch rewrote a prepared Lua slot, lane sign, note type, or sustain flag');

  // The legacy host path still adapts a Note for HScript/Psych callbacks.
  var native=new Interp();
  host.hscriptStates.set('native-legacy',native);
  var nativeId=-1;
  var nativeDirection=0;
  var nativeType:String=null;
  var nativeSustain=false;
  native.variables.set('noteMiss',function(id:Int,direction:Int,kind:String,sustain:Bool):Void {
   nativeId=id;nativeDirection=direction;nativeType=kind;nativeSustain=sustain;
  });
  check(host.callHscript('noteMiss',[liveNote],'native-legacy',true),
   'legacy native callback did not execute');
  check(nativeId==41&&nativeDirection==2&&nativeType=='Authored Hurt Type'&&nativeSustain,
   'native legacy Note-to-scalar callback adaptation changed');

  // Legacy Psych empty-press adaptation remains on the non-source path only.
  var legacyPress:Array<Dynamic>=[];
  source.variables.set('noteMissPress',function(direction:Int):Void legacyPress.push(direction));
  check(host.callHscript('noteMiss',[null,true,3],'psych-source',true),
   'legacy Psych empty press callback did not execute');
  check(legacyPress.length==1&&legacyPress[0]==3,
   'sourceArguments change removed legacy noteMissPress name/argument adaptation');

  Sys.println('OK');
 }
}
'''


class SourceCallbackArgumentsTest(unittest.TestCase):
    def test_source_prepared_arguments_and_native_legacy_adaptation(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = extract_method(play_state, "function callHscript(")
        method = method.replace("function callHscript(", "public function callHscript(", 1)
        host = PLAY_STATE_STUB.replace("__EXTRACTED_METHOD__", method)
        with tempfile.TemporaryDirectory(prefix="source-callback-args-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "PlayState.hx").write_text(host, encoding="utf-8", newline="\n")
            point = scratch / "flixel" / "math" / "FlxPoint.hx"
            point.parent.mkdir(parents=True, exist_ok=True)
            point.write_text(r'''package flixel.math;
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}
 public static function weak(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
 public function copyFrom(point:FlxPoint):FlxPoint return set(point.x,point.y);
}
class FlxCallbackPoint extends FlxPoint {
 final callback:FlxPoint->Void;
 public function new(setXCallback:FlxPoint->Void,?setYCallback:FlxPoint->Void,?setXYCallback:FlxPoint->Void){
  super();callback=setXYCallback!=null?setXYCallback:setXCallback;
 }
 override public function set(x:Float=0,y:Float=0):FlxCallbackPoint {super.set(x,y);if(callback!=null)callback(this);return this;}
}
''', encoding="utf-8", newline="\n")
            (scratch / "OptionsHandler.hx").write_text(
                "package; class OptionsHandler { public static var options:Dynamic={flashingLights:true}; }\n",
                encoding="utf-8", newline="\n",
            )
            (scratch / "LuaCompatInterp.hx").write_text(
                "package; class LuaCompatInterp extends hscript.Interp { public function new() super(); }\n",
                encoding="utf-8", newline="\n",
            )
            (scratch / "SourceCallbackArgumentsFixture.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(scratch),
                 "--run", "SourceCallbackArgumentsFixture"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
