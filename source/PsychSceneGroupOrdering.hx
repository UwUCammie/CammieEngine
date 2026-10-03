package;

/** Preserve nested source group boundaries in a host with a flat display list.
 * This only orders members supplied by the owner; unrelated scene objects keep
 * their relative order and remain outside the group's occupied range. */
class PsychSceneGroupOrdering {
	public static function append<T>(scene:Array<T>, group:Array<T>, member:T, ?insert:Int->T->Void):Void {
		if (member == null || scene.indexOf(member) >= 0) return;
		var last = -1;
		for (child in group) if (child != null) last = Std.int(Math.max(last, scene.indexOf(child)));
		var position = last < 0 ? scene.length : last + 1;
		if (insert != null) insert(position, member);
		else scene.insert(position, member);
	}

	public static function sort<T>(scene:Array<T>, groups:Array<PsychSceneGroup<T>>):Void {
		var units:Array<{members:Array<T>, z:Float, position:Int}> = [];
		var owned:Array<T> = [];
		var first = scene.length;
		for (group in groups) {
			// Child order is the native draw order, independently of cache-map order.
			var children:Array<T> = [];
			var position = scene.length;
			for (i in 0...scene.length) {
				var child = scene[i];
				if (child != null && group.members.indexOf(child) >= 0 && owned.indexOf(child) < 0) {
					children.push(child); owned.push(child);
					if (i < position) position = i;
				}
			}
			if (children.length == 0) continue;
			if (position < first) first = position;
			units.push({members:children, z:group.z, position:position});
		}
		if (units.length == 0) return;
		units.sort(function(a, b) return a.z < b.z ? -1 : a.z > b.z ? 1 : a.position - b.position);
		var remaining = [for (child in scene) if (owned.indexOf(child) < 0) child];
		var ordered:Array<T> = [];
		for (unit in units) for (child in unit.members) ordered.push(child);
		for (i in 0...ordered.length) remaining.insert(first + i, ordered[i]);
		scene.resize(0);
		for (child in remaining) scene.push(child);
	}
}

typedef PsychSceneGroup<T> = {
	var members:Array<T>;
	var z:Float;
};
