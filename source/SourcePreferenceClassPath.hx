package;

/**
	Psych 0.6 kept its preferences as flat `ClientPrefs` statics, 0.7 moved them
	under `data`, and Nightmare Vision reads them flat again. Every class
	reflection route resolves ClientPrefs to the chart owner's live preference
	object, so each route maps the authored path the same way before walking it.
**/
class SourcePreferenceClassPath {
	/** `prefsFor` gives the owner preference object for a class name (null for
	 * any other class); `pathFor` gives the dialect path inside that object. */
	public static function map(type:Dynamic, path:Dynamic, prefsFor:Dynamic->Dynamic,
		pathFor:Dynamic->Dynamic->String):Dynamic {
		var prefs = prefsFor(type);
		return prefs == null ? path : pathFor(prefs, path);
	}
}
