package;

/** Old name for the split-vocal resolver, which Psych songs now share. */
class NightmareVisionVocalRole {
	public static function resolve(stemId:Dynamic, authoredRole:Dynamic):String {
		return SourceVocalRole.resolve(stemId, authoredRole);
	}
}
