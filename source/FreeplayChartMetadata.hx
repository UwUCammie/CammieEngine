package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

/** Revalidate retained NV rejection receipts against the current adapter.
 * No authored chart or receipt is changed. Refresh discards all cached results. */
class FreeplayChartMetadata {
	public static inline var ADAPTER_VERSION:String = 'nv-fields-v2';
	static var validations:Map<String, {fingerprint:String, supported:Bool}> = new Map();

	public static function clear():Void validations.clear();

	public static function retainedChartSupported(song:String, difficulty:String, destination:String):Bool {
		var receipt = 'assets/data/' + song + '/importProvenance.json';
		if (!FNFAssets.exists(destination) || !FNFAssets.exists(receipt)) return false;
		try {
			var metadata:Dynamic = CoolUtil.parseJson(FNFAssets.getText(receipt));
			if (metadata == null || Reflect.field(metadata, 'sourceEngine') != ImportEngine.NIGHTMARE_VISION)
				return false;
			var path = destination;
			var owner:Dynamic = Reflect.field(metadata, 'sourceOwner');
			var folder:Dynamic = Reflect.field(metadata, 'sourceFolder');
			if (owner != null && (folder == null || !safeComponent(Std.string(folder))
				|| !safeComponent(difficulty))) return false;
			// A retained source chart is authoritative when available. Restrict
			// receipt paths to the imported owner tree and single safe components.
			if (owner != null && folder != null && safeComponent(Std.string(folder)) && safeComponent(difficulty)) {
				var root = safeOwnerRoot(owner);
				if (root == null) return false;
				// Package imports retain songs/<id>/data/<chart>, while direct
				// game-root imports retain data/<id>/<chart>. Resolve the source
				// basename using the same common song-prefixed and bare-difficulty
				// forms accepted by the importer, including JSONC files.
				path = retainedChartPath(root, Std.string(folder), song, difficulty);
				// A known retained owner must never be certified from a lossy
				// destination when its authoritative chart is unavailable.
				if (path == null) return false;
			}
			var fingerprint = ADAPTER_VERSION + ':' + identity(path) + ':' + identity(destination)
				+ ':' + identity(receipt) + ':' + haxe.Json.stringify(metadata);
			var previous = validations.get(destination);
			if (previous != null && previous.fingerprint == fingerprint) return previous.supported;
			var chart:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			var supported = NightmareVisionChartCompat.convert(chart, path).supported;
			validations.set(destination, {fingerprint:fingerprint, supported:supported});
			return supported;
		} catch (_:Dynamic) return false;
	}

	static function retainedChartPath(root:String, folder:String, song:String,
		difficulty:String):Null<String> {
		var suffix = StringTools.trim(difficulty).toLowerCase();
		var stems:Array<String> = suffix == 'normal'
			? ['normal', folder, folder + '-normal']
			: [difficulty, folder + '-' + difficulty];
		// Renamed destination songs retain their authored source folder first;
		// the destination key is a final source-name convention for older receipts.
		var destinationSong = song == null ? '' : StringTools.trim(song);
		if (safeComponent(destinationSong) && destinationSong.toLowerCase() != folder.toLowerCase()) {
			if (suffix == 'normal') stems.push(destinationSong);
			else stems.push(destinationSong + '-' + difficulty);
		}
		// Match appendAssetSongImports' order: ordinary data/<song>, nested
		// data/songs/<song>, Psych-family data/songData/<song>, then NMV's
		// package songs/<song>/data layout.
		var directories = [root + '/data/' + folder, root + '/data/songs/' + folder,
			root + '/data/songData/' + folder, root + '/songs/' + folder + '/data'];
		for (directory in directories)
			for (stem in stems)
				for (extension in ['.json', '.jsonc']) {
					var candidate = directory + '/' + stem + extension;
					#if sys
					var resolved = FNFAssets.resolveCaseInsensitivePath(candidate);
					if (resolved != null && FNFAssets.exists(resolved)) return resolved;
					#end
					if (FNFAssets.exists(candidate)) return candidate;
				}
		return null;
	}

	static function safeOwnerRoot(value:Dynamic):Null<String> {
		if (!Std.isOfType(value, String)) return null;
		var clean = StringTools.replace(StringTools.trim(cast value), '\\', '/');
		if (StringTools.startsWith(clean, '/') || clean.indexOf(':') >= 0) return null;
		var parts = clean.split('/');
		if (parts.length < 3 || parts[0] != 'assets' || parts[1] != 'imported_mods') return null;
		for (index in 2...parts.length) if (!safeComponent(parts[index])) return null;
		return Path.normalize(clean);
	}

	static function safeComponent(value:String):Bool
		return value != null && value != '' && value != '.' && value.indexOf('..') < 0
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0;

	static function identity(path:String):String {
		#if sys
		var resolved = FNFAssets.resolveCaseInsensitivePath(path);
		if (resolved != null && FileSystem.exists(resolved)) {
			var stat = FileSystem.stat(resolved);
			return resolved + ':' + stat.size + ':' + stat.mtime.getTime();
		}
		#end
		return path;
	}
}
