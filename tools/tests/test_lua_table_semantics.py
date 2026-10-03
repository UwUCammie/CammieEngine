"""Translated Lua keeps Lua table/truth rules without changing native HScript."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_animation_indices import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class LuaTableSemanticsTest(unittest.TestCase):
    def run_haxe(self, source):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(source, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HSCRIPT), "-main", "Fixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )

    def test_missing_lua_global_reads_nil_without_changing_native_scope(self):
        fixture = r'''
class Fixture {
 static function main() {
  var lua = new LuaCompatInterp();
  lua.variables.set('known', 9);
  lua.execute(new hscript.Parser().parseString(
   'var localValue = 4; if (missing != null || known != 9 || localValue != 4) throw "Lua read";'));
  var arithmeticFailed = false;
  try lua.execute(new hscript.Parser().parseString('missing * 10;'))
  catch (error:Dynamic) arithmeticFailed = Std.string(error).indexOf('lua arithmetic on nil') >= 0;
  if (!arithmeticFailed) throw 'Lua nil arithmetic was not diagnosed';
  arithmeticFailed = false;
  try lua.execute(new hscript.Parser().parseString('-missing;'))
  catch (error:Dynamic) arithmeticFailed = Std.string(error).indexOf('lua arithmetic on nil') >= 0;
  if (!arithmeticFailed) throw 'Lua nil unary arithmetic was not diagnosed';
  arithmeticFailed = false;
  try lua.execute(new hscript.Parser().parseString('missing >= 0;'))
  catch (error:Dynamic) arithmeticFailed = Std.string(error).indexOf('lua arithmetic on nil') >= 0;
  if (!arithmeticFailed) throw 'Lua nil ordering was not diagnosed';
  var operand = '';
  try lua.execute(new hscript.Parser().parseString('missing / 10;'))
  catch (error:Dynamic) operand = Std.string(error);
  if (operand.indexOf('left operand') < 0) throw 'Lua missing left operand was not identified';
  operand = '';
  try lua.execute(new hscript.Parser().parseString('10 / missing;'))
  catch (error:Dynamic) operand = Std.string(error);
  if (operand.indexOf('right operand') < 0) throw 'Lua missing right operand was not identified';
  var native = new hscript.Interp();
  var failed = false;
  try native.execute(new hscript.Parser().parseString('missing;'))
  catch (_:Dynamic) failed = true;
  if (!failed) throw 'native HScript unknown-global diagnostic was lost';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_luajit_table_oracle_and_native_array_boundary(self):
        # Expected values come from tmp/lua-semantics-oracle/check.lua run with
        # LuaJIT. Its one-line helper is split for LuaCompat's callback parser.
        fixture = r'''
class Fixture {
 static function main() {
  var lua = 'local seq = {"first", "second", "last"}\n'
   + 'local values = {}\nvalues["left"] = 0\nvalues["right"] = 7\n'
   + 'values[0] = "zero-key"\nvalues[-2] = "negative-key"\n'
   + 'local calls = 0\nfunction side()\n calls = calls + 1\n return 99\nend\n'
   + 'function onCreate()\n'
   + ' print(seq[1], seq[3], seq[4], values["left"], values["right"], values[0], values[-2])\n'
   + ' print(0 or side(), false or 8, nil or 9, "" and 4, false and side(), calls)\n'
   + ' local truth = 0\n if 0 then truth = truth + 1 end\n'
   + ' if "" then truth = truth + 1 end\n if values then truth = truth + 1 end\n'
   + ' print(truth)\n values["right"] = nil\n'
   + ' print(values["right"], values["left"])\nend\n';
  var translated = LuaCompat.translate(lua,'oracle.lua');
  if (!translated.supported || !StringTools.startsWith(translated.hscript,LuaCompat.TRANSLATED_MARKER))
   throw 'translated Lua marker/support was lost';
  var lines:Array<String> = [];
  var luaInterp = new LuaCompatInterp();
  luaInterp.variables.set('print', Reflect.makeVarArgs(function(args:Array<Dynamic>) {
   lines.push([for (value in args) value == null ? 'nil' : Std.string(value)].join(','));
  }));
  luaInterp.variables.set('nativeArray',['native-zero','native-one']);
  luaInterp.variables.set('nativeObject',{value:'native-field'});
  luaInterp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null,luaInterp.variables.get('onCreate'),[]);
  if (lines.join('|') != 'first,last,nil,0,7,zero-key,negative-key|0,8,9,4,false,0|3|nil,0')
   throw 'LuaJIT oracle mismatch: '+lines.join('|');
  luaInterp.execute(new hscript.Parser().parseString(
   'if (nativeArray[0] != "native-zero" || nativeArray[1] != "native-one"'
   + ' || nativeObject["value"] != "native-field") throw "native API indexing changed";'));
  var nativeInterp = new hscript.Interp();
  nativeInterp.execute(new hscript.Parser().parseString(
   'var native = ["zero", "one"]; if (native[0] != "zero") throw "native HScript changed";'));
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_parenthesized_song_clock_uses_refreshed_lua_timing_global(self):
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        lua_interp = (ROOT / 'source/LuaCompatInterp.hx').read_text()
        seed = extract_method(play_state,
                              'function seedEngineCompat(interp:Interp, ?extraPsychOwnerRoot:String):Void')
        sync = extract_method(play_state, 'function syncPsychTimingGlobals():Void')
        lua_expr = extract_method(lua_interp, 'override public function expr(expression:Expr):Dynamic')
        seed_bindings = [line.strip() for line in seed.splitlines()
                         if "variables.set('crochet'," in line
                         or "variables.set('getSongPosition'," in line]
        self.assertEqual(len(seed_bindings), 2, 'Psych song clock bindings changed')
        self.assertIn("variables.set('getSongPosition', function():Float return Conductor.songPosition);", seed)
        self.assertIn('smokeDiagnosticsEnabled = RuntimeSmokeHarness.enabled()', seed)
        self.assertIn("setAllHaxeVar('crochet', Conductor.crochet);", sync)
        self.assertIn('case ECall(target, params):', lua_expr)
        self.assertIn('isSongPositionCall(target)', lua_expr)
        self.assertIn('lastSongPositionCallProbe', lua_expr)
        fixture = r'''
class Conductor {
 static public var crochet:Float = 500;
 static public var songPosition:Float = -5000;
}
class Fixture {
 static function main() {
  var source = 'function onUpdatePost(elapsed)\n'
   + ' local wave = math.sin((getSongPosition()) / crochet * math.pi / 4)\n'
   + ' return wave\nend\n';
  var translated = LuaCompat.translate(source, 'timing.lua');
  if (!translated.supported) throw translated.diagnostics.join('|');
  var interp = new LuaCompatInterp();
  interp.variables.set('Math', Math);
  interp.smokeDiagnosticsEnabled = true;
''' + '\n'.join('  ' + line for line in seed_bindings) + r'''
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  var callback = interp.variables.get('onUpdatePost');
  var first:Float = Reflect.callMethod(null, callback, [0.016]);
  if (Math.abs(first - Math.sin(-5000 / 500 * Math.PI / 4)) > 0.000001)
   throw 'pre-countdown timing global mismatch';
  if (interp.lastSongPositionCallProbe.indexOf('result=-5000') < 0)
   throw 'live getSongPosition call result was not observed';
  Conductor.songPosition = 70000;
  Conductor.crochet = 342.857142857;
  interp.variables.set('crochet', Conductor.crochet); // mirrors syncPsychTimingGlobals/setAllHaxeVar
  var second:Float = Reflect.callMethod(null, callback, [0.016]);
  if (Math.abs(second - Math.sin(70000 / 342.857142857 * Math.PI / 4)) > 0.000001)
   throw 'BPM-refreshed timing global mismatch';
  if (interp.lastSongPositionCallProbe.indexOf('result=70000') < 0)
   throw 'refreshed getSongPosition call result was not observed';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_arithmetic_probe_reports_call_result_once_without_changing_error(self):
        fixture = r'''
class Fixture {
 static function main() {
  var source = 'function onUpdatePost(elapsed)\n'
   + ' local wave = math.sin((getSongPosition()) / crochet * math.pi / 4)\n'
   + ' return wave\nend\n';
  var translated = LuaCompat.translate(source, 'timing.lua');
  var interp = new LuaCompatInterp();
  interp.smokeDiagnosticsEnabled = true;
  interp.variables.set('__compatDiagnosticSource', 'timing.lua');
  interp.variables.set('__compatDiagnosticCallback', 'onUpdatePost');
  interp.variables.set('Math', Math);
  interp.variables.set('getSongPosition', function():Dynamic return null);
  interp.variables.set('crochet', 500);
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  var callback = interp.variables.get('onUpdatePost');
  var firstError = '';
  try Reflect.callMethod(null, callback, [0.016])
  catch (error:Dynamic) firstError = Std.string(error);
  var secondError = '';
  try Reflect.callMethod(null, callback, [0.016])
  catch (error:Dynamic) secondError = Std.string(error);
  if (firstError != 'lua arithmetic on nil (/, left operand)' || secondError != firstError)
   throw 'smoke probe changed Lua arithmetic error semantics';
  if (interp.lastSongPositionCallProbe.indexOf('result=nil') < 0)
   throw 'nil function-call result was not captured';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertEqual(output.count('[lua-arithmetic-probe]'), 1, output)
        self.assertIn('leftAst=', output)
        self.assertIn('getSongPosition=TFunction', output)

    def test_real_muns_translation_uses_all_nine_lua_indices(self):
        source_path = ROOT / "tmp/runtime-asset-recovery/assets-preserve-2026-09-17/data/resonance/Muns.lua"
        if not source_path.exists():
            self.skipTest("original Lua fixture is unavailable")
        fixture = r'''
import sys.io.File;
class Fixture {
 static function main() {
  var source=File.getContent(Sys.args()[0]);
  var translated=LuaCompat.translate(source,'Muns.lua');
  if (!translated.supported) throw translated.diagnostics.join('|');
  var properties:Map<String,Dynamic> = [];
  var created:Array<String> = [];
  var interp=new LuaCompatInterp();
  interp.variables.set('Math',Math);
  interp.variables.set('curStep',384);
  interp.variables.set('makeRangeArray',function(stop:Int,start:Int):Array<Int> {
   var out=[]; for (i in start...stop) out.push(i); return out;
  });
  interp.variables.set('luaTableLength',function(table:Dynamic):Int return (cast table:Array<Dynamic>).length);
  interp.variables.set('luaTableKey',function(_table:Dynamic,index:Int):Int return index);
  interp.variables.set('luaTableValue',function(table:Dynamic,key:Int):Dynamic return (cast table:Array<Dynamic>)[key-1]);
  interp.variables.set('makeLuaSprite',function(name:String,path:String,x:Float,y:Float) created.push(name));
  interp.variables.set('scaleObject',function(_name:Dynamic,_x:Dynamic,_y:Dynamic) {});
  interp.variables.set('addLuaSprite',function(_name:Dynamic) {});
  interp.variables.set('getRandomInt',function(min:Int,_max:Int):Int return min);
  interp.variables.set('setProperty',function(name:String,value:Dynamic) properties.set(name,value));
  interp.variables.set('getProperty',function(name:String):Dynamic return properties.get(name));
  interp.variables.set('getSongPosition',function():Float return 70000);
  interp.variables.set('doTweenX',function(_a:Dynamic,_b:Dynamic,_c:Dynamic,_d:Dynamic,_e:Dynamic) {});
  interp.variables.set('doTweenY',function(_a:Dynamic,_b:Dynamic,_c:Dynamic,_d:Dynamic,_e:Dynamic) {});
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null,interp.variables.get('onCreate'),[]);
  for (i in 0...9) Reflect.callMethod(null,interp.variables.get('onUpdate'),[7.1]);
  if (created.length != 9 || created[0] != 'E250' || created[8] != 'Oppo-A15')
   throw 'Lua ipairs creation changed';
  if (properties.get('E250.visible') != true || properties.get('Oppo-A15.visible') != true)
   throw 'one-based spawn skipped first or last authored item';
  for (name in created) {
   var y:Float = properties.get(name+'.y');
   if (Math.isNaN(y) || !Math.isFinite(y))
    throw 'translated phone movement produced non-finite y for '+name;
  }
 }
}
'''
        # Sys.args is passed after --interp, so keep the donor path outside the
        # temporary class and use Haxe's --run entry point below.
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HSCRIPT), "--run", "Fixture", str(source_path)],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_only_proven_lua_sources_select_lua_interpreter(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        selector = extract_method(play_state, "function luaProgramFor(")
        fixture = r'''
using StringTools;
class FNFAssets {
 public static var texts:Map<String,String> = [];
 public static function exists(path:String):Bool return texts.exists(path);
 public static function getText(path:String):String return texts.get(path);
}
class Fixture {
 function new() {}
''' + selector + r'''
 static function main() {
  var state = new Fixture();
  var lua = 'function onCreate()\n debugPrint("hello")\nend';
  var marked = LuaCompat.translate(lua,'legacy.lua').hscript;
  var marker = LuaCompat.TRANSLATED_MARKER + '\n';
  var oldGenerated = marked.substr(marker.length);
  FNFAssets.texts.set('legacy.lua',lua);
  if (!state.luaProgramFor('legacy.lua',marked).translated
   || !state.luaProgramFor('legacy.hscript',marked).translated
   || !state.luaProgramFor('legacy.hscript',oldGenerated).translated
   || !state.luaProgramFor('legacy',oldGenerated).translated)
   throw 'proven live/legacy Lua was not selected';
  if (state.luaProgramFor('legacy.hscript',oldGenerated).source != marked)
   throw 'legacy source was not upgraded to current Lua helpers';
  var pairsLua = 'local values = {}\nfunction onCreate()\n'
   + ' for key, value in pairs(values) do\n debugPrint(value)\n end\nend';
  var newPairs = LuaCompat.translate(pairsLua,'pairs.lua').hscript;
  var oldPairs = StringTools.replace(newPairs.substr(marker.length),'luaPairsLength','luaTableLength');
  oldPairs = StringTools.replace(oldPairs,'luaPairsKey','luaTableKey');
  oldPairs = StringTools.replace(oldPairs,'luaPairsValue','luaTableValue');
  FNFAssets.texts.set('pairs.lua',pairsLua);
  var upgraded = state.luaProgramFor('pairs.hscript',oldPairs);
  if (!upgraded.translated || upgraded.source != newPairs)
   throw 'prior pairs helper output was not safely upgraded';
  var sequenceLua = 'local values = {1,2}\nfunction onCreate()\n'
   + ' for i,v in ipairs(values) do\n debugPrint(v)\n end\n'
   + ' if #values > 0 then\n debugPrint("ok")\n end\nend';
  var newSequence = LuaCompat.translate(sequenceLua,'sequence.lua').hscript;
  var oldSequence = StringTools.replace(newSequence.substr(marker.length),'luaIpairsLength','luaTableLength');
  oldSequence = StringTools.replace(oldSequence,'luaIpairsKey','luaTableKey');
  oldSequence = StringTools.replace(oldSequence,'luaIpairsValue','luaTableValue');
  oldSequence = StringTools.replace(oldSequence,'luaSequenceLength(values)','values.length');
  FNFAssets.texts.set('sequence.lua',sequenceLua);
  var sequenceUpgrade = state.luaProgramFor('sequence.hscript',oldSequence);
  if (!sequenceUpgrade.translated || sequenceUpgrade.source != newSequence)
   throw 'prior ipairs/length output was not safely upgraded';
  if (state.luaProgramFor('mixed-stage.lua','var native = [1,2]; // native stage wrapper',true).translated)
   throw 'unmarked mixed native/Lua stage wrapper was reclassified';
  if (state.luaProgramFor('legacy.hscript',oldGenerated+' // edited').translated
   || state.luaProgramFor('native.hscript',oldGenerated).translated)
   throw 'native/edited HScript was reclassified as Lua';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PluginManager.addVarsToInterp(new LuaCompatInterp())", play_state)
        self.assertIn("interp.variables.set('luaPairsLength', EngineCompat.luaTableLength)", play_state)
        self.assertIn("(cast interp : LuaCompatInterp).installTableHelpers()", play_state)

    def test_mixed_keys_dot_alias_pairs_and_sparse_indices(self):
        fixture = r'''
class Fixture {
 static function main() {
  var lua = 'local mixed = {"one", "two"}\n'
   + 'local firstKey = {}\nlocal secondKey = {}\n'
   + 'mixed.label = "yes"\nmixed[0] = "zero"\nmixed["0"] = "stringzero"\n'
   + 'mixed[firstKey] = "first-object"\nmixed[secondKey] = "second-object"\n'
   + 'mixed[1000000000] = "sparse"\n'
   + 'local staged = {}\nstaged[3] = "c"\nstaged[1] = "a"\nstaged[2] = "b"\n'
   + 'local text = "hello"\n'
   + 'function onCreate()\n'
   + ' print(mixed.label, mixed["label"], mixed[0], mixed["0"], mixed[firstKey], mixed[secondKey])\n'
   + ' local pairCount = 0\n for key, value in pairs(mixed) do\n pairCount = pairCount + 1\n end\n'
   + ' local sequenceCount = 0\n for index, value in ipairs(mixed) do\n sequenceCount = sequenceCount + 1\n end\n'
   + ' print(pairCount, sequenceCount, mixed[1000000000], #mixed)\n'
   + ' print(#staged, staged[1], staged[2], staged[3], #text)\n'
   + ' mixed.label = nil\n print(mixed["label"])\nend\n';
  var converted=LuaCompat.translate(lua,'mixed.lua');
  if (!converted.supported) throw converted.diagnostics.join('|');
  var lines:Array<String> = [];
  var interp=new LuaCompatInterp();
  interp.variables.set('makeRangeArray',function(stop:Int,start:Int):Array<Int> {
   var out=[]; for (i in start...stop) out.push(i); return out;
  });
  interp.variables.set('luaTableLength',function(table:Dynamic):Int return (cast table:Array<Dynamic>).length);
  interp.variables.set('luaTableKey',function(_table:Dynamic,index:Int):Int return index);
  interp.variables.set('luaTableValue',function(table:Dynamic,key:Int):Dynamic return (cast table:Array<Dynamic>)[key-1]);
  interp.variables.set('print',Reflect.makeVarArgs(function(args:Array<Dynamic>) {
   lines.push([for (value in args) value == null ? 'nil' : Std.string(value)].join(','));
  }));
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null,interp.variables.get('onCreate'),[]);
  if (lines.join('|') != 'yes,yes,zero,stringzero,first-object,second-object|8,2,sparse,2|3,a,b,c,5|nil')
   throw 'mixed Lua table semantics changed: '+lines.join('|');
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ipairs_holes_native_pair_values_and_owned_clear_copy(self):
        fixture = r'''
class Fixture {
 static function main() {
  var lua = 'local object = {label="x"}\nlocal sparse = {1,2,3}\nsparse[2] = nil\n'
   + 'local mixed = {"one"}\nmixed.label = "side"\nmixed[0] = "zero"\n'
   + 'function onCreate()\n'
   + ' local objectCount = 0\n for i,v in ipairs(object) do\n objectCount = objectCount + 1\n end\n'
   + ' local sparseCount = 0\n for i,v in ipairs(sparse) do\n sparseCount = sparseCount + 1\n end\n'
   + ' for i,v in pairs(nativeArray) do\n print(i,v)\n end\n'
   + ' local copied = luaTableCopy(mixed)\n table.clear(mixed)\n'
   + ' print(objectCount,sparseCount,copied[1],copied.label,copied[0],#mixed,mixed.label,mixed[0])\n'
   + 'end\n';
  var converted=LuaCompat.translate(lua,'helpers.lua');
  if (!converted.supported) throw converted.diagnostics.join('|');
  var lines:Array<String> = [];
  var interp=new LuaCompatInterp();
  interp.variables.set('nativeArray',['first','second']);
  interp.variables.set('makeRangeArray',function(stop:Int,start:Int):Array<Int> {
   var out=[]; for (i in start...stop) out.push(i); return out;
  });
  interp.variables.set('print',Reflect.makeVarArgs(function(args:Array<Dynamic>) {
   lines.push([for (value in args) value == null ? 'nil' : Std.string(value)].join(','));
  }));
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null,interp.variables.get('onCreate'),[]);
  if (lines.join('|') != '1,first|2,second|0,1,one,side,zero,0,nil,nil')
   throw 'Lua helper boundary mismatch: '+lines.join('|');
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
