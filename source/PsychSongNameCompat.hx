package;

/** Psych's Paths.formatToSongPath convention for songName comparisons. */
class PsychSongNameCompat {
	public static function format(path:String):String {
		if (path == null) return '';
		var invalid = ~/[~&;:<>#\s]/g;
		var hidden = ~/[.,'"%?!]/g;
		return StringTools.trim(hidden.replace(invalid.replace(path, '-'), '')).toLowerCase();
	}
}
