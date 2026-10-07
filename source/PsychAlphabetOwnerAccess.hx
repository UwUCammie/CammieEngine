package;

import DynamicSprite.DynamicAtlasFrames;

/** One owner-bound resource factory for script glyphs and Language reloads. */
class PsychAlphabetOwnerAccess {
	public static function create(paths:Dynamic, preferences:Void->Dynamic):PsychAlphabetOwner {
		var ownedPath:String->String = function(relative) return Reflect.callMethod(paths,
			Reflect.field(paths, '__sourceOwnedPath'), [relative]);
		return {
			atlas:function(name) return name == 'alphabet'
				? SourceAlphabetAssets.atlas(ownedPath, function(image, xml) return DynamicAtlasFrames.fromSparrow(image, xml))
				: Reflect.callMethod(paths, Reflect.field(paths, 'getSparrowAtlas'), [name]),
			getPath:function(relative) {
				var owned = ownedPath(relative);
				if (owned != null) return owned;
				var stock = SourceAlphabetAssets.stockPath(relative);
				return stock == null ? Reflect.callMethod(paths, Reflect.field(paths, 'getPath'), [relative]) : stock;
			},
			exists:function(path) return FNFAssets.exists(path),
			text:function(path) return FNFAssets.getText(path),
			antialiasing:function() return preferences().antialiasing
		};
	}
}
