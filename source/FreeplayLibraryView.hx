package;

/** Host library identity and the shared registry-based All collector. */
class FreeplayLibraryView {
	public static inline var FAVORITES:String = '@favorites';
	public static function songs(categories:Array<Dynamic>):Array<Dynamic>
		return FreeplayDirectEntry.allCategorySongs(categories, true);
}
