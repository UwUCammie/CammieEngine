package;

/** The source dialect's exact Paths.sanitize spelling, shared with import metadata. */
class NightmareVisionSongNameCompat {
	public static function format(path:String):String {
		if (path == null) return '';
		return StringTools.trim(StringTools.replace(~/[^- a-zA-Z0-9..\/]+\//g.replace(path, ''), ' ', '-')).toLowerCase();
	}
}
