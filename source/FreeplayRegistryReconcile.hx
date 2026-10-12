package;

/** Reuse only one-to-one retained identities. Ambiguity never borrows another owner's row. */
class FreeplayRegistryReconcile {
	public static function retained(oldKeys:Array<String>, newKeys:Array<String>):Array<Int> {
		var old:Map<String, Int> = [];
		var counts:Map<String, Int> = [];
		for (i in 0...oldKeys.length) {
			var key = oldKeys[i];
			if (key == null || key == '') continue;
			old.set(key, old.exists(key) ? -1 : i);
		}
		for (key in newKeys) if (key != null && key != '') counts.set(key, counts.exists(key) ? counts.get(key) + 1 : 1);
		return [for (key in newKeys) key != null && key != '' && counts.get(key) == 1 && old.exists(key) ? old.get(key) : -1];
	}
}
