from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"
WHITTY_4CHAN = Path("/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/4chan.lua")


class LuaCompatibilityTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "LuaCompatTest.hx").write_text(source, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HAXESCRIPT), "-main", "LuaCompatTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_compact_then_exp_and_literal_gsub_execute(self):
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var source = "function onCreate()\n"
   + " if version == '0.5.1'then\n"
   + "  bit = string.gsub(version, '%.', '')\n"
   + "  probability = math.exp(-1)\n"
   + " end\n"
   + "end\n";
  var translated = LuaCompat.translate(source, "compact.lua");
  if (!translated.supported) throw translated.diagnostics.join(" | ");
  var interp = new LuaCompatInterp();
  interp.variables.set("Math", Math);
  interp.variables.set("version", "0.5.1");
  interp.variables.set("bit", "");
  interp.variables.set("probability", 0.0);
  interp.variables.set("luaStringGsub", EngineCompat.luaStringGsub);
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null, interp.variables.get("onCreate"), []);
  if (interp.variables.get("bit") != "051"
   || Math.abs(interp.variables.get("probability") - Math.exp(-1)) > 0.000001)
   throw "compact then or standard-library helpers did not execute";
  if (EngineCompat.luaStringGsub("a.b.c", "%.", "", 1) != "ab.c")
   throw "literal gsub maximum replacement count";
  var unsupported = LuaCompat.translate(
   "function onCreate()\n bit = string.gsub('a1', '%d', '')\nend", "class-pattern.lua");
  if (unsupported.supported || unsupported.diagnostics.join(" | ").indexOf("lua-string-library") < 0)
   throw "unsupported Lua pattern silently accepted";
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_if_and_elseif_allow_no_space_before_parenthesis(self):
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var source = "function onUpdate()\n"
   + " if(change) then\n"
   + "  change = false\n"
   + " elseif(other) then\n"
   + "  change = true\n"
   + " end\n"
   + "end";
  var converted = LuaCompat.translate(source, "compact-if.lua");
  if (!converted.supported) throw converted.diagnostics.join(" | ");
  if (converted.hscript.indexOf("if ((change)") < 0
   || converted.hscript.indexOf("} else if ((other)") < 0)
   throw "compact if/elseif did not preserve block structure: " + converted.hscript;
  new hscript.Parser().parseString(converted.hscript);
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_callbacks_tables_and_control_flow_translate(self):
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n"
            + "    local prefs = {move = 10, enabled = true, names = {'a', 'b'}}\n"
            + "    if prefs.enabled and #prefs.names == 2 then\n"
            + "        for i = 0, 3 do\n"
            + "            noteTweenX('n' .. i, i, prefs.move, 0.2, 'linear')\n"
            + "        end\n"
            + "    elseif not prefs.enabled then\n"
            + "        debugPrint('off')\n"
            + "    end\n"
            + "end\n"
            + "function onUpdate(elapsed)\n"
            + "    while elapsed > 1 do\n"
            + "        elapsed = elapsed - 1\n"
            + "    end\n"
            + "end";
        var converted = LuaCompat.translate(source, "fixture.lua");
        if (!converted.supported) fail("safe fixture unexpectedly diagnosed: " + converted.diagnostics.join(" | "));
        if (converted.hscript.indexOf("function onCreate() {") < 0) fail("callback conversion");
        if (converted.hscript.indexOf("{move: 10, enabled: true, names: ['a', 'b']}") < 0) fail("table conversion: " + converted.hscript);
        if (converted.hscript.indexOf("for (i in makeRangeArray(Std.int(3) + 1, Std.int(0))) {") < 0) fail("numeric loop conversion");
        if (converted.hscript.indexOf("&&") < 0 || converted.hscript.indexOf("luaSequenceLength(") < 0) fail("operator conversion");
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_add_lua_sprite_unknown_layer_uses_lua_nil_without_losing_locals(self):
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var source = "function onCreate()\n"
   + " local localLayer = true\n"
   + " makeLuaSprite('missing', 'missing', 0, 0)\n"
   + " addLuaSprite('missing', unresolvedLayer)\n"
   + " makeLuaSprite('local', 'local', 0, 0)\n"
   + " addLuaSprite('local', localLayer)\n"
   + " makeLuaSprite('engine', 'engine', 0, 0)\n"
   + " addLuaSprite('engine', engineLayer)\n"
   + "end\n";
  var converted = LuaCompat.translate(source, 'optional-sprite-layer.lua');
  if (converted.hscript.indexOf('luaReadOptional(function() { return unresolvedLayer; })') < 0
      || converted.hscript.indexOf('luaReadOptional(function() { return localLayer; })') < 0
      || converted.hscript.indexOf('luaReadOptional(function() { return engineLayer; })') < 0)
   throw 'layer optional read lowering: ' + converted.hscript;
  var observed:Map<String, Dynamic> = new Map<String, Dynamic>();
  var interp = new hscript.Interp();
  interp.variables.set('luaReadOptional', function(reader:Dynamic):Dynamic {
   try return Reflect.callMethod(null, reader, []) catch (_:Dynamic) return null;
  });
  interp.variables.set('makeLuaSprite', function(tag:String, image:String, x:Float, y:Float):Dynamic return {});
  interp.variables.set('addLuaSprite', function(tag:String, layer:Dynamic):Void observed.set(tag, layer));
  interp.variables.set('engineLayer', true);
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  var onCreate:Dynamic = interp.variables.get('onCreate');
  Reflect.callMethod(null, onCreate, []);
  if (observed.get('missing') != null || observed.get('local') != true || observed.get('engine') != true)
   throw 'missing globals must resolve to nil while local and engine values survive';
  Sys.println('ok');
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_whitty_stage_runtime_hscript_handles_undefined_layer(self):
        if not WHITTY_4CHAN.exists():
            self.skipTest("Whitty example donor stage is not mounted")
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var path = "/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/4chan.lua";
  var converted = LuaCompat.translate(sys.io.File.getContent(path), path);
  if (converted.hscript.indexOf('luaReadOptional(function() { return front; })') < 0)
   throw 'runtime translator did not lower the unresolved layer: ' + converted.hscript;
  var addedLayer:Dynamic = 'unset';
  var interp = new LuaCompatInterp();
  interp.variables.set('luaReadOptional', function(reader:Dynamic):Dynamic {
   try return Reflect.callMethod(null, reader, []) catch (_:Dynamic) return null;
  });
  interp.variables.set('makeLuaSprite', function(tag:String, image:String, x:Float, y:Float):Dynamic return {});
  interp.variables.set('setLuaSpriteScrollFactor', function(tag:String, x:Float, y:Float):Void {});
  interp.variables.set('setPropertyFromClass', function(className:String, property:String, value:Dynamic):Void {});
  interp.variables.set('addLuaSprite', function(tag:String, layer:Dynamic, ?extra:Dynamic):Void addedLayer = layer);
  interp.variables.set('close', function(?destroy:Bool):Void {});
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  var onCreate:Dynamic = interp.variables.get('onCreate');
  Reflect.callMethod(null, onCreate, []);
  if (addedLayer != null && addedLayer != false)
   throw 'undefined Lua layer did not resolve to nil/false: ' + Std.string(addedLayer);
  Sys.println('ok');
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.variables.set('luaReadOptional'", play_state)

    def test_translated_lua_functions_accept_omitted_positional_arguments(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "local function sprite(tag, image, x, y, scale)\n"
            + "  return scale\n"
            + "end\n"
            + "function onCreatePost()\n"
            + "  observedScale = sprite('resume_button', 'Pause/Pause1', 0, 0)\n"
            + "end";
        var converted = LuaCompat.translate(source, "optional-arguments.lua");
        if (!converted.supported)
            throw "optional Lua parameters were diagnosed: " + converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("function sprite(?tag, ?image, ?x, ?y, ?scale)") < 0)
            throw "translated parameters are still required: " + converted.hscript;
        var interp = new hscript.Interp();
        interp.variables.set("observedScale", "unset");
        interp.execute(new hscript.Parser().parseString(converted.hscript));
        Reflect.callMethod(null, interp.variables.get("onCreatePost"), []);
        if (interp.variables.get("observedScale") != null)
            throw "an omitted Lua argument did not become nil";
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_emitted_loops_carry_an_iteration_watchdog(self):
        """A runaway donor while-loop must throw a catchable diagnostic
        instead of spinning the whole engine inside one callback."""
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onUpdate(elapsed)\n"
            + "    while elapsed > 1 do\n"
            + "        elapsed = elapsed - 1\n"
            + "    end\n"
            + "end";
        var converted = LuaCompat.translate(source, "fixture-loop.lua");
        if (!converted.supported) fail("loop fixture unexpectedly diagnosed: " + converted.diagnostics.join(" | "));
        if (converted.hscript.indexOf("__luaLoopGuard") < 0) fail("loop guard missing");
        if (converted.hscript.indexOf("lua loop watchdog") < 0) fail("watchdog throw missing");
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsupported_lua_is_distinct_and_never_emitted_as_executable_haxe(self):
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n  runHaxeCode([[ FlxG.game.setFilters([]); ]])\n  setmetatable({}, {})\nend";
        var converted = LuaCompat.translate(source, "unsafe.lua");
        if (converted.supported) fail("unsafe source was marked supported");
        var all = converted.diagnostics.join(" | ");
        if (all.indexOf("lua-metatable") < 0 || all.indexOf("lua-raw-haxe") >= 0) fail(all);
        if (converted.hscript.indexOf("FlxG.game.setFilters") >= 0) fail("raw Haxe leaked into output");
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_standard_library_subset_routes_through_engine_helpers(self):
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n"
            + "  local angle = math.rad(90)\n"
            + "  local value = tonumber('12.5')\n"
            + "  local suffix = string.sub('abcdef', 2, 4)\n"
            + "  local now = os.clock()\n"
            + "  local kind = type(value)\n"
            + "  local found = table.find({'a', 'b'}, 'b')\n"
            + "  table.clear({})\n"
            + "end";
        var converted = LuaCompat.translate(source, "stdlib.lua");
        if (converted.diagnostics.length != 0)
            fail("standard library subset unexpectedly diagnosed: " + converted.diagnostics.join(" | "));
        for (token in ["luaMathRad", "luaNumber", "luaStringSub", "luaOsClock", "luaType", "luaTableFind", "luaTableClear"])
            if (converted.hscript.indexOf(token) < 0) fail("missing routed helper: " + token + " in " + converted.hscript);
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_collection_and_string_helpers_route_through_engine_helpers(self):
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n"
            + "  local values = {'a', 'b'}\n"
            + "  for i, value in ipairs(values) do\n"
            + "    debugPrint(string.format('%02d:%s', i, value))\n"
            + "  end\n"
            + "  for _, value in pairs(values) do\n"
            + "    debugPrint(value)\n"
            + "  end\n"
            + "  for part in string.gmatch('a,b,,c', '([^,]+)') do\n"
            + "    debugPrint(part)\n"
            + "  end\n"
            + "end";
        var converted = LuaCompat.translate(source, "collections.lua");
        if (!converted.supported)
            fail("collection/string helpers unexpectedly diagnosed: " + converted.diagnostics.join(" | "));
        for (token in ["luaIpairsLength", "luaIpairsKey", "luaIpairsValue",
            "luaPairsLength", "luaPairsKey", "luaPairsValue", "luaStringFormat", "luaStringGmatch"])
            if (converted.hscript.indexOf(token) < 0) fail("missing routed helper: " + token + " in " + converted.hscript);
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1').is_dir(), 'mounted Lua corpus is unavailable')
    def test_representative_donor_scripts_produce_parseable_partial_hscript(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var all = [
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Resonance/Recolor2.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/stages/Haven.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Xfracture/Used later/noteMoveOnPress.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/hellbeats_kade_engine/HellBeats Kade Engine/assets/data/tutorial/modchart.lua"
        ];
        // The mounted donor set changes as mods are added and removed; only
        // translate what is actually present, but require at least one.
        var paths = [];
        for (path in all)
            if (sys.FileSystem.exists(path))
                paths.push(path);
        if (paths.length == 0)
            throw "no mounted donor scripts";
        for (path in paths) {
            var result = LuaCompat.translate(sys.io.File.getContent(path), path);
            new hscript.Parser().parseString(result.hscript);
        }
		for (path in paths) {
			var converted = LuaCompat.translate(sys.io.File.getContent(path), path);
			for (diagnostic in converted.diagnostics)
				if (diagnostic.indexOf("lua-math") >= 0)
					throw "Kade math helper was not routed: " + diagnostic;
		}
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1').is_dir(), 'mounted Lua corpus is unavailable')
    def test_donor_dynamic_globals_route_exact_supported_surface(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var all = [
            "/run/media/cammie/External Storage/FNF-Example-Mods/hellbeats_kade_engine/HellBeats Kade Engine/assets/data/tutorial/modchart.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Resonance/Modchart11.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Resonance/Used/Scary.lua",
            "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Resonance/Used/Shaders.lua"
        ];
        var expected = [2, 10, 1, 1];
        var paths = [];
        var expectedPresent = [];
        for (index in 0...all.length)
            if (sys.FileSystem.exists(all[index])) {
                paths.push(all[index]);
                expectedPresent.push(expected[index]);
            }
        if (paths.length == 0)
            throw "no mounted donor scripts";
        var supportedOccurrences = 0;
        var remainingOccurrences = 0;
        for (index in 0...paths.length) {
            var source = sys.io.File.getContent(paths[index]);
            var sourceCount = source.split("_G").length - 1;
            if (sourceCount != expectedPresent[index])
                throw "donor count changed for " + paths[index] + ": " + sourceCount;
            var converted = LuaCompat.translate(source, paths[index]);
            if (!converted.supported)
                throw "dynamic-global donor was diagnosed: " + converted.diagnostics.join(" | ");
            if (converted.hscript.indexOf("_G") >= 0)
                throw "dynamic-global source leaked into HScript: " + paths[index];
            new hscript.Parser().parseString(converted.hscript);
            var pathName = paths[index];
            var isTutorial = pathName.indexOf("tutorial/modchart") >= 0;
            var isResonanceStrum = pathName.indexOf("Modchart11") >= 0;
            if (isTutorial && converted.hscript.indexOf("luaGetDefaultStrum(i, \"x\")") < 0
                    && converted.hscript.indexOf("luaGetDefaultStrum(i, \"y\")") < 0)
                throw "tutorial default route missing: " + converted.hscript;
            if (isResonanceStrum && (converted.hscript.indexOf("luaSetScriptGlobal") < 0
                    || converted.hscript.indexOf("luaGetScriptGlobal") < 0))
                throw "Resonance strum-global route missing: " + converted.hscript;
            if (!isTutorial && !isResonanceStrum && converted.hscript.indexOf("luaSetScriptGlobal(\"objects\"") < 0
                    && pathName.indexOf("Scary") >= 0)
                throw "Resonance objects export route missing: " + converted.hscript;
            supportedOccurrences += sourceCount;
        }
        if (supportedOccurrences < 1)
            throw "supported dynamic-global count changed: " + supportedOccurrences;
        if (remainingOccurrences != 0)
            throw "remaining dynamic-global count changed: " + remainingOccurrences;
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_dynamic_globals_stay_diagnostic_and_non_executable(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  _G['notWhitelisted' .. suffix] = 1\n"
            + "  _G.secret = 2\n"
            + "  _G['defaultStrum' .. i .. 'X'] = 1\n"
            + "end";
        var converted = LuaCompat.translate(source, "unknown-global.lua");
        if (converted.supported)
            throw "unknown dynamic global was marked supported";
        if (converted.diagnostics.join(" | ").indexOf("lua-global-table") < 0)
            throw "unknown dynamic global lost its diagnostic: " + converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("luaSetScriptGlobal") >= 0
                || converted.hscript.indexOf("luaGetScriptGlobal") >= 0)
            throw "unknown dynamic global was routed";
        new hscript.Parser().parseString(converted.hscript);
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dynamic_global_runtime_adapter_is_whitelisted(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var globals:Map<String, Dynamic> = [];
        if (!EngineCompat.luaSetScriptGlobal(globals, "objects", [1, 2])) throw "objects write";
        if (EngineCompat.luaGetScriptGlobal(globals, "objects") == null) throw "objects read";
        if (EngineCompat.luaSetScriptGlobal(globals, "notAllowed", 1)) throw "unsafe write";
        if (EngineCompat.luaDynamicGlobalAllowed("defaultPlayerStrumX4")) throw "bad index";
        if (!EngineCompat.luaDynamicGlobalAllowed("defaultPlayerStrumY3")) throw "valid index";
        if (!EngineCompat.luaDynamicGlobalAllowed("defaultOpponentStrumX0")) throw "opponent alias";
        if (EngineCompat.luaDynamicGlobalAllowed("defaultOpponentStrumY4")) throw "bad opponent index";
        var x = [10.0, 20.0];
        var y = [30.0, 40.0];
        if (EngineCompat.luaGetDefaultStrum(x, y, 1, "x") != 20) throw "x read";
        if (EngineCompat.luaGetDefaultStrum(x, y, 1, "y") != 40) throw "y read";
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_runhaxe_camera_shader_filters_use_safe_native_route(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onCreatePost()\n"
            + "runHaxeCode([[ game.camGame.setFilters([new ShaderFilter(game.getLuaObject('Chrom').shader), new ShaderFilter(game.getLuaObject('Chrom2').shader)]); ]])\n"
            + "end\n"
            + "function onDestroy()\n"
            + "runHaxeCode([[ FlxG.game.setFilters([]); ]])\n"
            + "end";
        var converted = LuaCompat.translate(source, "shader.lua");
        if (converted.hscript.indexOf('setCameraShaderFilters("camGame", ["Chrom", "Chrom2"])') < 0)
            throw "camera shader route missing: " + converted.hscript;
        if (converted.hscript.indexOf('clearCameraShaderFilters("camGame")') < 0)
            throw "camera shader clear missing: " + converted.hscript;
        for (diagnostic in converted.diagnostics)
            if (diagnostic.indexOf('[lua-raw-haxe]') >= 0)
                throw "safe shader block was still rejected: " + diagnostic;
        new hscript.Parser().parseString(converted.hscript);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repeated_raw_haxe_shapes_use_narrow_native_routes(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "runHaxeCode([[ var chrom = game.createRuntimeShader('chromabber'); chrom.setFloat('amount', 0.25); game.camGame.setFilters([new ShaderFilter(game.getLuaObject('shaderBG').shader), new ShaderFilter(chrom)]); ]])\n"
            + "runHaxeCode([[ FlxTween.tween(game.boyfriend.colorTransform, { redOffset: ]]..rgbbf[1]..[[, greenOffset: ]]..rgbbf[2]..[[, blueOffset: ]]..rgbbf[3]..[[, redMultiplier: 0, greenMultiplier: 0, blueMultiplier: 0 }, ]]..v1..[[); ]])\n"
            + "runHaxeCode([[ for (i in 0...game.strumLineNotes.length) { game.strumLineNotes.members[i].useRGBShader = false; } ]])\n"
            + "runHaxeCode([[ var angleLerp = FlxMath.bound(FlxMath.bound(]]..el..[[ * 2.4 / 0.4, 0, 1) * ]]..speed..[[ * cameraSpeed * playbackRate,0,1); game.camGame.angle = FlxMath.lerp(game.camGame.angle,0 + ]]..offsetX..[[ / 30, angleLerp); ]])\n"
            + "end";
        var converted = LuaCompat.translate(source, "routes.lua");
        if (converted.diagnostics.length != 0)
            throw converted.diagnostics.join(" | ");
        for (token in ["setCameraShaderFilters", "chromabber", "tweenCharacterColorRGB", "luaTableValue", "setStrumLineRGBShader", "updateCameraAngle"])
            if (converted.hscript.indexOf(token) < 0) throw "missing route: " + token + " in " + converted.hscript;
        new hscript.Parser().parseString(converted.hscript);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_angle_route_accepts_callback_elapsed_without_raw_haxe(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onUpdate(elapsed)\n"
            + "runHaxeCode([[ var angleLerp = FlxMath.bound(FlxMath.bound(]]..elapsed..[[ * 2.4 / 0.4, 0, 1) * ]]..speed..[[ * cameraSpeed * playbackRate,0,1); game.camGame.angle = FlxMath.lerp(game.camGame.angle,0 + ]]..offsetX..[[ / 30, angleLerp); ]])\n"
            + "end";
        var converted = LuaCompat.translate(source, "elapsed-camera-angle.lua");
        if (!converted.supported)
            throw "callback elapsed camera route was diagnosed: " + converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("updateCameraAngle(elapsed, offsetX, speed)") < 0)
            throw "callback elapsed route missing: " + converted.hscript;
        if (converted.hscript.indexOf("runHaxeCode") >= 0)
            throw "raw Haxe leaked into callback elapsed route";
        new hscript.Parser().parseString(converted.hscript);
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_angle_route_accepts_legacy_els_alias_without_raw_haxe(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onUpdate(elapsed)\n"
            + "runHaxeCode([[ var angleLerp = FlxMath.bound(FlxMath.bound(]]..els..[[ * 2.4 / 0.4, 0, 1) * ]]..speed..[[ * cameraSpeed * playbackRate,0,1); game.camGame.angle = FlxMath.lerp(game.camGame.angle,0 + ]]..offsetX..[[ / 30, angleLerp); ]])\n"
            + "end";
        var converted = LuaCompat.translate(source, "legacy-els-camera-angle.lua");
        if (!converted.supported)
            throw "legacy els camera route was diagnosed: " + converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("updateCameraAngle(elapsed, offsetX, speed)") < 0)
            throw "legacy els route missing: " + converted.hscript;
        if (converted.hscript.indexOf("runHaxeCode") >= 0)
            throw "raw Haxe leaked into legacy els route";
        new hscript.Parser().parseString(converted.hscript);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_quoted_runhaxe_move_camera_boolean_uses_safe_native_route(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onUpdatePost()\n"
            + "  runHaxeCode('PlayState.instance.moveCamera(' .. tostring(IsDad) .. ');')\n"
            + "end";
        var converted = LuaCompat.translate(source, "camera-follow.lua");
        if (!converted.supported)
            throw "quoted moveCamera route was diagnosed: " + converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("currentPlayState.moveCamera(IsDad)") < 0)
            throw "quoted moveCamera call was not lowered: " + converted.hscript;
        if (converted.hscript.indexOf("runHaxeCode") >= 0)
            throw "raw Haxe leaked into converted source";
        new hscript.Parser().parseString(converted.hscript);

        var observed:Array<Bool> = [];
        var interp = new hscript.Interp();
        interp.variables.set("currentPlayState", {moveCamera:function(isDad:Bool) observed.push(isDad)});
        interp.variables.set("IsDad", true);
        interp.execute(new hscript.Parser().parseString(converted.hscript));
        var callback:Dynamic = interp.variables.get("onUpdatePost");
        Reflect.callMethod(null, callback, []);
        interp.variables.set("IsDad", false);
        Reflect.callMethod(null, callback, []);
        if (observed.length != 2 || observed[0] != true || observed[1] != false)
            throw "moveCamera did not receive the Lua boolean: " + observed.join(",");

        var nearMatch = LuaCompat.translate("function onUpdatePost()\n"
            + "  runHaxeCode('PlayState.instance.moveCamera(' .. tostring(IsDad) .. '); trace(1);')\n"
            + "end", "camera-follow-near-match.lua");
        if (nearMatch.supported || nearMatch.hscript.indexOf("currentPlayState.moveCamera") >= 0)
            throw "moveCamera near-match escaped the complete-call allowlist: " + nearMatch.hscript;
        if (nearMatch.diagnostics.join(" | ").indexOf("lua-raw-haxe") < 0)
            throw "moveCamera near-match was not diagnosed: " + nearMatch.diagnostics.join(" | ");
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reverse_glitch_shader_and_resize_blocks_use_whole_block_routes(self):
        fixture = r'''
class LuaCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "local shaderName = \"invert\"\n"
            + "runHaxeCode([[\n"
            + "    var shaderName = \"]] .. shaderName .. [[\";\n"
            + "    game.initLuaShader(shaderName);\n"
            + "    var shader0 = game.createRuntimeShader(shaderName);\n"
            + "    game.getLuaObject(\"invert\").shader = shader0;\n"
            + "    game.variables.set(\"invertShader\", shader0);\n"
            + "]])\n"
            + "runHaxeCode([[\n"
            + "    var shader = game.variables.get(\"invertShader\");\n"
            + "    game.camGame.setFilters([new ShaderFilter(shader)]);\n"
            + "]])\n"
            + "runHaxeCode([[\n"
            + "    resetCamCache = function(?spr) {\n"
            + "        if (spr == null || spr.filters == null) return;\n"
            + "        spr.__cacheBitmap = null;\n"
            + "        spr.__cacheBitmapData = null;\n"
            + "    }\n"
            + "    fixShaderCoordFix = function(?_) {\n"
            + "        resetCamCache(game.camGame.flashSprite);\n"
            + "        resetCamCache(game.camHUD.flashSprite);\n"
            + "        resetCamCache(game.camOther.flashSprite);\n"
            + "    }\n"
            + "    FlxG.signals.gameResized.add(fixShaderCoordFix);\n"
            + "    fixShaderCoordFix();\n"
            + "]])\n"
            + "runHaxeCode([[ FlxG.signals.gameResized.remove(fixShaderCoordFix); ]])";
        var converted = LuaCompat.translate(source, "reverse-glitch.lua");
        if (!converted.supported)
            fail("reverse glitch route diagnosed: " + converted.diagnostics.join(" | "));
        for (token in ["createRuntimeShaderAndStore", "setCameraShaderFiltersFromStored",
            "installShaderCoordFix", "removeShaderCoordFix"])
            if (converted.hscript.indexOf(token) < 0)
                fail("missing reverse glitch route: " + token + " in " + converted.hscript);
        if (converted.hscript.indexOf("runHaxeCode") >= 0)
            fail("raw runHaxeCode leaked into converted source");
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reverse_glitch_routes_reject_extra_raw_haxe_operations(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "runHaxeCode([[\n"
            + "    var shader = game.variables.get(\"invertShader\");\n"
            + "    game.camGame.setFilters([new ShaderFilter(shader)]);\n"
            + "    game.camGame.visible = true;\n"
            + "]])";
        var converted = LuaCompat.translate(source, "reverse-glitch-extra.lua");
        if (converted.supported)
            throw "extra operation was incorrectly routed";
        var all = converted.diagnostics.join(" | ");
        if (all.indexOf("lua-raw-haxe") < 0)
            throw "strict route did not preserve raw-Haxe diagnostic: " + all;
        if (converted.hscript.indexOf("game.camGame.visible") >= 0)
            throw "raw Haxe leaked into output";
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1').is_dir(), 'mounted Lua corpus is unavailable')
    def test_reverse_glitch_donor_has_no_unrouted_runhaxe_sites(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var path = "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Resonance/All scripts/Reverse Glitch.lua";
        var converted = LuaCompat.translate(sys.io.File.getContent(path), path);
        if (!converted.supported)
            throw "donor diagnostics: " + converted.diagnostics.join(" | ");
        for (diagnostic in converted.diagnostics)
            if (diagnostic.indexOf("lua-raw-haxe") >= 0)
                throw "unrouted Reverse Glitch block: " + diagnostic;
        for (token in ["createRuntimeShaderAndStore", "setCameraShaderFiltersFromStored",
            "installShaderCoordFix", "removeShaderCoordFix"])
            if (converted.hscript.indexOf(token) < 0)
                throw "missing donor route: " + token;
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1').is_dir(), 'mounted Lua corpus is unavailable')
    def test_donor_has_lua_callbacks_and_engine_calls(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
        files = list(donor.rglob("*.lua"))
        self.assertGreater(len(files), 100)
        text = "\n".join(path.read_text(errors="ignore") for path in files)
        for token in ("function onCreate", "function onUpdate", "setProperty(", "doTween", "noteTween"):
            self.assertIn(token, text)

    def test_non_unit_numeric_for_loop_is_routed_without_dropping_the_body(self):
        fixture = r'''
class LuaCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  for i = 7, 1, -2 do\n"
            + "    debugPrint(i)\n"
            + "  end\n"
            + "end";
        var converted = LuaCompat.translate(source, "stepped-loop.lua");
        if (!converted.supported)
            throw converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("__luaForStep") < 0
            || converted.hscript.indexOf("while (") < 0
            || converted.hscript.indexOf("debugPrint(i)") < 0)
            throw converted.hscript;
        new hscript.Parser().parseString(converted.hscript);
        Sys.println("ok");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_unit_numeric_for_loop_advances_and_terminates(self):
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var source = "function onCreate()\n"
   + " for i = 0, 7, 2 do\n print(i)\n end\n"
   + " for j = 7, 1, -3 do\n print(j)\n end\n"
   + "end\n";
  var translated = LuaCompat.translate(source, 'steps.lua');
  if (!translated.supported) throw translated.diagnostics.join('|');
  var seen:Array<Int> = [];
  var interp = new LuaCompatInterp();
  interp.variables.set('Std', Std);
  interp.variables.set('print', function(value:Int):Void seen.push(value));
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  if (seen.join(',') != '0,2,4,6,7,4,1') throw seen.join(',');
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_numeric_step_expression_is_evaluated_once_and_zero_is_diagnosed(self):
        fixture = r'''
class LuaCompatTest {
 static function main() {
  var source = "function onCreatePost()\n"
   + " for i = 0, 7, getProperty('unspawnNotes.length') - 1 do\n"
   + "  print(i)\n end\nend\n";
  var translated = LuaCompat.translate(source, 'dynamic-step.lua');
  if (!translated.supported) throw translated.diagnostics.join('|');
  var length = 5;
  var calls = 0;
  var seen:Array<Int> = [];
  var interp = new LuaCompatInterp();
  interp.variables.set('Std', Std);
  interp.variables.set('getProperty', function(_:String):Int { calls++; return length; });
  interp.variables.set('print', function(value:Int):Void seen.push(value));
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  var callback = interp.variables.get('onCreatePost');
  Reflect.callMethod(null, callback, []);
  if (seen.join(',') != '0,4' || calls != 1) throw 'dynamic step: ' + seen.join(',') + '/' + calls;
  length = 1;
  var diagnosed = false;
  try Reflect.callMethod(null, callback, [])
  catch (error:Dynamic) diagnosed = Std.string(error).indexOf('step is zero') >= 0;
  if (!diagnosed) throw 'zero step silently skipped';
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1').is_dir(), 'mounted Lua corpus is unavailable')
    def test_last_two_corpus_edges_have_bounded_routes_and_parseable_output(self):
        fixture = r'''
import hscript.Parser;
import sys.io.File;

class LuaCompatTest {
    static function main() {
        var zPath = "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/custom_events/zCameraFix.lua";
        var z = LuaCompat.translate(File.getContent(zPath), zPath);
        if (!z.supported)
            throw "zCameraFix should use the scoped table/metatable adapters: " + z.diagnostics.join(" | ");
        if (z.hscript.indexOf("luaTableCopy") < 0
                || z.hscript.indexOf("luaSetMetatable") < 0
                || z.hscript.indexOf("t.skew.set(t.skew") < 0)
            throw "zCameraFix route dropped a safe operation: " + z.hscript;
        new Parser().parseString(z.hscript);

        var camPath = "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/data/Xfracture/camAngle.lua";
        var cam = LuaCompat.translate(File.getContent(camPath), camPath);
        new Parser().parseString(cam.hscript);
        if (!cam.supported)
            throw "camAngle legacy elapsed alias was diagnosed: " + cam.diagnostics.join(" | ");
        if (cam.hscript.indexOf("updateCameraAngle(el, offsetX, speed)") < 0)
            throw "camAngle safe angle route missing: " + cam.hscript;
        if (cam.hscript.indexOf("updateCameraAngle(elapsed, offsetX, speed)") < 0)
            throw "camAngle legacy els route missing: " + cam.hscript;
        if (cam.hscript.indexOf("runHaxeCode") >= 0)
            throw "raw Haxe leaked into camAngle output";
        trace("OK");
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_mounted_lua_corpus_translates_without_crash_or_invalid_hscript(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
        if not donor.exists():
            self.skipTest("example donor is not mounted")
        fixture = r'''
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

class LuaCompatTest {
    static function collect(path:String, output:Array<String>):Void {
        if (!FileSystem.exists(path)) return;
        if (!FileSystem.isDirectory(path)) {
            if (Path.extension(path).toLowerCase() == "lua") output.push(path);
            return;
        }
        for (name in FileSystem.readDirectory(path))
            collect(Path.join([path, name]), output);
    }

    static function main() {
        var files:Array<String> = [];
        collect("/run/media/cammie/External Storage/FNF-Example-Mods", files);
        if (files.length < 100) throw "mounted Lua corpus shrank: " + files.length;
        var supported = 0;
        var diagnosedPaths:Array<String> = [];
        for (corpusPath in files) {
            var path = corpusPath;
            var converted = LuaCompat.translate(File.getContent(path), path);
            new hscript.Parser().parseString(converted.hscript);
            if (converted.supported) supported++;
            else diagnosedPaths.push(path + "|" + converted.diagnostics.join(" | "));
        }
        if (files.length == 0 || diagnosedPaths.length != 0)
            throw "Lua compatibility corpus changed: " + supported + "/" + files.length
                + "; diagnosed=" + diagnosedPaths.join(" || ");
        Sys.println("Lua corpus clean: " + supported + "/" + files.length);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_donor_lua_surface_has_central_routes_and_explicit_gaps(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
        files = list(donor.rglob("*.lua"))
        if not files:
            self.skipTest("example donor is not mounted")
        text = "\n".join(path.read_text(errors="ignore") for path in files)
        # These counts are intentionally lower bounds: they document the
        # concrete mounted corpus and catch regressions where the shared
        # adapter silently drops a donor API while the pack grows.
        self.assertGreaterEqual(len(files), 120)
        self.assertGreaterEqual(text.count("setProperty("), 400)
        self.assertGreaterEqual(text.count("getProperty("), 200)
        self.assertGreaterEqual(text.count("doTweenAlpha("), 60)
        self.assertGreaterEqual(text.count("runTimer("), 50)
        self.assertGreaterEqual(text.count("runHaxeCode("), 20)
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        lower = engine.lower()
        for routed in (
            "setproperty", "getproperty", "dotweenalpha", "runtimer",
            "starttween", "setactorx", "setactory", "tweencamerazoom",
            "settextalignment", "gettextfont", "getrandombool",
            "getmousex", "getmousey", "getmouseclicked", "playmusic",
        ):
            self.assertIn("'" + routed + "'", lower, routed)
        # Raw Haxe, unknown _G/metatable use and complex string iteration
        # remain explicit diagnostics. They must not be mislabeled as support.
        self.assertIn("lua-raw-haxe", (ROOT / "source/LuaCompat.hx").read_text())
        self.assertIn("lua-global-table", (ROOT / "source/LuaCompat.hx").read_text())
        self.assertIn("lua-metatable", (ROOT / "source/LuaCompat.hx").read_text())

    def test_importer_and_runtime_use_the_same_central_adapter(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("LuaCompat.translate", module)
        self.assertIn("generatedModchart", module)
        self.assertIn("getCompatibleHscript", play_state)
        self.assertIn("LuaCompat.translate(FNFAssets.getText(luaPath), luaPath)", play_state)
        self.assertIn("difficultyModchart + '.lua'", play_state)


if __name__ == "__main__":
    unittest.main()
