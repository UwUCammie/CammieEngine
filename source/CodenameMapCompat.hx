package;

/** Small map surface for Codename Haxe map literals translated to HScript.
 * Object keys retain reference identity and iteration preserves source order. */
class CodenameMapCompat {
	var entries:Array<{key:Dynamic, value:Dynamic}> = [];

	public function new() {}

	public static function fromPairs(pairs:Array<Dynamic>):CodenameMapCompat {
		var result = new CodenameMapCompat();
		if (pairs != null) for (pair in pairs) {
			if (pair == null || !Reflect.hasField(pair, 'key') || !Reflect.hasField(pair, 'value'))
				throw '[codename-script-map] Invalid translated map entry';
			result.set(Reflect.field(pair, 'key'), Reflect.field(pair, 'value'));
		}
		return result;
	}

	public function keys():Array<Dynamic>
		return [for (entry in entries) entry.key];

	public function get(key:Dynamic):Dynamic {
		for (entry in entries) if (entry.key == key) return entry.value;
		return null;
	}

	public function exists(key:Dynamic):Bool {
		for (entry in entries) if (entry.key == key) return true;
		return false;
	}

	public function set(key:Dynamic, value:Dynamic):Void {
		for (entry in entries) if (entry.key == key) {
			entry.value = value;
			return;
		}
		entries.push({key:key, value:value});
	}

	public function copy():CodenameMapCompat {
		var result = new CodenameMapCompat();
		for (entry in entries) result.entries.push({key:entry.key, value:entry.value});
		return result;
	}
}
