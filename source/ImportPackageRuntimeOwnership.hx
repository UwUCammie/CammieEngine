package;

import haxe.io.Path;

/** A verified package needs owned content, not just generated metadata/core files.
 * Historical NV content folders have no required per-package metadata file. */
class ImportPackageRuntimeOwnership {
	public static function isPayload(path:String, namespaceRoot:String):Bool {
		if (path == null || namespaceRoot == null) return false;
		var prefix = Path.normalize(StringTools.replace(namespaceRoot, "\\", "/")).toLowerCase() + "/";
		var key = Path.normalize(StringTools.replace(path, "\\", "/")).toLowerCase();
		if (!StringTools.startsWith(key, prefix)) return false;
		var relative = key.substr(prefix.length);
		return relative.indexOf("/") > 0 && !StringTools.startsWith(relative, "__nmv_core/")
			&& !StringTools.startsWith(relative, ".");
	}
}
