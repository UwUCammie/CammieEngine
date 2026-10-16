package;

/** Psych finds an icon through every loaded mod, so a song that was imported
 * as an add-on finds the icons of the base mod from the same import. The
 * selected owner keeps priority and each root stays confined to its own Paths. */
class SourceHealthIconRoots {
	/** The Paths holding the file: the selected owner first, then the other
	 * roots in order. The selected owner answers when none holds it. */
	public static function owning(selected:Dynamic, dependencies:Array<Dynamic>, file:String):Dynamic {
		if (dependencies == null || holds(selected, file))
			return selected;
		for (paths in dependencies)
			if (holds(paths, file))
				return paths;
		return selected;
	}

	static function holds(paths:Dynamic, file:String):Bool
		return FNFAssets.exists(Reflect.callMethod(paths, Reflect.field(paths, 'getPath'),
			[file, openfl.utils.AssetType.IMAGE]));
}
