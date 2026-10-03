package;

/** Select the HUD asset contract from the selected engine-core package. The
	older NMV runtime shipped rating and combo art at the image root and shared
	the script-facing ratingPrefix/ratingSuffix; newer cores split those paths. */
@:keep
class NightmareVisionHUDProfile {
	public final name:String;
	public final usesSharedRatingPrefix:Bool;
	public final comboPrefix:String;
	public final ratingsPrefix:String;
	public final countdownPrefix:String;
	public final uiPrefix:String;
	public final detected:Bool;
	public final splitDigitCount:Int;
	public final legacyDigitCount:Int;

	function new(name:String, sharedPrefix:Bool, combo:String, ratings:String, countdown:String, ui:String,
		detected:Bool, splitCount:Int, legacyCount:Int) {
		this.name = name;
		usesSharedRatingPrefix = sharedPrefix;
		comboPrefix = combo;
		ratingsPrefix = ratings;
		countdownPrefix = countdown;
		uiPrefix = ui;
		this.detected = detected;
		splitDigitCount = splitCount;
		legacyDigitCount = legacyCount;
	}

	/** Require a complete digit set before selecting a layout. This is a
		capability check on the selected owner dependency, not a path fallback. */
	public static function detect(paths:NightmareVisionPaths):NightmareVisionHUDProfile {
		if (paths == null) throw '[nightmare-vision-hud-profile] Missing owner paths';

		var splitCount = countDigits(paths, 'UI/combo/');
		var legacyCount = countDigits(paths, '');

		// The complete split namespace identifies the newer API even when a core
		// also retains the old root-level files for unrelated compatibility.
		if (splitCount == 10)
			return new NightmareVisionHUDProfile('split', false, 'UI/combo/', 'UI/ratings/',
				'UI/countdown/', 'UI/', true, splitCount, legacyCount);
		if (legacyCount == 10)
			return new NightmareVisionHUDProfile('legacy-shared', true, '', '', 'UI/countdown/', 'UI/',
				true, splitCount, legacyCount);

		// Some selected cores do not ship either complete default set (for
		// example, a custom HUD supplies its own assets). Keep the current split
		// defaults and exact-path errors; partial flat files never imply legacy.
		return new NightmareVisionHUDProfile('unknown-split-default', false, 'UI/combo/', 'UI/ratings/',
			'UI/countdown/', 'UI/', false, splitCount, legacyCount);
	}

	static function countDigits(paths:NightmareVisionPaths, prefix:String):Int {
		var present = 0;
		for (digit in 0...10) {
			var relative = 'images/' + prefix + 'num' + digit + '.png';
			if (paths.exists(paths.getCorePath(relative))) present++;
		}
		return present;
	}
}
