package;

import hscript.Interp;
import flixel.FlxBasic;
import PlayState.DisplayLayer;

/** Psych's reflection API over the same live objects used by Iris scripts. */
@:access(PlayState)
class PsychReflectionBindings {
	final host:PlayState;
	final interp:Interp;
	var nativeClasses:SourceNativeClassScope;

	public function new(host:PlayState, interp:Interp) {
		this.host = host;
		this.interp = interp;
	}

	public function install():Void {
		var paths:Dynamic = interp.variables.get('Paths');
		var ownerRoot = host.selectedPsychSkinRoot();
		if (paths == null && ownerRoot != null) paths = PsychOwnerPaths.create(ownerRoot, host.psychStageLibrary);
		if (Std.isOfType(interp, SourceIrisBridge)) nativeClasses = (cast interp:SourceIrisBridge).evaluator.sourceClassScope();
		else if (paths != null && Reflect.isFunction(Reflect.field(paths, '__sourceOwnerRoot')))
			nativeClasses = host.psychLuaNativeClassScope(paths);
		else nativeClasses = new SourceNativeClassScope();
		PsychStateClassBindings.installScope(nativeClasses);
		if (host.nightmareVisionLegacyFieldCameras) installLegacyProperties();
		else PsychPropertyBindings.install(host,interp,nativeClasses,parse);
		interp.variables.set('instanceArg', function(path:String, ?type:String):String {
			return SourceScriptReflection.INSTANCE_PREFIX + path + (type == null ? '' : '::' + type);
		});

	}

	function installLegacyProperties():Void {
		interp.variables.set('createInstance', function(name:String, type:String,
			?args:Array<Dynamic>):Bool {
			name = StringTools.replace(StringTools.trim(name), '.', '');
			if (host.psychScriptVariables.get(name) != null) return false;
			var resolved = resolveClass(type);
			if (resolved == null) return false;
			var object:Dynamic = nativeClasses.createInstance(resolved, parsedArgs(args));
			if (object == null) return false;
			host.psychScriptVariables.set(name, object);
			return true;
		});
		interp.variables.set('addInstance', function(name:String, front:Bool = false):Void {
			var object = host.psychScriptVariables.get(name);
			if (!Std.isOfType(object, FlxBasic)) return;
			host.addHscriptSprite(cast object, front ? DisplayLayer.BEHIND_NONE : DisplayLayer.BEHIND_ALL);
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
		var previousClassGet = interp.variables.get('getPropertyFromClass');
		var previousClassSet = interp.variables.get('setPropertyFromClass');
		interp.variables.set('getPropertyFromClass', function(type:Dynamic, path:Dynamic,
			allowMaps:Bool = false):Dynamic {
			return nativeClasses.hasRuntimeClass(Std.string(type)) ? readPath(resolveClass(type), Std.string(path), allowMaps)
				: allowMaps ? readPath(resolveClass(type), Std.string(path), true)
				: Reflect.callMethod(null, previousClassGet, [type, path]);
		});
		interp.variables.set('setPropertyFromClass', function(type:Dynamic, path:Dynamic,
			value:Dynamic, allowMaps:Bool = false, allowInstances:Bool = false):Dynamic {
			if (allowInstances) value = parse(value);
			if (nativeClasses.hasRuntimeClass(Std.string(type)) || allowMaps) writePath(resolveClass(type), Std.string(path), value, allowMaps);
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
			return SourceScriptReflection.call(resolveClass(type),
				host.compatPathTokens(path), parsedArgs(args), readPart);
		});
	}

	function root(name:String):Dynamic {
		return host.psychScriptVariables.exists(name) ? host.psychScriptVariables.get(name)
			: host.compatPropertyRoot(name);
	}

	function resolveClass(type:Dynamic):Dynamic {
		var name = Std.string(type);
		return nativeClasses.hasRuntimeClass(name) ? nativeClasses.resolveClass(name) : host.compatResolveClass(type);
	}
	function readClassPart(target:Dynamic, key:String):Dynamic {
		return nativeClasses.hasBinding(target, key) ? nativeClasses.read(target, key) : host.compatReadPathPart(target, key);
	}
	function writeClassPart(target:Dynamic, key:String, value:Dynamic):Bool {
		if (nativeClasses.hasBinding(target, key)) {nativeClasses.write(target, key, value); return true;}
		return host.compatWritePathPart(target, key, value);
	}
	function readPart(object:Dynamic, key:String):Dynamic {
		return SourceScriptReflection.read(object, host.compatPathIndex(key), true,
			function(target, _) return readClassPart(target, key));
	}

	function readPath(object:Dynamic, path:String, maps:Bool):Dynamic {
		for (key in host.compatPathTokens(path)) {
			object = SourceScriptReflection.read(object, host.compatPathIndex(key), maps,
				function(target, _) return readClassPart(target, key));
			if (object == null) break;
		}
		return object;
	}

	function writePath(object:Dynamic, path:String, value:Dynamic, maps:Bool):Void {
		var tokens = host.compatPathTokens(path);
		if (tokens.length == 0) return;
		var last = tokens.pop();
		for (key in tokens) object = SourceScriptReflection.read(object, host.compatPathIndex(key), maps,
			function(target, _) return readClassPart(target, key));
		SourceScriptReflection.write(object, host.compatPathIndex(last), value, maps,
			function(target, _, next) return writeClassPart(target, last, next));
	}

	function get(path:Dynamic, maps:Bool):Dynamic {
		var tokens = host.compatPathTokens(EngineCompat.propertyPath(path));
		if (tokens.length == 0) return null;
		var value = root(tokens.shift());
		for (key in tokens) value = SourceScriptReflection.read(value, host.compatPathIndex(key), maps,
			function(target, _) return readClassPart(target, key));
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
			function(target, _) return readClassPart(target, key));
		SourceScriptReflection.write(object, host.compatPathIndex(last), value, maps,
			function(target, _, next) return writeClassPart(target, last, next));
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
		if (!host.nightmareVisionLegacyFieldCameras) return PsychInstanceArguments.parse(value, true, resolveClass,
			function(object,key) return nativeClasses.read(object,key));
		return SourceScriptReflection.parseInstances(value, function(path, type) {
			return type == null ? get(path, true) : readPath(resolveClass(type), path, true);
		});
	}

	function parsedArgs(args:Array<Dynamic>):Array<Dynamic> {
		return args == null ? [] : cast parse(args);
	}
}
