package;

/** Runtime duplicate cleanup for source note-miss callbacks. */
class SourceMissDuplicates {
	/** Psych removes matching live members when a player-owned note misses.
	 * Modern Nightmare Vision does not remove runtime siblings; historical NV
	 * uses matches() inside its live group traversal. */
	public static function select(note:Dynamic, candidates:Array<Dynamic>, nightmare:Bool):Array<Dynamic> {
		var duplicates:Array<Dynamic> = [];
		if (nightmare || note == null || candidates == null || note.mustPress != true) return duplicates;

		for (candidate in candidates) {
			// Match FlxGroup.forEachAlive: only extant, live members are visited.
			if (candidate == null || candidate == note || candidate.exists != true || candidate.alive != true) continue;
			if (matches(note, candidate, true)) duplicates.push(candidate);
		}
		return duplicates;
	}
	/** Shared source predicate; the caller supplies the family-specific ownership rule. */
	public static function matches(note:Dynamic, candidate:Dynamic, controlled:Bool):Bool {
		return controlled && note != null && candidate != null && candidate != note
			&& candidate.exists == true && candidate.alive == true
			&& note.noteData == candidate.noteData && note.isSustainNote == candidate.isSustainNote
			&& Math.abs(note.strumTime - candidate.strumTime) < 1;
	}

}
