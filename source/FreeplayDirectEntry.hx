package;

/** Resolve a direct FreeplayState launch which did not pass through the native
	category chooser. An explicitly scoped imported entry sees only its registered
	songs; an unscoped launch uses the first populated category. The caller supplies
	provenance so this selection can be tested without filesystem or game-state side effects. */
class FreeplayDirectEntry {
	public static function select(categories:Array<Dynamic>, ownerRoot:String,
		ownerForSong:String->String):Array<Dynamic> {
		var selected:Array<Dynamic> = [];
		if (categories == null) return selected;
		var owner = CompatScriptManifest.destinationKey(ownerRoot);
		if (owner != '') {
			if (ownerForSong == null) return selected;
			var seen:Map<String, Bool> = new Map();
			for (category in categories) {
				var songs:Dynamic = category == null ? null : Reflect.field(category, 'songs');
				if (!Std.isOfType(songs, Array)) continue;
				for (song in (cast songs:Array<Dynamic>)) {
					var name:Dynamic = song == null ? null : Reflect.field(song, 'name');
					if (!Std.isOfType(name, String) || seen.exists(name)) continue;
					seen.set(name, true);
					if (CompatScriptManifest.destinationKey(ownerForSong(name)) == owner)
						selected.push(song);
				}
			}
			return selected;
		}
		for (category in categories) {
			var songs:Dynamic = category == null ? null : Reflect.field(category, 'songs');
			if (Std.isOfType(songs, Array) && (cast songs:Array<Dynamic>).length > 0)
				return cast songs;
		}
		return selected;
	}
}
