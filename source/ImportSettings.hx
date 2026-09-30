package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

/**
 * Shared import configuration.
 *
 * Keep the importer name separate from the UI so every import entry point
 * resolves the same source directory.  The names in this table are user
 * facing engine labels, rather than implementation class names.  That makes
 * the saved setting stable while the importer implementation can grow behind
 * it (and lets Auto choose per discovered root).
 */
class ImportSettings {
	public static inline var AUTO:String = ImportEngine.AUTO;
	public static inline var V_SLICE:String = ImportEngine.V_SLICE;
	public static inline var KADE_ENGINE:String = ImportEngine.KADE;
	public static inline var MODDING_PLUS:String = ImportEngine.MODDING_PLUS;
	public static inline var PSYCH_ENGINE:String = ImportEngine.PSYCH;
	public static inline var NIGHTMARE_VISION:String = ImportEngine.NIGHTMARE_VISION;
	public static inline var FPS_PLUS:String = ImportEngine.FPS_PLUS;
	public static inline var CODENAME:String = ImportEngine.CODENAME;
	public static inline var LEGACY_POLYMOD:String = ImportEngine.LEGACY_POLYMOD;

	// Kept as a source/save compatibility alias.  Older builds exposed this
	// wording in the only-option selector; it is normalized to the actual
	// Modding Plus engine label and is intentionally not shown as a duplicate
	// engine option in the new selector.
	public static inline var MODDING_POOP:String = "Modding Poop";
	public static final IMPORT_TYPES:Array<String> = ImportEngine.names();

	static var cachedType:String;
	static var cachedSourcePath:String;

	public static function getTypes():Array<String> {
		// The selector must not be able to mutate the registry itself.
		return IMPORT_TYPES.copy();
	}

	public static function normalizeType(value:Dynamic):String {
		if (value != null) {
			var candidate = StringTools.trim(Std.string(value));
			// Accept the old selector value and common saved aliases.  Do this
			// before the registry lookup so an old options.json never strands a
			// user on a removed importer label.
			switch (candidate.toLowerCase()) {
				case 'modding poop', 'moddingplus', 'modding plus engine':
					return MODDING_PLUS;
				case 'v-slices', 'v slice', 'v_slice':
					return V_SLICE;
				case 'kade', 'kadeengine':
					return KADE_ENGINE;
				case 'psych', 'psychengine':
					return PSYCH_ENGINE;
				case 'nightmarevision', 'nightmare vision engine', 'nmv':
					return NIGHTMARE_VISION;
				case 'fps', 'fpsplus', 'fps plus engine':
					return FPS_PLUS;
				case 'legacy', 'legacy fnf', 'polymod', 'legacy polymod':
					return LEGACY_POLYMOD;
				case 'auto-detect', 'automatic':
					return AUTO;
			}
			for (importType in IMPORT_TYPES) {
				if (candidate == importType)
					return importType;
			}
		}
		return AUTO;
	}

	public static function getSelectedType():String {
		if (cachedType == null) {
			var savedType:Dynamic = Reflect.field(OptionsHandler.options, "importType");
			cachedType = normalizeType(savedType);
		}
		return cachedType;
	}

	public static function setSelectedType(value:Dynamic):String {
		cachedType = normalizeType(value);
		var options:Dynamic = OptionsHandler.options;
		Reflect.setField(options, "importType", cachedType);
		OptionsHandler.options = cast options;
		return cachedType;
	}

	/**
	 * Normalize a path returned by Lime's file dialog.  Lime returns native
	 * separators, but old Modding Plus metadata can contain Windows paths even
	 * when it is being imported on Linux/Wine.  Forward slashes are accepted by
	 * all of the native targets and make comparisons deterministic.
	 */
	public static function normalizeSourcePath(path:Dynamic):String {
		if (path == null)
			return '';
		var normalized = StringTools.trim(Std.string(path));
		if (normalized == '')
			return '';
		normalized = StringTools.replace(normalized, '\\', '/');
		// Path.normalize treats a leading double slash as redundant.  That is
		// correct for POSIX paths, but it destroys the server/share boundary of
		// a Windows UNC path.  Remember the prefix before normalizing so a
		// donor selected through a network share keeps a stable identity.
		var unc = StringTools.startsWith(normalized, '//');
		normalized = Path.normalize(normalized);
		if (unc && !StringTools.startsWith(normalized, '//')) {
			while (StringTools.startsWith(normalized, '/'))
				normalized = normalized.substr(1);
			normalized = normalized == '' ? '//' : '//' + normalized;
		}
		while (normalized.length > 1 && StringTools.endsWith(normalized, '/')) {
			// Keep a POSIX root and a Windows drive root intact.
			if (normalized == '/' || normalized == '//' || (normalized.length == 3 && normalized.charAt(1) == ':'))
				break;
			normalized = normalized.substr(0, normalized.length - 1);
		}
		return normalized;
	}

	/**
	 * The selected folder is deliberately separate from getImportRoot().  The
	 * latter remains the legacy staging directory used by the per-item module
	 * UI; this value is the source root used by the recursive importer.
	 */
	public static function getSourcePath():String {
		if (cachedSourcePath == null) {
			var savedPath:Dynamic = Reflect.field(OptionsHandler.options, "importPath");
			cachedSourcePath = normalizeSourcePath(savedPath);
			if (cachedSourcePath == '')
				cachedSourcePath = normalizeSourcePath(getImportRoot());
		}
		return cachedSourcePath;
	}

	public static function setSourcePath(path:Dynamic):String {
		var normalized = normalizeSourcePath(path);
		if (normalized == '')
			return getSourcePath();
		cachedSourcePath = normalized;
		var options:Dynamic = OptionsHandler.options;
		Reflect.setField(options, "importPath", cachedSourcePath);
		OptionsHandler.options = cast options;
		return cachedSourcePath;
	}

	/**
	 * Return the on-disk root for an import implementation.
	 *
	 * Path.join keeps this valid on Windows/Wine as well as native Linux and
	 * avoids relying on a platform-specific separator in callers.
	 */
	public static function getImportRoot(?importType:String):String {
		var selected = normalizeType(importType == null ? getSelectedType() : importType);
		// All engine-aware importers stage legacy per-item payloads in the same
		// canonical tree.  The selected engine is carried by the workflow and
		// determines how a discovered root is decoded; it must not fragment the
		// destination tree or the existing ModuleState workflow.
		return Path.join(["assets", "module", "import"]);
	}

	/** Human-readable text used by the native directory picker. */
	public static function sourceDialogTitle(?importType:String):String {
		var selected = normalizeType(importType == null ? getSelectedType() : importType);
		return selected == AUTO ? 'Select game/mod folders to scan' : 'Select ' + selected + ' folder';
	}

	/** A compact label for statuses and reports. */
	public static function typeLabel(?importType:String):String {
		return normalizeType(importType == null ? getSelectedType() : importType);
	}

	public static function getImportPath(folder:String, ?importType:String):String {
		return Path.join([getImportRoot(importType), folder]);
	}

	/**
	 * Ensure the native importer has a place to look for each supported
	 * Modding+ payload.  Empty directories are not retained by Lime's asset
	 * sync, so a clean checkout (and an AppImage extraction) may not contain
	 * them yet.
	 */
	public static function ensureImportDirectories():Void {
		#if sys
		var root = getImportRoot();
		if (FileSystem.exists(root) && !FileSystem.isDirectory(root))
			return;
		ensureDirectory(root);
		for (folder in ['songs', 'characters', 'stages']) {
			var path = Path.join([root, folder]);
			if (!FileSystem.exists(path))
				ensureDirectory(path);
		}
		#end
	}

	#if sys
	static function ensureDirectory(path:String):Void {
		if (path == null || path == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		FileSystem.createDirectory(path);
	}
	#end
}
