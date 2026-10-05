package;

using StringTools;

/** Transient chart-editor handoff state isolated by Psych import owner. */
@:keep
class PsychOwnerChartingMode {
	static inline var OWNER_PREFIX:String = 'assets/imported_mods/';
	static var chartingModes:Map<String, Bool> = new Map();

	/** Missing, invalid, native, and NV owners all read as false. */
	@:keep public static function get(ownerRoot:String):Bool {
		var key = ownerKey(ownerRoot);
		return key != '' && chartingModes.get(key) == true;
	}

	/** A false value is represented by absence, keeping the default false. */
	@:keep public static function set(ownerRoot:String, value:Bool):Void {
		var key = ownerKey(ownerRoot);
		if (key == '') return;
		if (value) chartingModes.set(key, true);
		else chartingModes.remove(key);
	}

	@:keep public static function clear(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key != '') chartingModes.remove(key);
	}

	static function ownerKey(ownerRoot:String):String {
		if (ownerRoot == null) return '';
		var path = StringTools.replace(StringTools.trim(ownerRoot), '\\', '/');
		while (path.indexOf('//') >= 0) path = StringTools.replace(path, '//', '/');
		while (path.endsWith('/')) path = path.substr(0, path.length - 1);
		if (!path.startsWith(OWNER_PREFIX) || path.length <= OWNER_PREFIX.length
			|| path.indexOf(String.fromCharCode(0)) >= 0 || path.indexOf(':') >= 0)
			return '';
		for (part in path.split('/'))
			if (part == '.' || part == '..') return '';
		#if windows
		path = path.toLowerCase();
		#end
		return path;
	}
}
