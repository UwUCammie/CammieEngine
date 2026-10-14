package;

import haxe.ds.ArraySort;

/**
	The Lua 5.1 standard library as translated scripts see it: the `string`,
	`math`, `table` and `os` tables plus the base functions (print, pcall,
	error, assert, unpack, select, next, rawget and friends).

	`install` binds them into a translated Lua scope as real tables, so a
	script can alias them (`local floor = math.floor`) or add its own fields
	(`math.lerp = function ... end`). The string and number work itself lives
	in EngineCompat (luaString*, luaNumber, luaType) and LuaPattern, which
	scripts in other languages share.

	os is kept to time, clock, date and difftime on purpose. Nothing here can
	touch files, run programs or load code.
*/
@:access(LuaCompatInterp)
@:access(hscript.Interp)
class LuaStdlib {
	public static var STRING_NAMES(default, null):Array<String> = [
		'len', 'sub', 'upper', 'lower', 'rep', 'reverse', 'byte', 'char', 'format', 'find', 'match', 'gmatch',
		'gsub'
	];
	public static var MATH_NAMES(default, null):Array<String> = [
		'abs', 'ceil', 'floor', 'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2', 'sinh', 'cosh', 'tanh',
		'exp', 'log', 'log10', 'pow', 'fmod', 'modf', 'deg', 'rad', 'max', 'min', 'ldexp', 'random', 'randomseed'
	];
	public static var TABLE_NAMES(default, null):Array<String> = ['insert', 'remove', 'concat', 'sort', 'getn', 'maxn', 'unpack'];
	public static var OS_NAMES(default, null):Array<String> = ['time', 'clock', 'date', 'difftime'];
	// STRING_NAMES as a lookup. Every `text:method()` call and string library
	// check asks this, and a list scan per call adds up in per-frame scripts.
	static var stringNameSet:haxe.ds.StringMap<Bool> = null;

	/** Whether `name` is a function of the Lua string library. */
	public static function isStringName(name:String):Bool {
		if (name == null)
			return false;
		var names = stringNameSet;
		if (names == null) {
			names = new haxe.ds.StringMap();
			for (entry in STRING_NAMES)
				names.set(entry, true);
			stringNameSet = names;
		}
		return names.exists(name);
	}

	static var weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
	static var months = [
		'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
		'December'
	];

	/**
		Bind the library tables and base functions into a translated Lua scope.
		Safe to call again: tables a script already extended are kept and only
		missing entries are filled in, and a global the scope already has (the
		engine's or the script's own) is left alone.
	*/
	public static function install(interp:LuaCompatInterp):Void {
		if (interp == null)
			return;
		library(interp, 'string', STRING_NAMES, function(name, args) return stringCall(name, args, interp));
		var math:Dynamic = library(interp, 'math', MATH_NAMES, function(name, args) return mathCall(name, args, interp));
		if (Reflect.field(math, 'huge') == null)
			Reflect.setField(math, 'huge', Math.POSITIVE_INFINITY);
		if (Reflect.field(math, 'pi') == null)
			Reflect.setField(math, 'pi', Math.PI);
		var table:Dynamic = library(interp, 'table', TABLE_NAMES, function(name, args) return tableCall(name, args, interp));
		library(interp, 'os', OS_NAMES, function(name, args) return osCall(name, args, interp));

		global(interp, 'print', function(args) {
			printLine(interp, [for (value in args) EngineCompat.luaString(value)].join('\t'));
			return null;
		});
		global(interp, 'tostring', function(args) return EngineCompat.luaString(args[0]));
		global(interp, 'tonumber', function(args) return EngineCompat.luaNumber(args[0], args[1]));
		global(interp, 'type', function(args) return EngineCompat.luaType(args[0]));
		global(interp, 'error', function(args):Dynamic {
			throw(args[0] == null ? 'nil' : args[0]);
		});
		global(interp, 'assert', function(args):Dynamic {
			if (!truthy(args[0]))
				throw(args.length > 1 && args[1] != null ? args[1] : 'assertion failed!');
			return results(args);
		});
		global(interp, 'pcall', function(args) return protectedCall(interp, args));
		global(interp, 'select', function(args):Dynamic {
			if (args[0] == '#')
				return args.length - 1;
			var index = integer(args[0], 'select');
			if (index < 0)
				index = args.length + index;
			if (index < 1)
				throw "bad argument #1 to 'select' (index out of range)";
			return new LuaValues(args.slice(index));
		});
		global(interp, 'unpack', function(args) return unpack(args, interp));
		// Lua 5.2 moved unpack here and plenty of scripts use that spelling.
		if (Reflect.field(table, 'unpack') == null)
			Reflect.setField(table, 'unpack', native(interp, function(args) return unpack(args, interp)));
		global(interp, 'next', function(args) return next(interp, args[0], args[1]));
		global(interp, 'rawget', function(args) return interp.readIndex(args[0], args[1]));
		global(interp, 'rawset', function(args):Dynamic {
			if (args[0] == null)
				throw "bad argument #1 to 'rawset' (table expected, got nil)";
			interp.writeIndex(args[0], args[1], args[2]);
			return args[0];
		});
		global(interp, 'rawequal', function(args):Dynamic return args[0] == args[1]);

		installScopedStringHelpers(interp);
	}

	/**
		The engine binds single-result spellings of these for every script
		language. A Lua scope understands result lists, so here they hand back
		everything Lua would (find's end index, gsub's count, every capture of
		match) and take any number of arguments. The game seeds its shared
		helpers after the scope is built, so it calls this again afterwards.
	*/
	public static function installScopedStringHelpers(interp:LuaCompatInterp):Void {
		if (interp == null)
			return;
		for (name in ['find', 'match', 'gsub', 'byte', 'char', 'format'])
			interp.variables.set('luaString' + name.charAt(0).toUpperCase() + name.substr(1),
				native(interp, function(args) return stringCall(name, args, interp)));
	}

	/** Wrap a library function so the scope passes it every result of a trailing call, as Lua does for any function. */
	static function native(interp:LuaCompatInterp, call:Array<Dynamic>->Dynamic):Dynamic {
		return interp.registerMultiValueFunction(Reflect.makeVarArgs(call));
	}

	/**
		A method call on a string value, `text:upper()` or `value:match(...)`.
		Lua looks the name up in the string library with the value as the first
		argument.
	*/
	public static function stringMethod(receiver:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		if (!isStringName(name))
			throw "attempt to call method '" + name + "' (a nil value)";
		var all:Array<Dynamic> = [receiver];
		if (args != null)
			for (value in args)
				all.push(value);
		return stringCall(name, all, null);
	}

	static function library(interp:LuaCompatInterp, name:String, names:Array<String>,
			call:String->Array<Dynamic>->Dynamic):Dynamic {
		var table:Dynamic = interp.variables.get(name);
		if (table == null || !interp.luaOwned(table) || Std.isOfType(table, Array)) {
			table = {};
			interp.luaTables.set(table, true);
			interp.variables.set(name, table);
		}
		for (entry in names)
			if (Reflect.field(table, entry) == null)
				Reflect.setField(table, entry, native(interp, function(args:Array<Dynamic>):Dynamic {
					return call(entry, args);
				}));
		return table;
	}

	static function global(interp:LuaCompatInterp, name:String, call:Array<Dynamic>->Dynamic):Void {
		if (interp.variables.get(name) != null)
			return;
		interp.variables.set(name, native(interp, call));
	}

	// ---------------------------------------------------------------- values

	static inline function isNumber(value:Dynamic):Bool {
		return Std.isOfType(value, Float);
	}

	static inline function truthy(value:Dynamic):Bool {
		return value != null && value != false;
	}

	static inline function at(args:Array<Dynamic>, index:Int):Dynamic {
		return index < args.length ? args[index] : null;
	}

	static function text(value:Dynamic):String {
		return value == null ? '' : Std.string(value);
	}

	static inline function whole(value:Float):Dynamic {
		return EngineCompat.luaWholeNumber(value);
	}

	static function number(value:Dynamic, what:String):Float {
		if (isNumber(value))
			return value;
		if (Std.isOfType(value, String)) {
			// Lua quietly turns numeric strings into numbers for arithmetic library calls.
			var parsed:Dynamic = EngineCompat.luaNumber(value);
			if (parsed != null)
				return parsed;
		}
		throw "bad argument to '" + what + "' (number expected, got " + EngineCompat.luaType(value) + ')';
	}

	static function integer(value:Dynamic, what:String):Int {
		return Std.int(number(value, what));
	}

	/** One value stays a plain value; anything else travels as a result list. */
	static function results(values:Array<Dynamic>):Dynamic {
		if (values == null)
			return null;
		return values.length == 1 ? values[0] : new LuaValues(values);
	}

	// ---------------------------------------------------------------- string

	static function stringCall(name:String, args:Array<Dynamic>, interp:LuaCompatInterp):Dynamic {
		var subject:Dynamic = at(args, 0);
		var second:Dynamic = at(args, 1);
		var third:Dynamic = at(args, 2);
		switch (name) {
			case 'len':
				return text(subject).length;
			case 'sub':
				return EngineCompat.luaStringSub(subject, second == null ? 1 : integer(second, 'sub'), third == null ? null : integer(third, 'sub'));
			case 'upper':
				return text(subject).toUpperCase();
			case 'lower':
				return text(subject).toLowerCase();
			case 'rep':
				return EngineCompat.luaStringRep(subject, second == null ? 0 : integer(second, 'rep'), third);
			case 'reverse':
				return EngineCompat.luaStringReverse(subject);
			case 'byte':
				return results(EngineCompat.luaStringBytes(subject, second == null ? null : integer(second, 'byte'),
					third == null ? null : integer(third, 'byte')));
			case 'char':
				return EngineCompat.luaStringChars(args);
			case 'format':
				return EngineCompat.luaStringFormatList(text(subject), args.slice(1));
			case 'find':
				var found = EngineCompat.luaStringFindAll(subject, second, third == null ? null : integer(third, 'find'), truthy(at(args, 3)));
				return found == null ? null : new LuaValues(found);
			case 'match':
				return results(EngineCompat.luaStringMatchAll(subject, second, third == null ? null : integer(third, 'match')));
			case 'gmatch':
				var matches = LuaPattern.gmatch(text(subject), text(second));
				var cursor = 0;
				// A real Lua iterator: every call hands back the next match, then nil.
				return Reflect.makeVarArgs(function(_:Array<Dynamic>):Dynamic {
					return cursor < matches.length ? results(matches[cursor++]) : null;
				});
			case 'gsub':
				var fourth:Dynamic = at(args, 3);
				// A replacement table is a script table, so it is read through the scope.
				var lookup:Dynamic->Dynamic->Dynamic = interp == null ? null : function(table:Dynamic, key:Dynamic):Dynamic {
					return interp.readIndex(table, key);
				};
				return new LuaValues(EngineCompat.luaStringGsubAll(subject, second, third,
					fourth == null ? null : integer(fourth, 'gsub'), lookup));
			default:
				throw "attempt to call field '" + name + "' (a nil value)";
		}
	}

	// ------------------------------------------------------------------ math

	/** math.max / math.min over any number of arguments. The winner is returned untouched, so an Int stays an Int. */
	public static function extreme(args:Array<Dynamic>, largest:Bool):Dynamic {
		var name = largest ? 'max' : 'min';
		if (args == null || args.length == 0)
			throw "bad argument #1 to '" + name + "' (number expected, got no value)";
		var best:Dynamic = args[0];
		var bestValue = number(best, name);
		for (index in 1...args.length) {
			var value = number(args[index], name);
			if (largest ? value > bestValue : value < bestValue) {
				best = args[index];
				bestValue = value;
			}
		}
		return isNumber(best) ? best : bestValue;
	}

	/**
		math.random without an engine random source behind it. No arguments
		gives a float in [0, 1), one gives 1..m, two give m..n.
	*/
	public static function random(?first:Dynamic, ?second:Dynamic):Dynamic {
		var roll = Math.random();
		if (first == null)
			return roll;
		var low = second == null ? 1 : integer(first, 'random');
		var high = integer(second == null ? first : second, 'random');
		if (high < low)
			throw "bad argument to 'random' (interval is empty)";
		return low + Std.int(Math.ffloor(roll * (high - low + 1)));
	}

	static function mathCall(name:String, args:Array<Dynamic>, interp:LuaCompatInterp):Dynamic {
		switch (name) {
			case 'max':
				return extreme(args, true);
			case 'min':
				return extreme(args, false);
			case 'random':
				// The engine seeds its own random source for replays, so use it whenever the scope has one.
				var engineRandom:Dynamic = interp == null ? null : interp.variables.get('luaMathRandom');
				if (engineRandom != null && Reflect.isFunction(engineRandom))
					return Reflect.callMethod(null, engineRandom, [
						at(args, 0) == null ? null : integer(args[0], name),
						at(args, 1) == null ? null : integer(args[1], name)
					]);
				return random(at(args, 0), at(args, 1));
			case 'randomseed':
				return null;
			default:
		}
		var original:Dynamic = at(args, 0);
		var x = number(original, name);
		switch (name) {
			case 'abs':
				if (Std.isOfType(original, Int))
					return whole(Math.abs(x));
				return Math.abs(x);
			case 'ceil':
				return whole(Math.fceil(x));
			case 'floor':
				return whole(Math.ffloor(x));
			case 'sqrt':
				return Math.sqrt(x);
			case 'sin':
				return Math.sin(x);
			case 'cos':
				return Math.cos(x);
			case 'tan':
				return Math.tan(x);
			case 'asin':
				return Math.asin(x);
			case 'acos':
				return Math.acos(x);
			case 'atan':
				return at(args, 1) == null ? Math.atan(x) : Math.atan2(x, number(args[1], name));
			case 'atan2':
				return Math.atan2(x, number(at(args, 1), name));
			case 'sinh':
				return (Math.exp(x) - Math.exp(-x)) / 2;
			case 'cosh':
				return (Math.exp(x) + Math.exp(-x)) / 2;
			case 'tanh':
				var grow = Math.exp(x), shrink = Math.exp(-x);
				return (grow - shrink) / (grow + shrink);
			case 'exp':
				return Math.exp(x);
			case 'log':
				return at(args, 1) == null ? Math.log(x) : Math.log(x) / Math.log(number(args[1], name));
			case 'log10':
				return Math.log(x) / Math.log(10);
			case 'pow':
				return Math.pow(x, number(at(args, 1), name));
			case 'fmod':
				return x % number(at(args, 1), name);
			case 'modf':
				var integral = x < 0 ? Math.fceil(x) : Math.ffloor(x);
				return new LuaValues([whole(integral), Math.isFinite(x) ? x - integral : 0.0]);
			case 'deg':
				return x * 180 / Math.PI;
			case 'rad':
				return x * Math.PI / 180;
			case 'ldexp':
				return x * Math.pow(2, number(at(args, 1), name));
			default:
				throw "attempt to call field '" + name + "' (a nil value)";
		}
	}

	// ----------------------------------------------------------------- table

	static function plainArray(table:Dynamic, interp:LuaCompatInterp):Bool {
		return Std.isOfType(table, Array) && (interp == null || !interp.luaOwned(table));
	}

	static function sequenceLength(table:Dynamic, interp:LuaCompatInterp):Int {
		if (interp != null)
			return interp.luaSequenceLength(table);
		if (!Std.isOfType(table, Array))
			return 0;
		var values:Array<Dynamic> = cast table;
		var count = 0;
		while (count < values.length && values[count] != null)
			count++;
		return count;
	}

	/** Read slot `index` (one based). Engine arrays are plain Haxe arrays underneath, script tables go through the scope. */
	static function sequenceGet(table:Dynamic, index:Int, interp:LuaCompatInterp):Dynamic {
		if (plainArray(table, interp)) {
			var values:Array<Dynamic> = cast table;
			return index >= 1 && index <= values.length ? values[index - 1] : null;
		}
		return interp == null ? null : interp.readIndex(table, index);
	}

	static function sequenceSet(table:Dynamic, index:Int, value:Dynamic, interp:LuaCompatInterp):Void {
		if (plainArray(table, interp))
			(cast table : Array<Dynamic>)[index - 1] = value;
		else if (interp != null)
			interp.writeIndex(table, index, value);
	}

	static function requireTable(table:Dynamic, what:String):Void {
		if (table == null || Std.isOfType(table, String) || isNumber(table) || Std.isOfType(table, Bool))
			throw "bad argument #1 to '" + what + "' (table expected, got " + EngineCompat.luaType(table) + ')';
	}

	/** table.remove: takes out slot `position` (the last one by default), closes the gap and returns what was there. */
	public static function remove(table:Dynamic, ?position:Null<Int>, ?interp:LuaCompatInterp):Dynamic {
		requireTable(table, 'remove');
		var length = sequenceLength(table, interp);
		if (length == 0)
			return null;
		var index = position == null ? length : position;
		if (index < 1 || index > length)
			return null;
		if (Std.isOfType(table, Array))
			return (cast table : Array<Dynamic>).splice(index - 1, 1)[0];
		var removed = sequenceGet(table, index, interp);
		for (slot in index...length)
			sequenceSet(table, slot, sequenceGet(table, slot + 1, interp), interp);
		sequenceSet(table, length, null, interp);
		return removed;
	}

	/** table.concat with the optional separator and one-based range. */
	public static function concat(table:Dynamic, ?separator:Dynamic, ?first:Null<Int>, ?last:Null<Int>,
			?interp:LuaCompatInterp):String {
		requireTable(table, 'concat');
		var glue = separator == null ? '' : Std.string(separator);
		var from = first == null ? 1 : first;
		var to = last == null ? sequenceLength(table, interp) : last;
		var output = new StringBuf();
		for (index in from...to + 1) {
			var value:Dynamic = sequenceGet(table, index, interp);
			if (!Std.isOfType(value, String) && !isNumber(value))
				throw "invalid value (at index " + index + ") in table for 'concat'";
			if (index > from)
				output.add(glue);
			output.add(Std.string(value));
		}
		return output.toString();
	}

	static function lessThan(left:Dynamic, right:Dynamic):Bool {
		if (isNumber(left) && isNumber(right))
			return (left : Float) < (right : Float);
		if (Std.isOfType(left, String) && Std.isOfType(right, String))
			return (left : String) < (right : String);
		throw 'attempt to compare ' + EngineCompat.luaType(left) + ' with ' + EngineCompat.luaType(right);
	}

	/** table.sort, in place. `comparator(a, b)` says whether a goes before b; without one, numbers and strings sort ascending. */
	public static function sort(table:Dynamic, ?comparator:Dynamic, ?interp:LuaCompatInterp):Void {
		requireTable(table, 'sort');
		var length = sequenceLength(table, interp);
		var values:Array<Dynamic> = [for (index in 1...length + 1) sequenceGet(table, index, interp)];
		var before:Dynamic->Dynamic->Bool = comparator == null ? lessThan : function(left:Dynamic, right:Dynamic):Bool {
			return truthy(LuaValues.first(Reflect.callMethod(null, comparator, [left, right])));
		};
		ArraySort.sort(values, function(left:Dynamic, right:Dynamic):Int {
			return before(left, right) ? -1 : before(right, left) ? 1 : 0;
		});
		for (index in 0...length)
			sequenceSet(table, index + 1, values[index], interp);
	}

	static function unpack(args:Array<Dynamic>, interp:LuaCompatInterp):Dynamic {
		var table:Dynamic = at(args, 0);
		requireTable(table, 'unpack');
		var from = at(args, 1) == null ? 1 : integer(args[1], 'unpack');
		var to = at(args, 2) == null ? sequenceLength(table, interp) : integer(args[2], 'unpack');
		return new LuaValues([for (index in from...to + 1) sequenceGet(table, index, interp)]);
	}

	static function tableCall(name:String, args:Array<Dynamic>, interp:LuaCompatInterp):Dynamic {
		var table:Dynamic = at(args, 0);
		switch (name) {
			case 'insert':
				var scoped:Dynamic = interp == null ? null : interp.variables.get('luaTableInsert');
				if (scoped != null && Reflect.isFunction(scoped))
					return Reflect.callMethod(null, scoped, args);
				requireTable(table, name);
				if (args.length == 2)
					(cast table : Array<Dynamic>).push(args[1]);
				else
					(cast table : Array<Dynamic>).insert(integer(args[1], name) - 1, args[2]);
				return null;
			case 'remove':
				return remove(table, at(args, 1) == null ? null : integer(args[1], name), interp);
			case 'concat':
				return concat(table, at(args, 1), at(args, 2) == null ? null : integer(args[2], name),
					at(args, 3) == null ? null : integer(args[3], name), interp);
			case 'sort':
				sort(table, at(args, 1), interp);
				return null;
			case 'getn':
				requireTable(table, name);
				return sequenceLength(table, interp);
			case 'maxn':
				requireTable(table, name);
				var largest:Float = sequenceLength(table, interp);
				if (interp != null)
					for (key in interp.pairKeys(table))
						if (isNumber(key) && (key : Float) > largest)
							largest = key;
				return whole(largest);
			case 'unpack':
				return unpack(args, interp);
			default:
				throw "attempt to call field '" + name + "' (a nil value)";
		}
	}

	// -------------------------------------------------------------------- os

	static function osCall(name:String, args:Array<Dynamic>, interp:LuaCompatInterp):Dynamic {
		switch (name) {
			case 'clock':
				return haxe.Timer.stamp();
			case 'time':
				var fields:Dynamic = at(args, 0);
				if (fields == null)
					return whole(Math.ffloor(Date.now().getTime() / 1000));
				var read = function(field:String, fallback:Int):Int {
					var value:Dynamic = interp == null ? Reflect.field(fields, field) : interp.readIndex(fields, field);
					return value == null ? fallback : integer(value, name);
				};
				// Like Lua, a date table without a time of day means noon.
				var moment = new Date(read('year', 1970), read('month', 1) - 1, read('day', 1), read('hour', 12),
					read('min', 0), read('sec', 0));
				return whole(Math.ffloor(moment.getTime() / 1000));
			case 'difftime':
				return number(at(args, 0), name) - (at(args, 1) == null ? 0 : number(args[1], name));
			case 'date':
				return date(at(args, 0), at(args, 1), interp);
			default:
				throw "attempt to call field '" + name + "' (a nil value)";
		}
	}

	/** os.date: strftime style text, or a field table for the `*t` format. A leading `!` asks for UTC. */
	public static function date(?template:Dynamic, ?time:Dynamic, ?interp:LuaCompatInterp):Dynamic {
		var pattern = template == null ? '%c' : Std.string(template);
		var moment = time == null ? Date.now() : Date.fromTime(number(time, 'date') * 1000.0);
		var utc = StringTools.startsWith(pattern, '!');
		if (utc)
			pattern = pattern.substr(1);
		var year = utc ? moment.getUTCFullYear() : moment.getFullYear();
		var month = utc ? moment.getUTCMonth() : moment.getMonth();
		var day = utc ? moment.getUTCDate() : moment.getDate();
		var hour = utc ? moment.getUTCHours() : moment.getHours();
		var minute = utc ? moment.getUTCMinutes() : moment.getMinutes();
		var second = utc ? moment.getUTCSeconds() : moment.getSeconds();
		var weekday = utc ? moment.getUTCDay() : moment.getDay();
		var leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
		var monthLengths = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
		var yearDay = day;
		for (index in 0...month)
			yearDay += monthLengths[index];

		if (StringTools.startsWith(pattern, '*t')) {
			var fields:Dynamic = {
				year: year,
				month: month + 1,
				day: day,
				hour: hour,
				min: minute,
				sec: second,
				wday: weekday + 1,
				yday: yearDay,
				isdst: false
			};
			if (interp != null)
				interp.luaTables.set(fields, true);
			return fields;
		}

		var two = function(value:Int):String return value < 10 ? '0' + value : Std.string(value);
		var clock = two(hour) + ':' + two(minute) + ':' + two(second);
		var shortDate = two(month + 1) + '/' + two(day) + '/' + two(year % 100);
		var output = new StringBuf();
		var index = 0;
		while (index < pattern.length) {
			var character = pattern.charAt(index++);
			if (character != '%' || index >= pattern.length) {
				output.add(character);
				continue;
			}
			var code = pattern.charAt(index++);
			output.add(switch (code) {
				case 'a': weekdays[weekday].substr(0, 3);
				case 'A': weekdays[weekday];
				case 'b': months[month].substr(0, 3);
				case 'B': months[month];
				case 'c': shortDate + ' ' + clock;
				case 'd': two(day);
				case 'H': two(hour);
				case 'I': two(hour % 12 == 0 ? 12 : hour % 12);
				case 'j': StringTools.lpad(Std.string(yearDay), '0', 3);
				case 'm': two(month + 1);
				case 'M': two(minute);
				case 'p': hour < 12 ? 'AM' : 'PM';
				case 'S': two(second);
				case 'w': Std.string(weekday);
				case 'x': shortDate;
				case 'X': clock;
				case 'y': two(year % 100);
				case 'Y': Std.string(year);
				case 'Z': '';
				case '%': '%';
				default: '%' + code;
			});
		}
		return output.toString();
	}

	// ------------------------------------------------------------- base functions

	static function printLine(interp:LuaCompatInterp, line:String):Void {
		var debugPrint:Dynamic = interp.variables.get('debugPrint');
		if (debugPrint != null && Reflect.isFunction(debugPrint)) {
			// The engine's on-screen log takes (text, colour); a broken overlay must not take the script down.
			try {
				Reflect.callMethod(null, debugPrint, [line, null]);
				return;
			} catch (_:Dynamic) {}
		}
		trace(line);
	}

	/**
		next() keeps the keys it took at the start of a walk and where it
		stopped, so stepping on is cheap and a key the loop just cleared, which
		Lua allows, does not end the walk. Fields cleared further ahead are
		skipped. Any other call takes the keys afresh.
	*/
	static function next(interp:LuaCompatInterp, table:Dynamic, key:Dynamic):Dynamic {
		var keys:Array<Dynamic>;
		var index:Int;
		var position = interp.nextPosition;
		if (key != null && interp.nextTable == table && interp.nextKeys != null && position > 0
			&& position <= interp.nextKeys.length && interp.nextKeys[position - 1] == key) {
			keys = interp.nextKeys;
			index = position;
		} else {
			keys = interp.pairKeys(table);
			index = 0;
			if (key != null) {
				index = -1;
				for (slot in 0...keys.length)
					if (keys[slot] == key) {
						index = slot + 1;
						break;
					}
				// A key that was never part of this walk ends it, the way it did before.
				if (index < 0)
					return null;
			}
		}
		while (index < keys.length) {
			var value:Dynamic = interp.luaPairsValue(table, keys[index]);
			if (value != null) {
				interp.nextTable = table;
				interp.nextKeys = keys;
				interp.nextPosition = index + 1;
				return new LuaValues([keys[index], value]);
			}
			index++;
		}
		interp.nextTable = null;
		interp.nextKeys = null;
		interp.nextPosition = 0;
		return null;
	}

	/**
		pcall: run a function and turn a thrown error into `false, message`
		instead of letting it end the callback.
	*/
	static function protectedCall(interp:LuaCompatInterp, args:Array<Dynamic>):Dynamic {
		var callee:Dynamic = at(args, 0);
		if (callee == null || !Reflect.isFunction(callee))
			return new LuaValues([false, 'attempt to call a ' + EngineCompat.luaType(callee) + ' value']);
		// A script function that throws half way leaves the scope pointing at
		// its own locals unless the interpreter knows it is inside a try, so
		// mark one and put everything back afterwards, like a script try block.
		var locals = interp.locals;
		var depth = interp.depth;
		var declared = interp.declared.length;
		var inTry = interp.inTry;
		interp.inTry = true;
		try {
			var value:Dynamic = Reflect.callMethod(null, callee, args.slice(1));
			interp.inTry = inTry;
			var all:Array<Dynamic> = [true];
			if (Std.isOfType(value, LuaValues))
				for (item in LuaValues.list(value))
					all.push(item);
			else
				all.push(value);
			return new LuaValues(all);
		} catch (error:Dynamic) {
			interp.inTry = inTry;
			interp.locals = locals;
			interp.depth = depth;
			interp.restore(declared);
			if (isControlFlow(error))
				throw error;
			return new LuaValues([false, errorValue(error)]);
		}
	}

	/** break, continue and return travel as interpreter exceptions; those are not script errors. */
	static function isControlFlow(error:Dynamic):Bool {
		if (!Reflect.isEnumValue(error))
			return false;
		try {
			var owner = Type.getEnum(error);
			if (owner == null)
				return false;
			var name = Type.getEnumName(owner);
			return name != null && StringTools.endsWith(name, 'Stop');
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** What pcall hands back: a thrown string, number, boolean or table as is, anything else as text. */
	static function errorValue(error:Dynamic):Dynamic {
		if (error == null)
			return 'nil';
		if (Std.isOfType(error, String) || isNumber(error) || Std.isOfType(error, Bool) || Std.isOfType(error, Array))
			return error;
		try {
			switch (Type.typeof(error)) {
				case TObject: return error;
				default:
			}
		} catch (_:Dynamic) {}
		return Std.string(error);
	}
}
