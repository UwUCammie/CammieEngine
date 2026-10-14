package;

/** One actor built ahead of time, with the slot position it was built at. */
typedef CharacterSlotEntry<T> = {
	var actor:T;
	var x:Float;
	var y:Float;
}

/** Characters built during loading for a later Change Character, keyed by
 * slot and name.  Building a Character reads its atlas and definition, which
 * hitches when it happens mid-song, so the swap takes a ready one instead.
 * Each actor is handed out once and the swap that takes it owns it from then
 * on; whatever is never taken is disposed on release. */
class CharacterSlotCache<T> {
	final waiting:Map<String, Array<CharacterSlotEntry<T>>> = new Map();
	final construct:String->String->Float->Float->T;
	final dispose:T->Void;
	/** Most actors kept for one slot and name, so a chart that swaps back and
	 * forth many times does not hold a copy for every swap. */
	public final limit:Int;

	public function new(construct:String->String->Float->Float->T, dispose:T->Void, limit:Int = 2) {
		this.construct = construct;
		this.dispose = dispose;
		this.limit = limit;
	}

	static inline function key(slot:String, name:String):String return slot + '|' + name;

	public function count(slot:String, name:String):Int {
		var list = waiting.get(key(slot, name));
		return list == null ? 0 : list.length;
	}

	/** Build actors at (x, y) until `wanted` of them wait for this slot and
	 * name (never more than the limit). Returns how many were built. */
	public function reserve(slot:String, name:String, x:Float, y:Float, wanted:Int = 1):Int {
		var id = key(slot, name);
		var list = waiting.get(id);
		if (list == null) {
			list = [];
			waiting.set(id, list);
		}
		var target = wanted < limit ? wanted : limit;
		var built = 0;
		while (list.length < target) {
			var actor = construct(slot, name, x, y);
			if (actor == null) break;
			list.push({actor: actor, x: x, y: y});
			built++;
		}
		return built;
	}

	/** Hand out the oldest ready actor, or null when none was built. */
	public function take(slot:String, name:String):Null<CharacterSlotEntry<T>> {
		var list = waiting.get(key(slot, name));
		return list == null || list.length == 0 ? null : list.shift();
	}

	/** Dispose every actor nobody took. */
	public function release():Void {
		for (list in waiting)
			for (entry in list)
				if (entry.actor != null) dispose(entry.actor);
		waiting.clear();
	}
}
