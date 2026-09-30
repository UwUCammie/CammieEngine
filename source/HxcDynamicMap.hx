package;

/**
	Small map implementation exposed to generated HXC HScript.

	Haxe map literals allow object/class keys and preserve insertion order only
	through the donor runtime's implementation.  HScript has no equivalent
	`key => value` literal, so the compatibility pass materializes the authored
	pairs here instead of pretending they are an object literal.  Keeping the
	container engine-owned also means generated scripts cannot instantiate a
	donor map class or reach a global registry.
*/
class HxcDynamicMap {
	var keysData:Array<Dynamic> = [];
	var valuesData:Array<Dynamic> = [];

	public function new(?entries:Array<Dynamic>) {
		if (entries == null)
			return;
		for (entry in entries) {
			if (entry == null)
				continue;
			var pair:Array<Dynamic> = cast entry;
			if (pair != null && pair.length >= 2)
				set(pair[0], pair[1]);
		}
	}

	public function set(key:Dynamic, value:Dynamic):Void {
		var index = indexOf(key);
		if (index < 0) {
			keysData.push(key);
			valuesData.push(value);
		} else {
			valuesData[index] = value;
		}
	}

	public function get(key:Dynamic):Dynamic {
		var index = indexOf(key);
		if (index < 0)
			return null;
		var value = valuesData[index];
		if (Std.isOfType(value, HxcDeferredValue)) {
			value = (cast value:HxcDeferredValue).get();
			valuesData[index] = value;
		}
		return value;
	}

	public function exists(key:Dynamic):Bool {
		return indexOf(key) >= 0;
	}

	public function remove(key:Dynamic):Bool {
		var index = indexOf(key);
		if (index < 0)
			return false;
		keysData.splice(index, 1);
		valuesData.splice(index, 1);
		return true;
	}

	public function keys():Array<Dynamic> {
		return keysData.copy();
	}

	public function iterator():Iterator<Dynamic> {
		return keysData.iterator();
	}

	function indexOf(key:Dynamic):Int {
		for (index in 0...keysData.length)
			if (keysData[index] == key)
				return index;
		return -1;
	}
}
