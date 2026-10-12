/** Resolve the concrete source selected by the legacy extensionless loader. */
class CompatScriptOrigin {
	public static function resolve(path:String, nativeExtensions:Array<String>, exists:String->Bool):String {
		if (path == null || exists(path)) return path;
		for (extension in nativeExtensions) {
			var candidate = path + '.' + extension;
			if (exists(candidate)) return candidate;
		}
		var luaPath = StringTools.endsWith(path.toLowerCase(), '.hscript')
			? path.substr(0, path.length - '.hscript'.length) + '.lua' : path + '.lua';
		return exists(luaPath) ? luaPath : path;
	}
}
