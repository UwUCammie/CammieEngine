package;

import hscript.Interp;
import flixel.FlxBasic;
import PlayState.DisplayLayer;

/** Psych's reflection API over the same live objects used by Iris scripts. */
@:access(PlayState)
class PsychReflectionBindings {
	final host:PlayState;
	final interp:Interp;

	public function new(host:PlayState, interp:Interp) {
		this.host = host;
		this.interp = interp;
	}

	public function install():Void {
		var previousGet = interp.variables.get('getProperty');
		var previousSet = interp.variables.get('setProperty');
		interp.variables.set('getProperty', function(path:Dynamic, allowMaps:Bool = false):Dynamic {
			var token = EngineCompat.propertyPath(path);
			if (host.psychScriptVariables.exists(host.compatPathTokens(token)[0])) return get(path, allowMaps);
			return allowMaps ? get(path, true) : Reflect.callMethod(null, previousGet, [path]);
		});
		interp.variables.set('setProperty', function(path:Dynamic, value:Dynamic,
			allowMaps:Bool = false, allowInstances:Bool = false):Dynamic {
			if (allowInstances) value = parse(value);
			if (allowMaps || host.psychScriptVariables.exists(host.compatPathTokens(EngineCompat.propertyPath(path))[0])) set(path, value, allowMaps);
			else Reflect.callMethod(null, previousSet, [path, value]);
			return value;
		});
		interp.variables.set('getPropertyFromGroup', function(group:Dynamic, index:Dynamic,
			property:Dynamic, allowMaps:Bool = false):Dynamic {
			return readPath(member(group, index), propertyPath(property), allowMaps);
		});
		interp.variables.set('setPropertyFromGroup', function(group:Dynamic, index:Dynamic,
			property:Dynamic, value:Dynamic, allowMaps:Bool = false,
			allowInstances:Bool = false):Dynamic {
			if (allowInstances) value = parse(value);
			writePath(member(group, index), propertyPath(property), value, allowMaps);
			return value;
		});
		var previousClassGet = interp.variables.get('getPropertyFromClass');
		var previousClassSet = interp.variables.get('setPropertyFromClass');
		interp.variables.set('getPropertyFromClass', function(type:Dynamic, path:Dynamic,
			allowMaps:Bool = false):Dynamic {
			return allowMaps ? readPath(host.compatResolveClass(type), Std.string(path), true)
				: Reflect.callMethod(null, previousClassGet, [type, path]);
		});
		interp.variables.set('setPropertyFromClass', function(type:Dynamic, path:Dynamic,
			value:Dynamic, allowMaps:Bool = false, allowInstances:Bool = false):Dynamic {
			if (allowInstances) value = parse(value);
			if (allowMaps) writePath(host.compatResolveClass(type), Std.string(path), value, true);
			else Reflect.callMethod(null, previousClassSet, [type, path, value]);
			return value;
		});
		interp.variables.set('callMethod', function(path:String, ?args:Array<Dynamic>):Dynamic {
			var tokens = host.compatPathTokens(path);
			var object:Dynamic = host;
			if (tokens.length > 0) {
				var first = tokens[0];
				if (host.psychScriptVariables.exists(first)) {
					object = host.psychScriptVariables.get(first);
					tokens.shift();
				} else if (tokens.length > 1) {
					object = root(tokens.shift());
				}
			}
			return SourceScriptReflection.call(object, tokens, parsedArgs(args), readPart);
		});
		interp.variables.set('callMethodFromClass', function(type:String, path:String,
			?args:Array<Dynamic>):Dynamic {
			return SourceScriptReflection.call(host.compatResolveClass(type),
				host.compatPathTokens(path), parsedArgs(args), readPart);
		});
		interp.variables.set('instanceArg', function(path:String, ?type:String):String {
			return SourceScriptReflection.INSTANCE_PREFIX + path + (type == null ? '' : '::' + type);
		});
		interp.variables.set('createInstance', function(name:String, type:String,
			?args:Array<Dynamic>):Bool {
			name = StringTools.replace(StringTools.trim(name), '.', '');
			if (host.psychScriptVariables.get(name) != null) return false;
			var resolved = host.compatResolveClass(type);
			if (resolved == null) return false;
			var object:Dynamic = Type.createInstance(resolved, parsedArgs(args));
			if (object == null) return false;
			host.psychScriptVariables.set(name, object);
			return true;
		});
		interp.variables.set('addInstance', function(name:String, front:Bool = false):Void {
			var object = host.psychScriptVariables.get(name);
			if (!Std.isOfType(object, FlxBasic)) return;
			host.addHscriptSprite(cast object, front ? DisplayLayer.BEHIND_NONE : DisplayLayer.BEHIND_ALL);
		});
		interp.variables.set('addToGroup', function(group:String, tag:String, index:Int = -1):Void {
			var object = root(tag);
			if (object == null || !Reflect.isFunction(Reflect.getProperty(object, 'destroy'))) return;
			SourceScriptReflection.addToGroup(get(group, true), object, index);
		});
		interp.variables.set('removeFromGroup', function(group:String, index:Int = -1,
			?tag:String, destroy:Bool = true):Void {
			var object = tag == null ? null : root(tag);
			if (tag != null && object == null) return;
			SourceScriptReflection.removeFromGroup(get(group, true), index, object, destroy);
		});
	}

	function root(name:String):Dynamic {
		return host.psychScriptVariables.exists(name) ? host.psychScriptVariables.get(name)
			: host.compatPropertyRoot(name);
	}

	function readPart(object:Dynamic, key:String):Dynamic {
		return SourceScriptReflection.read(object, host.compatPathIndex(key), true,
			function(target, _) return host.compatReadPathPart(target, key));
	}

	function readPath(object:Dynamic, path:String, maps:Bool):Dynamic {
		for (key in host.compatPathTokens(path)) {
			object = SourceScriptReflection.read(object, host.compatPathIndex(key), maps,
				function(target, _) return host.compatReadPathPart(target, key));
			if (object == null) break;
		}
		return object;
	}

	function writePath(object:Dynamic, path:String, value:Dynamic, maps:Bool):Void {
		var tokens = host.compatPathTokens(path);
		if (tokens.length == 0) return;
		var last = tokens.pop();
		for (key in tokens) object = SourceScriptReflection.read(object, host.compatPathIndex(key), maps,
			function(target, _) return host.compatReadPathPart(target, key));
		SourceScriptReflection.write(object, host.compatPathIndex(last), value, maps,
			function(target, _, next) return host.compatWritePathPart(target, last, next));
	}

	function get(path:Dynamic, maps:Bool):Dynamic {
		var tokens = host.compatPathTokens(EngineCompat.propertyPath(path));
		if (tokens.length == 0) return null;
		var value = root(tokens.shift());
		for (key in tokens) value = SourceScriptReflection.read(value, host.compatPathIndex(key), maps,
			function(target, _) return host.compatReadPathPart(target, key));
		return value;
	}

	function set(path:Dynamic, value:Dynamic, maps:Bool):Void {
		var tokens = host.compatPathTokens(EngineCompat.propertyPath(path));
		if (tokens.length == 0) return;
		if (tokens.length == 1) {
			if (host.psychScriptVariables.exists(tokens[0])) host.psychScriptVariables.set(tokens[0], value);
			else host.compatSetProperty(path, value);
			return;
		}
		var object = root(tokens.shift());
		var last = tokens.pop();
		for (key in tokens) object = SourceScriptReflection.read(object, host.compatPathIndex(key), maps,
			function(target, _) return host.compatReadPathPart(target, key));
		SourceScriptReflection.write(object, host.compatPathIndex(last), value, maps,
			function(target, _, next) return host.compatWritePathPart(target, last, next));
	}

	function member(group:Dynamic, index:Dynamic):Dynamic {
		var nativeMember = host.compatGroupMember(group, index);
		if (nativeMember != null) return nativeMember;
		var object = get(group, true);
		return host.compatReadPathPart(object, '[' + Std.string(index) + ']');
	}

	static function propertyPath(property:Dynamic):String {
		return Std.isOfType(property, Int) ? '[' + Std.string(property) + ']' : Std.string(property);
	}

	function parse(value:Dynamic):Dynamic {
		return SourceScriptReflection.parseInstances(value, function(path, type) {
			return type == null ? get(path, true) : readPath(host.compatResolveClass(type), path, true);
		});
	}

	function parsedArgs(args:Array<Dynamic>):Array<Dynamic> {
		return args == null ? [] : cast parse(args);
	}
}
