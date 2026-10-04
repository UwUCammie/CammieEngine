"""Portable coverage for the Psych-to-Iris facade and embedded HScript route."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class SourceIrisBridgeTest(unittest.TestCase):
    def test_persistent_evaluation_imports_vars_to_bring_and_recovery(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Host { public function new() {} }
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var bridge = new SourceIrisBridge(new Host());
  check(bridge.variables == bridge.evaluator.variables, 'facade and Iris globals are not aliased');
  bridge.variables.set('FlxG', 'seeded-flxg');
  bridge.variables.set('retained', 9);
  bridge.variables.set('brought', 'original-seed');

  bridge.evaluate('import flixel.FlxG; imported = FlxG;', 'raw-import.hx');
  check(bridge.variables.get('imported') == 'seeded-flxg', 'seeded import alias did not bind');
  var preNormalized = PsychHscriptCompat.normalize('import flixel.FlxG; markedImport = FlxG;');
  check(preNormalized.supported, 'fixture source failed Psych normalization');
  bridge.evaluate(preNormalized.source, 'marked-import.hx');
  check(bridge.variables.get('markedImport') == 'seeded-flxg',
   'pre-normalized source lost its known import binding');

  // Exercise the same marked source returned by PlayState discovery; native
  // imports outside the old preset allowlist must reach the runtime resolver.
  check(Type.getClassName(haxe.crypto.Md5) == 'haxe.crypto.Md5', 'native fixture class not linked');
  var runtimeSource = PsychHscriptCompat.normalize('import haxe.crypto.Md5; nativeDigest = Md5.encode("test");', true);
  check(runtimeSource.supported, 'native direct import rejected before runtime');
  bridge.evaluate(runtimeSource.source, 'native-import.hx');
  check(bridge.variables.get('nativeDigest') == '098f6bcd4621d373cade4e832627b4f6', 'native class import did not execute');
  var missingImport = false;
  try bridge.evaluate('import nonexistent.ContractClass;', 'missing-native.hx') catch (error:Dynamic) {
   missingImport = Std.string(error).indexOf('nonexistent.ContractClass') >= 0;
  }
  check(missingImport, 'unresolvable native import lacked an attributable diagnostic');

  bridge.evaluate('persistent = 5; function twice(value) return persistent * 2 + value;',
   'first.hx');
  var returned = bridge.evaluate('persistent += 1; lastValue = twice(3); lastValue;', 'second.hx');
  check(returned == 15 && bridge.variables.get('lastValue') == 15,
   'later evaluation did not retain the function and global');
  check(bridge.callFunction('twice', [4]) == 16, 'named callback did not use Iris callback dispatch');

  var firstBring:Dynamic = {brought: 2, stale: 3};
  bridge.evaluate('observedFirst = brought;', 'vars-first.hx', firstBring);
  check(bridge.variables.get('observedFirst') == 2 && bridge.variables.get('stale') == 3,
   'varsToBring did not seed trimmed fields');
  var secondBring:Dynamic = {brought: 4};
  bridge.evaluate('observedSecond = brought;', 'vars-second.hx', secondBring);
  check(bridge.variables.get('observedSecond') == 4 && !bridge.variables.exists('stale'),
   'replacing varsToBring did not remove prior brought keys');
  check(bridge.variables.get('retained') == 9 && bridge.variables.get('brought') == 4,
   'varsToBring replacement restored an old seed or removed an unrelated global');
  bridge.evaluate('afterBringClear = retained;', 'vars-clear.hx');
  check(!bridge.variables.exists('brought') && bridge.variables.get('retained') == 9,
   'omitting varsToBring did not remove its previous keys or preserve other globals');

  bridge.evaluate('function broken() { var callbackLocal = 1; throw "fixture failure"; }',
   'errors.hx');
  var failed = false;
  try bridge.callFunction('broken', []) catch (_:Dynamic) failed = true;
  check(failed, 'throwing callback unexpectedly returned');
  bridge.evaluate('afterFailure = 42;', 'recovered.hx');
  check(bridge.variables.get('afterFailure') == 42,
   'callback failure retained an Iris execution frame');

  var callbackRegistry = new PsychSourceCallbackRegistry();
  var parentLua = new hscript.Interp();
  parentLua.variables.set('__compatDiagnosticSource', 'owner/script.lua');
  callbackRegistry.attach('owner', parentLua, true, function(callback, args) return Reflect.callMethod(null, callback, args));
  callbackRegistry.attach('owner', bridge, false, function(callback, args) return bridge.callCallback(callback, args));
  var callbacks:Dynamic = callbackRegistry.bridge('owner', bridge, 'owner/script.lua', parentLua);
  var parentFacade:Dynamic = callbacks.parentFacade('owner/script.lua', bridge);
  bridge.variables.set('parentLua', parentFacade);
  bridge.variables.set('createCallback', function(name:String, callback:Dynamic):Void callbacks.registerLocal('owner/script.lua', name, callback, parentFacade));
  bridge.evaluate('parentName = parentLua.scriptName; parentClosed = parentLua.closed; createCallback("fromHaxe", function(value) return value + 8);', 'callback-registration.hx');
  check(bridge.variables.get('parentName') == 'owner/script.lua' && bridge.variables.get('parentClosed') == false, 'Iris did not read source parent facade properties');
  check(Reflect.callMethod(null, parentLua.variables.get('fromHaxe'), [5]) == 13, 'registered HScript closure did not execute through Iris');
  bridge.evaluate('createCallback("throwFromHaxe", function() { var inner = 1; throw "callback failure"; });', 'throw-registration.hx');
  failed = false;
  try Reflect.callMethod(null, parentLua.variables.get('throwFromHaxe'), []) catch (_:Dynamic) failed = true;
  check(failed && bridge.callFunction('twice', [4]) == 16, 'Lua callback bridge failed to restore the Iris frame');
  callbackRegistry.release();

  bridge.release();
  check(bridge.evaluator == null && !bridge.variables.exists('retained'),
   'release retained evaluator globals');
 }
}'''

        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic, value:Dynamic, ?_op:String='='):Dynamic return value;
}'''
        with tempfile.TemporaryDirectory(prefix="source-iris-", dir=ROOT / "tmp") as scratch:
            write_flixel_point_stub(Path(scratch))
            (Path(scratch) / "Main.hx").write_text(fixture, newline="\n")
            (Path(scratch) / "HxcCompatRuntime.hx").write_text(runtime_stub, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", scratch,
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_embedded_hscript_concat_preserves_haxe_literals_and_optional_args(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class LuaEmbeddedTest {
 static function main():Void {
  var source = 'function onCreate()\n'
   + ' local label = "runHaxeCode math.sin string.format"\n'
   + ' -- runHaxeCode([[comment-only]])\n'
   + ' runHaxeCode([[var literal = "runHaxeCode math.sin string.format tostring table.concat and nil .."; var built = ]] .. elapsed .. [[;]], {elapsed = elapsed}, "refresh", {elapsed})\n'
   + 'end';
  var blocked = LuaCompat.translate(source, 'embedded.lua');
  if (blocked.supported || blocked.diagnostics.join(' ').indexOf('lua-raw-haxe') < 0)
   throw 'default mode stopped blocking arbitrary HScript';

  var translated = LuaCompat.translate(source, 'embedded.lua', true);
  if (!translated.supported) throw translated.diagnostics.join(' | ') + '\n' + translated.hscript;
  if (translated.hscript.indexOf('sourceRunHaxeCode(') < 0
   || translated.hscript.indexOf('luaString(elapsed)') < 0)
   throw 'embedded HScript concat or internal runtime alias was not emitted: ' + translated.hscript;
  if (translated.hscript.indexOf('math.sin string.format tostring table.concat and nil ..') < 0
   || translated.hscript.indexOf('runHaxeCode math.sin string.format') < 0)
   throw 'Lua rewrites changed a literal inside embedded HScript: ' + translated.hscript;
  new hscript.Parser().parseString(translated.hscript);

  var interp = new hscript.Interp();
  var capturedCode:String = null;
  var capturedVars:Dynamic = null;
  var capturedCallback:String = null;
  var capturedArgs:Array<Dynamic> = null;
  interp.variables.set('elapsed', 0.25);
  interp.variables.set('luaString', function(value:Dynamic):String return Std.string(value));
  interp.variables.set('sourceRunHaxeCode', function(code:String, ?vars:Dynamic,
   ?callback:String, ?args:Array<Dynamic>):Dynamic {
    capturedCode = code;
    capturedVars = vars;
    capturedCallback = callback;
    capturedArgs = args;
    return null;
   });
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  if (capturedCode != 'var literal = "runHaxeCode math.sin string.format tostring table.concat and nil .."; var built = 0.25;')
   throw 'runtime HScript body changed through Lua translation: ' + capturedCode;
  if (Reflect.field(capturedVars, 'elapsed') != 0.25 || capturedCallback != 'refresh'
   || capturedArgs == null || capturedArgs.length != 1 || capturedArgs[0] != 0.25)
   throw 'optional runHaxeCode arguments were not preserved';
 }
}'''
        with tempfile.TemporaryDirectory(prefix="source-embedded-haxe-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "LuaEmbeddedTest.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", scratch, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "--run", "LuaEmbeddedTest"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
