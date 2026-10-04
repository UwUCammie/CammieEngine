package;

/** Psych's current sentinels plus historical script-return spellings. */
class ScriptCallbackResult {
	public static inline var STOP = '##PSYCHLUA_FUNCTIONSTOP';
	public static inline var CONTINUE = '##PSYCHLUA_FUNCTIONCONTINUE';
	public static inline var STOP_LUA = '##PSYCHLUA_FUNCTIONSTOPLUA';
	public static inline var STOP_HSCRIPT = '##PSYCHLUA_FUNCTIONSTOPHSCRIPT';
	public static inline var STOP_ALL = '##PSYCHLUA_FUNCTIONSTOPALL';

	public static function stopsGate(value:Dynamic):Bool {
		if (value == true) return true;
		if (!Std.isOfType(value, String)) return false;
		var text = StringTools.trim(cast value).toLowerCase();
		return text == 'function_stop' || text == 'function stop' || text == 'stop'
			|| text == STOP.toLowerCase() || text == STOP_ALL.toLowerCase();
	}

	public static function continues(value:Dynamic):Bool {
		if (value == null || value == false) return true;
		if (!Std.isOfType(value, String)) return false;
		var text = StringTools.trim(cast value).toLowerCase();
		return text == 'function_continue' || text == 'function continue'
			|| text == 'continue' || text == CONTINUE.toLowerCase();
	}
}
