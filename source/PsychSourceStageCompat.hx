package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** A compiled Psych stage class selected by the donor PlayState dispatcher. */
typedef PsychCompiledStageSource = {
	var stage:String;
	var className:String;
	/** HScript-ex module path derived from the owner source file location. */
	var modulePath:String;
	var sourcePath:String;
	var dispatchPath:String;
}

/**
	Read-only lookup for stage implementations selected by Psych's compiled
	`PlayState` switch. The class body stays donor Haxe; this adapter only lets
	import diagnostics distinguish source code the target cannot execute from
	a stage whose source files were omitted.
*/
class PsychSourceStageCompat {
	/** Class bindings shipped in the Psych 0.2.8 source archive used by imports.
	 * Runtime owners retain charts/assets but not source/*.hx, so this small
	 * engine-owned index keeps runtime diagnostics specific after import. */
	public static function knownSourceClass(stageName:String):Null<String> {
		if (stageName == null)
			return null;
		return switch (StringTools.trim(stageName).toLowerCase()) {
			case 'stage': 'StageWeek1';
			case 'spooky': 'Spooky';
			case 'philly': 'Philly';
			case 'limo': 'Limo';
			case 'mall': 'Mall';
			case 'malleevil': 'MallEvil';
			case 'school': 'School';
			case 'schoolevil': 'SchoolEvil';
			case 'tank': 'Tank';
			case 'phillystreets': 'PhillyStreets';
			case 'phillyblazin': 'PhillyBlazin';
			default: null;
		};
	}

	public static function resolve(sourceRoot:String, stageName:String):Null<PsychCompiledStageSource> {
		#if sys
		return resolveFromSourceTree(sourceRoot, stageName);
		#else
		return null;
		#end
	}

	/** True only for a regular source module inside this owner. Runtime adapters
	 * use this when adding a source/import.hx module that is otherwise implicit
	 * to Haxe but must be registered in the owner class scope.
	 */
	public static function sourceModuleExists(sourceRoot:String, modulePath:String):Bool {
		#if sys
		if (sourceRoot == null || modulePath == null || modulePath == '') return false;
		var parts = modulePath.split('.');
		for (part in parts)
			if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(part)) return false;
		var path = Path.join([sourceRoot, 'source', parts.join('/') + '.hx']);
		return FileSystem.exists(path) && !FileSystem.isDirectory(path)
			&& CodenameScriptDiscovery.withinRoot(sourceRoot, path);
		#else
		return false;
		#end
	}

	#if sys
	static function resolveFromSourceTree(sourceRoot:String, stageName:String):Null<PsychCompiledStageSource> {
		var stage = stageName == null ? '' : StringTools.trim(stageName);
		if (sourceRoot == null || stage == '' || !safeStageName(stage)
			|| !FileSystem.isDirectory(sourceRoot))
			return null;

		var source = findDirectory(sourceRoot, 'source');
		var states = source == null ? null : findDirectory(source, 'states');
		var stageDirectory = states == null ? null : findDirectory(states, 'stages');
		var dispatchPath = states == null ? null : findFile(states, 'PlayState.hx');
		if (stageDirectory == null || dispatchPath == null)
			return null;

		var dispatch:String;
		try {
			dispatch = File.getContent(dispatchPath);
		} catch (_:Dynamic) {
			return null;
		}
		// Psych source releases bind the chart stage id to a concrete Haxe class
		// in `switch (curStage)`. Require that exact shape and the corresponding
		// class file; loose references elsewhere in PlayState are not a binding.
		var matcher = new EReg("case\\s+['\"]" + stage + "['\"]\\s*:\\s*new\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(", 'i');
		if (!matcher.match(dispatch))
			return null;
		var className = matcher.matched(1);
		var sourcePath = findFile(stageDirectory, className + '.hx');
		if (sourcePath == null)
			return null;
		var modulePath = modulePathFromSource(sourceRoot, sourcePath);
		if (modulePath == null)
			return null;
		return {
			stage:stage,
			className:className,
			modulePath:modulePath,
			sourcePath:normalizePath(sourcePath),
			dispatchPath:normalizePath(dispatchPath)
		};
	}

	/** Resolve the exact Haxe module name from this selected owner's source path.
	 * HScript's class loader takes imports, while Psych's dispatcher records the
	 * short constructor name. Deriving the package here keeps the two contracts
	 * tied to the same file and avoids a parallel stage-name table at runtime.
	 */
	static function modulePathFromSource(sourceRoot:String, sourcePath:String):Null<String> {
		var prefix = normalizePath(Path.join([sourceRoot, 'source'])) + '/';
		var path = normalizePath(sourcePath);
		if (!path.startsWith(prefix) || !path.toLowerCase().endsWith('.hx'))
			return null;
		var relative = path.substr(prefix.length, path.length - prefix.length - 3);
		if (relative == '')
			return null;
		var parts = relative.split('/');
		for (part in parts)
			if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(part))
				return null;
		return parts.join('.');
	}

	static function safeStageName(value:String):Bool {
		return value != null && new EReg('^[A-Za-z0-9_-]+$', '').match(value);
	}

	static function findDirectory(parent:String, wanted:String):String {
		if (parent == null || wanted == null || !FileSystem.isDirectory(parent))
			return null;
		var exact = Path.join([parent, wanted]);
		if (FileSystem.isDirectory(exact))
			return normalizePath(exact);
		for (entry in readDirectory(parent)) {
			if (entry.toLowerCase() != wanted.toLowerCase())
				continue;
			var candidate = Path.join([parent, entry]);
			if (FileSystem.isDirectory(candidate))
				return normalizePath(candidate);
		}
		return null;
	}

	static function findFile(parent:String, wanted:String):String {
		if (parent == null || wanted == null || !FileSystem.isDirectory(parent))
			return null;
		var exact = Path.join([parent, wanted]);
		if (FileSystem.exists(exact) && !FileSystem.isDirectory(exact))
			return normalizePath(exact);
		for (entry in readDirectory(parent)) {
			if (entry.toLowerCase() != wanted.toLowerCase())
				continue;
			var candidate = Path.join([parent, entry]);
			if (FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate))
				return normalizePath(candidate);
		}
		return null;
	}

	static function readDirectory(path:String):Array<String> {
		try {
			var entries = FileSystem.readDirectory(path);
			entries.sort(function(a:String, b:String):Int {
				var lowerA = a.toLowerCase();
				var lowerB = b.toLowerCase();
				if (lowerA < lowerB) return -1;
				if (lowerA > lowerB) return 1;
				return a < b ? -1 : (a > b ? 1 : 0);
			});
			return entries;
		} catch (_:Dynamic) {
			return [];
		}
	}

	static function normalizePath(path:String):String {
		return path == null ? '' : StringTools.replace(Path.normalize(path), '\\', '/');
	}
	#end
}
