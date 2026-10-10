package;

/** Static source bridge to the selected Psych owner's mutable preferences.
	Owner values live separately from native options; standalone source tools
	use the small detached fallback without loading the entire gameplay graph.
*/
class PsychClientPrefsCompat {
	/** Exact nested fields advertised to CodenameScriptClassLoader's narrow
	 * StringTools receiver proof. */
	public static final __hscriptStringFieldPaths:Array<String> = [
		'data.noteSkin', 'defaultData.noteSkin'
	];

	public static var data(get, set):Dynamic;
	public static var defaultData(get, set):Dynamic;
	static var fallbackData:Dynamic;
	static var fallbackDefaultData:Dynamic;

	static function currentOwner():Dynamic {
		var playClass = Type.resolveClass('PlayState');
		if (playClass == null) return null;
		var play:Dynamic = Reflect.getProperty(playClass, 'instance');
		return play == null ? null : Reflect.getProperty(play, 'psychClientPrefs');
	}

	static function get_data():Dynamic {
		var owner = currentOwner();
		if (owner != null) return Reflect.getProperty(owner, 'data');
		if (fallbackData != null) return fallbackData;
		// Resolve lazily so standalone owner-class fixtures can compile this
		// facade without importing the whole game's options and asset graph.
		var options:Dynamic = null;
		var optionClass = Type.resolveClass('OptionsHandler');
		if (optionClass != null) {
			try options = Reflect.getProperty(optionClass, 'options') catch (_:Dynamic) {}
		}
		fallbackData = {
			noteSkin:'Default', noteOffset:0.0,
			ratingOffset:0.0, sickWindow:45.0, goodWindow:90.0, badWindow:135.0, safeFrames:10.0,
			// This engine has no lowQuality preference or matching quality mode.
			lowQuality:false,
			scoreZoom:true,
			antialiasing:readBool(options, 'antialiasing', true),
			shaders:readBool(options, 'gameplayShaders', true)
		};
		return fallbackData;
	}

	static function set_data(value:Dynamic):Dynamic {
		var owner = currentOwner();
		if (owner != null) Reflect.setProperty(owner, 'data', value);
		else fallbackData = value;
		return value;
	}

	static function get_defaultData():Dynamic {
		var owner = currentOwner();
		if (owner != null) return Reflect.getProperty(owner, 'defaultData');
		if (fallbackDefaultData == null)
			fallbackDefaultData = {noteSkin:'Default', noteOffset:0.0, ratingOffset:0.0, sickWindow:45.0, goodWindow:90.0, badWindow:135.0, safeFrames:10.0, lowQuality:false, scoreZoom:true, antialiasing:true, shaders:true};
		return fallbackDefaultData;
	}

	static function set_defaultData(value:Dynamic):Dynamic {
		var owner = currentOwner();
		if (owner != null) Reflect.setProperty(owner, 'defaultData', value);
		else fallbackDefaultData = value;
		return value;
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
