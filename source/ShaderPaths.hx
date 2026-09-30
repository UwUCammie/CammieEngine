package;

import haxe.io.Path;

using StringTools;

class ShaderPaths {
	/**
		Resolve a shader name against the active compatibility roots first.

		Foreign V-Slice trees are copied below the destination-only manifest
		namespace.  Keeping those roots in the lookup makes two imported mods
		with the same `vignette.frag` (or any other shader name) independent;
		the ordinary assets/shaders fallback remains for native/legacy content.
	*/
	public static function resolve(name:String, ?compatRoots:Array<String>, ?allowNativeFallback:Bool = true):Null<String> {
		if (name == null || StringTools.trim(name) == '')
			return null;
		var raw = Path.normalize(StringTools.replace(StringTools.trim(name), '\\', '/'));
		var relative = raw;
		if (StringTools.startsWith(relative.toLowerCase(), 'assets/'))
			relative = relative.substr('assets/'.length);
		if (StringTools.startsWith(relative.toLowerCase(), 'shaders/'))
			relative = relative.substr('shaders/'.length);
		if (!safeRelative(relative))
			return null;
		if (Path.extension(relative).toLowerCase() != 'frag')
			relative += '.frag';

		// A manifest root is already a destination-local `assets/imported_mods/*`
		// directory. Search its direct shader tree and its legacy shared tree,
		// never the donor's absolute path.
		if (compatRoots != null)
			for (root in compatRoots) {
				if (root == null || StringTools.trim(root) == '')
					continue;
				var cleanRoot = Path.normalize(StringTools.replace(StringTools.trim(root), '\\', '/'));
				if (!safeRoot(cleanRoot))
					continue;
				for (candidate in [
					Path.join([cleanRoot, 'shaders', relative]),
					Path.join([cleanRoot, 'shared', 'shaders', relative])
				])
					if (FNFAssets.exists(candidate))
						return candidate;
			}

		if (!allowNativeFallback)
			return null;
		var path = Path.normalize(raw);
		if (!StringTools.startsWith(path.toLowerCase(), 'assets/'))
			path = 'assets/shaders/' + relative;
		else if (Path.extension(path).toLowerCase() != 'frag')
			path += '.frag';
		if (FNFAssets.exists(path))
			return path;
		// Older imports flattened mod-specific shader folders.
		var flat = 'assets/shaders/' + Path.withoutDirectory(path);
		return FNFAssets.exists(flat) ? flat : null;
	}

	static function safeRelative(value:String):Bool {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf(':') >= 0)
			return false;
		for (part in value.split('/'))
			if (part == '' || part == '..')
				return false;
		return true;
	}

	static function safeRoot(value:String):Bool {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf(':') >= 0)
			return false;
		// Only manifest-style destination roots may be selected as foreign roots.
		// Keep this resolver usable as a small standalone asset helper too; the
		// manifest owns the same stable prefix, but importing that class here would
		// make legacy shader-only callers depend on the whole compatibility layer.
		return value == 'assets' || value.startsWith('assets/imported_mods/');
	}
}
