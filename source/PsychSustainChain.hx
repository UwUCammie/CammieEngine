package;

/** The Psych GH-sustain miss-chain side effects isolated from PlayState. */
@:keep
class PsychSustainChain {
	/** Match Psych's extra input restriction for sustain notes. */
	public static function canHitSustain(note:Dynamic, enabled:Bool):Bool {
		if (!enabled) return true;
		if (note == null || Reflect.field(note, 'isSustainNote') != true) return note != null;
		var parent:Dynamic = Reflect.field(note, 'parent');
		return parent != null && Reflect.field(parent, 'wasGoodHit') == true;
	}

	/**
	 * Apply the GH-sustain part of Psych's noteMissCommon. False means the
	 * donor returns immediately and must skip all ordinary miss accounting.
	 */
	public static function prepareMiss(note:Dynamic, enabled:Bool):Bool {
		if (!enabled || note == null) return true;

		var parent:Dynamic = Reflect.field(note, 'parent');
		if (parent == null) {
			var tail:Array<Dynamic> = noteTail(note);
			if (tail.length > 0) {
				Reflect.setField(note, 'alpha', 0.35);
				for (child in tail) {
					if (child == null) continue;
					Reflect.setField(child, 'alpha', Reflect.field(note, 'alpha'));
					Reflect.setField(child, 'missed', true);
					Reflect.setProperty(child, 'canBeHit', false);
					Reflect.setField(child, 'ignoreNote', true);
					Reflect.setField(child, 'tooLate', true);
				}
				Reflect.setField(note, 'missed', true);
				Reflect.setProperty(note, 'canBeHit', false);
			}

			// This early return is present even when the head had no tail.
			if (Reflect.field(note, 'missed') == true) return false;
		}

		if (parent != null && Reflect.field(note, 'isSustainNote') == true) {
			if (Reflect.field(note, 'missed') == true) return false;
			var parentTail:Array<Dynamic> = noteTail(parent);
			if (Reflect.field(parent, 'wasGoodHit') == true && parentTail.length > 0) {
				for (sibling in parentTail) {
					if (sibling == null || sibling == note) continue;
					Reflect.setField(sibling, 'missed', true);
					Reflect.setProperty(sibling, 'canBeHit', false);
					Reflect.setField(sibling, 'ignoreNote', true);
					Reflect.setField(sibling, 'tooLate', true);
				}
			}
		}
		return true;
	}

	static function noteTail(note:Dynamic):Array<Dynamic> {
		var tail:Dynamic = Reflect.field(note, 'tail');
		return tail != null && Std.isOfType(tail, Array) ? cast tail : [];
	}
}
