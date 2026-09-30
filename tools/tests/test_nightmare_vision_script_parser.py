"""Exercise NMV parser syntax and owner-scoped Iris import/using bindings."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionScriptParserTest(unittest.TestCase):
    def test_import_typedef_final_using_isolation_fallback_and_release(self):
        if not HAXE.is_file() or not (IRIS / "crowplexus/hscript/Parser.hx").is_file():
            self.skipTest("portable Haxe or pinned hscript-iris 1.1.3 is unavailable")

        fixture = r'''import crowplexus.hscript.Expr;
import crowplexus.iris.Iris;

@:access(crowplexus.hscript.Interp)
@:access(NightmareVisionScriptInterp)
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function parse(source:String):Expr {
  var parser = new NightmareVisionScriptParser();
  return parser.parseString(source, "nmv-binding-fixture");
 }
 static function interpreter():NightmareVisionScriptInterp
  return new NightmareVisionScriptInterp();
 static function main():Void {
  // Keep this native class linked so Iris's normal Tools.getClass fallback is
  // exercised when the per-interpreter adapter map has no matching entry.
  var linkedMap:Dynamic = new haxe.ds.StringMap<Dynamic>();
  check(linkedMap != null, "native fallback fixture class was not linked");

  var globalUsingCount = Iris.registeredUsingEntries.length;
  var ownerA = interpreter();
  var ownerB = interpreter();
  ownerA.bindImport("fixture.owner.Adapter", OwnerAAdapter);
  ownerB.bindImport("fixture.owner.Adapter", OwnerBAdapter);
  var ownerUsingPath = "fixture.owner.TextExtensions";
  ownerA.bindUsing(ownerUsingPath, function(object:Dynamic, field:String,
    args:Array<Dynamic>):Dynamic {
   if (field == "tag") return "A:" + Std.string(object) + Std.string(args[0]);
   return null;
  });
  ownerB.bindUsing(ownerUsingPath, function(object:Dynamic, field:String,
    args:Array<Dynamic>):Dynamic {
   if (field == "tag") return "B:" + Std.string(object) + Std.string(args[0]);
   return null;
  });

  ownerA.execute(parse(
   "import fixture.owner.Adapter as ScopedAdapter;\n"
   + "typedef AdapterAlias = ScopedAdapter;\n"
   + "aliasResult = AdapterAlias.identify();\n"
   + "shortResult = Adapter.identify();\n"
   + "using fixture.owner.TextExtensions;\n"
   + "using fixture.owner.TextExtensions;\n"
   + "usingResult = 'note'.tag('!');\n"
   + "var name = 'Iris';\n"
   + "var value = 4;\n"
   + "simpleInterpolation = 'hello $name';\n"
   + "expressionInterpolation = 'sum=${value + 1}';\n"
   + 'doubleQuotedLiteral = "hello $$name";\n'
   + "escapedDollar = '$$name';\n"
   + "import haxe.ds.StringMap;\n"
   + "var nativeMap = new StringMap();\n"
   + "nativeMap.set('source', 'native-fallback');\n"
   + "nativeFallbackResult = nativeMap.get('source');\n"
   + "final locked:Int = 7;\n"
   + "locked = 99;\n"
   + "lockedResult = locked;\n"
  ));
 ownerB.execute(parse(
   "import fixture.owner.Adapter as ScopedAdapter;\n"
   + "typedef AdapterAlias = ScopedAdapter;\n"
   + "aliasResult = AdapterAlias.identify();\n"
   + "shortResult = Adapter.identify();\n"
   + "using fixture.owner.TextExtensions;\n"
   + "usingResult = 'note'.tag('!');\n"
  ));

  // Exercise the fork's key/value loop source syntax over both array indices
  // and map keys, including comprehension lowering and loop control flow.
  ownerA.variables.set("savedKey", "outer-key");
  ownerA.variables.set("savedValue", "outer-value");
  var previousError = Iris.error;
  var capturedErrors:Array<String> = [];
  Iris.error = function(message:Dynamic, ?pos:haxe.PosInfos):Void {
   capturedErrors.push(Std.string(message));
  };
  try {
   ownerA.execute(parse(
    "import haxe.ds.StringMap;\n"
    + "var sourceArray = ['first', 'skip', 'break', 'last'];\n"
    + "var arrayTrace = [];\n"
    + "for (arrayKey => arrayValue in sourceArray) {\n"
    + " if (arrayValue == 'skip') continue;\n"
    + " if (arrayValue == 'break') break;\n"
    + " arrayTrace.push(arrayKey + ':' + arrayValue);\n"
    + "}\n"
    + "arrayLoopResult = arrayTrace.join(',');\n"
    + "var sourceMap = new StringMap();\n"
    + "sourceMap.set('north', 2);\n"
    + "sourceMap.set('south', 3);\n"
    + "var mapTrace = [];\n"
    + "for (mapKey => mapValue in sourceMap) mapTrace.push(mapKey + '=' + mapValue);\n"
    + "mapNorthSeen = mapTrace.indexOf('north=2') >= 0;\n"
    + "mapSouthSeen = mapTrace.indexOf('south=3') >= 0;\n"
    + "mapComprehension = [for (mapKey => mapValue in sourceMap) mapKey + '=' + mapValue];\n"
    + "comprehensionNorthSeen = mapComprehension.indexOf('north=2') >= 0;\n"
    + "comprehensionSouthSeen = mapComprehension.indexOf('south=3') >= 0;\n"
    + "function returnFromLoop(source) {\n"
    + " for (mapKey => mapValue in source) {\n"
    + "  if (mapKey == 'south') return mapValue;\n"
    + " }\n"
    + " return -1;\n"
    + "}\n"
    + "returnLoopResult = returnFromLoop(sourceMap);\n"
    + "function restoreLoopScope(source) {\n"
    + " var scopeKey = 'inner-key';\n"
    + " var scopeValue = 'inner-value';\n"
    + " for (scopeKey => scopeValue in source) {}\n"
    + " return scopeKey + ':' + scopeValue;\n"
    + "}\n"
    + "localScopeRestoreResult = restoreLoopScope(sourceMap);\n"
    + "for (savedKey => savedValue in sourceMap) {}\n"
    + "savedKeyAfter = savedKey;\n"
    + "savedValueAfter = savedValue;\n"
    + "var missingCallObject = {};\n"
    + "missingMethodResult = missingCallObject.noSuchMethod();\n"
    + "callbackContinued = true;\n"
  ));
  } catch (error:Dynamic) {
   Iris.error = previousError;
   throw error;
  }
  Iris.error = previousError;

  check(ownerA.variables.get("aliasResult") == "owner-A"
   && ownerA.variables.get("shortResult") == "owner-A"
   && ownerB.variables.get("aliasResult") == "owner-B"
   && ownerB.variables.get("shortResult") == "owner-B",
   "import alias, short import name, or typedef resolved outside its owner");
  check(ownerA.variables.get("usingResult") == "A:note!"
   && ownerB.variables.get("usingResult") == "B:note!",
   "using adapter dispatch was not scoped to the current interpreter");
  check(ownerA.variables.get("simpleInterpolation") == "hello Iris"
   && ownerA.variables.get("expressionInterpolation") == "sum=5"
   && ownerA.variables.get("doubleQuotedLiteral") == "hello $name"
   && ownerA.variables.get("escapedDollar") == "$name",
   "source NMV single-quote interpolation, double-quote literal, or escaped dollar semantics changed");
  check(ownerA.imports.get("Adapter") == OwnerAAdapter
   && ownerA.imports.get("ScopedAdapter") == OwnerAAdapter
   && ownerB.imports.get("Adapter") == OwnerBAdapter
   && ownerB.imports.get("ScopedAdapter") == OwnerBAdapter,
   "import names or aliases were not retained in each interpreter");
  check(ownerA.imports.get("StringMap") == haxe.ds.StringMap
   && ownerA.variables.get("nativeFallbackResult") == "native-fallback",
   "unbound import did not fall back to Iris native class resolution");
  check(ownerA.variables.get("lockedResult") == 7,
   "final local was reassigned by the imported Iris interpreter");
  check(ownerA.variables.get("arrayLoopResult") == "0:first",
   "array key/value iteration or break/continue control flow changed");
  check(ownerA.variables.get("mapNorthSeen") == true
   && ownerA.variables.get("mapSouthSeen") == true
   && ownerA.variables.get("comprehensionNorthSeen") == true
   && ownerA.variables.get("comprehensionSouthSeen") == true,
   "map key/value iteration or key/value array comprehension omitted entries");
  check(ownerA.variables.get("returnLoopResult") == 3,
   "return from a key/value loop did not propagate through the script function");
  check(ownerA.variables.get("localScopeRestoreResult") == "inner-key:inner-value"
   && ownerA.variables.get("savedKeyAfter") == "outer-key"
   && ownerA.variables.get("savedValueAfter") == "outer-value",
   "key/value loop did not restore preexisting local and interpreter variables");
  check(ownerA.variables.get("missingMethodResult") == null
   && ownerA.variables.get("callbackContinued") == true
   && capturedErrors.length == 1
   && capturedErrors[0].indexOf("Unknown function: noSuchMethod") >= 0,
   "missing method did not report through Iris.error and allow the script to continue");

  var nullLoopOwner = interpreter();
  var nullLoopFailure:Dynamic = null;
  try {
   nullLoopOwner.execute(parse("for (key => value in [null]) {}"));
  } catch (error:Dynamic) {
   nullLoopFailure = error;
  }
  check(nullLoopFailure != null
   && Std.string(nullLoopFailure).indexOf("value has no field value") >= 0,
   "key/value loop did not reject the null value as the NMV source interpreter does");
  nullLoopOwner.execute(parse("recoveredAfterNullLoop = true;"));
  check(nullLoopOwner.variables.get("recoveredAfterNullLoop") == true,
   "interpreter could not execute a later script after rejecting a null key/value entry");

  var enumOwner = interpreter();
  enumOwner.bindImport("fixture.owner.UserLoopErrorFactory", UserLoopErrorFactory);
  var userEnumFailure:Dynamic = null;
  try {
   enumOwner.execute(parse(
    "import fixture.owner.UserLoopErrorFactory;\n"
    + "for (key => item in ['x']) throw UserLoopErrorFactory.create();"
   ));
  } catch (error:Dynamic) {
   userEnumFailure = error;
  }
  check(userEnumFailure != null && Type.enumConstructor(userEnumFailure) == "UserProblem",
   "key/value loop swallowed an ordinary thrown user enum instead of propagating it");

  var callbackShared:Map<String, Dynamic> = new Map();
  var callbackOwner = new NightmareVisionScriptInterp(new ParentScopeFixture(), callbackShared);
  callbackOwner.execute(parse(
   "function failingCallback() { var inherited = 99; throw 'callback failure'; }"
  ));
  var callbackFrame = callbackOwner.locals;
  var callbackDeclared = callbackOwner.declared.length;
  var callbackTry = callbackOwner.inTry;
  callbackOwner.returnValue = 123;
  var callbackFailure:Dynamic = null;
  try {
   callbackOwner.callCallback(callbackOwner.variables.get("failingCallback"), []);
  } catch (error:Dynamic) {
   callbackFailure = error;
  }
  check(Std.string(callbackFailure).indexOf("callback failure") >= 0,
   "failed callback did not propagate its original error");
  check(callbackOwner.depth == 0, "failed callback retained a nonzero execution depth");
  check(callbackOwner.locals == callbackFrame, "failed callback did not restore the caller locals map");
  check(callbackOwner.declared.length == callbackDeclared,
   "failed callback retained declarations from its local scope");
  check(callbackOwner.inTry == callbackTry, "failed callback did not restore try state");
  check(callbackOwner.returnValue == 123, "failed callback did not restore pending return state");
  callbackOwner.expr(parse("public var afterCallbackFailure = 12;"));
  callbackOwner.expr(parse("parentValueAfterCallbackFailure = inherited;"));
  check(callbackShared.get("afterCallbackFailure") == 12
   && callbackOwner.variables.get("parentValueAfterCallbackFailure") == 7,
   "failed callback depth or local shadow hid public metadata or its parent field");

  var reentrantOwner = interpreter();
  ReentrantHost.owner = reentrantOwner;
  ReentrantHost.nestedError = "";
  reentrantOwner.bindImport("fixture.owner.ReentrantHost", ReentrantHost);
  reentrantOwner.execute(parse(
   "import fixture.owner.ReentrantHost;\n"
   + "function nestedFailure() { var nestedLocal = 'inner'; throw 'nested callback failure'; }\n"
   + "function outerCallback() { var callerLocal = 'caller-kept'; ReentrantHost.invokeNested(); outerResult = callerLocal; return callerLocal; }"
  ));
  var outerCallbackResult:Dynamic = null;
  try {
   outerCallbackResult = reentrantOwner.callCallback(
    reentrantOwner.variables.get("outerCallback"), []);
  } catch (error:Dynamic) {
   ReentrantHost.owner = null;
   throw error;
  }
  check(outerCallbackResult == "caller-kept"
   && reentrantOwner.variables.get("outerResult") == "caller-kept"
   && ReentrantHost.nestedError.indexOf("nested callback failure") >= 0
   && reentrantOwner.depth == 0,
   "nested host re-entry error corrupted the calling script callback frame");
  ReentrantHost.owner = null;

  var ownerAUsing:Array<Dynamic> = cast ownerA.usings;
  var ownerBUsing:Array<Dynamic> = cast ownerB.usings;
  check(ownerAUsing.length == 1 && ownerBUsing.length == 1,
   "repeated using declaration registered duplicate or missing local entries");
  var hasGlobalUsing = false;
  for (entry in Iris.registeredUsingEntries)
   if (entry.name == ownerUsingPath) hasGlobalUsing = true;
  check(Iris.registeredUsingEntries.length == globalUsingCount && !hasGlobalUsing,
   "owner-bound using leaked into Iris's process-global registry");
  check(!Iris.proxyImports.exists("fixture.owner.Adapter"),
   "owner-bound import leaked into Iris's process-global proxy table");

  ownerA.release();
  check(ownerA.parent == null && ownerA.sharedFields == null
   && ownerA.importBindings.keys().hasNext() == false
   && ownerA.imports.keys().hasNext() == false
   && ownerA.variables.keys().hasNext() == false
   && ownerA.usings.length == 0,
   "release retained import, using, variable, parent, or shared references");
  check(ownerB.variables.get("aliasResult") == "owner-B"
   && ownerB.imports.get("ScopedAdapter") == OwnerBAdapter
   && ownerB.usings.length == 1,
   "releasing one interpreter changed another owner's bindings");
  ownerB.release();
  nullLoopOwner.release();
  enumOwner.release();
  callbackOwner.release();
  reentrantOwner.release();
 }
}

class OwnerAAdapter {
 public static function identify():String return "owner-A";
}
class OwnerBAdapter {
 public static function identify():String return "owner-B";
}
enum UserLoopError {
 UserProblem;
}
class UserLoopErrorFactory {
 public static function create():Dynamic return UserLoopError.UserProblem;
}
class ParentScopeFixture {
 public var inherited:Int = 7;
 public function new() {}
}
class ReentrantHost {
 public static var owner:NightmareVisionScriptInterp;
 public static var nestedError:String = "";
 public static function invokeNested():Dynamic {
  try {
   owner.callCallback(owner.variables.get("nestedFailure"), []);
  } catch (error:Dynamic) {
   nestedError = Std.string(error);
  }
  return null;
 }
}'''

        with tempfile.TemporaryDirectory(prefix="nmv-parser-bindings-", dir=ROOT / "tmp") as scratch:
            fixture_path = Path(scratch) / "Main.hx"
            fixture_path.write_text(fixture)
            for use_positions in (False, True):
                command = [str(HAXE), "-cp", str(ROOT / "source"),
                           "-cp", str(IRIS), "-cp", scratch]
                if use_positions:
                    command.extend(["-D", "hscriptPos"])
                command.extend(["--run", "Main"])
                with self.subTest(hscriptPos=use_positions):
                    result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                            text=True, timeout=60)
                    self.assertEqual(result.returncode, 0,
                                     result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
