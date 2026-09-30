package;

import haxe.io.Path;

using StringTools;

/**
	Pure routing helpers shared by the native Freeplay HXC host and its focused
	interpreter tests. Imported compatibility roots are associated with the
	songs whose compatScripts manifest names them; only the destination's native
	assets/scripts root is global by default.
*/
class HxcFreeplayRouting {
	/** Normalize a destination root without changing its case-sensitive path. */
	public static function normalizeRoot(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		return clean == '' ? '' : Path.normalize(clean);
	}

	/** Normalize song/capsule ids for manifest association and payload matching. */
	public static function normalizeSong(value:String):String {
		if (value == null || value == '')
			return '';
		var output = new StringBuf();
		for (index in 0...value.length) {
			var character = value.charAt(index).toLowerCase();
			var code = character.charCodeAt(0);
			if ((code >= 97 && code <= 122) || (code >= 48 && code <= 57))
				output.add(character);
		}
		return output.toString();
	}

	/** Associate one imported root with a song without duplicating the entry. */
	public static function associateSong(rootSongs:Map<String, Array<String>>,
		root:String, song:String):Void {
		if (rootSongs == null)
			return;
		var rootKey = normalizeRoot(root);
		var songKey = normalizeSong(song);
		if (rootKey == '' || songKey == '')
			return;
		var songs = rootSongs.get(rootKey);
		if (songs == null) {
			songs = [];
			rootSongs.set(rootKey, songs);
		}
		if (songs.indexOf(songKey) < 0)
			songs.push(songKey);
	}

	/** Return whether a scope may receive a payload for the selected capsule. */
	public static function scopeMatches(global:Bool, associatedSongs:Array<String>,
		selectedSong:String):Bool {
		if (global)
			return true;
		var selectedKey = normalizeSong(selectedSong);
		if (selectedKey == '' || associatedSongs == null)
			return false;
		for (song in associatedSongs)
			if (normalizeSong(song) == selectedKey)
				return true;
		return false;
	}

	/**
		Extract the selected song from the generic Freeplay lifecycle payload.
		Keep this tolerant of old capsule views: imported donors may expose only
		name, songName, freeplayData.levelId, or freeplayData.data.id.
	*/
	public static function selectedSong(payload:Dynamic):String {
		if (payload == null)
			return '';
		var candidates:Array<Dynamic> = [
			Reflect.field(payload, 'capsule'),
			Reflect.field(payload, 'eventData'),
			Reflect.field(payload, 'value')
		];
		for (candidate in candidates) {
			var result = songFromValue(candidate);
			if (result != '')
				return result;
		}
		return songFromValue(payload);
	}

	/**
		Parse an HXC module request. Unqualified lookups stay in the caller's
		root; `global:ModuleName` (or `global/ModuleName`) explicitly addresses a
		destination-global module and never another imported root.
	*/
	public static function moduleRequest(value:String):{name:String, global:Bool} {
		var name = StringTools.trim(value == null ? '' : value);
		var lower = name.toLowerCase();
		for (prefix in ['global:', 'global/'])
			if (lower.startsWith(prefix))
				return {name:StringTools.trim(name.substr(prefix.length)), global:true};
		return {name:name, global:false};
	}

	/**
		Resolve a module only in the caller's namespace, except for an explicit
		global: request. The Dynamic value is the owning HXC scope in production;
		tests use simple sentinel values.
	*/
	public static function moduleLookup(modules:Map<String, Map<String, Dynamic>>,
		callerRoot:String, globalRoot:String, request:String):Dynamic {
		if (modules == null)
			return null;
		var parsed = moduleRequest(request);
		var root = parsed.global ? normalizeRoot(globalRoot) : normalizeRoot(callerRoot);
		var scoped = modules.get(root);
		if (scoped == null || parsed.name == '')
			return null;
		return scoped.get(normalizeSong(parsed.name));
	}

	static function songFromValue(value:Dynamic):String {
		if (value == null)
			return '';
		if (Std.isOfType(value, String))
			return normalizeSong(Std.string(value));
		for (field in ['name', 'songName', 'levelId', 'id']) {
			var direct = Reflect.field(value, field);
			if (direct != null) {
				var result = normalizeSong(Std.string(direct));
				if (result != '')
					return result;
			}
		}
		for (field in ['capsule', 'freeplayData', 'data', 'value']) {
			var nested = songFromValue(Reflect.field(value, field));
			if (nested != '')
				return nested;
		}
		return '';
	}
}
