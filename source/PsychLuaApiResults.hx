package;

import hscript.Interp;

/** Converts returned Haxe arrays at the Lua source-API boundary only. */
class PsychLuaApiResults {
	public static function install(interp:Interp):Void {
		if (!Std.isOfType(interp, LuaCompatInterp))
			return;
		var lua:LuaCompatInterp = cast interp;
		wrap(interp, lua, 'getProperty');
		wrap(interp, lua, 'getPropertyFromGroup');
		wrap(interp, lua, 'getPropertyFromClass');
	}

	static function wrap(interp:Interp, lua:LuaCompatInterp, name:String):Void {
		var original = interp.variables.get(name);
		if (!Reflect.isFunction(original))
			return;
		interp.variables.set(name, Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			var result = Reflect.callMethod(null, original, args);
			return lua.sourceApiResult(result);
		}));
	}
}
