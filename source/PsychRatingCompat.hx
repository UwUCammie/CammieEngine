package;

/** Psych backend Rating compatibility without process-global ClientPrefs. */
@:keep
class PsychRatingCompat extends SourceRating {
	public function new(name:String) {
		super(name);

		try {
			var sourceWindow:Dynamic = Reflect.field(PsychClientPrefsCompat.data, name + 'Window');
			if (sourceWindow == null) hitWindow = null;
			else if (Std.isOfType(sourceWindow, Int) || Std.isOfType(sourceWindow, Float))
				hitWindow = cast sourceWindow;
			else
				hitWindow = 0;
		} catch (_:Dynamic) {
			// Psych's constructor starts at zero and leaves that value in place
			// when reading its preference field throws.
			hitWindow = 0;
		}

		// Psych's bare constructor does not call a name-based setup switch.
		ratingMod = 1;
		score = 350;
		noteSplash = true;
	}

	/** Psych's default list uses per-entry overrides after the bare constructor. */
	public static function loadDefault():Array<SourceRating> {
		var ratings:Array<SourceRating> = [new PsychRatingCompat('sick')];

		var good = new PsychRatingCompat('good');
		good.ratingMod = 0.67;
		good.score = 200;
		good.noteSplash = false;
		ratings.push(good);

		var bad = new PsychRatingCompat('bad');
		bad.ratingMod = 0.34;
		bad.score = 100;
		bad.noteSplash = false;
		ratings.push(bad);

		var shit = new PsychRatingCompat('shit');
		shit.ratingMod = 0;
		shit.score = 50;
		shit.noteSplash = false;
		ratings.push(shit);
		return ratings;
	}
}
