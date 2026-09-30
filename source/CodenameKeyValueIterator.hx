package;

/** Snapshot the key/value pairs used by Codename's indexed Haxe `for` loops.
 * A snapshot evaluates the iterable once, as the source loop does. */
class CodenameKeyValueIterator {
	public static function facade():Dynamic {
		return {
			entries: function(value:Dynamic):Dynamic return entries(value),
			iterate: function(value:Dynamic):Dynamic return iterate(value),
			range: function(start:Int, stop:Int):Dynamic return range(start, stop)
		};
	}

	/** Lazy Haxe-style key/value iteration for imported class modules. Array
	 * values are read when next() advances, and hasNext() observes the live length.
	 * Map keys follow the map's own key iterator and values are looked up lazily.
	 */
	public static function iterate(value:Dynamic):Dynamic {
		if (value == null) throw '[codename-indexed-loop] Cannot iterate null';
		if (Std.isOfType(value, Array))
			return arrayPairs(cast value);
		if (Std.isOfType(value, CodenameMapCompat)) {
			var map:CodenameMapCompat = cast value;
			var keys:Array<Dynamic> = map.keys();
			return keyPairs(arrayValues(keys), function(key:Dynamic):Dynamic return map.get(key));
		}

		var keyValueIterator = Reflect.field(value, 'keyValueIterator');
		if (Reflect.isFunction(keyValueIterator)) {
			var pairs = Reflect.callMethod(value, keyValueIterator, []);
			return directPairs(pairs);
		}
		var keys = Reflect.field(value, 'keys');
		var get = Reflect.field(value, 'get');
		if (Reflect.isFunction(keys) && Reflect.isFunction(get)) {
			var keyIterator = Reflect.callMethod(value, keys, []);
			return keyPairs(keyIterator, function(key:Dynamic):Dynamic
				return Reflect.callMethod(value, get, [key]));
		}
		throw '[codename-indexed-loop] Iterable has no key/value iterator';
	}

	static function arrayPairs(items:Array<Dynamic>):Dynamic {
		var index = 0;
		return {
			hasNext: function():Bool return index < items.length,
			next: function():Dynamic {
				if (index >= items.length) throw '[codename-indexed-loop] Array iterator advanced past its live end';
				var key = index++;
				return {key:key, value:items[key]};
			}
		};
	}

	static function arrayValues(items:Array<Dynamic>):Dynamic {
		var index = 0;
		return {
			hasNext: function():Bool return index < items.length,
			next: function():Dynamic {
				if (index >= items.length) throw '[codename-indexed-loop] Key iterator advanced past its end';
				return items[index++];
			}
		};
	}

	static function keyPairs(keys:Dynamic, getValue:Dynamic->Dynamic):Dynamic {
		var hasNext = keys == null ? null : Reflect.field(keys, 'hasNext');
		var next = keys == null ? null : Reflect.field(keys, 'next');
		if (!Reflect.isFunction(hasNext) || !Reflect.isFunction(next))
			throw '[codename-indexed-loop] Map key iterator has no hasNext/next methods';
		return {
			hasNext: function():Bool return Reflect.callMethod(keys, hasNext, []),
			next: function():Dynamic {
				var key = Reflect.callMethod(keys, next, []);
				return {key:key, value:getValue(key)};
			}
		};
	}

	static function directPairs(pairs:Dynamic):Dynamic {
		var hasNext = pairs == null ? null : Reflect.field(pairs, 'hasNext');
		var next = pairs == null ? null : Reflect.field(pairs, 'next');
		if (!Reflect.isFunction(hasNext) || !Reflect.isFunction(next))
			throw '[codename-indexed-loop] Key/value iterator has no hasNext/next methods';
		return {
			hasNext: function():Bool return Reflect.callMethod(pairs, hasNext, []),
			next: function():Dynamic return Reflect.callMethod(pairs, next, [])
		};
	}

	/** HScript cannot reflect IntIterator's inline methods on native targets. */
	public static function range(start:Int, stop:Int):Dynamic {
		var cursor = start;
		return {
			hasNext: function():Bool return cursor < stop,
			next: function():Int return cursor++
		};
	}

	public static function entries(value:Dynamic):Array<{key:Dynamic, value:Dynamic}> {
		if (value == null) throw '[codename-indexed-loop] Cannot iterate null';
		var result:Array<{key:Dynamic, value:Dynamic}> = [];
		if (Std.isOfType(value, Array)) {
			var items:Array<Dynamic> = cast value;
			for (index in 0...items.length)
				result.push({key:index, value:items[index]});
			return result;
		}
		if (Std.isOfType(value, CodenameMapCompat)) {
			var map:CodenameMapCompat = cast value;
			for (key in map.keys()) result.push({key:key, value:map.get(key)});
			return result;
		}
		var keys = Reflect.field(value, 'keys');
		var get = Reflect.field(value, 'get');
		if (Reflect.isFunction(keys) && Reflect.isFunction(get)) {
			var iterator = Reflect.callMethod(value, keys, []);
			if (Std.isOfType(iterator, Array)) {
				for (key in (cast iterator:Array<Dynamic>))
					result.push({key:key, value:Reflect.callMethod(value, get, [key])});
				return result;
			}
			var hasNext = iterator == null ? null : Reflect.field(iterator, 'hasNext');
			var next = iterator == null ? null : Reflect.field(iterator, 'next');
			if (Reflect.isFunction(hasNext) && Reflect.isFunction(next)) {
				while (Reflect.callMethod(iterator, hasNext, [])) {
					var key = Reflect.callMethod(iterator, next, []);
					result.push({key:key, value:Reflect.callMethod(value, get, [key])});
				}
				return result;
			}
		}
		throw '[codename-indexed-loop] Iterable has no key/value iterator';
	}
}
