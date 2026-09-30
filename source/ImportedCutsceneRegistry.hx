package;

import CompatScriptManifest.CompatScriptManifestData;
using StringTools;

/** Resolve a legacy cutscene from the chart's selected import owner. */
class ImportedCutsceneRegistry {
	public static function resolve(songFolder:String, requested:String, exists:String->Bool,
		read:String->String, parse:String->Dynamic):Dynamic {
		var song = safeName(songFolder);
		var cutscene = safeName(requested);
		if (song == '' || cutscene == '' || exists == null || read == null || parse == null)
			return null;
		var manifestPath = 'assets/data/' + song.toLowerCase() + '/'
			+ CompatScriptManifest.FILE_NAME;
		if (!exists(manifestPath)) return null;
		var manifest:CompatScriptManifestData = null;
		try manifest = CompatScriptManifest.parse(read(manifestPath)) catch (_:Dynamic) return null;
		if (manifest == null) return null;
		var owner = CompatScriptManifest.selectedRoot(manifest);
		if (owner == '') return null;
		var selectedEngine = '';
		for (root in CompatScriptManifest.rootsInPrecedence(manifest))
			if (root != null && root.path == owner) {
				selectedEngine = root.engine == null ? '' : root.engine.trim().toLowerCase();
				break;
			}
		if (selectedEngine != ImportEngine.MODDING_PLUS.toLowerCase()) return null;
		var directory = owner + '/images/custom_cutscenes/';
		var registryPath = directory + 'cutscenes.json';
		if (!exists(registryPath))
			return unavailable(cutscene, '', directory, 'registry-unavailable');
		var registry:Dynamic = null;
		try registry = parse(read(registryPath)) catch (_:Dynamic)
			return unavailable(cutscene, '', directory, 'registry-invalid');
		if (registry == null || Type.typeof(registry) != TObject)
			return unavailable(cutscene, '', directory, 'registry-invalid');
		var key:String = null;
		for (candidate in Reflect.fields(registry))
			if (candidate == cutscene) { key = candidate; break; }
		if (key == null) {
			var matches:Array<String> = [];
			for (candidate in Reflect.fields(registry))
				if (candidate.toLowerCase() == cutscene.toLowerCase()) matches.push(candidate);
			if (matches.length != 1)
				return unavailable(cutscene, '', directory,
					matches.length == 0 ? 'cutscene-unregistered' : 'registry-key-ambiguous');
			key = matches[0];
		}
		var raw:Dynamic = Reflect.field(registry, key);
		if (!Std.isOfType(raw, String))
			return unavailable(key, '', directory, 'script-id-invalid');
		var script = StringTools.trim(cast raw);
		if (script.toLowerCase().endsWith('.hscript'))
			script = script.substr(0, script.length - '.hscript'.length);
		script = safeName(script);
		if (script == '') return unavailable(key, '', directory, 'script-id-invalid');
		if (!exists(directory + script + '.hscript'))
			return unavailable(key, script, directory, 'script-unavailable');
		return {name:key, script:script, directory:directory,
			unavailable:false, reason:''};
	}

	static function unavailable(name:String, script:String, directory:String, reason:String):Dynamic
		return {name:name, script:script, directory:directory,
			unavailable:true, reason:reason};

	static function safeName(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		if (clean == '' || clean.startsWith('/') || clean.indexOf('/') >= 0
			|| clean.indexOf('\\') >= 0 || clean.indexOf('..') >= 0
			|| clean.indexOf(':') >= 0)
			return '';
		return clean;
	}
}
