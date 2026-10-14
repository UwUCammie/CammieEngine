package;

/** One script scope taking part in the ordered event broadcast. */
private typedef ScriptDispatchEntry = {
	var key:String;
	var rank:Int;
	var priority:Int;
	var id:String;
	var sequence:Int;
};

/**
	Broadcast order for V-Slice script scopes.

	V-Slice hands every gameplay event to modules first (lowest priority number
	first, then by id), then the song, song events, note kinds, the stage, the
	conversation and finally the characters, so a module always gets the first
	chance to cancel or stop an event. The scope table is a hash map with no
	order of its own, so this keeps the ordered key list beside it.

	The list is sorted only when a scope is added or removed. A broadcast calls
	arrange(), which writes the ordered keys into the slots the registered
	scopes already hold in the caller's key list: other scopes (Psych, Lua,
	Nightmare Vision, plain HScript) keep exactly the positions they had.
*/
class ScriptDispatchOrder {
	/** V-Slice's Module default when the constructor gives no priority. */
	public static inline var DEFAULT_MODULE_PRIORITY:Int = 1000;

	var entries:Map<String, ScriptDispatchEntry> = new Map();
	var ordered:Array<String> = [];
	var dirty:Bool = false;
	var nextSequence:Int = 0;

	public var count(default, null):Int = 0;

	public function new() {}

	/** Rank of a script family in the V-Slice event order; unknown families run last. */
	public static function familyRank(family:String):Int {
		return switch (family == null ? '' : family.toLowerCase()) {
			case 'module': 0;
			case 'song' | 'song-script': 1;
			case 'event' | 'song-event': 2;
			case 'note' | 'note-kind': 3;
			case 'stage': 4;
			case 'conversation' | 'dialogue': 5;
			case 'character': 6;
			default: 7;
		};
	}

	/** Add or replace one scope. Only modules use priority and id for their order. */
	public function register(key:String, family:String, ?priority:Null<Int>, ?id:String):Void {
		if (key == null)
			return;
		var rank = familyRank(family);
		if (!entries.exists(key))
			count++;
		entries.set(key, {
			key: key,
			rank: rank,
			priority: rank == 0 && priority != null ? priority : DEFAULT_MODULE_PRIORITY,
			id: id == null ? '' : id,
			sequence: nextSequence++
		});
		dirty = true;
	}

	public function remove(key:String):Void {
		if (key != null && entries.remove(key)) {
			count--;
			dirty = true;
		}
	}

	public function clear():Void {
		entries.clear();
		ordered.resize(0);
		count = 0;
		dirty = false;
	}

	public inline function has(key:String):Bool
		return entries.exists(key);

	/** The registered keys in dispatch order. Shared list; callers only read it. */
	public function orderedKeys():Array<String> {
		if (dirty)
			rebuild();
		return ordered;
	}

	/**
		Rewrite `keys` in place so the registered scopes it holds appear in
		dispatch order. `live` is the scope table: a registered key that is no
		longer in it is passed over, so a stale entry cannot take a live slot.
	*/
	public function arrange<T>(keys:Array<String>, live:Map<String, T>):Void {
		if (count == 0 || keys == null)
			return;
		var order = orderedKeys();
		var next = 0;
		for (index in 0...keys.length) {
			if (!entries.exists(keys[index]))
				continue;
			while (next < order.length && !live.exists(order[next]))
				next++;
			if (next >= order.length)
				return;
			keys[index] = order[next++];
		}
	}

	function rebuild():Void {
		ordered.resize(0);
		var list:Array<ScriptDispatchEntry> = [];
		for (entry in entries)
			list.push(entry);
		list.sort(compare);
		for (entry in list)
			ordered.push(entry.key);
		dirty = false;
	}

	static function compare(a:ScriptDispatchEntry, b:ScriptDispatchEntry):Int {
		if (a.rank != b.rank)
			return a.rank - b.rank;
		if (a.rank == 0) {
			if (a.priority != b.priority)
				return a.priority - b.priority;
			if (a.id != b.id)
				return a.id < b.id ? -1 : 1;
		}
		return a.sequence - b.sequence;
	}
}
