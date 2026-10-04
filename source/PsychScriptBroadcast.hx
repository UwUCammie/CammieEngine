package;

/** Pure Psych callback ordering and result semantics for caller-owned scopes. */
class PsychScriptBroadcast {
	public static function callOnScripts<T>(luaScopes:Array<T>, hscriptScopes:Array<T>,
		functionName:String, args:Array<Dynamic>, scopeName:T->String, isClosed:T->Bool,
		invokeLua:(T, String, Array<Dynamic>)->Dynamic,
		invokeHScript:(T, String, Array<Dynamic>)->Dynamic,
		?removeClosedLua:T->Void, ?ignoreStops:Bool = false,
		?exclusions:Array<String>, ?excludeValues:Array<Dynamic>):Dynamic {
		if (exclusions == null) exclusions = [];
		if (excludeValues == null) excludeValues = [ScriptCallbackResult.CONTINUE];
		if (args == null) args = [];

		var result = callOnLuas(luaScopes, functionName, args, scopeName, isClosed,
			invokeLua, removeClosedLua, ignoreStops, exclusions, excludeValues);
		if (result == null || excludeValues.contains(result))
			result = callOnHScript(hscriptScopes, functionName, args, scopeName,
				invokeHScript, ignoreStops, exclusions, excludeValues);
		return result;
	}

	public static function callOnLuas<T>(scopes:Array<T>, functionName:String,
		args:Array<Dynamic>, scopeName:T->String, isClosed:T->Bool,
		invoke:(T, String, Array<Dynamic>)->Dynamic,
		?removeClosed:T->Void, ?ignoreStops:Bool = false,
		?exclusions:Array<String>, ?excludeValues:Array<Dynamic>):Dynamic {
		var returnValue:Dynamic = ScriptCallbackResult.CONTINUE;
		if (args == null) args = [];
		if (exclusions == null) exclusions = [];
		if (excludeValues == null) excludeValues = [ScriptCallbackResult.CONTINUE];
		if (scopes == null) return returnValue;

		var toRemove:Array<T> = [];
		for (scope in scopes) {
			if (scope == null) continue;
			if (isClosed(scope)) {
				toRemove.push(scope);
				continue;
			}
			if (exclusions.contains(scopeName(scope))) continue;

			// Sentinel comparisons must not infer String and coerce numeric,
			// Boolean or object callback returns on native targets.
			var value:Dynamic = invoke(scope, functionName, args);
			if ((value == ScriptCallbackResult.STOP_LUA || value == ScriptCallbackResult.STOP_ALL)
				&& !excludeValues.contains(value) && !ignoreStops) {
				returnValue = value;
				break;
			}
			if (value != null && !excludeValues.contains(value)) returnValue = value;
			if (isClosed(scope)) toRemove.push(scope);
		}

		for (scope in toRemove) {
			if (removeClosed != null) removeClosed(scope);
			else scopes.remove(scope);
		}
		return returnValue;
	}

	public static function callOnHScript<T>(scopes:Array<T>, functionName:String,
		args:Array<Dynamic>, scopeName:T->String,
		invoke:(T, String, Array<Dynamic>)->Dynamic,
		?ignoreStops:Bool = false, ?exclusions:Array<String>,
		?excludeValues:Array<Dynamic>):Dynamic {
		var returnValue:Dynamic = ScriptCallbackResult.CONTINUE;
		if (args == null) args = [];
		if (exclusions == null) exclusions = [];
		if (excludeValues == null) excludeValues = [];
		// Psych HScript always ignores Function_Continue, including when a caller
		// supplies a custom exclusion list. The source implementation appends it.
		excludeValues.push(ScriptCallbackResult.CONTINUE);
		if (scopes == null) return returnValue;

		for (scope in scopes) {
			if (scope == null || exclusions.contains(scopeName(scope))) continue;
			var value:Dynamic = invoke(scope, functionName, args);
			if ((value == ScriptCallbackResult.STOP_HSCRIPT || value == ScriptCallbackResult.STOP_ALL)
				&& !excludeValues.contains(value) && !ignoreStops) {
				returnValue = value;
				break;
			}
			if (value != null && !excludeValues.contains(value)) returnValue = value;
		}
		return returnValue;
	}
}
