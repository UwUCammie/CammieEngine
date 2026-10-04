package;

/** Note selection rules shared by source input adapters. */
class SourceInputNotes {
	/** Psych selects hittable heads first, then normal-priority notes before
	 * low-priority notes, with each priority group ordered by strum time. */
	public static function psych<T>(notes:Array<T>, accepts:T->Bool, isSustain:T->Bool,
		isLift:T->Bool, lowPriority:T->Bool, time:T->Float):Array<T> {
		var result:Array<T> = [];
		if (notes == null) return result;
		for (note in notes) {
			if (note == null || !accepts(note) || isSustain(note) || isLift(note)) continue;
			result.push(note);
		}
		result.sort(function(a:T, b:T):Int {
			var aLow = lowPriority(a);
			var bLow = lowPriority(b);
			if (aLow != bLow) return aLow ? 1 : -1;
			var aTime = time(a);
			var bTime = time(b);
			return aTime < bTime ? -1 : (aTime > bTime ? 1 : 0);
		});
		return result;
	}

	/** Reproduce the donor scan: a higher priority replaces the top candidate,
	 * and any candidate at an equal or lower priority replaces it when earlier.
	 * Sustains only mark lane occupancy and never become the selected top note. */
	public static function nightmareVision<T>(notes:Array<T>, accepts:T->Bool,
		isSustain:T->Bool, priority:T->Int, time:T->Float):{var top:Null<T>; var hasSustain:Bool;} {
		var top:Null<T> = null;
		var hasSustain = false;
		if (notes == null) return {top:top, hasSustain:hasSustain};
		for (note in notes) {
			if (note == null || !accepts(note)) continue;
			if (isSustain(note)) {
				hasSustain = true;
				continue;
			}
			var higherPriority = top == null || priority(note) > priority(top);
			if (higherPriority || (!higherPriority && time(note) < time(top))) top = note;
		}
		return {top:top, hasSustain:hasSustain};
	}
}
