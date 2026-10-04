package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** File operations shared by imported script APIs after their owner resolver
	chooses an allowed path. The resolver owns all scope and fallback policy. */
typedef SourceScriptPathResolver = (String, Bool, Bool) -> Null<String>;

@:keep
class SourceScriptFileAccess {
	final resolvePath:SourceScriptPathResolver;

	/** `write` asks for an owner-local destination; `absolute` asks the caller's
		resolver to validate an explicit path without widening its owner scope. */
	public function new(resolvePath:SourceScriptPathResolver) {
		if (resolvePath == null) throw '[source-script-files] Missing path resolver';
		this.resolvePath = resolvePath;
	}

	public function resolve(path:String, write:Bool = false, absolute:Bool = false):Null<String> {
		if (path == null || StringTools.trim(path) == '') return null;
		var resolved = resolvePath(path, write, absolute);
		return resolved == null || StringTools.trim(resolved) == '' ? null : Path.normalize(resolved);
	}

	public function exists(path:String, absolute:Bool = false):Bool {
		var resolved = resolve(path, false, absolute);
		if (resolved == null) return false;
		#if sys
		return FileSystem.exists(resolved);
		#else
		return FNFAssets.exists(resolved);
		#end
	}

	/** Source Paths.getTextFromFile returns null for a missing file. */
	public function getText(path:String, absolute:Bool = false):Null<String> {
		var resolved = resolve(path, false, absolute);
		if (resolved == null) return null;
		#if sys
		if (!FileSystem.exists(resolved) || FileSystem.isDirectory(resolved)) return null;
		try return File.getContent(resolved) catch (_:Dynamic) return null;
		#else
		if (!FNFAssets.exists(resolved)) return null;
		try return FNFAssets.getText(resolved) catch (_:Dynamic) return null;
		#end
	}

	public function isDirectory(path:String, absolute:Bool = false):Bool {
		var resolved = resolve(path, false, absolute);
		if (resolved == null) return false;
		#if sys
		try return FileSystem.exists(resolved) && FileSystem.isDirectory(resolved) catch (_:Dynamic) return false;
		#else
		return false;
		#end
	}

	/** Return the immediate entry names in source order. */
	public function readDirectory(path:String, absolute:Bool = false):Array<String> {
		var resolved = resolve(path, false, absolute);
		if (resolved == null) return [];
		#if sys
		try {
			if (!FileSystem.exists(resolved) || !FileSystem.isDirectory(resolved)) return [];
			return FileSystem.readDirectory(resolved);
		} catch (_:Dynamic) {
			return [];
		}
		#else
		return [];
		#end
	}

	public function saveText(path:String, content:String, absolute:Bool = false):Bool {
		var resolved = resolve(path, true, absolute);
		if (resolved == null || content == null) return false;
		#if sys
		try {
			createParentDirectories(Path.directory(resolved));
			File.saveContent(resolved, content);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	#if sys
	/** The resolver has already validated this owner-scoped destination. Create
		missing parents from the nearest existing ancestor before writing. */
	static function createParentDirectories(directory:String):Void {
		if (directory == null || directory == '' || FileSystem.exists(directory)) return;
		var missing:Array<String> = [];
		var current = Path.normalize(directory);
		while (current != '' && !FileSystem.exists(current)) {
			missing.push(current);
			var parent = Path.directory(current);
			if (parent == current || parent == '') break;
			current = parent;
		}
		for (index in 0...missing.length) {
			var target = missing[missing.length - 1 - index];
			if (!FileSystem.exists(target)) FileSystem.createDirectory(target);
		}
	}
	#end

	public function deleteFile(path:String, absolute:Bool = false):Bool {
		var resolved = resolve(path, true, absolute);
		if (resolved == null) return false;
		#if sys
		try {
			if (!FileSystem.exists(resolved) || FileSystem.isDirectory(resolved)) return false;
			FileSystem.deleteFile(resolved);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}
}
