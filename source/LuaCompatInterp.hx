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

	public function new() {
		super();
		for (op in ['+', '-', '*', '/', '%', '>', '<', '>=', '<='])
			binops.set(op, function(left:Expr, right:Expr):Dynamic {
				return luaArithmetic(op, left, right);
			});
		installTableHelpers();
	}

	function luaArithmetic(op:String, left:Expr, right:Expr):Dynamic {
		var a = expr(left);
		var b = expr(right);
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
		return switch (op) {
			case '+': a + b;
			case '/': a / b;
			case '>': a > b;
			case '<': a < b;
			case '>=': a >= b;
			case '<=': a <= b;
			default: dpFloatAwareArith(op, a, b);
		};
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

	public function luaPairsLength(table:Dynamic):Int return pairKeys(table).length;
	public function luaPairsKey(table:Dynamic, index:Int):Dynamic {
		var keys = pairKeys(table);
		return index > 0 && index <= keys.length ? keys[index - 1] : null;
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
		return target;
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
		if (luaOwned(object) && Std.isOfType(object, Array)
			&& field != 'push' && field != 'pop'
			&& field != 'splice' && field != 'remove' && field != 'resize'
			&& field != 'shift' && field != 'unshift')
			return readIndex(object, field);
		return super.get(object, field);
	}

	override function set(object:Dynamic, field:String, value:Dynamic):Dynamic {
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
			case EArrayDecl(_) | EObject(_):
				var table = super.expr(expression);
				if (table != null)
					luaTables.set(table, true);
				return table;
			case EArray(table, key):
				return readIndex(expr(table), expr(key));
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
				return -value;
			case EIf(condition, yes, no):
				return truthy(expr(condition)) ? expr(yes) : no == null ? null : expr(no);
			case ETernary(condition, yes, no):
				return truthy(expr(condition)) ? expr(yes) : expr(no);
			case ECall(target, params):
				if (smokeDiagnosticsEnabled && params.length == 0
					&& isSongPositionCall(target)) {
					var callee:Dynamic = expr(target);
					var result:Dynamic = super.expr(expression);
					lastSongPositionCallProbe = 'callback='
						+ diagnosticValue(variables.get('__compatDiagnosticCallback'))
						+ ' callee=' + diagnosticValue(callee)
						+ ' result=' + diagnosticValue(result)
						+ ' songPos=' + diagnosticValue(variables.get('songPos'));
					return result;
				}
				return super.expr(expression);
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
			case EArray(table, key): writeIndex(expr(table), expr(key), expr(right));
			default: super.assign(left, right);
		};
	}

	override function evalAssignOp(op:String, operation:Dynamic->Dynamic->Dynamic,
		left:Expr, right:Expr):Dynamic {
		return switch (Tools.expr(left)) {
			case EArray(tableExpr, keyExpr):
				var table = expr(tableExpr);
				var key = expr(keyExpr);
				writeIndex(table, key, operation(readIndex(table, key), expr(right)));
			default: super.evalAssignOp(op, operation, left, right);
		};
	}
}
