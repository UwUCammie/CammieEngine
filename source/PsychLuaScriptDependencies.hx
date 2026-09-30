package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

typedef PsychLuaDependency = {
	var source:String;
	var relative:String;
}

typedef PsychLuaDependencyScan = {
	var files:Array<PsychLuaDependency>;
	var complete:Bool;
}

/** Follow literal addLuaScript dependencies without copying an arbitrary donor tree. */
class PsychLuaScriptDependencies {
	public static final MAX_ENTRIES:Int = 8192;
	public static final MAX_SOURCE_BYTES:Int = 512 * 1024;
	public static final MAX_DEPTH:Int = 4;

	public static function relativeLuaPath(value:String):Null<String> {
		if (value == null)
			return null;
		var clean = StringTools.replace(value.trim(), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.startsWith('imported_mods/'))
			return null;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return null;
		if (!clean.toLowerCase().endsWith('.lua')) {
			if (Path.extension(clean) != '')
				return null;
			clean += '.lua';
		}
		return clean;
	}

	public static function literalReferences(source:String):Array<String> {
		var found:Array<String> = [];
		if (source == null || source == '')
			return found;
		var pattern = ~/\baddLuaScript\s*\(\s*(['"])([^'"\r\n\\]{1,240})\1\s*[,)]/g;
		var cursor = 0;
		while (pattern.matchSub(source, cursor)) {
			var pos = pattern.matchedPos();
			if (pos.len <= 0)
				break;
			cursor = pos.pos + pos.len;
			var lineStart = source.lastIndexOf('\n', pos.pos - 1) + 1;
			var linePrefix = source.substr(lineStart, pos.pos - lineStart);
			if (linePrefix.indexOf('--') >= 0)
				continue;
			var relative = relativeLuaPath(pattern.matched(2));
			if (relative != null && found.indexOf(relative) < 0)
				found.push(relative);
		}
		return found;
	}

	#if sys
	public static function discover(contentRoot:String):PsychLuaDependencyScan {
		var result:PsychLuaDependencyScan = {files:[], complete:true};
		if (contentRoot == null || !FileSystem.isDirectory(contentRoot))
			return result;
		var budget = [MAX_ENTRIES];
		var queue:Array<String> = [];
		for (directory in ['data', 'scripts', 'stages', 'events', 'notetypes',
			'custom_events', 'custom_notetypes'])
			collectLuaFiles(Path.join([contentRoot, directory]), 0, budget, queue, result);
		var visited:Map<String, Bool> = [];
		var dependencies:Map<String, Bool> = [];
		var index = 0;
		while (index < queue.length) {
			if (budget[0] <= 0) {
				result.complete = false;
				break;
			}
			var path = queue[index++];
			if (visited.exists(path))
				continue;
			visited.set(path, true);
			budget[0]--;
			try {
				var stat = FileSystem.stat(path);
				if (stat.size > MAX_SOURCE_BYTES) {
					result.complete = false;
					continue;
				}
				for (relative in literalReferences(File.getContent(path))) {
					var source = Path.join([contentRoot, relative]);
					if (!FileSystem.exists(source) || FileSystem.isDirectory(source))
						continue;
					if (!dependencies.exists(relative)) {
						dependencies.set(relative, true);
						result.files.push({source:source, relative:relative});
					}
					queue.push(source);
				}
			} catch (_:Dynamic) {
				result.complete = false;
			}
		}
		result.files.sort(function(a, b) return Reflect.compare(a.relative, b.relative));
		return result;
	}

	static function collectLuaFiles(path:String, depth:Int, budget:Array<Int>, queue:Array<String>,
		result:PsychLuaDependencyScan):Void {
		if (!FileSystem.isDirectory(path))
			return;
		if (depth > MAX_DEPTH) {
			result.complete = false;
			return;
		}
		var entries:Array<String> = [];
		try entries = FileSystem.readDirectory(path) catch (_:Dynamic) {
			result.complete = false;
			return;
		}
		entries.sort(Reflect.compare);
		for (entry in entries) {
			if (budget[0] <= 0) {
				result.complete = false;
				return;
			}
			budget[0]--;
			if (entry == '' || entry == '.' || entry == '..' || entry.indexOf('/') >= 0
				|| entry.indexOf('\\') >= 0 || entry.indexOf(':') >= 0)
				continue;
			var child = Path.join([path, entry]);
			if (FileSystem.isDirectory(child)) {
				collectLuaFiles(child, depth + 1, budget, queue, result);
			} else if (entry.toLowerCase().endsWith('.lua')) {
				queue.push(child);
			}
		}
	}
	#end
}
