package;

/** Pure Psych callback ordering and result semantics for caller-owned scopes. */
class PsychScriptBroadcast {
	// Engine dispatches run per note hit and spawn, almost always without
	// custom lists. These defaults are only read, never handed to a caller or
	// mutated, so one shared copy replaces three small arrays per broadcast.
	static final NO_EXCLUSIONS:Array<String> = [];
	static final CONTINUE_ONLY:Array<Dynamic> = [ScriptCallbackResult.CONTINUE];

	public static function callOnScripts<T>(luaScopes:Array<T>, hscriptScopes:Array<T>,
		functionName:String, args:Array<Dynamic>, scopeName:T->String, isClosed:T->Bool,
		invokeLua:(T, String, Array<Dynamic>)->Dynamic,
		invokeHScript:(T, String, Array<Dynamic>)->Dynamic,
		?removeClosedLua:T->Void, ?ignoreStops:Bool = false,
		?exclusions:Array<String>, ?excludeValues:Array<Dynamic>):Dynamic {
		if (args == null) args = [];

		var result = callOnLuas(luaScopes, functionName, args, scopeName, isClosed,
			invokeLua, removeClosedLua, ignoreStops, exclusions, excludeValues);
		// A null list means Continue only; callOnHScript appends Continue to a
		// caller's list itself, so the default is passed on as null.
		if (result == null || (excludeValues == null ? CONTINUE_ONLY : excludeValues).contains(result))
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
		if (exclusions == null) exclusions = NO_EXCLUSIONS;
		if (excludeValues == null) excludeValues = CONTINUE_ONLY;
		if (scopes == null) return returnValue;

		// Closed scopes are rare; allocate the removal list only when one appears.
		var toRemove:Array<T> = null;
		for (scope in scopes) {
			if (scope == null) continue;
			if (isClosed(scope)) {
				if (toRemove == null) toRemove = [];
				toRemove.push(scope);
				continue;
			}
			if (exclusions.length > 0 && exclusions.contains(scopeName(scope))) continue;

			// Sentinel comparisons must not infer String and coerce numeric,
			// Boolean or object callback returns on native targets.
			var value:Dynamic = invoke(scope, functionName, args);
			if ((value == ScriptCallbackResult.STOP_LUA || value == ScriptCallbackResult.STOP_ALL)
				&& !excludeValues.contains(value) && !ignoreStops) {
				returnValue = value;
				break;
			}
			if (value != null && !excludeValues.contains(value)) returnValue = value;
			if (isClosed(scope)) {
				if (toRemove == null) toRemove = [];
				toRemove.push(scope);
			}
		}

		if (toRemove != null) for (scope in toRemove) {
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
		if (exclusions == null) exclusions = NO_EXCLUSIONS;
		// Psych HScript always ignores Function_Continue, including when a caller
		// supplies a custom exclusion list. The source implementation appends it.
		// Without a list that leaves exactly Continue, the shared default.
		if (excludeValues == null) excludeValues = CONTINUE_ONLY;
		else excludeValues.push(ScriptCallbackResult.CONTINUE);
		if (scopes == null) return returnValue;

		for (scope in scopes) {
			if (scope == null || (exclusions.length > 0 && exclusions.contains(scopeName(scope)))) continue;
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
