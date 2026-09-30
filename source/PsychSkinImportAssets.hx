package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

typedef PsychSkinImportResult = {
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	var diagnostics:Array<String>;
}

/** Copy only note skins named by selected Psych charts and bounded Lua literals. */
class PsychSkinImportAssets {
	public static final DEFAULT_SKIN = 'noteSkins/NOTE_assets';
	public static final MAX_LUA_FILES = 4096;
	public static final MAX_LUA_BYTES = 512 * 1024;
	public static final MAX_DEPTH = 4;

	public static function chartKeys(charts:Array<Dynamic>):Array<String> {
		var keys = [DEFAULT_SKIN];
		if (charts != null)
			for (chart in charts) {
				var song = chart == null ? null : Reflect.field(chart, 'song');
				var value = song == null ? null : Reflect.field(song, 'arrowSkin');
				if (value != null && Std.isOfType(value, String) && value != '' && keys.indexOf(value) < 0)
					keys.push(value);
			}
		return keys;
	}

	/** Recognize only literal assignments to texture or SONG.arrowSkin. */
	public static function luaKeys(source:String):Array<String> {
		var keys:Array<String> = [];
		if (source == null) return keys;
		var patterns = [
			~/\bsetProperty(?:FromGroup)?\s*\([^\r\n]*?['"][^'"\r\n]*(?:\.texture|texture|arrowSkin)['"]\s*,\s*['"]([^'"\r\n]+)['"]/g,
			~/\b(?:texture|arrowSkin)\s*=\s*['"]([^'"\r\n]+)['"]/g
		];
		for (pattern in patterns) {
			var at = 0;
			while (pattern.matchSub(source, at)) {
				var position = pattern.matchedPos();
				var value = pattern.matched(1);
				if (value != '' && keys.indexOf(value) < 0)
					keys.push(value);
				at = position.pos + position.len;
			}
		}
		return keys;
	}

	#if sys
	public static function copy(sourceRoot:String, ownerRoot:String, charts:Array<Dynamic>):PsychSkinImportResult {
		var result:PsychSkinImportResult = {copied:0, skipped:0, failed:0, diagnostics:[]};
		if (sourceRoot == null)
			return result;
		sourceRoot = Path.normalize(sourceRoot);
		while (sourceRoot.length > 1 && sourceRoot.endsWith('/'))
			sourceRoot = sourceRoot.substr(0, sourceRoot.length - 1);
		if (!FileSystem.isDirectory(sourceRoot)
			|| !safeOwner(ownerRoot))
			return result;
		var keys = chartKeys(charts);
		var files:Array<String> = [];
		var budget = [MAX_LUA_FILES];
		for (root in [sourceRoot, Path.join([sourceRoot, 'shared'])])
			for (directory in ['data', 'scripts', 'stages', 'events', 'notetypes', 'custom_events', 'custom_notetypes'])
				collectLua(Path.join([root, directory]), 0, budget, files, result);
		for (file in files) {
			try {
				if (FileSystem.stat(file).size > MAX_LUA_BYTES) {
					result.diagnostics.push('Psych skin Lua scan skipped oversized file: ' + file);
					continue;
				}
				var source = File.getContent(file);
				for (key in luaKeys(source))
					if (keys.indexOf(key) < 0) keys.push(key);
				for (line in source.split('\n'))
					if ((line.indexOf('setProperty') >= 0 && line.indexOf('texture') >= 0
						|| line.indexOf('arrowSkin') >= 0 && line.indexOf('=') >= 0)
						&& luaKeys(line).length == 0) {
						result.diagnostics.push('Dynamic Psych skin reference requires manual asset import: ' + file);
						break;
					}
			} catch (error:Dynamic) {
				result.diagnostics.push('Psych skin Lua scan could not read ' + file + ': ' + Std.string(error));
			}
		}
		for (key in keys)
			copyKey(sourceRoot, ownerRoot, key, result);
		return result;
	}

	static function copyKey(sourceRoot:String, ownerRoot:String, key:String,
		result:PsychSkinImportResult):Void {
		if (!safeKey(key)) {
			result.diagnostics.push('Unsafe Psych skin key: ' + key);
			return;
		}
		var found = false;
		var roots = [
			{root:sourceRoot, prefix:''},
			{root:sourceRoot, prefix:'shared/'}
		];
		// Psych source distributions can keep core sheets beside a base_game
		// content root at assets/shared. Keep their relative shared/ path in the
		// selected owner; do not resolve a missing sheet from another import.
		var parent = Path.directory(sourceRoot);
		var sibling = Path.join([parent, 'shared']);
		if (Path.withoutDirectory(parent).toLowerCase() == 'assets'
			&& parent != sourceRoot && sibling != sourceRoot && FileSystem.isDirectory(sibling))
			roots.push({root:parent, prefix:'shared/'});
		for (location in roots) {
			var imageRoot = Path.join([location.root, location.prefix + 'images']);
			var sparrow = Path.join([imageRoot, key]);
			var pixel = Path.join([imageRoot, 'pixelUI', key]);
			if (copyPair(location.root, ownerRoot, key, sparrow,
				[sparrow + '.png', sparrow + '.xml'], result)) found = true;
			if (copyPair(location.root, ownerRoot, key, pixel,
				[pixel + '.png', pixel + 'ENDS.png'], result)) found = true;
		}
		// The host's normal UI atlas is Psych's unmodified default skin.
		// Do not report a missing donor sheet when runtime resolution can use it.
		if (!found && (key != DEFAULT_SKIN || PsychSkinResolver.resolve(key, ownerRoot, false) == null))
			result.diagnostics.push('Psych skin sheet not found for ' + key + ' in ' + sourceRoot);
	}

	static function copyPair(sourceRoot:String, ownerRoot:String, key:String, stem:String,
		files:Array<String>, result:PsychSkinImportResult):Bool {
		var first = FileSystem.exists(files[0]) && !FileSystem.isDirectory(files[0]);
		var second = FileSystem.exists(files[1]) && !FileSystem.isDirectory(files[1]);
		if (!first && !second) return false;
		if (!first || !second) {
			result.diagnostics.push('Incomplete Psych skin sheet for ' + key + ' at ' + stem);
			return false;
		}
		for (file in files) {
			var relative = file.substr(sourceRoot.length + 1);
			var destination = Path.join([ownerRoot, relative]);
			if (FileSystem.exists(destination)) {
				result.skipped++;
				continue;
			}
			try {
				FileSystem.createDirectory(Path.directory(destination));
				File.copy(file, destination);
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
				result.diagnostics.push('Could not copy Psych skin file ' + destination + ': ' + Std.string(error));
			}
		}
		return true;
	}

	static function collectLua(directory:String, depth:Int, budget:Array<Int>, files:Array<String>,
		result:PsychSkinImportResult):Void {
		if (!FileSystem.exists(directory) || !FileSystem.isDirectory(directory)) return;
		if (depth > MAX_DEPTH || budget[0] <= 0) {
			result.diagnostics.push('Psych skin Lua scan budget reached at ' + directory);
			return;
		}
		var entries = FileSystem.readDirectory(directory);
		entries.sort(Reflect.compare);
		for (entry in entries) {
			if (budget[0]-- <= 0) {
				result.diagnostics.push('Psych skin Lua scan budget reached at ' + directory);
				return;
			}
			if (entry == '.' || entry == '..' || entry.indexOf('/') >= 0 || entry.indexOf('\\') >= 0)
				continue;
			var path = Path.join([directory, entry]);
			if (FileSystem.isDirectory(path)) collectLua(path, depth + 1, budget, files, result);
			else if (entry.toLowerCase().endsWith('.lua')) files.push(path);
		}
	}
	#end

	static function safeKey(value:String):Bool {
		if (value == null || value == '' || value != value.trim()
			|| value.indexOf('\\') >= 0 || value.indexOf(':') >= 0 || value.startsWith('/'))
			return false;
		for (part in value.split('/'))
			if (part == '' || part == '.' || part == '..') return false;
		return true;
	}

	static function safeOwner(value:String):Bool {
		if (value == null || !value.startsWith('assets/imported_mods/')
			|| value.indexOf('\\') >= 0 || value.indexOf(':') >= 0)
			return false;
		var parts = value.split('/');
		return parts.length == 3 && safeKey(parts[2]);
	}
}
