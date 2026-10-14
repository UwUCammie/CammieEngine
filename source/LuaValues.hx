package;

/**
	Several values travelling together, the way a Lua `return a, b` or a
	library call like string.find hands back more than one result.

	Only translated Lua scopes ever see one of these. Anything that wants a
	single value (an assignment, an operand, an engine callback result) takes
	`LuaValues.first(value)`, and the few places Lua expands a list (the last
	argument of a call, a multiple assignment) take `LuaValues.list(value)`.
*/
class LuaValues {
	public var values(default, null):Array<Dynamic>;

	public function new(values:Array<Dynamic>) {
		this.values = values == null ? [] : values;
	}

	/** Wrap a result list. A nested list in the last slot is flattened, as Lua does for `return a, f()`. */
	public static function of(values:Array<Dynamic>):LuaValues {
		if (values == null)
			return new LuaValues([]);
		var count = values.length;
		if (count > 0 && Std.isOfType(values[count - 1], LuaValues)) {
			var flat:Array<Dynamic> = [];
			for (index in 0...count - 1)
				flat.push(first(values[index]));
			for (value in (cast values[count - 1] : LuaValues).values)
				flat.push(value);
			return new LuaValues(flat);
		}
		var single:Array<Dynamic> = [];
		for (value in values)
			single.push(first(value));
		return new LuaValues(single);
	}

	public static inline function is(value:Dynamic):Bool {
		return Std.isOfType(value, LuaValues);
	}

	/** The one value a single-value context sees: the first result, or nil for an empty list. */
	public static function first(value:Dynamic):Dynamic {
		if (!Std.isOfType(value, LuaValues))
			return value;
		var values = (cast value : LuaValues).values;
		return values.length == 0 ? null : values[0];
	}

	/** Every result as a plain array. A plain value is a list of one. */
	public static function list(value:Dynamic):Array<Dynamic> {
		if (Std.isOfType(value, LuaValues))
			return (cast value : LuaValues).values.copy();
		return [value];
	}

	/** Result number `index` (zero based), nil when there are fewer results. */
	public static function at(value:Dynamic, index:Int):Dynamic {
		if (!Std.isOfType(value, LuaValues))
			return index == 0 ? value : null;
		var values = (cast value : LuaValues).values;
		return index >= 0 && index < values.length ? values[index] : null;
	}

	public function toString():String {
		var parts:Array<String> = [];
		for (value in values)
			parts.push(Std.string(value));
		return parts.join(', ');
	}
}
