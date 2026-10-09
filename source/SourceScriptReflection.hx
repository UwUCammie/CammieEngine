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

	/** Historical Psych-family paths preserve raw bracket keys and map dispatch. */
	public static function readLegacyPathPart(object:Dynamic, variable:String,
		readProperty:(Dynamic,String)->Dynamic):Dynamic {
		var parts = variable.split('[');
		if (parts.length > 1) {
			var value:Dynamic = readProperty(object, parts[0]);
			for (i in 1...parts.length) {
				var key:Dynamic = parts[i].substr(0, parts[i].length - 1);
				value = value[key];
			}
			return value;
		}
		return readLegacyField(object, variable, readProperty);
	}
	static function readLegacyField(object:Dynamic, key:String, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		return switch (Type.typeof(object)) {
			case TClass(haxe.ds.StringMap) | TClass(haxe.ds.ObjectMap) | TClass(haxe.ds.IntMap) | TClass(haxe.ds.EnumValueMap): object.get(key);
			default: readProperty(object, key);
		};
	}
	public static function writeLegacyPathPart(object:Dynamic, variable:String, value:Dynamic,
		readProperty:(Dynamic,String)->Dynamic, writeProperty:(Dynamic,String,Dynamic)->Void):Void {
		var parts = variable.split('[');
		if (parts.length > 1) {
			var target:Dynamic = readProperty(object, parts[0]);
			for (i in 1...parts.length) {
				var key:Dynamic = parts[i].substr(0, parts[i].length - 1);
				if (i == parts.length - 1) target[key] = value;
				else target = target[key];
			}
			return;
		}
		switch (Type.typeof(object)) {
			case TClass(haxe.ds.StringMap) | TClass(haxe.ds.ObjectMap) | TClass(haxe.ds.IntMap) | TClass(haxe.ds.EnumValueMap): object.set(variable, value);
			default: writeProperty(object, variable, value);
		}
	}

	static function legacyPathOwner(parts:Array<String>, instance:()->Dynamic,
		resolveObject:String->Dynamic, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		if (parts.length == 1) return instance();
		var target = resolveObject(parts[0]);
		for (i in 1...parts.length - 1) target = readLegacyPathPart(target, parts[i], readProperty);
		return target;
	}

	public static function getLegacyLuaProperty(path:String, instance:()->Dynamic,
		resolveObject:String->Dynamic, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		var parts = path.split('.');
		return readLegacyPathPart(legacyPathOwner(parts, instance, resolveObject, readProperty), parts[parts.length - 1], readProperty);
	}

	public static function setLegacyLuaProperty(path:String, value:Dynamic, instance:()->Dynamic,
		resolveObject:String->Dynamic, readProperty:(Dynamic,String)->Dynamic,
		writeProperty:(Dynamic,String,Dynamic)->Void):Bool {
		var parts = path.split('.');
		writeLegacyPathPart(legacyPathOwner(parts, instance, resolveObject, readProperty), parts[parts.length - 1], value, readProperty, writeProperty);
		return true;
	}

	public static function legacyGroupRoot(path:String, instance:()->Dynamic,
		resolveObject:String->Dynamic, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		var parts = path.split('.');
		var result = readProperty(instance(), path);
		if (parts.length > 1) {
			result = resolveObject(parts[0]);
			for (i in 1...parts.length) result = readLegacyPathPart(result, parts[i], readProperty);
		}
		return result;
	}
	static function legacyGroupFieldOwner(object:Dynamic, parts:Array<String>, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		for (i in 0...parts.length - 1) object = readProperty(object, parts[i]);
		return object;
	}
	public static function readLegacyGroupField(object:Dynamic, field:String, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		var parts = field.split('.');
		var owner = legacyGroupFieldOwner(object, parts, readProperty);
		var key = parts[parts.length - 1];
		return readLegacyField(owner, key, readProperty);
	}
	public static function writeLegacyGroupField(object:Dynamic, field:String, value:Dynamic,
		readProperty:(Dynamic,String)->Dynamic, writeProperty:(Dynamic,String,Dynamic)->Void):Void {
		var parts = field.split('.');
		writeProperty(legacyGroupFieldOwner(object, parts, readProperty), parts[parts.length - 1], value);
	}
	public static function getLegacyGroupProperty(group:Dynamic, index:Int, field:Dynamic,
		isGroup:Dynamic->Bool, readProperty:(Dynamic,String)->Dynamic, missing:()->Void):Dynamic {
		if (isGroup(group)) return readLegacyGroupField(group.members[index], field, readProperty);
		var item:Dynamic = group[index];
		if (item != null) {
			if (Type.typeof(field) == TInt) return item[field];
			return readLegacyGroupField(item, field, readProperty);
		}
		missing();
		return null;
	}
	public static function setLegacyGroupProperty(group:Dynamic, index:Int, field:Dynamic, value:Dynamic,
		isGroup:Dynamic->Bool, readProperty:(Dynamic,String)->Dynamic, writeProperty:(Dynamic,String,Dynamic)->Void):Void {
		if (isGroup(group)) {writeLegacyGroupField(group.members[index], field, value, readProperty, writeProperty);return;}
		var item:Dynamic = group[index];
		if (item != null) {
			if (Type.typeof(field) == TInt) {item[field] = value;return;}
			writeLegacyGroupField(item, field, value, readProperty, writeProperty);
		}
	}
	/** Read the live root at each source access; kill/remove hooks may replace it. */
	public static function removeLegacyGroupMember(root:()->Dynamic, index:Int, dontDestroy:Bool,
		isGroup:Dynamic->Bool, removeGroup:(Dynamic,Dynamic)->Void):Void {
		if (isGroup(root())) {
			var item:Dynamic = root().members[index];
			if (!dontDestroy) item.kill();
			removeGroup(root(), item);
			if (!dontDestroy) item.destroy();
			return;
		}
		var receiver:Dynamic = root();
		var item:Dynamic = root()[index];
		receiver.remove(item);
	}
	public static function getLegacyClassProperty(type:Dynamic, path:String, readProperty:(Dynamic,String)->Dynamic):Dynamic {
		var parts = path.split('.');
		var result = type;
		for (part in parts) result = readLegacyPathPart(result, part, readProperty);
		return result;
	}
	public static function setLegacyClassProperty(type:Dynamic, path:String, value:Dynamic,
		readProperty:(Dynamic,String)->Dynamic, writeProperty:(Dynamic,String,Dynamic)->Void):Bool {
		var parts = path.split('.');
		var target = type;
		for (i in 0...parts.length - 1) target = readLegacyPathPart(target, parts[i], readProperty);
		writeLegacyPathPart(target, parts[parts.length - 1], value, readProperty, writeProperty);
		return true;
	}

	/** Final fields are literal Reflect property names, including bracket text. */
	public static function setLegacyProperty(state:Dynamic, path:String, value:Dynamic,
		resolveObject:String->Dynamic, readProperty:(Dynamic,String)->Dynamic,
		writeProperty:(Dynamic,String,Dynamic)->Void):Void {
		var parts = path.split('.');
		var target = legacyPathOwner(parts, function() return state, resolveObject, readProperty);
		writeProperty(target, parts[parts.length - 1], value);
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
