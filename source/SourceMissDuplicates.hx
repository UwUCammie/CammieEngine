package;

/** Runtime duplicate cleanup for source note-miss callbacks. */
class SourceMissDuplicates {
	/** Psych removes matching live members when a player-owned note misses.
	 * Nightmare Vision handles duplicate chart rows during chart normalization
	 * and does not remove sibling notes from its runtime miss callback. */
	public static function select(note:Dynamic, candidates:Array<Dynamic>, nightmare:Bool):Array<Dynamic> {
		var duplicates:Array<Dynamic> = [];
		if (nightmare || note == null || candidates == null || note.mustPress != true) return duplicates;

		for (candidate in candidates) {
			// Match FlxGroup.forEachAlive: only extant, live members are visited.
			if (candidate == null || candidate == note || candidate.exists != true || candidate.alive != true) continue;
			if (note.noteData == candidate.noteData
				&& note.isSustainNote == candidate.isSustainNote
				&& Math.abs(note.strumTime - candidate.strumTime) < 1)
				duplicates.push(candidate);
		}
		return duplicates;
	}
}
