"""Psych HScript onEvent receives the event's strumTime as its fourth argument.

Psych 0.7 and later call onEvent(eventName, value1, value2, strumTime). hscript
rejects a call with fewer arguments than the function declares, so a script
declaring strumTime failed on every event while the engine passed three values.
The fixture runs the real EngineCompat adapters and a real hscript function.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_camera_alias import extract_method

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / '.haxelib/hscript/2,5,0'


class PsychOnEventStrumTimeTest(unittest.TestCase):
	def test_four_parameter_script_receives_strum_time(self):
		fixture = r'''
class PsychOnEventProbe {
	static function check(value:Bool, message:String) if (!value) throw message;
	static function run(source:String, args:Array<Dynamic>):Dynamic {
		var interp = new hscript.Interp();
		var parser = new hscript.Parser();
		// Psych scripts carry type annotations, which the engine parser accepts.
		parser.allowTypes = true;
		interp.execute(parser.parseString(source));
		return Reflect.callMethod(null, interp.variables.get('onEvent'), args);
	}
	static function main() {
		var row:Array<Dynamic> = ['Play Video', 'intro', '0.5', '', 1234.5];
		var adapted = EngineCompat.callbackArguments('onEvent', 'onEvent', row, false);
		check(adapted.length == 3, 'shared event ABI stays three values');
		var psych = EngineCompat.psychHscriptEventArguments(adapted, row);
		check(psych.length == 4 && psych[3] == 1234.5 && psych[0] == 'Play Video' && psych[2] == '0.5', 'strumTime appended');
		check(adapted.length == 3, 'adapter does not change the shared array');
		var four = 'function onEvent(eventName:String, value1:String, value2:String, strumTime:Float) return eventName + "|" + value1 + "|" + strumTime;';
		check(run(four, psych) == 'Play Video|intro|1234.5', 'four-parameter script runs');
		var failed = false;
		try run(four, adapted) catch (_:Dynamic) failed = true;
		check(failed, 'three values still fail a four-parameter script, which is why the time is passed');
		var three = 'function onEvent(name, value1, value2) return name + "|" + value2;';
		check(run(three, psych) == 'Play Video|0.5', 'three-parameter script ignores the extra value');
		// A row without the time slot, as other callers pass, keeps the three-value ABI.
		var short:Array<Dynamic> = ['Hey!', 'BF', '', 'extended'];
		var shortAdapted = EngineCompat.callbackArguments('onEvent', 'onEvent', short, false);
		check(EngineCompat.psychHscriptEventArguments(shortAdapted, short).length == 3, 'no time slot, no fourth value');
		check(EngineCompat.psychHscriptEventArguments(null, row) == null, 'null stays null');
	}
}
'''
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'PsychOnEventProbe.hx').write_text(fixture, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
				'--run', 'PsychOnEventProbe'], cwd=ROOT, capture_output=True, text=True, timeout=300)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_psych_hscript_dispatch_passes_the_event_time(self):
		source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
		fire = extract_method(source, 'function fireNativeSongEvent(')
		self.assertIn("callAllHScript('onEvent', [e.name, e.v1, e.v2, e.v3 == null ? '' : e.v3, eventStrumTime(e)]", fire)
		call = extract_method(source, 'function callHscript(')
		# Psych HScript and Lua files get the fourth value; HXC and source broadcasts keep their ABI.
		self.assertIn("if (!sourceArguments && func_name == 'onEvent'\n"
			"\t\t\t&& (Std.isOfType(interp, LuaCompatInterp) || interp.variables.get('__psychPlainHscript') == true))\n"
			"\t\t\tcallArgs = EngineCompat.psychHscriptEventArguments(callArgs, args);", call)
		self.assertLess(call.index('EngineCompat.callbackArguments('), call.index('EngineCompat.psychHscriptEventArguments('))

	def test_psych_lua_receives_strum_time(self):
		# Psych calls Lua onEvent with strumTime too. Translated Lua functions must take
		# the fourth value when declared and drop it otherwise, as real Lua does.
		fixture = r'''
class PsychLuaOnEventProbe {
	static function check(value:Bool, message:String) if (!value) throw message;
	static function run(lua:String, args:Array<Dynamic>):Dynamic {
		var converted = LuaCompat.translate(lua, 'event.lua');
		check(converted.supported, converted.diagnostics.join(' | '));
		var interp = new LuaCompatInterp();
		interp.variables.set('Std', Std);
		interp.variables.set('luaString', EngineCompat.luaString);
		interp.variables.set('luaNumber', EngineCompat.luaNumber);
		interp.installTableHelpers();
		interp.execute(new hscript.Parser().parseString(converted.hscript));
		return Reflect.callMethod(null, interp.variables.get('onEvent'), args);
	}
	static function main() {
		var row:Array<Dynamic> = ['Hey!', 'BF', '0.6', '', 2500.0];
		var luaArgs = EngineCompat.psychHscriptEventArguments(
			EngineCompat.callbackArguments('onEvent', 'onEvent', row, false), row);
		check(luaArgs.length == 4 && luaArgs[3] == 2500.0, 'Lua gets the event time');
		var four = 'function onEvent(name, v1, v2, strumTime)\n return name .. "|" .. v2 .. "|" .. strumTime\nend';
		check(Std.string(run(four, luaArgs)) == 'Hey!|0.6|2500', 'four-parameter Lua sees strumTime: ' + run(four, luaArgs));
		var three = 'function onEvent(name, v1, v2)\n return name .. "|" .. v1 .. "|" .. v2\nend';
		check(run(three, luaArgs) == 'Hey!|BF|0.6', 'three-parameter Lua ignores the extra value');
		// A historical row of three values still calls a four-parameter Lua function, with nil time.
		check(Std.string(run('function onEvent(name, v1, v2, strumTime)\n return strumTime == nil\nend', ['Hey!', 'BF', '0.6'])) == 'true',
			'missing time is nil');
	}
}
'''
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'PsychLuaOnEventProbe.hx').write_text(fixture, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
				'--run', 'PsychLuaOnEventProbe'], cwd=ROOT, capture_output=True, text=True, timeout=300)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_native_lua_event_closure_accepts_the_time(self):
		# A native closure with three parameters would reject the fourth value under hxcpp.
		source = (ROOT / 'source/RuntimeSmokeLegacyEventMap.hx').read_text(encoding='utf-8')
		self.assertIn("lua.variables.set('onEvent',Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {", source)
		self.assertNotIn("lua.variables.set('onEvent',function(n:String,a:String,b:String)", source)

	def test_event_time_conversion(self):
		source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
		method = extract_method(source, 'static function eventStrumTime(')
		fixture = 'class Main {\n' + method + r'''
	static function main() {
		if (eventStrumTime({time: 1500}) != 1500) throw 'int';
		if (eventStrumTime({time: 12.25}) != 12.25) throw 'float';
		if (eventStrumTime({time: '800.5'}) != 800.5) throw 'string';
		if (eventStrumTime({time: null}) != 0) throw 'null time';
		if (eventStrumTime({time: 'bad'}) != 0) throw 'bad time';
		if (eventStrumTime(null) != 0) throw 'null event';
	}
}
'''
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'], cwd=ROOT,
				capture_output=True, text=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
	unittest.main()
