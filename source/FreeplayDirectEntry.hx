package;

import FreeplaySongOrder.FreeplaySongEntry;

/** Resolve a direct FreeplayState launch which did not pass through the native
	category chooser. An explicitly scoped imported entry sees only its registered
	songs; an unscoped launch uses the first populated category. The caller supplies
	provenance so this selection can be tested without filesystem or game-state side effects. */
class FreeplayDirectEntry {
	public static function select(categories:Array<Dynamic>, ownerRoot:String,
		ownerForSong:String->String, ?preferredCategory:String = ''):Array<Dynamic> {
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
		if (preferredCategory != null && StringTools.trim(preferredCategory) != '') {
			for (category in categories) {
				var categoryName:Dynamic = category == null ? null : Reflect.field(category, 'name');
				if (!Std.isOfType(categoryName, String) || categoryName != preferredCategory)
					continue;
				if (preferredCategory == 'All')
					return allCategorySongs(categories);
				var songs:Dynamic = Reflect.field(category, 'songs');
				return Std.isOfType(songs, Array) ? cast songs : selected;
			}
		}
		for (category in categories) {
			var songs:Dynamic = category == null ? null : Reflect.field(category, 'songs');
			if (Std.isOfType(songs, Array) && (cast songs:Array<Dynamic>).length > 0)
				return cast songs;
		}
		return selected;
	}

	/** Match CategoryState's virtual All list when rebuilding after a registry
	 * generation change. Its registry row contains only Random-Song; the visible
	 * category also includes every authored category's songs. */
	static function allCategorySongs(categories:Array<Dynamic>):Array<Dynamic> {
		var entries:Array<FreeplaySongEntry> = [];
		for (category in categories) {
			var name:Dynamic = category == null ? null : Reflect.field(category, 'name');
			if (!Std.isOfType(name, String) || name == 'All')
				continue;
			var songs:Dynamic = Reflect.field(category, 'songs');
			if (!Std.isOfType(songs, Array))
				continue;
			for (song in (cast songs:Array<Dynamic>)) {
				var data:Dynamic = song;
				if (Std.isOfType(song, String)) {
					var songName:String = cast song;
					data = {name:songName, week:-1, character:'face'};
				}
				entries.push({song:data, base:name == 'Base Game', order:entries.length});
			}
		}
		var result:Array<Dynamic> = [{name:'Random-Song', week:0, character:'bf'}];
		for (song in FreeplaySongOrder.sort(entries))
			result.push(song);
		return result;
	}
}
