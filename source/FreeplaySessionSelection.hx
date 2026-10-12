package;

/** One departed menu, retained only until the next Freeplay entry in this process. */
class FreeplaySessionSelection {
	var bookmark:FreeplayRefreshBookmark;
	var generation:Int = -1;
	public function new() {}
	public function remember(value:FreeplayRefreshBookmark, revision:Int):Void {
		bookmark = value;
		generation = revision;
	}
	/** Never carry a selection into another owner/view or an unchanged registry. */
	public function take(scope:String, revision:Int):FreeplayRefreshBookmark {
		var value = bookmark;
		bookmark = null;
		return value != null && value.scope == scope && generation != revision ? value : null;
	}
}
