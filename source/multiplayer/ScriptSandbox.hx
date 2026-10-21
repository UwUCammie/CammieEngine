package multiplayer;

/**
	Limits for scripts while a multiplayer song plays from another player's files.

	Ported scripts reach classes in many ways (hscript imports, Psych and Codename class
	lookups, Type handed to scripts directly), so the limits sit underneath all of them, in
	the native standard library (source-native: Type, sys.FileSystem, sys.io.File,
	sys.io.Process):

	- class lookups by name refuse the file, process, network and system packages and the
	  engine classes that install, update or delete things;
	- file writes are refused outside the save folder, the multiplayer cache and tmp/;
	- starting a process is refused.

	Everything is off outside a match, so single-player and installed content are untouched.
	The checks are string tests only: they never call the file system themselves.
**/
class ScriptSandbox {
	public static var active(default, null):Bool = false;
	static var writeRoots:Array<String> = [];
	static var writeFiles:Array<String> = [];

	/** Package prefixes and exact class names scripts cannot look up while active. Lowercase. */
	static final DENIED_PREFIXES:Array<String> = [
		'sys.', 'cpp.', 'haxe.http', 'haxe.remoting.', 'lime.net.', 'lime.system.', 'lime.tools.',
		'openfl.net.', 'flash.net.', 'openfl.desktop.', 'flash.desktop.', 'openfl.filesystem.', 'flash.filesystem.',
		'multiplayer.'
	];
	static final DENIED_NAMES:Array<String> = [
		'sys', 'openfl.lib', 'flash.lib', 'main', 'updatechecker', 'windowsupdatedownload', 'websiteupdatemanifest',
		'savedatastate', 'importworkflow', 'importrefreshmanager', 'importremovalmanager', 'modulefunctions',
		'fileparser', 'pluginmanager', 'importedmoddiscovery', 'userlibrary'
	];

	/** Start limiting. `roots` are folders that writes stay allowed in, `files` single files the engine itself saves. */
	public static function enable(roots:Array<String>, ?files:Array<String>):Void {
		writeRoots = [for (root in roots) if (root != null && root != '') folder(normalize(absolute(root)))];
		writeFiles = files == null ? [] : [for (file in files) normalize(absolute(file))];
		active = true;
	}

	public static function disable():Void {
		active = false;
		writeRoots = [];
		writeFiles = [];
	}

	public static function classAllowed(name:String):Bool {
		if (!active || name == null)
			return true;
		var lower = name.toLowerCase();
		if (DENIED_NAMES.indexOf(lower) >= 0)
			return false;
		for (prefix in DENIED_PREFIXES)
			if (StringTools.startsWith(lower, prefix))
				return false;
		return true;
	}

	public static function writeAllowed(path:String):Bool {
		if (!active)
			return true;
		if (path == null || path == '')
			return false;
		var full = normalize(absolute(path));
		if (full.indexOf('/../') >= 0 || StringTools.endsWith(full, '/..'))
			return false;
		if (writeFiles.indexOf(full) >= 0)
			return true;
		for (root in writeRoots)
			if (StringTools.startsWith(full + '/', root))
				return true;
		return false;
	}

	public static function guardWrite(path:String):Void {
		if (!writeAllowed(path))
			throw 'Blocked while playing another player\'s song: writing ' + path;
	}

	public static function guardProcess(command:String):Void {
		if (active)
			throw 'Blocked while playing another player\'s song: starting ' + command;
	}

	/** Forward slashes, lowercase on Windows, no trailing slash, "." and ".." folded. */
	public static function normalize(path:String):String {
		#if windows
		return tidy(path).toLowerCase();
		#else
		return tidy(path);
		#end
	}

	/** Forward slashes, no doubled or trailing slash, "." and ".." folded; spelling kept. */
	public static function tidy(path:String):String {
		var value = StringTools.replace(path, '\\', '/');
		var parts:Array<String> = [];
		var split = value.split('/');
		for (index in 0...split.length) {
			var part = split[index];
			// Keep a leading empty part so "/x" stays absolute.
			if (part == '' && index > 0)
				continue;
			if (part == '.')
				continue;
			if (part == '..' && parts.length > 0 && parts[parts.length - 1] != '..' && parts[parts.length - 1] != '') {
				parts.pop();
				continue;
			}
			parts.push(part);
		}
		var result = parts.join('/');
		return result == '' && StringTools.startsWith(value, '/') ? '/' : result;
	}

	static function folder(path:String):String
		return StringTools.endsWith(path, '/') ? path : path + '/';

	static function absolute(path:String):String {
		var value = StringTools.replace(path, '\\', '/');
		if (StringTools.startsWith(value, '/') || (value.length > 1 && value.charAt(1) == ':'))
			return value;
		#if sys
		return Sys.getCwd() + '/' + value;
		#else
		return value;
		#end
	}
}
