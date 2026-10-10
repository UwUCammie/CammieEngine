"""Exercise Psych's seeded Countdown enum through the real Iris bridge."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


MAIN_TEMPLATE = r'''package;
import hscript.Interp;

class FakeHost {
 public var nightmareVisionLegacyFieldCameras:Bool=false;
 public var compatCustomSubstate:Dynamic = {customName:"fixture"};
 public var psychScriptVariables:Map<String,Dynamic> = [];
 public function sourceClassSession(root:String):SourceClassAccess return null;
 public function new() {}
}

class PsychHscriptSourceBindings {
 final host:FakeHost;
 final interp:Interp;
 final origin:String;
 final callbackBridge:Dynamic;
 final parentLua:Dynamic;
 public function new(host:FakeHost, interp:Interp, origin:String, callbackBridge:Dynamic) {
  this.host=host;this.interp=interp;this.origin=origin;this.callbackBridge=callbackBridge;
  parentLua=null;
 }
 __INSTALL_METHOD__
 static function sourceBuildTarget():String return "fixture";
 static function setSharedVar(vars:Map<String,Dynamic>,name:String,value:Dynamic):Dynamic {
  vars.set(name,value);return value;
 }
 static function getSharedVar(vars:Map<String,Dynamic>,name:String):Dynamic return vars.get(name);
 static function removeSharedVar(vars:Map<String,Dynamic>,name:String):Bool return vars.remove(name);
 static function registerGlobal(_bridge:Dynamic,_origin:String,_name:String,_func:Dynamic):Void {}
 static function registerLocal(_bridge:Dynamic,_origin:String,_name:String,_func:Dynamic,
  _parent:Dynamic):Void {}
}

class PsychHscriptCustomSubstateFacade {
 public function new(_host:FakeHost) {}
}
class PsychCustomSubstate {public static var name='unnamed';public static var instance:Dynamic;}
class PsychRatingCompat {}
class PsychHscriptCamera {}
class PsychHscriptErrorHandledRuntimeShader {}

class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var host=new FakeHost();
  var plain=new SourceIrisBridge(host);
  new PsychHscriptSourceBindings(host,plain,"plain.hx",null).install();
  check(PsychAchievementsIntegration.hscriptCalls.length==1
   && PsychAchievementsIntegration.hscriptCalls[0][0]==host
   && PsychAchievementsIntegration.hscriptCalls[0][1]==plain
   && PsychAchievementsIntegration.hscriptCalls[0][2]=="plain.hx",
   "preset installation forwards the captured host, interpreter, and origin");
  check(plain.variables.get("Countdown")==PsychBaseStageCountdown,
   "plain Psych preset did not expose the engine countdown enum type");

  plain.evaluate("bareNames = [Type.enumConstructor(Countdown.THREE), "
   +"Type.enumConstructor(Countdown.TWO), Type.enumConstructor(Countdown.ONE), "
   +"Type.enumConstructor(Countdown.GO), Type.enumConstructor(Countdown.START)].join(','); "
   +"bareValues = [Countdown.THREE, Countdown.TWO, Countdown.ONE, Countdown.GO, Countdown.START];",
   "plain.hx");
  check(plain.variables.get("bareNames")=="THREE,TWO,ONE,GO,START",
   "bare Countdown enum constructors were missing or out of order");
  checkMatches(plain.variables.get("bareValues"),"plain bare binding");

  plain.evaluate("import backend.BaseStage.Countdown; "
   +"qualifiedNames = [Type.enumConstructor(Countdown.THREE), "
   +"Type.enumConstructor(Countdown.TWO), Type.enumConstructor(Countdown.ONE), "
   +"Type.enumConstructor(Countdown.GO), Type.enumConstructor(Countdown.START)].join(','); "
   +"qualifiedValues = [Countdown.THREE, Countdown.TWO, Countdown.ONE, Countdown.GO, Countdown.START];",
   "plain-import.hx");
  check(plain.variables.get("qualifiedNames")=="THREE,TWO,ONE,GO,START",
   "qualified backend.BaseStage.Countdown import did not resolve through the Psych import binder");
  checkMatches(plain.variables.get("qualifiedValues"),"qualified import binding");

  // PsychRuntimeBindings.module() copies owner globals, then installs the
  // same preset on its independent embedded runHaxeCode interpreter.
  var embedded=new SourceIrisBridge(host);
  for (name => value in plain.variables) embedded.variables.set(name,value);
  new PsychHscriptSourceBindings(host,embedded,"embedded.hx",null).install();
  check(PsychAchievementsIntegration.hscriptCalls.length==2
   && PsychAchievementsIntegration.hscriptCalls[1][0]==host
   && PsychAchievementsIntegration.hscriptCalls[1][1]==embedded
   && PsychAchievementsIntegration.hscriptCalls[1][2]=="embedded.hx",
   "embedded preset installation retains its own interpreter and origin");
  check(embedded.variables.get("Countdown")==PsychBaseStageCountdown,
   "embedded Psych preset did not retain the real countdown enum type");
  embedded.evaluate("import backend.BaseStage.Countdown; "
   +"embeddedNames = [Type.enumConstructor(Countdown.THREE), "
   +"Type.enumConstructor(Countdown.TWO), Type.enumConstructor(Countdown.ONE), "
   +"Type.enumConstructor(Countdown.GO), Type.enumConstructor(Countdown.START)].join(','); "
   +"embeddedValues = [Countdown.THREE, Countdown.TWO, Countdown.ONE, Countdown.GO, Countdown.START]; "
   +"function localShadow(Countdown) return Countdown; "
   +"shadowResult = localShadow('local-value'); "
   +"afterShadow = Type.enumConstructor(Countdown.THREE);",
   "embedded.hx");
  check(embedded.variables.get("embeddedNames")=="THREE,TWO,ONE,GO,START",
   "embedded interpreter lost a Countdown constructor");
  checkMatches(embedded.variables.get("embeddedValues"),"embedded import binding");
  check(embedded.variables.get("shadowResult")=="local-value"
   && embedded.variables.get("afterShadow")=="THREE",
   "a local Countdown variable shadow changed the owner preset");
  check(plain.variables.get("Countdown")==PsychBaseStageCountdown,
   "embedded import or local shadow changed the plain owner's enum binding");
  embedded.evaluator.release();
  plain.evaluator.release();
 }

 static function checkMatches(values:Dynamic,label:String):Void {
  var actual:Array<Dynamic>=cast values;
  var expected:Array<Dynamic>=[PsychBaseStageCountdown.THREE,PsychBaseStageCountdown.TWO,
   PsychBaseStageCountdown.ONE,PsychBaseStageCountdown.GO,PsychBaseStageCountdown.START];
  check(actual!=null&&actual.length==expected.length,label+" returned the wrong number of cases");
  for(index in 0...expected.length)
   check(actual[index]==expected[index],label+" returned a different enum value at index "+index);
 }
}
'''


class PsychHscriptCountdownPresetTest(unittest.TestCase):
    def test_plain_and_embedded_presets_expose_the_real_enum_and_import(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        if not (IRIS / "crowplexus/hscript/Interp.hx").is_file():
            self.skipTest("pinned Iris interpreter is unavailable")

        source = (ROOT / "source/PsychHscriptSourceBindings.hx").read_text(encoding="utf-8")
        install = extract_method(source, "public function install():Void")
        fixture = MAIN_TEMPLATE.replace("__INSTALL_METHOD__", install)
        # Countdown-only scopes intentionally have no selected source asset owner.
        fixture = fixture.replace(' public function new() {}', ' public var psychStageLibrary:String;public function compatPsychOwnerForScript(o:String):String return null;public function bindSourceBarClass(i:Dynamic,n:Bool,p:Dynamic):Void{} public function new() {}', 1)

        with tempfile.TemporaryDirectory(prefix="psych-countdown-preset-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            from psych_standard_fixture_support import write_standard_services_stub
            write_standard_services_stub(scratch)
            write_flixel_point_stub(scratch)
            (scratch / "PsychAchievementsIntegration.hx").write_text(
                """import hscript.Interp;
class PsychAchievementsIntegration {
 public static var hscriptCalls:Array<Array<Dynamic>>=[];
 public static function installHscript(host:Dynamic,interp:Interp,origin:String):Void
  hscriptCalls.push([host,interp,origin]);
}
""", encoding="utf-8", newline="\n")
            (scratch / "PsychOwnerPaths.hx").write_text('class PsychOwnerPaths {public static function create(r:String,?l:String):Dynamic return null;}')
            # State-class registration has an independent connected contract probe.
            (scratch / 'PsychStateClassBindings.hx').write_text('class PsychStateClassBindings {public static function registry(h:Dynamic):Dynamic return h.psychScriptVariables;public static function installScope(s:Dynamic):Void {} public static function install(i:Dynamic):Void {}}')
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            command = [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                       "-cp", str(IRIS), "-cp", str(scratch), "--run", "Main"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
