package;

/** Versioned file inventory shared by the game and the standalone helper. */
class WebsiteUpdateManifest {
	public static inline var ROOT:String = 'https://uwucammie.com/cammie-engine/';
	public static inline var INSTALLED:String = 'RELEASE_FILES.json';

	public static function parse(body:String, tag:String):Array<{path:String, sha256:String, size:Int}> {
		var data:Dynamic = haxe.Json.parse(body);
		if (data == null || data.schema != 1 || data.platform != 'windows-x64' || data.tag != tag
			|| !Std.isOfType(data.files, Array) || data.files.length == 0 || data.files.length > 100000)
			throw 'Invalid website release manifest.';
		var result:Array<{path:String, sha256:String, size:Int}> = [];
		var seen:Map<String, Bool> = new Map();
		var directories:Map<String, Bool> = new Map();
		for (entry in (cast data.files:Array<Dynamic>)) {
			if (entry == null || !Std.isOfType(entry.path, String) || !safePath(entry.path)
				|| !Std.isOfType(entry.sha256, String) || !~/^[0-9a-f]{64}$/.match(entry.sha256)
				|| !Std.isOfType(entry.size, Int) || entry.size < 0)
				throw 'Invalid website release file.';
			var path:String = entry.path;
			var key = path.toLowerCase();
			if (key == INSTALLED.toLowerCase() || seen.exists(key) || directories.exists(key))
				throw 'Duplicate website release path.';
			var parts = key.split('/');
			for (index in 1...parts.length) {
				var parent = parts.slice(0, index).join('/');
				if (seen.exists(parent)) throw 'Website release file/directory collision.';
				directories.set(parent, true);
			}
			seen.set(key, true);
			result.push({path:path, sha256:entry.sha256, size:entry.size});
		}
		for (required in ['Funkin.exe', 'lime.ndll', 'CammieUpdateHelper.exe', 'RELEASE_TAG', 'BUNDLED_ASSETS.json'])
			if (!seen.exists(required.toLowerCase())) throw 'Website release is missing ' + required;
		return result;
	}

	public static function safePath(path:String):Bool {
		if (path == null || path == '' || path.indexOf('\\') >= 0 || path.indexOf(':') >= 0) return false;
		for (part in path.split('/')) {
			if (part == '' || part == '.' || part == '..' || StringTools.endsWith(part, '.')
				|| StringTools.endsWith(part, ' ') || ~/[<>"|?*\x00-\x1f\x7f]/.match(part)
				|| ~/^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)/i.match(part)) return false;
		}
		return true;
	}

	public static function releaseRoot(tag:String):String {
		if (tag == null || !~/^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/.match(tag))
			throw 'Invalid website release tag.';
		return ROOT + 'releases/' + tag + '/';
	}
}
