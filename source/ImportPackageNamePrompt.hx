package;

typedef ImportPackageNameRequest = {
	var root:String;
	var suggestedName:String;
}

/** Shared planning and validation for the interactive package-label prompt.
 * A user label is also the durable fallback package identity when the source
 * has no authored ID; it is never used as a chart folder name. */
class ImportPackageNamePrompt {
	public static function normalizeRoot(root:String):String {
		return ImportSettings.normalizeSourcePath(root);
	}

	/** Match the importer's platform-specific path identity rules. */
	public static function rootKey(root:String):String {
		var normalized = normalizeRoot(root);
		#if windows
		return normalized.toLowerCase();
	#else
		return normalized;
		#end
	}

	/** Request a name only for an actual song candidate selected by the scan,
	 * and only when the source package did not author one. */
	public static function collectUnnamedRoots(songs:Array<Dynamic>):Array<ImportPackageNameRequest> {
		var requests:Array<ImportPackageNameRequest> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		if (songs == null)
			return requests;
		for (song in songs) {
			if (song == null || Reflect.field(song, 'willImport') != true)
				continue;
			var rawRoot:Dynamic = Reflect.field(song, 'source');
			if (rawRoot == null)
				continue;
			var root = normalizeRoot(Std.string(rawRoot));
			var key = rootKey(root);
			if (root == '' || key == '' || seen.exists(key))
				continue;
			seen.set(key, true);
			var info = ImportSongOwnership.displayNameInfo(root);
			if (info == null || info.authored)
				continue;
			requests.push({root:root, suggestedName:info.name});
		}
		return requests;
	}

	/** Freeplay labels are text, never path components. Reject only blank,
	 * oversized, or multiline/control input so ordinary punctuation and Unicode
	 * remain available to mod authors. */
	public static function validName(value:String):Bool {
		if (value == null)
			return false;
		var name = StringTools.trim(value);
		if (name == '' || name.length > 80)
			return false;
		for (index in 0...name.length) {
			var code = name.charCodeAt(index);
			if (code == null || code < 32 || code == 127)
				return false;
		}
		return true;
	}

	/** Build an immutable-at-the-call-site map for ImportWorkflow. */
	public static function createOverrides(requests:Array<ImportPackageNameRequest>,
		values:Array<String>):Null<Map<String, String>> {
		if (requests == null || values == null || requests.length != values.length)
			return null;
		var result:Map<String, String> = new Map<String, String>();
		for (index in 0...requests.length) {
			var request = requests[index];
			var name = StringTools.trim(values[index] == null ? '' : values[index]);
			if (request == null || request.root == null || normalizeRoot(request.root) == '' || !validName(name))
				return null;
			result.set(rootKey(request.root), name);
		}
		return result;
	}
}
