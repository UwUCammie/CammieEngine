package;

import haxe.Constraints.IMap;
import haxe.ds.IntMap;

/** Shared object operations for the Lua and Iris chart front ends. */
class SourceScriptReflection {
	public static inline var INSTANCE_PREFIX = '##PSYCHLUA_STRINGTOOBJ::';

	public static function mapKey(object:Dynamic, key:String):Dynamic {
		return Std.isOfType(object, IntMap) ? Std.parseInt(key) : key;
	}

	public static function read(object:Dynamic, key:String, maps:Bool,
		fallback:(Dynamic, String)->Dynamic):Dynamic {
		if (object == null) return null;
		if (maps && Std.isOfType(object, IMap)) {
			var parsed = mapKey(object, key);
			return parsed == null ? null : (cast object:IMap<Dynamic, Dynamic>).get(parsed);
		}
		return fallback(object, key);
	}

	public static function write(object:Dynamic, key:String, value:Dynamic, maps:Bool,
		fallback:(Dynamic, String, Dynamic)->Bool):Bool {
		if (object == null) return false;
		if (maps && Std.isOfType(object, IMap)) {
			var parsed = mapKey(object, key);
			if (parsed == null) return false;
			(cast object:IMap<Dynamic, Dynamic>).set(parsed, value);
			return true;
		}
		return fallback(object, key, value);
	}

	/** Only the explicit instance sentinel is special; ordinary strings survive. */
	public static function parseInstances(value:Dynamic,
		resolve:(String, Null<String>)->Dynamic):Dynamic {
		if (Std.isOfType(value, Array)) {
			var values:Array<Dynamic> = cast value;
			return [for (item in values) parseInstances(item, resolve)];
		}
		if (!Std.isOfType(value, String)) return value;
		var text:String = cast value;
		if (!StringTools.startsWith(text, INSTANCE_PREFIX)) return value;
		text = text.substr(INSTANCE_PREFIX.length);
		var separator = text.lastIndexOf('::');
		return separator < 0 ? resolve(text, null)
			: resolve(text.substr(0, separator), text.substr(separator + 2));
	}

	/** Keep the actual receiver for nested calls, including anonymous methods. */
	public static function call(object:Dynamic, tokens:Array<String>, args:Array<Dynamic>,
		readPart:(Dynamic, String)->Dynamic):Dynamic {
		if (object == null) return null;
		if (tokens == null || tokens.length == 0)
			return Reflect.isFunction(object) ? Reflect.callMethod(null, object, args == null ? [] : args) : null;
		var receiver = object;
		for (i in 0...tokens.length - 1) {
			receiver = readPart(receiver, tokens[i]);
			if (receiver == null) return null;
		}
		var method = readPart(receiver, tokens[tokens.length - 1]);
		return Reflect.isFunction(method) ? Reflect.callMethod(receiver, method, args == null ? [] : args) : null;
	}

	public static function addToGroup(group:Dynamic, object:Dynamic, index:Int = -1):Bool {
		if (group == null || object == null) return false;
		if (Std.isOfType(group, Array)) {
			var array:Array<Dynamic> = cast group;
			if (index < 0) array.push(object); else array.insert(index, object);
			return true;
		}
		var name = index < 0 ? 'add' : 'insert';
		var method = Reflect.getProperty(group, name);
		if (!Reflect.isFunction(method)) return false;
		Reflect.callMethod(group, method, index < 0 ? [object] : [index, object]);
		return true;
	}

	public static function removeFromGroup(group:Dynamic, index:Int = -1,
		object:Dynamic = null, destroy:Bool = true):Bool {
		if (group == null) return false;
		var byObject = object != null;
		var array:Array<Dynamic> = Std.isOfType(group, Array) ? cast group : null;
		var members:Array<Dynamic> = array == null ? Reflect.getProperty(group, 'members') : array;
		if (object == null) {
			if (members == null || index < 0 || index >= members.length) return false;
			object = members[index];
		}
		if (object == null) return false;
		var removed = false;
		if (array != null) removed = array.remove(object);
		else {
			var method = Reflect.getProperty(group, 'remove');
			if (!Reflect.isFunction(method)) return false;
			removed = Reflect.callMethod(group, method, [object, true]) != null;
		}
		// Psych's indexed Array removal does not destroy; tagged removal does.
		if (removed && destroy && (array == null || byObject)) {
			var method = Reflect.getProperty(object, 'destroy');
			if (Reflect.isFunction(method)) Reflect.callMethod(object, method, []);
		}
		return removed;
	}
}
