package;

/** Psych note-miss callback arguments and Lua/HScript stop handling. */
class PsychMissCallbacks {
	public static function dispatch(note:Dynamic, direction:Int, groupSlot:Int,
		broadcast:(String, Array<Dynamic>, String)->Dynamic):Void {
		if (broadcast == null) return;

		if (note == null) {
			broadcast('noteMissPress', [direction], 'Scripts');
			return;
		}

		// Keep the miss-specific Lua lane ABI intact, then share the same family
		// stop handling and live-Note HScript ABI as good/opponent note hits.
		PsychNoteCallbacks.dispatch('noteMiss', note, groupSlot,
			Reflect.getProperty(note, 'noteData'), broadcast);
	}
}
