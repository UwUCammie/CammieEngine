package;

/** Shared Lua-scalar/HScript-live-Note ABI for Psych note callbacks. */
class PsychNoteCallbacks {
	/**
		Dispatch one real-note callback in Psych order. The caller supplies the
		lane value because donors differ slightly in how they normalize it
		(goodNoteHit rounds, opponentNoteHit and noteMiss do not).
	*/
	public static function dispatch(callback:String, note:Dynamic, groupSlot:Int, lane:Dynamic,
		broadcast:(String, Array<Dynamic>, String)->Dynamic,
		?luaArgs:Array<Dynamic>):Dynamic {
		if (broadcast == null || note == null) return null;

		// noteType may be a script-facing property backed by an authored-kind
		// accessor. Read it as a property so callers see the same value as Psych.
		var preparedLuaArgs = luaArgs == null ? [groupSlot, lane,
			Reflect.getProperty(note, 'noteType'), Reflect.getProperty(note, 'isSustainNote')] : luaArgs;
		var result = broadcast(callback, preparedLuaArgs, 'Luas');
		if (result == ScriptCallbackResult.STOP || result == ScriptCallbackResult.STOP_HSCRIPT
			|| result == ScriptCallbackResult.STOP_ALL) return result;

		// STOP_LUA only stops the Lua family. Continue, null and ordinary values
		// all permit the live Note callback in HScript.
		return broadcast(callback, [note], 'HScript');
	}
}
