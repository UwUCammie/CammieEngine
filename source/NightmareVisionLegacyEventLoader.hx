package;

/** Historical discovery snapshots extensions, then checks mod/core for each one. */
class NightmareVisionLegacyEventLoader {
	public static function select(name:String, extensions:Array<String>, mod:String->String,
		core:String->String, exists:String->Bool):NightmareVisionScriptDiscovery.NightmareVisionScriptEntry {
		var exts = ['lua'];
		for (extension in extensions) exts.push(extension);
		for (extension in exts) {
			var relative = 'custom_events/' + name + '.' + extension;
			for (path in [mod(relative), core(relative)]) if (exists(path))
				return {scope:'event', name:name, path:path, relative:path};
		}
		return null;
	}
}
