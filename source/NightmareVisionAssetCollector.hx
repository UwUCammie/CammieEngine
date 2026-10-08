package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

/**
	Read-only collector for one Nightmare Vision content root. It does not copy,
	rewrite, or flatten owner content.
*/
class NightmareVisionAssetCollector {
	public static inline var CORE_SUBTREE:String = '__nmv_core';

	/**
		Return the donor game-assets root selected by NightmareVisionScriptDiscovery's
		root rules. A selected package under `content/<package>` uses its sibling
		`assets` directory; when the selected source is itself an `assets` root,
		that root is the core dependency. Other package shapes have no inferred core.
	*/
	public static function resolveCoreAssetsRoot(sourceRoot:String):String {
		#if sys
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return '';
		var owner = canonicalExisting(sourceRoot);
		if (owner == '') return '';
		// A caller that explicitly selected an assets directory retains the
		// existing core-only behavior. Its identity does not depend on a parent
		// directory's name.
		if (Path.withoutDirectory(owner).toLowerCase() == 'assets')
			return owner;
		var parent = Path.directory(owner);
		if (parent != null && Path.withoutDirectory(parent).toLowerCase() == 'content'
			&& isDirectChild(owner, parent)) {
			// A package's own assets/ tree is package-owned, not the engine core.
			// Resolve the sibling game assets only when the actual parent root has
			// NMV project/executable/chart evidence. A folder merely named content
			// cannot borrow an unrelated parent tree.
			var gameRoot = Path.directory(parent);
			if (gameRoot == null || gameRoot == parent || !isNightmareVisionGameRoot(gameRoot))
				return '';
			var candidate = Path.join([gameRoot, 'assets']);
			return FileSystem.isDirectory(candidate) ? canonicalExisting(candidate) : '';
		}
		var nestedAssets = Path.join([owner, 'assets']);
		if (FileSystem.isDirectory(nestedAssets))
			return canonicalExisting(nestedAssets);
		#end
		return '';
	}

	/** Retain an authenticated enclosing game when a selected content package
		depends on its sibling core. Conversion still uses the original selected
		root allowlist; sibling packages are not added to the import selection. */
	public static function retentionRoot(sourceRoot:String):String {
		#if sys
		var selected = canonicalExisting(sourceRoot);
		if (selected == '') return sourceRoot;
		var core = resolveCoreAssetsRoot(selected);
		if (core == '') return selected;
		var container = Path.directory(selected);
		if (container == null || Path.withoutDirectory(container).toLowerCase() != 'content') return selected;
		var game = Path.directory(container);
		if (game != null && core == canonicalExisting(Path.join([game, 'assets']))) return game;
		#end
		return sourceRoot;
	}

	/**
		Collect all files below the selected content root. NMV's generic Paths API
		can address arbitrary package-relative files, so this deliberately does not
		guess a fixed folder list. Callers pass either a selected content package
		or the explicit engine `assets` root, never its enclosing installation.
		Traversal is iterative and uncapped. In-root symlink aliases keep their
		authored relative path; only ancestor cycles are stopped. Out-of-root links
		and read failures make `complete` false so callers can report partial imports.
	*/
	public static function collect(root:String, ?isCancelled:Void->Bool):Dynamic {
		var result:Dynamic = {files:[], complete:true, errors:[], cycles:0};
		#if sys
		if (root == null || !FileSystem.isDirectory(root)) {
			result.complete = false;
			result.errors.push('Asset root is missing or is not a directory: ' + Std.string(root));
			return result;
		}
		var sourceRoot = canonicalExisting(root);
		if (sourceRoot == '') {
			result.complete = false;
			result.errors.push('Could not resolve asset root: ' + root);
			return result;
		}
		var stack:Array<Dynamic> = [{source:sourceRoot, relative:'', ancestors:[sourceRoot]}];
		while (stack.length > 0) {
				if (cancelled(isCancelled)) {
					fail(result, 'Asset traversal cancelled');
					return result;
				}
				var current:Dynamic = stack.pop();
				var currentSource:String = current.source;
				if (!within(currentSource, sourceRoot)) {
					fail(result, 'Asset path escapes its selected root: ' + currentSource);
					continue;
				}
				var entries:Array<String>;
				try entries = FileSystem.readDirectory(currentSource) catch (error:Dynamic) {
					fail(result, 'Could not read asset directory: ' + currentSource + ' (' + Std.string(error) + ')');
					continue;
				}
				entries.sort(compareNames);
				for (entry in entries) {
					if (cancelled(isCancelled)) {
						fail(result, 'Asset traversal cancelled');
						return result;
					}
					if (!validEntryName(entry)) {
						fail(result, 'Unsafe asset entry name: ' + entry);
						continue;
					}
					var sourcePath = Path.join([currentSource, entry]);
					if (!FileSystem.exists(sourcePath)) {
						fail(result, 'Asset entry disappeared or is unreadable: ' + sourcePath);
						continue;
					}
					if (!within(sourcePath, sourceRoot)) {
						fail(result, 'Asset symlink escapes its selected root: ' + sourcePath);
						continue;
					}
					var relative:String = current.relative == '' ? entry : current.relative + '/' + entry;
					if (FileSystem.isDirectory(sourcePath)) {
						var key = canonicalExisting(sourcePath);
						if (key == '') {
							fail(result, 'Could not resolve asset directory: ' + sourcePath);
							continue;
						}
						var ancestors:Array<String> = current.ancestors;
					if (ancestors.indexOf(key) >= 0) {
						result.cycles++;
						continue;
					}
					var childAncestors = ancestors.copy();
					childAncestors.push(key);
					stack.push({source:sourcePath, relative:relative, ancestors:childAncestors});
					} else {
					result.files.push({source:sourcePath, relative:relative});
				}
				}
		}
		result.files.sort(function(a:Dynamic, b:Dynamic):Int return compareNames(a.relative, b.relative));
		#end
		return result;
	}

	#if sys
	static function isDirectChild(child:String, parent:String):Bool {
		var normalizedChild = canonicalExisting(child);
		var normalizedParent = canonicalExisting(parent);
		if (normalizedChild == '' || normalizedParent == '') return false;
		var parentOfChild = Path.directory(normalizedChild);
		#if windows
		return parentOfChild != null && parentOfChild.toLowerCase() == normalizedParent.toLowerCase();
		#else
		return parentOfChild == normalizedParent;
		#end
	}

	static function isNightmareVisionGameRoot(root:String):Bool {
		if (root == null || !FileSystem.isDirectory(root)) return false;
		var resolved = canonicalExisting(root);
		if (resolved == '' || !isDirectChild(Path.join([resolved, 'content']), resolved)) return false;
		var inspected = ImportRootScanner.inspectRoot(resolved, ImportEngine.AUTO);
		if (inspected == null || inspected.engine != ImportEngine.NIGHTMARE_VISION
			|| inspected.evidence == null) return false;
		return ImportRootScanner.hasNightmareVisionContainerProof(inspected.evidence);
	}

	static function canonicalExisting(path:String):String {
		try return Path.normalize(FileSystem.fullPath(path)) catch (_:Dynamic) return '';
	}

	static function within(path:String, root:String):Bool {
		var fullPath = canonicalExisting(path);
		var fullRoot = canonicalExisting(root);
		if (fullPath == '' || fullRoot == '')
			return false;
		#if windows
		fullPath = fullPath.toLowerCase();
		fullRoot = fullRoot.toLowerCase();
		#end
		return fullPath == fullRoot || fullPath.startsWith(StringTools.endsWith(fullRoot, '/') ? fullRoot : fullRoot + '/');
	}

	static function validEntryName(name:String):Bool {
		return name != null && name != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf('\x00') < 0;
	}

	static function cancelled(callback:Void->Bool):Bool return callback != null && callback();
	static function fail(result:Dynamic, message:String):Void {
		result.complete = false;
		result.errors.push(message);
	}
	#end

	static function compareNames(a:String, b:String):Int {
		var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
		return lower == 0 ? Reflect.compare(a, b) : lower;
	}
}
