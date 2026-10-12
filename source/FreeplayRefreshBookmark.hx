package;

/** One menu replacement's transient view state, never persisted as library identity. */
class FreeplayRefreshBookmark {
	public final key:String;
	public final search:String;
	public final difficulty:String;
	public final scope:String;
	public function new(key:String, search:String, difficulty:String, scope:String) {
		this.key = key; this.search = search; this.difficulty = difficulty; this.scope = scope;
	}
	/** Fail closed on duplicate retained identities instead of selecting a different owner. */
	public function find(count:Int, identity:Int->String):Int {
		if (key == null || key == '') return -1;
		var found = -1;
		for (i in 0...count) if (identity(i) == key) {
			if (found >= 0) return -2;
			found = i;
		}
		return found;
	}
}
