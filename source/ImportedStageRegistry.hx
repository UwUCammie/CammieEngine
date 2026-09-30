package;

import CompatScriptManifest.CompatScriptManifestData;

/**
 * Resolve an imported stage only from the song's selected Modding Plus or
 * Codename owner. A matched owner registry row stays authoritative even when
 * its script is missing or unsafe, so callers can block a foreign global
 * registry collision rather than silently loading another engine's stage.
 */
class ImportedStageRegistry {
	/**
	 * Resolve one safe flat song/stage id against its selected imported owner.
	 * `exists` receives concrete file paths (including their extensions);
	 * `script` in the returned object is extensionless for the caller's loader.
	 */
	public static function resolve(song:String, requested:String, exists:String->Bool,
		read:String->String, parse:String->Dynamic):Dynamic {
		var safeSong = safeFlatId(song);
		var safeRequested = safeFlatId(requested);
		// Validate both caller-controlled ids before touching any path or callback.
		if (safeSong == '' || safeRequested == '' || exists == null || read == null || parse == null)
			return null;

		var manifestPath = 'assets/data/' + safeSong.toLowerCase() + '/'
			+ CompatScriptManifest.FILE_NAME;
		var hasManifest = false;
		try hasManifest = exists(manifestPath) catch (_:Dynamic) return null;
		if (!hasManifest)
			return null;

		var manifest:CompatScriptManifestData = null;
		try manifest = CompatScriptManifest.parse(read(manifestPath)) catch (_:Dynamic) return null;
		if (manifest == null)
			return null;
		var owner = CompatScriptManifest.selectedRoot(manifest);
		if (owner == '')
			return null;
		var ownerEngine = '';
		for (root in CompatScriptManifest.rootsInPrecedence(manifest))
			if (root != null && root.path == owner) {
				ownerEngine = root.engine == null ? '' : StringTools.trim(root.engine).toLowerCase();
				break;
			}
		if (ownerEngine != ImportEngine.MODDING_PLUS.toLowerCase()
			&& ownerEngine != ImportEngine.CODENAME.toLowerCase())
			return null;

		var directory = owner + '/images/custom_stages/';
		var registryPath = directory + 'custom_stages.json';
		var registryExists = false;
		try registryExists = exists(registryPath) catch (_:Dynamic) return unavailable(safeRequested, '', directory, 'registry-unreadable');
		if (!registryExists) {
			registryPath = directory + 'custom_stages.jsonc';
			try registryExists = exists(registryPath) catch (_:Dynamic) return unavailable(safeRequested, '', directory, 'registry-unreadable');
		}
		if (!registryExists)
			return null;

		var registry:Dynamic = null;
		try {
			var raw = read(registryPath);
			registry = raw == null ? null : parse(raw);
		} catch (_:Dynamic) {
			return unavailable(safeRequested, '', directory, 'registry-invalid');
		}
		if (registry == null || Type.typeof(registry) != TObject)
			return unavailable(safeRequested, '', directory, 'registry-invalid');

		var keys:Array<String> = [];
		try keys = Reflect.fields(registry) catch (_:Dynamic) return unavailable(safeRequested, '', directory, 'registry-invalid');
		var registryName:Null<String> = null;
		for (key in keys)
			if (key == safeRequested) {
				registryName = key;
				break;
			}
		if (registryName == null) {
			var matches:Array<String> = [];
			for (key in keys)
				if (key.toLowerCase() == safeRequested.toLowerCase())
					matches.push(key);
			if (matches.length == 0)
				return null;
			if (matches.length > 1)
				return unavailable(safeRequested, '', directory, 'registry-key-ambiguous');
			registryName = matches[0];
		}

		var value:Dynamic = Reflect.field(registry, registryName);
		if (value == null || !Std.isOfType(value, String))
			return unavailable(registryName, '', directory, 'script-id-invalid');
		var script = StringTools.trim(Std.string(value));
		if (StringTools.endsWith(script.toLowerCase(), '.hscript'))
			script = script.substr(0, script.length - '.hscript'.length);
		script = safeFlatId(script);
		if (script == '')
			return unavailable(registryName, '', directory, 'script-id-invalid');

		var scriptPath = directory + script + '.hscript';
		var scriptExists = false;
		try scriptExists = exists(scriptPath) catch (_:Dynamic) return unavailable(registryName, script, directory, 'script-unavailable');
		if (!scriptExists)
			return unavailable(registryName, script, directory, 'script-unavailable');
		return {name:registryName, script:script, directory:directory,
			unavailable:false, reason:''};
	}

	static function unavailable(name:String, script:String, directory:String, reason:String):Dynamic {
		return {name:name, script:script, directory:directory,
			unavailable:true, reason:reason};
	}

	static function safeFlatId(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		if (clean == '' || StringTools.startsWith(clean, '/') || clean.indexOf('/') >= 0
			|| clean.indexOf('\\') >= 0 || clean.indexOf('..') >= 0
			|| clean.indexOf(':') >= 0)
			return '';
		return clean;
	}
}
