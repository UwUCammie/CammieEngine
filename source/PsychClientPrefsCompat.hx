package;

/** Read-only Psych preference view for owner-scoped source modules.
	Values with engine equivalents follow the current options. Psych's data
	object stays detached so imported code cannot overwrite the user's options
	by mutating ClientPrefs.data.
*/
class PsychClientPrefsCompat {
	/** Exact nested fields advertised to CodenameScriptClassLoader's narrow
	 * StringTools receiver proof. */
	public static final __hscriptStringFieldPaths:Array<String> = [
		'data.noteSkin', 'defaultData.noteSkin'
	];

	public static var data(get, never):Dynamic;
	public static var defaultData(get, never):Dynamic;

	static function get_data():Dynamic {
		// Resolve lazily so standalone owner-class fixtures can compile this
		// facade without importing the whole game's options and asset graph.
		var options:Dynamic = null;
		var optionClass = Type.resolveClass('OptionsHandler');
		if (optionClass != null) {
			try options = Reflect.getProperty(optionClass, 'options') catch (_:Dynamic) {}
		}
		return {
			noteSkin:'Default',
			// This engine has no lowQuality preference or matching quality mode.
			lowQuality:false,
			antialiasing:readBool(options, 'antialiasing', true),
			shaders:readBool(options, 'gameplayShaders', true)
		};
	}

	static function get_defaultData():Dynamic {
		return {noteSkin:'Default', lowQuality:false, antialiasing:true, shaders:true};
	}

	static function readBool(options:Dynamic, field:String, fallback:Bool):Bool {
		var value = options == null ? null : Reflect.field(options, field);
		return Std.isOfType(value, Bool) ? cast value : fallback;
	}

	/** Bind only the source class names used by Psych's global imports. */
	public static function addBindings(bindings:Map<String, Dynamic>):Void {
		if (bindings == null) return;
		bindings.set('ClientPrefs', PsychClientPrefsCompat);
		bindings.set('backend.ClientPrefs', PsychClientPrefsCompat);
	}
}
