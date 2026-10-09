package;

/** Base/Psych-era library ordering, independent of the asset storage backend. */
class SourceLibraryPaths {
	public static function libraryPath(file:String, library:String):String
		return library == 'preload' || library == 'default' ? 'assets/' + file
			: forcedPath(file, library);

	public static function forcedPath(file:String, library:String):String
		return library + ':assets/' + library + '/' + file;

	public static function select(file:String, currentLevel:String, library:Null<String>, exists:String->Bool):String {
		if (library != null) return libraryPath(file, library);
		if (currentLevel != null) {
			if (currentLevel != 'shared') {
				var level = forcedPath(file, currentLevel);
				if (exists(level)) return level;
			}
			var shared = forcedPath(file, 'shared');
			if (exists(shared)) return shared;
		}
		return 'assets/' + file;
	}
}
