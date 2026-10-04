"""Pin Lua fallthrough returns independently from HScript's last-expression result."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LuaCompatImplicitNilTest(unittest.TestCase):
    def test_named_and_supported_inline_callbacks_return_lua_nil_on_fallthrough(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''package;
import hscript.Parser;

class LuaCompatImplicitNilFixture {
 static function main():Void {
  var source = "function onGameOverConfirm()\n"
   + " setProperty('camZooming', true)\n"
   + "end\n"
   + "function inlineCallback() setProperty('camZooming', true) end\n"
   + "function explicitCallback()\n"
   + " setProperty('camZooming', true)\n"
   + " return 37\n"
   + "end\n"
   + "function conditionalCallback(condition)\n"
   + " if condition then\n"
   + "  return 'early'\n"
   + " end\n"
   + " setProperty('camZooming', false)\n"
   + "end\n"
   + "function bareReturnCallback()\n"
   + " return\n"
   + "end\n"
   + "inlineReturnCallback = function(value) return value + 3 end\n";
  var translated = LuaCompat.translate(source, 'implicit-nil.lua');
  if (!translated.supported) throw translated.diagnostics.join(' | ');

  var setters = 0;
  var interp = new LuaCompatInterp();
  interp.variables.set('setProperty', function(_name:String, _value:Dynamic):Bool {
   setters++;
   return true;
  });
  interp.execute(new Parser().parseString(translated.hscript));

  function call(name:String, args:Array<Dynamic>):Dynamic
   return Reflect.callMethod(null, interp.variables.get(name), args);

  if (call('onGameOverConfirm', []) != null)
   throw 'multiline Lua callback returned its final HScript setter value';
  var luaScopes:Array<{name:String}>=[{name:'source-lua'}];
  var hscriptScopes:Array<{name:String}>=[{name:'source-hscript'}];
  var hscriptCalls=0;
  var fallback=PsychScriptBroadcast.callOnScripts(luaScopes,hscriptScopes,
   'onGameOverConfirm',[],function(scope) return scope.name,function(_scope) return false,
   function(_scope,callback,args) return Reflect.callMethod(null,interp.variables.get(callback),args),
   function(_scope,_callback,_args) {hscriptCalls++;return 'hscript-delivered';});
  if (fallback!='hscript-delivered'||hscriptCalls!=1)
   throw 'Lua nil fallthrough did not permit the source HScript fallback';
  if (call('inlineCallback', []) != null)
   throw 'inline Lua callback returned its final HScript setter value';
  if (call('explicitCallback', []) != 37)
   throw 'explicit Lua return was replaced by the implicit-nil epilogue';
  if (call('conditionalCallback', [true]) != 'early')
   throw 'explicit return from a branch was not preserved';
  if (call('conditionalCallback', [false]) != null)
   throw 'branch fallthrough returned its final HScript setter value';
  if (call('bareReturnCallback', []) != null)
   throw 'bare Lua return did not produce nil';
  if (call('inlineReturnCallback', [5]) != 8)
   throw 'supported anonymous explicit-return closure changed';
  if (setters != 5)
   throw 'setter callbacks did not all execute before falling through: ' + setters;
 }
}
'''

        with tempfile.TemporaryDirectory(prefix="lua-compat-implicit-nil-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "LuaCompatImplicitNilFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(scratch), "--run", "LuaCompatImplicitNilFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
