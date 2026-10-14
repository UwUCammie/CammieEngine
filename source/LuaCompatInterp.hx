package;

import hscript.Expr;
import hscript.Interp;
import hscript.Tools;
import haxe.Constraints.IMap;
import haxe.ds.ObjectMap;
import haxe.ds.StringMap;

/** Lua table and truth-value rules for translated Lua scopes only. */
class LuaCompatInterp extends Interp {
	var luaTables:ObjectMap<Dynamic, Bool> = new ObjectMap();
	var extraFields:ObjectMap<Dynamic, StringMap<Dynamic>> = new ObjectMap();
	var objectFields:ObjectMap<Dynamic, ObjectMap<Dynamic, Dynamic>> = new ObjectMap();
	var extraOrder:ObjectMap<Dynamic, Array<Dynamic>> = new ObjectMap();
	public var smokeDiagnosticsEnabled:Bool = false;
	public var lastSongPositionCallProbe:String = '';
	var nilArithmeticProbeEmitted:Bool = false;
	// Functions that take every result of a trailing call, like Lua functions do.
	// Translated Lua functions are added as they are created; closures a script
	// builds every frame must not pile up here, hence the weak map where one exists.
	#if cpp
	var multiCallees:haxe.ds.WeakMap<Dynamic, Bool> = new haxe.ds.WeakMap();
	#else
	var multiCallees:ObjectMap<Dynamic, Bool> = new ObjectMap();
	#end
	// True while the running Lua function was called from a spot that reads all
	// of its results. Everything else, the engine included, gets the first one.
	var multiWanted:Bool = false;
	var returnSlot:Expr = null;
	var methodCallHelper:Dynamic = null;
	var seededFunctions:StringMap<Bool> = null;
	// Metatables the script set. Stays null until the first setmetatable, so
	// scripts that never use one pay nothing on table reads and writes.
	var metatables:ObjectMap<Dynamic, Dynamic> = null;
	// The keys a pairs loop walks, taken once when the loop starts. Working
	// them out again on every step made each loop quadratic. A few slots, so a
	// loop over another table inside the body does not drop the outer walk.
	var walkTables:Array<Dynamic> = [for (_ in 0...WALK_SLOTS) null];
	var walkKeyLists:Array<Array<Dynamic>> = [for (_ in 0...WALK_SLOTS) null];
	var walkCursor:Int = 0;
	static inline var WALK_SLOTS = 8;
	// Same for next(): where the last step stopped, so the walk can go on
	// after the loop clears the key it is standing on.
	var nextTable:Dynamic = null;
	var nextKeys:Array<Dynamic> = null;
	var nextPosition:Int = 0;

	public function new() {
		super();
		for (op in ['+', '-', '*', '/', '%', '>', '<', '>=', '<='])
			binops.set(op, function(left:Expr, right:Expr):Dynamic {
				return luaArithmetic(op, left, right);
			});
		installTableHelpers();
	}

	function luaArithmetic(op:String, left:Expr, right:Expr):Dynamic {
		var a:Dynamic = expr(left);
		// Lua's `a // b` arrives as `a / __luaFloorDivisor(b)`, which keeps the
		// precedence of `/` without needing an operator HScript does not have.
		var floorDivision = false;
		if (op == '/')
			switch (Tools.expr(right)) {
				case ECall(marker, [divisor]) if (isFloorDivisor(marker)):
					right = divisor;
					floorDivision = true;
				default:
			}
		var b:Dynamic = expr(right);
		if (a == null || b == null) {
			if (smokeDiagnosticsEnabled && !nilArithmeticProbeEmitted) {
				nilArithmeticProbeEmitted = true;
				var source = variables.get('__compatDiagnosticSource');
				var callback = variables.get('__compatDiagnosticCallback');
				trace('[lua-arithmetic-probe] source=' + (source == null ? '' : Std.string(source))
					+ ' callback=' + (callback == null ? '' : Std.string(callback))
					+ ' op=' + op + ' leftAst=' + expressionSummary(left)
					+ ' rightAst=' + expressionSummary(right)
					+ ' left=' + diagnosticValue(a) + ' right=' + diagnosticValue(b)
					+ ' getSongPosition=' + diagnosticValue(variables.get('getSongPosition'))
					+ ' songPos=' + diagnosticValue(variables.get('songPos'))
					+ ' crochet=' + diagnosticValue(variables.get('crochet'))
					+ ' callProbe=' + (lastSongPositionCallProbe == '' ? '<none>' : lastSongPositionCallProbe));
			}
			var missingOperand = a == null && b == null ? 'left and right operands'
				: a == null ? 'left operand' : 'right operand';
			throw 'lua arithmetic on nil (' + op + ', ' + missingOperand + ')';
		}
		if (Std.isOfType(a, String) || Std.isOfType(b, String)) {
			switch (op) {
				case '+':
					// Lua only ever adds, so a number plus a numeric string is a sum.
					if (Std.isOfType(a, String) != Std.isOfType(b, String)) {
						var number:Dynamic = luaNumericString(Std.isOfType(a, String) ? a : b);
						if (number != null) {
							if (Std.isOfType(a, String)) a = number; else b = number;
						}
					} else if (!concatOperand(left) && !concatOperand(right)) {
						// Two numeric strings add as well. Translated `..` always has a
						// quoted or `"" + x` operand, so joining text never lands here.
						var leftNumber:Dynamic = luaNumericString(a);
						var rightNumber:Dynamic = leftNumber == null ? null : luaNumericString(b);
						if (rightNumber != null) {
							a = leftNumber;
							b = rightNumber;
						}
					}
				case '-' | '*' | '/' | '%':
					if (Std.isOfType(a, String)) {
						var leftNumber:Dynamic = luaNumericString(a);
						if (leftNumber != null) a = leftNumber;
					}
					if (Std.isOfType(b, String)) {
						var rightNumber:Dynamic = luaNumericString(b);
						if (rightNumber != null) b = rightNumber;
					}
				default:
			}
		}
		return switch (op) {
			case '+': a + b;
			case '/': floorDivision ? luaFloorDivide(a, b) : a / b;
			case '>': a > b;
			case '<': a < b;
			case '>=': a >= b;
			case '<=': a <= b;
			case '%': luaModulo(a, b);
			default: dpFloatAwareArith(op, a, b);
		};
	}

	static function isFloorDivisor(marker:Expr):Bool {
		return switch (Tools.expr(marker)) {
			case EIdent('__luaFloorDivisor'): true;
			default: false;
		};
	}

	static function luaFloorDivide(a:Dynamic, b:Dynamic):Dynamic {
		var left:Float = a;
		var right:Float = b;
		return EngineCompat.luaWholeNumber(Math.ffloor(left / right));
	}

	/** Whether an operand of `+` is one of the ways translated `..` spells text. */
	static function concatOperand(operand:Expr):Bool {
		return switch (Tools.expr(operand)) {
			case EConst(CString(_)): true;
			case EParent(inner): concatOperand(inner);
			case EBinop('+', left, right): concatOperand(left) || concatOperand(right);
			default: false;
		};
	}

	/** The number a Lua string turns into inside arithmetic, or null when it is not one. */
	static function luaNumericString(value:String):Dynamic {
		var text = StringTools.trim(value);
		if (~/^[+-]?0[xX][0-9A-Fa-f]+$/.match(text)) {
			var negative = text.charAt(0) == '-';
			var digits = text.charAt(0) == '-' || text.charAt(0) == '+' ? text.substr(1) : text;
			var parsed:Null<Int> = Std.parseInt(digits);
			return parsed == null ? null : (negative ? -parsed : parsed);
		}
		if (~/^[+-]?[0-9]+$/.match(text) && text.length < 10)
			return Std.parseInt(text.charAt(0) == '+' ? text.substr(1) : text);
		if (~/^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/.match(text))
			return Std.parseFloat(text);
		return null;
	}

	/** Lua's `%` takes the sign of the divisor: -1 % 5 is 4, where Haxe gives -1. */
	static function luaModulo(a:Dynamic, b:Dynamic):Dynamic {
		if (Std.isOfType(a, Int) && Std.isOfType(b, Int)) {
			var left:Int = a;
			var right:Int = b;
			if (right == 0)
				return Math.NaN;
			var rest = left % right;
			if (rest != 0 && ((rest < 0) != (right < 0)))
				rest += right;
			return rest;
		}
		var left:Float = a;
		var right:Float = b;
		if (right == 0)
			return Math.NaN;
		var rest = left % right;
		if (rest != 0 && ((rest < 0) != (right < 0)))
			rest += right;
		return rest;
	}


	/** Let a native helper receive every result of a trailing call, e.g. `f(g())`. */
	public function registerMultiValueFunction(fn:Dynamic):Dynamic {
		if (fn != null)
			multiCallees.set(fn, true);
		return fn;
	}

	function acceptsMultipleValues(fn:Dynamic):Bool {
		return fn != null && Reflect.isFunction(fn) && multiCallees.exists(fn);
	}

	/**
		Whether a call to `fn` can hand back several results. Lua functions and
		the Lua library do. An engine function never does, and a callback it
		runs along the way must not think the engine reads more than one.
	*/
	function returnsMultipleValues(fn:Dynamic):Bool {
		return fn != null && (fn == methodCallHelper || acceptsMultipleValues(fn));
	}

	/**
		Run one call the way Lua does: the function expression first, then the
		arguments, and a call in the last argument slot hands over all of its
		results when the callee can take them. `wantMulti` says whether the caller
		reads every result; if not, a Lua function called here returns just one.
	*/
	function callValues(target:Expr, params:Array<Expr>, wantMulti:Bool):Dynamic {
		var receiver:Dynamic = null;
		var field:String = null;
		var callee:Dynamic = null;
		// A method is looked up once, then called directly. A string receiver
		// has no Haxe method to find and goes through fcall to the string library.
		var resolved = true;
		switch (Tools.expr(target)) {
			case EField(owner, name):
				receiver = expr(owner);
				if (receiver == null) {
					nullAccessDiagnose('call', name);
					return null;
				}
				field = name;
				resolved = Std.isOfType(receiver, String);
			default:
				callee = expr(target);
		}
		var args:Array<Dynamic> = [];
		var last = params.length - 1;
		for (index in 0...params.length) {
			var param = params[index];
			if (index == last) {
				switch (Tools.expr(param)) {
					case ECall(innerTarget, innerParams):
						if (!resolved) {
							callee = get(receiver, field);
							resolved = true;
						}
						var accepts = takesEveryResult(callee, receiver, field, args);
						var value:Dynamic = callValues(innerTarget, innerParams, accepts);
						if (!Std.isOfType(value, LuaValues))
							args.push(value);
						else if (accepts)
							for (item in (cast value : LuaValues).values)
								args.push(item);
						else
							args.push(LuaValues.first(value));
						continue;
					default:
				}
			}
			args.push(expr(param));
		}
		if (!resolved) {
			callee = get(receiver, field);
			resolved = true;
		}
		var saved = multiWanted;
		multiWanted = wantMulti && returnsMultipleValues(callee);
		var result:Dynamic = null;
		try {
			result = field == null ? call(null, callee, args)
				: callee != null ? call(receiver, callee, args) : fcall(receiver, field, args);
		} catch (error:Dynamic) {
			multiWanted = saved;
			throw error;
		}
		multiWanted = saved;
		if (smokeDiagnosticsEnabled && params.length == 0 && isSongPositionCall(target))
			lastSongPositionCallProbe = 'callback='
				+ diagnosticValue(variables.get('__compatDiagnosticCallback'))
				+ ' callee=' + diagnosticValue(callee)
				+ ' result=' + diagnosticValue(result)
				+ ' songPos=' + diagnosticValue(variables.get('songPos'));
		return result;
	}

	/**
		Whether a call hands the callee every result of a trailing call. Lua
		functions and the library do; `obj:method(f())` on a worked-out receiver
		asks the method itself, and string methods are the string library.
	*/
	function takesEveryResult(callee:Dynamic, receiver:Dynamic, field:String, args:Array<Dynamic>):Bool {
		if (field != null && Std.isOfType(receiver, String))
			return LuaStdlib.STRING_NAMES.indexOf(field) >= 0;
		if (callee == methodCallHelper && callee != null && args.length >= 2) {
			var self:Dynamic = args[0];
			if (Std.isOfType(self, String))
				return LuaStdlib.STRING_NAMES.indexOf(Std.string(args[1])) >= 0;
			return self != null && acceptsMultipleValues(get(self, Std.string(args[1])));
		}
		return acceptsMultipleValues(callee);
	}

	/** Names the engine bound before the script ran, so `_G` writes cannot swap out engine functions. */
	override public function execute(program:Expr):Dynamic {
		if (seededFunctions == null) {
			seededFunctions = new StringMap();
			for (name in variables.keys())
				if (Reflect.isFunction(variables.get(name)))
					seededFunctions.set(name, true);
		}
		return super.execute(program);
	}

	static function readOnlyGlobal(key:String):Bool {
		return ~/^default(?:Player|Opponent)?Strum(?:[XY][0-9]+|[0-9]+[XY])$/.match(key);
	}

	/** `_G[key]` read: the script's own globals, plus the few names the engine routes itself. */
	function luaGlobalGet(name:Dynamic):Dynamic {
		if (name == null)
			return null;
		var key = Std.string(name);
		if (key == 'objects' || readOnlyGlobal(key)) {
			var routed:Dynamic = variables.get('luaGetScriptGlobal');
			var value:Dynamic = routed == null ? null : Reflect.callMethod(null, routed, [key]);
			if (value != null)
				return value;
		}
		return variables.get(key);
	}

	/** `_G[key] = value` write. Engine functions and the default strum slots stay as they are. */
	function luaGlobalSet(name:Dynamic, value:Dynamic):Bool {
		if (name == null)
			return false;
		var key = Std.string(name);
		if (readOnlyGlobal(key))
			return false;
		if (key == 'objects') {
			var routed:Dynamic = variables.get('luaSetScriptGlobal');
			if (routed != null)
				return Reflect.callMethod(null, routed, [key, value]) == true;
		}
		var current:Dynamic = variables.get(key);
		if (current != null && Reflect.isFunction(current)
			&& (seededFunctions == null || seededFunctions.exists(key)) && !acceptsMultipleValues(current))
			return false;
		variables.set(key, value);
		return true;
	}


	/** Turn the expression list of a generic `for` into one step function. */
	function luaIterator(args:Array<Dynamic>):Dynamic {
		var source:Dynamic = args.length == 0 ? null : args[0];
		if (source != null && Reflect.isFunction(source)) {
			var state:Dynamic = args.length > 1 ? args[1] : null;
			var control:Dynamic = args.length > 2 ? args[2] : null;
			return registerMultiValueFunction(function():Dynamic {
				// The loop reads every result, but only a Lua iterator has more than one.
				multiWanted = multiWanted && acceptsMultipleValues(source);
				var step:Dynamic = Reflect.callMethod(null, source, [state, control]);
				control = LuaValues.first(step);
				return step;
			});
		}
		if (Std.isOfType(source, Array)) {
			// A ready-made list of matches: one entry per step, a list entry being
			// the captures of that match.
			var list:Array<Dynamic> = cast source;
			var position = 0;
			return function():Dynamic {
				if (position >= list.length)
					return null;
				var item:Dynamic = list[position++];
				return Std.isOfType(item, Array) && !luaOwned(item) ? new LuaValues((cast item : Array<Dynamic>).copy()) : item;
			};
		}
		throw 'lua for-in needs an iterator function';
	}

	static function diagnosticValue(value:Dynamic):String {
		if (value == null)
			return 'nil';
		return switch (Type.typeof(value)) {
			case TInt | TFloat | TBool | TClass(String): Std.string(value);
			default: Std.string(Type.typeof(value));
		};
	}

	static function expressionSummary(expression:Expr):String {
		return switch (Tools.expr(expression)) {
			case EIdent(name): 'ident(' + name + ')';
			case EParent(inner): 'parent(' + expressionSummary(inner) + ')';
			case ECall(target, params): 'call(' + expressionSummary(target) + ',argc=' + params.length + ')';
			case EBinop(op, _, _): 'binop(' + op + ')';
			default: Std.string(Type.enumConstructor(Tools.expr(expression)));
		};
	}

	/** Lua reads an unset global as nil; keep that rule inside Lua scopes. */
	override function resolve(id:String):Dynamic {
		if (locals.get(id) == null && !variables.exists(id))
			return null;
		return super.resolve(id);
	}

	/** Reapply after the shared PlayState bindings, which seed base fallbacks. */
	public function installTableHelpers():Void {
		var legacyClear:Dynamic = variables.get('luaTableClear');
		var legacyCopy:Dynamic = variables.get('luaTableCopy');
		variables.set('luaPairsLength', luaPairsLength);
		variables.set('luaPairsKey', luaPairsKey);
		variables.set('luaPairsValue', luaPairsValue);
		variables.set('luaIpairsLength', luaIpairsLength);
		variables.set('luaIpairsKey', luaIpairsKey);
		variables.set('luaIpairsValue', luaIpairsValue);
		variables.set('luaSequenceLength', luaSequenceLength);
		variables.set('luaGlobalGet', luaGlobalGet);
		variables.set('luaGlobalSet', luaGlobalSet);
		// Real metatables here; the shared seed only copies fields across.
		variables.set('luaSetMetatable', luaSetMetatable);
		variables.set('luaGetMetatable', luaGetMetatable);
		// Read through by `/` itself; bound so a stray use is plain division.
		variables.set('__luaFloorDivisor', function(value:Dynamic):Dynamic return value);
		variables.set('luaValues', registerMultiValueFunction(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			return LuaValues.of(args);
		})));
		// `a, b = f()`: exactly `count` slots, padded with nil or cut short.
		variables.set('luaAssignValues', registerMultiValueFunction(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			var count:Int = args.length == 0 ? 0 : Std.int(args[0]);
			var values = LuaValues.of(args.slice(1)).values;
			var slots:Array<Dynamic> = [];
			for (index in 0...count)
				slots.push(index < values.length ? values[index] : null);
			return slots;
		})));
		variables.set('luaIterator', registerMultiValueFunction(Reflect.makeVarArgs(luaIterator)));
		variables.set('luaVarargsValues', function(list:Dynamic):Dynamic {
			return new LuaValues(Std.isOfType(list, Array) ? (cast list : Array<Dynamic>).copy() : []);
		});
		// A Lua function declared with `...`: the extra arguments arrive as one list.
		variables.set('luaVarargFunction', function(fixed:Int, body:Dynamic):Dynamic {
			return registerMultiValueFunction(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
				var call:Array<Dynamic> = [];
				for (index in 0...fixed)
					call.push(index < args.length ? args[index] : null);
				call.push(args.length > fixed ? args.slice(fixed) : []);
				return Reflect.callMethod(null, body, call);
			}));
		});
		methodCallHelper = Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			var receiver:Dynamic = args[0];
			var name:String = Std.string(args[1]);
			if (receiver == null) {
				nullAccessDiagnose('call', name);
				return null;
			}
			var rest = args.slice(2);
			// `text:upper()` is the string library called with the text first.
			if (Std.isOfType(receiver, String))
				return LuaStdlib.stringMethod(receiver, name, rest);
			var method:Dynamic = get(receiver, name);
			if (method == null) {
				nullAccessDiagnose('call', name);
				return null;
			}
			rest.unshift(receiver);
			// Same rule as any other call: an engine method has one result.
			multiWanted = multiWanted && acceptsMultipleValues(method);
			return call(receiver, method, rest);
		});
		variables.set('luaMethodCall', methodCallHelper);
		// The string, math, table and os tables plus print, pcall, select, next
		// and friends. After the helpers above so the library can build on them.
		LuaStdlib.install(this);
		if (!variables.exists('pairs'))
			variables.set('pairs', function(table:Dynamic):Dynamic {
				return new LuaValues([variables.get('next'), table, null]);
			});
		if (!variables.exists('ipairs'))
			variables.set('ipairs', function(table:Dynamic):Dynamic {
				var step = function(list:Dynamic, index:Dynamic):Dynamic {
					var next:Int = Std.int(index) + 1;
					var value:Dynamic = luaIpairsValue(list, next);
					return value == null ? null : new LuaValues([next, value]);
				};
				return new LuaValues([step, table, 0]);
			});
		variables.set('luaTableInsert', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			if (args.length != 2 && args.length != 3) throw 'table.insert expects two or three arguments';
			var table = args[0];
			if (table == null || (!luaOwned(table) && !Std.isOfType(table, Array)))
				throw 'table.insert expects a table';
			var length = luaSequenceLength(table);
			var position:Dynamic = args.length == 2 ? length + 1 : args[1];
			if ((!Std.isOfType(position, Int) && !Std.isOfType(position, Float))
				|| !Math.isFinite(position) || position != Std.int(position) || position < 1 || position > length + 1)
				throw 'table.insert position is out of bounds';
			var index:Int = Std.int(position);
			var value = args[args.length - 1];
			if (Std.isOfType(table, Array) && !luaOwned(table))
				(cast table:Array<Dynamic>).insert(index - 1, value);
			else {
				var cursor = length;
				while (cursor >= index) {
					writeIndex(table, cursor + 1, readIndex(table, cursor));
					cursor--;
				}
				writeIndex(table, index, value);
			}
			return null;
		}));
		variables.set('luaTableClear', function(table:Dynamic):Void {
			if (luaOwned(table))
				clearOwned(table);
			else if (legacyClear != null)
				Reflect.callMethod(null, legacyClear, [table]);
		});
		variables.set('luaTableCopy', function(source:Dynamic, ?destination:Dynamic,
			?copyMeta:Dynamic, ?depth:Dynamic):Dynamic {
			if (luaOwned(source))
				return copyOwned(source, destination, copyMeta != false, [], []);
			return legacyCopy == null ? source
				: Reflect.callMethod(null, legacyCopy, [source, destination, copyMeta, depth]);
		});
	}

	/**
		Mirror llua's Haxe-Array-to-Lua-table return conversion for source APIs.
		Native HScript arrays keep their zero-based behavior everywhere else.
	*/
	public function sourceApiResult(value:Dynamic):Dynamic {
		if (!Std.isOfType(value, Array) || luaOwned(value))
			return value;
		return snapshotSourceArray(value, new ObjectMap<Dynamic, Dynamic>());
	}

	function snapshotSourceArray(value:Dynamic, seen:ObjectMap<Dynamic, Dynamic>):Dynamic {
		if (!Std.isOfType(value, Array) || luaOwned(value))
			return value;
		var previous = seen.get(value);
		if (previous != null)
			return previous;

		var output:Array<Dynamic> = [];
		seen.set(value, output);
		luaTables.set(output, true);
		for (element in (cast value : Array<Dynamic>))
			output.push(snapshotSourceArray(element, seen));
		return output;
	}

	/**
		`text:upper()` reaches here as `text.upper(text)`. A Haxe string has no
		such method, so a string receiver with a Lua string library name is that
		library call.
	*/
	override function fcall(object:Dynamic, field:String, args:Array<Dynamic>):Dynamic {
		if (Std.isOfType(object, String) && LuaStdlib.STRING_NAMES.indexOf(field) >= 0)
			return LuaStdlib.stringMethod(object, field, args.length > 0 && args[0] == object ? args.slice(1) : args);
		return super.fcall(object, field, args);
	}

	/**
		Translated callbacks can also sit inside a script that keeps an ordinary
		interpreter. Give that interpreter the helper names the translator emits,
		without result lists or Lua tables: a call there has one result.
	*/
	public static function seedPlainHelpers(interp:Interp):Void {
		var variables = interp.variables;
		function seed(name:String, value:Dynamic):Void {
			if (!variables.exists(name))
				variables.set(name, value);
		}
		seed('luaValues', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic return args.length == 0 ? null : args[0]));
		seed('luaAssignValues', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			var count:Int = args.length == 0 ? 0 : Std.int(args[0]);
			return [for (index in 0...count) index + 1 < args.length ? args[index + 1] : null];
		}));
		seed('luaMethodCall', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			var receiver:Dynamic = args[0];
			var name:String = Std.string(args[1]);
			if (receiver == null)
				return null;
			if (Std.isOfType(receiver, String))
				return LuaValues.first(LuaStdlib.stringMethod(receiver, name, args.slice(2)));
			var method:Dynamic = Reflect.getProperty(receiver, name);
			if (method == null)
				return null;
			var rest = args.slice(2);
			rest.unshift(receiver);
			return Reflect.callMethod(receiver, method, rest);
		}));
		seed('luaGlobalGet', function(name:Dynamic):Dynamic return name == null ? null : variables.get(Std.string(name)));
		seed('luaGlobalSet', function(name:Dynamic, value:Dynamic):Bool {
			if (name == null || readOnlyGlobal(Std.string(name)) || Reflect.isFunction(variables.get(Std.string(name))))
				return false;
			variables.set(Std.string(name), value);
			return true;
		});
	}

	static function truthy(value:Dynamic):Bool {
		if (value == null)
			return false;
		return Std.isOfType(value, Bool) ? value == true : true;
	}

	function luaOwned(value:Dynamic):Bool {
		return value != null && luaTables.exists(value);
	}

	static function extraKey(key:Dynamic):String {
		if (Std.isOfType(key, String))
			return 'string:' + key;
		if (Std.isOfType(key, Int) || Std.isOfType(key, Float))
			return 'number:' + key;
		if (Std.isOfType(key, Bool))
			return 'boolean:' + key;
		throw 'unsupported Lua table key type';
	}

	static function objectKey(key:Dynamic):Bool {
		return key != null && !Std.isOfType(key, String)
			&& !Std.isOfType(key, Int) && !Std.isOfType(key, Float)
			&& !Std.isOfType(key, Bool) && Reflect.isObject(key);
	}

	function readExtra(table:Dynamic, key:Dynamic):Dynamic {
		if (objectKey(key)) {
			var objects = objectFields.get(table);
			return objects == null ? null : objects.get(key);
		}
		var fields = extraFields.get(table);
		return fields == null || key == null ? null : fields.get(extraKey(key));
	}

	function writeExtra(table:Dynamic, key:Dynamic, value:Dynamic):Void {
		if (key == null)
			return;
		var previous = readExtra(table, key);
		if (objectKey(key)) {
			var objects = objectFields.get(table);
			if (objects == null) {
				objects = new ObjectMap();
				objectFields.set(table, objects);
			}
			if (value == null)
				objects.remove(key);
			else
				objects.set(key, value);
		} else {
			var fields = extraFields.get(table);
			if (fields == null) {
				fields = new StringMap();
				extraFields.set(table, fields);
			}
			var field = extraKey(key);
			if (value == null)
				fields.remove(field);
			else
				fields.set(field, value);
		}
		var order = extraOrder.get(table);
		if (order == null) {
			order = [];
			extraOrder.set(table, order);
		}
		if (previous == null && value != null)
			order.push(key);
		else if (previous != null && value == null)
			order.remove(key);
	}

	function pairKeys(table:Dynamic):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (table == null)
			return result;
		if (Std.isOfType(table, Array)) {
			var values:Array<Dynamic> = cast table;
			for (index in 0...values.length)
				if (values[index] != null)
					result.push(index + 1);
		} else
			for (field in Reflect.fields(table))
				if (Reflect.field(table, field) != null)
					result.push(field);
		var extras = extraOrder.get(table);
		if (extras != null)
			for (key in extras)
				result.push(key);
		return result;
	}

	// A pairs loop asks for the length once and then one key per step. The keys
	// are kept from that first call, so clearing a field mid-loop no longer
	// shifts the rest and skips one, nested loops over other tables included.
	public function luaPairsLength(table:Dynamic):Int {
		return rememberWalk(table).length;
	}
	public function luaPairsKey(table:Dynamic, index:Int):Dynamic {
		var keys:Array<Dynamic> = null;
		var slot = walkCursor;
		for (_ in 0...WALK_SLOTS) {
			slot = (slot + WALK_SLOTS - 1) % WALK_SLOTS;
			if (walkKeyLists[slot] != null && walkTables[slot] == table) {
				keys = walkKeyLists[slot];
				break;
			}
		}
		if (keys == null)
			keys = rememberWalk(table);
		return index > 0 && index <= keys.length ? keys[index - 1] : null;
	}

	/** Take a table's keys for a new walk, reusing its slot when it already has one. */
	function rememberWalk(table:Dynamic):Array<Dynamic> {
		var keys = pairKeys(table);
		for (slot in 0...WALK_SLOTS)
			if (walkKeyLists[slot] != null && walkTables[slot] == table) {
				walkKeyLists[slot] = keys;
				return keys;
			}
		walkTables[walkCursor] = table;
		walkKeyLists[walkCursor] = keys;
		walkCursor = (walkCursor + 1) % WALK_SLOTS;
		return keys;
	}
	public function luaPairsValue(table:Dynamic, key:Dynamic):Dynamic {
		return Std.isOfType(table, Array) && !luaOwned(table)
			? luaIpairsValue(table, key) : readIndex(table, key);
	}

	public function luaSequenceLength(table:Dynamic):Int {
		if (table == null)
			return 0;
		if (Std.isOfType(table, String))
			return (cast table : String).length;
		if (Std.isOfType(table, Array)) {
			var values:Array<Dynamic> = cast table;
			var count = 0;
			while (count < values.length && values[count] != null)
				count++;
			return count;
		}
		var count = 0;
		while (readIndex(table, count + 1) != null)
			count++;
		return count;
	}

	public function luaIpairsLength(table:Dynamic):Int return luaSequenceLength(table);
	public function luaIpairsKey(_table:Dynamic, index:Int):Int return index;
	public function luaIpairsValue(table:Dynamic, key:Dynamic):Dynamic {
		if (Std.isOfType(table, Array) && !luaOwned(table)) {
			var list:Array<Dynamic> = cast table;
			var index = Std.int(key) - 1;
			return index >= 0 && index < list.length ? list[index] : null;
		}
		return readIndex(table, key);
	}

	function clearOwned(table:Dynamic):Void {
		if (Std.isOfType(table, Array))
			(cast table : Array<Dynamic>).resize(0);
		else
			for (field in Reflect.fields(table))
				Reflect.deleteField(table, field);
		extraFields.remove(table);
		objectFields.remove(table);
		extraOrder.remove(table);
	}

	function copyOwned(source:Dynamic, destination:Dynamic, copyMeta:Bool,
		seenSources:Array<Dynamic>, seenTargets:Array<Dynamic>):Dynamic {
		if (!luaOwned(source))
			return source;
		var existing = seenSources.indexOf(source);
		if (existing >= 0)
			return seenTargets[existing];
		var array = Std.isOfType(source, Array);
		var target:Dynamic = destination != source && destination != null
			&& Std.isOfType(destination, Array) == array ? destination : array ? [] : {};
		luaTables.set(target, true);
		clearOwned(target);
		seenSources.push(source);
		seenTargets.push(target);
		if (array) {
			var values:Array<Dynamic> = cast source;
			var output:Array<Dynamic> = cast target;
			for (value in values)
				output.push(copyOwned(value, null, copyMeta, seenSources, seenTargets));
		} else
			for (field in Reflect.fields(source)) {
				if (!copyMeta && field == '__luaMetatable')
					continue;
				Reflect.setField(target, field,
					copyOwned(Reflect.field(source, field), null, copyMeta, seenSources, seenTargets));
			}
		var extras = extraOrder.get(source);
		if (extras != null)
			for (key in extras)
				writeIndex(target, key, copyOwned(readExtra(source, key), null, copyMeta, seenSources, seenTargets));
		var meta = copyMeta ? metatableOf(source) : null;
		if (meta != null)
			metatables.set(target, meta);
		return target;
	}

	function metatableOf(value:Dynamic):Dynamic {
		if (metatables == null || value == null || Std.isOfType(value, String)
			|| Std.isOfType(value, Float) || Std.isOfType(value, Bool))
			return null;
		return metatables.get(value);
	}

	/** setmetatable: the table keeps its identity and its own keys; lookups that miss go to the metatable. */
	function luaSetMetatable(table:Dynamic, meta:Dynamic):Dynamic {
		if (table == null || Std.isOfType(table, String) || Std.isOfType(table, Float) || Std.isOfType(table, Bool))
			throw "bad argument #1 to 'setmetatable' (table expected, got " + EngineCompat.luaType(table) + ')';
		var current = metatableOf(table);
		if (current != null && rawIndex(current, '__metatable') != null)
			throw 'cannot change a protected metatable';
		if (meta == null) {
			if (metatables != null)
				metatables.remove(table);
			return table;
		}
		if (metatables == null)
			metatables = new ObjectMap();
		metatables.set(table, meta);
		return table;
	}

	function luaGetMetatable(table:Dynamic):Dynamic {
		var meta = metatableOf(table);
		if (meta == null)
			return null;
		var guard:Dynamic = rawIndex(meta, '__metatable');
		return guard != null ? guard : meta;
	}

	/** A read that skips metatables, and never indexes an engine array by name. */
	function rawIndex(table:Dynamic, key:Dynamic):Dynamic {
		if (Std.isOfType(table, Array) && !luaOwned(table) && !Std.isOfType(key, Float))
			return null;
		return readIndex(table, key);
	}

	/** What `__index` gives for a key the table itself does not have. */
	function metaIndex(table:Dynamic, key:Dynamic):Dynamic {
		var current:Dynamic = table;
		for (_ in 0...100) {
			var meta = metatableOf(current);
			if (meta == null)
				return null;
			var handler:Dynamic = rawIndex(meta, '__index');
			if (handler == null)
				return null;
			if (Reflect.isFunction(handler))
				return LuaValues.first(call(null, handler, [current, key]));
			var value:Dynamic = rawIndex(handler, key);
			if (value != null)
				return value;
			current = handler;
		}
		throw "'__index' chain too long; possible loop";
	}

	/** `t[k]` read the Lua way: the table first, then its `__index`. */
	function indexValue(table:Dynamic, key:Dynamic):Dynamic {
		var value:Dynamic = readIndex(table, key);
		return value == null && metatables != null ? metaIndex(table, key) : value;
	}

	/** Hand a write of a new key to `__newindex` when there is one. True when it took the write. */
	function metaNewIndex(table:Dynamic, key:Dynamic, value:Dynamic):Bool {
		var meta = metatableOf(table);
		if (meta == null)
			return false;
		var handler:Dynamic = rawIndex(meta, '__newindex');
		if (handler == null || rawIndex(table, key) != null)
			return false;
		if (Reflect.isFunction(handler))
			call(null, handler, [table, key, value]);
		else
			assignIndex(handler, key, value);
		return true;
	}

	/** `t[k] = v` the Lua way: `__newindex` for a key the table does not have, else a plain write. */
	function assignIndex(table:Dynamic, key:Dynamic, value:Dynamic):Dynamic {
		if (metatables != null && metaNewIndex(table, key, value))
			return value;
		return writeIndex(table, key, value);
	}

	/** Calling a table runs its `__call` with the table in front of the arguments. */
	override function call(object:Dynamic, fn:Dynamic, args:Array<Dynamic>):Dynamic {
		if (metatables != null && fn != null && !Reflect.isFunction(fn)) {
			var meta = metatableOf(fn);
			var handler:Dynamic = meta == null ? null : rawIndex(meta, '__call');
			if (handler != null) {
				var all:Array<Dynamic> = [fn];
				for (value in args)
					all.push(value);
				return call(object, handler, all);
			}
		}
		return super.call(object, fn, args);
	}

	function readIndex(table:Dynamic, key:Dynamic):Dynamic {
		if (table == null)
			return null;
		if (Std.isOfType(table, IMap))
			return (cast table : IMap<Dynamic, Dynamic>).get(key);
		if (luaOwned(table) && Std.isOfType(table, Array)) {
			var list:Array<Dynamic> = cast table;
			if (Std.isOfType(key, Int) || Std.isOfType(key, Float)) {
				var index = Std.int(key);
				if (index == key && index > 0 && index <= list.length)
					return list[index - 1];
			}
			return readExtra(table, key);
		}
		if (Std.isOfType(table, Array))
			return untyped table[key]; // Native API arrays keep their zero-based ABI.
		if (luaOwned(table) && key != null && !Std.isOfType(key, String))
			return readExtra(table, key);
		return key == null ? null : Reflect.getProperty(table, Std.string(key));
	}

	function writeIndex(table:Dynamic, key:Dynamic, value:Dynamic):Dynamic {
		if (table == null)
			return value;
		if (Std.isOfType(table, IMap)) {
			(cast table : IMap<Dynamic, Dynamic>).set(key, value);
			return value;
		}
		if (luaOwned(table) && Std.isOfType(table, Array)) {
			var list:Array<Dynamic> = cast table;
			if (Std.isOfType(key, Int) || Std.isOfType(key, Float)) {
				var index = Std.int(key);
				if (index == key && index > 0 && index <= list.length + 1) {
					list[index - 1] = value;
					// Sparse numeric keys stay in the sidecar until the contiguous
					// sequence reaches them; never allocate a giant Array for t[1e9].
					while (readExtra(table, list.length + 1) != null) {
						var next = readExtra(table, list.length + 1);
						writeExtra(table, list.length + 1, null);
						list.push(next);
					}
				} else
					writeExtra(table, key, value);
			} else
				writeExtra(table, key, value);
			return value;
		}
		if (Std.isOfType(table, Array))
			untyped table[key] = value;
		else if (key != null) {
			if (luaOwned(table) && !Std.isOfType(key, String))
				writeExtra(table, key, value);
			else if (luaOwned(table) && value == null)
				Reflect.deleteField(table, Std.string(key));
			else
				Reflect.setProperty(table, Std.string(key), value);
		}
		return value;
	}

	override function get(object:Dynamic, field:String):Dynamic {
		if (luaOwned(object) && Std.isOfType(object, Array)) {
			// The table's own key or its metatable's comes first, so an object
			// with a `remove` method is not handed the Haxe Array one.
			var value:Dynamic = indexValue(object, field);
			if (value == null && (field == 'push' || field == 'pop'
				|| field == 'splice' || field == 'remove' || field == 'resize'
				|| field == 'shift' || field == 'unshift'))
				return super.get(object, field);
			return value;
		}
		var value:Dynamic = super.get(object, field);
		return value == null && metatables != null && object != null ? metaIndex(object, field) : value;
	}

	override function set(object:Dynamic, field:String, value:Dynamic):Dynamic {
		if (metatables != null && metaNewIndex(object, field, value))
			return value;
		if (luaOwned(object))
			return writeIndex(object, field, value);
		return super.set(object, field, value);
	}

	function boolCondition(condition:Expr):Expr {
		var inverse = Tools.mk(EUnop('!', true, condition), condition);
		return Tools.mk(EUnop('!', true, inverse), condition);
	}

	override public function expr(expression:Expr):Dynamic {
		switch (Tools.expr(expression)) {
			case EArrayDecl(items):
				var table:Dynamic = null;
				var lastItem = items.length - 1;
				var trailingCall = lastItem >= 0 && switch (Tools.expr(items[lastItem])) {
					case ECall(_, _): true;
					default: false;
				};
				if (trailingCall) {
					// `{a, f()}` keeps every result of the last call.
					var list:Array<Dynamic> = [];
					for (index in 0...lastItem)
						list.push(expr(items[index]));
					switch (Tools.expr(items[lastItem])) {
						case ECall(target, params):
							for (value in LuaValues.list(callValues(target, params, true)))
								list.push(value);
						default:
					}
					table = list;
				} else
					table = super.expr(expression);
				if (table != null)
					luaTables.set(table, true);
				return table;
			case EObject(_):
				var table = super.expr(expression);
				if (table != null)
					luaTables.set(table, true);
				return table;
			case EFunction(_, _, _, _):
				var created:Dynamic = super.expr(expression);
				multiCallees.set(created, true);
				return created;
			case EReturn(value) if (value != null):
				switch (Tools.expr(value)) {
					case ECall(target, params):
						// `return f()` passes every result of f on, but only to a
						// caller that reads them.
						var result:Dynamic = callValues(target, params, multiWanted);
						variables.set('__luaReturnValue', multiWanted ? result : LuaValues.first(result));
						if (returnSlot == null)
							returnSlot = Tools.mk(EReturn(Tools.mk(EIdent('__luaReturnValue'), expression)), expression);
						return super.expr(returnSlot);
					default:
						return super.expr(expression);
				}
			case EArray(table, key):
				return indexValue(expr(table), expr(key));
			case EBinop('||', left, right):
				var value = expr(left);
				return truthy(value) ? value : expr(right);
			case EBinop('&&', left, right):
				var value = expr(left);
				return truthy(value) ? expr(right) : value;
			case EUnop('!', _, operand):
				return !truthy(expr(operand));
			case EUnop('-', _, operand):
				var value:Dynamic = expr(operand);
				if (value == null)
					throw 'lua arithmetic on nil (unary -)';
				if (Std.isOfType(value, String)) {
					var number:Dynamic = luaNumericString(value);
					if (number != null)
						value = number;
				}
				return -value;
			case EIf(condition, yes, no):
				return truthy(expr(condition)) ? expr(yes) : no == null ? null : expr(no);
			case ETernary(condition, yes, no):
				return truthy(expr(condition)) ? expr(yes) : expr(no);
			case ECall(target, params):
				// Anything that is not a multiple-value spot sees one value.
				return LuaValues.first(callValues(target, params, false));
			case EWhile(condition, body):
				return super.expr(Tools.mk(EWhile(boolCondition(condition), body), expression));
			case EDoWhile(condition, body):
				return super.expr(Tools.mk(EDoWhile(boolCondition(condition), body), expression));
			default:
				return super.expr(expression);
		}
	}

	static function isSongPositionCall(target:Expr):Bool {
		return switch (Tools.expr(target)) {
			case EIdent('getSongPosition'): true;
			case EParent(inner): isSongPositionCall(inner);
			default: false;
		};
	}

	override function assign(left:Expr, right:Expr):Dynamic {
		return switch (Tools.expr(left)) {
			case EArray(table, key): assignIndex(expr(table), expr(key), expr(right));
			default: super.assign(left, right);
		};
	}

	override function evalAssignOp(op:String, operation:Dynamic->Dynamic->Dynamic,
		left:Expr, right:Expr):Dynamic {
		return switch (Tools.expr(left)) {
			case EArray(tableExpr, keyExpr):
				var table = expr(tableExpr);
				var key = expr(keyExpr);
				assignIndex(table, key, operation(indexValue(table, key), expr(right)));
			default: super.evalAssignOp(op, operation, left, right);
		};
	}
}
