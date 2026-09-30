package;

/**
 * Engine-neutral state and note-chain helpers for the pooled V-Slice cover.
 * Keeping these operations free of Flixel makes the importer/runtime contract
 * executable in the lightweight regression harness as well as in the game.
 */
typedef NoteHoldCoverPoolState = {
	var alive:Bool;
	var exists:Bool;
	var active:Bool;
}

class NoteHoldCoverCompat {
	/** FlxBasic.kill() clears exists; every pooled replay must restore all flags. */
	public static function activate():NoteHoldCoverPoolState {
		return {alive: true, exists: true, active: true};
	}

	/** Resolve an HXC note wrapper without exposing donor objects to gameplay. */
	public static function unwrap(note:Dynamic):Dynamic {
		if (note == null)
			return null;
		if (Reflect.hasField(note, 'nativeNote')) {
			var nativeNote = Reflect.field(note, 'nativeNote');
			return nativeNote == null ? note : nativeNote;
		}
		return note;
	}

	/** Resolve any generated sustain segment to its authored hold head. */
	public static function resolveHead(note:Dynamic):Dynamic {
		var current = unwrap(note);
		var guard = 0;
		while (current != null && guard++ < 1024
			&& Reflect.field(current, 'isSustainNote') == true) {
			var previous = Reflect.field(current, 'prevNote');
			if (previous == null || previous == current)
				break;
			current = unwrap(previous);
		}
		return current;
	}

	/** Shared end predicate for authored duration and forced miss/cancel ends. */
	public static function shouldEnd(endTime:Float, songPosition:Float, forced:Bool = false):Bool {
		return forced || (!Math.isNaN(endTime) && endTime != Math.POSITIVE_INFINITY
			&& songPosition >= endTime);
	}
}
