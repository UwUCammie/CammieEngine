package;

/** Interpreter-local routes over real native classes. No process-global statics
 * or class identities are replaced by owner metadata. */
class SourceNativeClassScope {
	var statics:Array<{type:Dynamic, name:String, read:Void->Dynamic, write:Dynamic->Dynamic}> = [];
	var instanceProperties:Array<{type:Dynamic, name:String, read:Dynamic->Dynamic}> = [];
	var runtimeClasses:Map<String, Dynamic> = new Map();
	var runtimeEnums:Map<String, Dynamic> = new Map();
	var classNames:Array<{type:Dynamic, name:String}> = [];
	var enumNames:Array<{type:Dynamic, name:String}> = [];
	public var construct:Dynamic->Array<Dynamic>->Dynamic;
	public var sourceObjects:SourceClassAccess;
	var reflectView:Dynamic;
	var typeView:Dynamic;

	public function new() {}
	public function bindRuntimeClass(name:String, type:Dynamic):Void {runtimeClasses.set(name, type); classNames.push({type:type, name:name});}
	public function bindRuntimeEnum(name:String, type:Dynamic):Void {runtimeEnums.set(name, type); enumNames.push({type:type, name:name});}
	public function bindStaticField(type:Dynamic, name:String, read:Void->Dynamic, ?write:Dynamic->Dynamic):Void {
		for (binding in statics) if (binding.type == type && binding.name == name) {
			binding.read = read; binding.write = write; return;
		}
		statics.push({type:type, name:name, read:read, write:write});
	}
	/** Source property views preserve native typed callers and apply across interpreters. */
	public function bindInstanceProperty(type:Dynamic, name:String, read:Dynamic->Dynamic):Void {
		for (binding in instanceProperties) if (binding.type == type && binding.name == name) {
			binding.read = read; return;
		}
		instanceProperties.push({type:type, name:name, read:read});
	}
	/** Release per-instance native field routes when their source object dies. */
	public function unbindStaticFields(type:Dynamic):Void {
		statics = statics.filter(function(binding) return binding.type != type);
	}
	public function hasBinding(type:Dynamic, name:String):Bool {
		for (binding in statics) if (binding.type == type && binding.name == name) return true;
		for (binding in instanceProperties) if (binding.name == name && Std.isOfType(type, binding.type)) return true;
		return false;
	}
	public function read(type:Dynamic, name:String, property:Bool = true):Dynamic {
		if (sourceObjects != null && sourceObjects.handles(type)) return sourceObjects.read(type, name);
		for (binding in statics) if (binding.type == type && binding.name == name) return binding.read();
		if (property) for (binding in instanceProperties) if (binding.name == name && Std.isOfType(type, binding.type)) return binding.read(type);
		return property ? Reflect.getProperty(type, name) : Reflect.field(type, name);
	}
	public function write(type:Dynamic, name:String, value:Dynamic, property:Bool = true):Dynamic {
		if (sourceObjects != null && sourceObjects.handles(type)) return sourceObjects.write(type, name, value);
		for (binding in statics) if (binding.type == type && binding.name == name && binding.write != null)
			return binding.write(value);
		if (property) Reflect.setProperty(type, name, value); else Reflect.setField(type, name, value);
		return value;
	}
	public function ownsClass(type:Dynamic):Bool {
		for (binding in classNames) if (binding.type == type) return true;
		for (binding in enumNames) if (binding.type == type) return true;
		return false;
	}
	public function hasRuntimeClass(name:String):Bool return runtimeClasses.exists(name);
	/** Independently retained aliases for an actual source object owner. */
	public function captureClassMap():Map<String, Dynamic> return runtimeClasses.copy();

	public function resolveClass(name:String):Dynamic {
		if (runtimeClasses.exists(name)) return runtimeClasses.get(name);
		if (sourceObjects != null) {var value = sourceObjects.importClass(name);if (value != null) return value;}
		return Type.resolveClass(name);
	}
	public function resolveEnum(name:String):Dynamic
		return runtimeEnums.exists(name) ? runtimeEnums.get(name) : Type.resolveEnum(name);
	public function createInstance(type:Dynamic, args:Array<Dynamic>):Dynamic {
		if (sourceObjects != null && sourceObjects.isClass(type)) return sourceObjects.construct(type, args);
		return construct == null ? Type.createInstance(type, args) : construct(type, args);
	}
	public function reflectFacade():Dynamic {
		if (reflectView != null) return reflectView;
		reflectView = {};
		for (name in Type.getClassFields(Reflect)) Reflect.setField(reflectView, name, Reflect.field(Reflect, name));
		Reflect.setField(reflectView, 'field', function(object:Dynamic, field:String) return read(object, field, false));
		Reflect.setField(reflectView, 'getProperty', function(object:Dynamic, field:String) return read(object, field));
		Reflect.setField(reflectView, 'setField', function(object:Dynamic, field:String, value:Dynamic):Void {write(object, field, value, false);});
		Reflect.setField(reflectView, 'setProperty', function(object:Dynamic, field:String, value:Dynamic):Void {write(object, field, value);});
		Reflect.setField(reflectView, 'copy', function(object:Dynamic):Dynamic {
			if (!ownsClass(object)) return Reflect.copy(object);
			var result:Dynamic = {};
			for (name in Reflect.fields(object)) Reflect.setField(result, name, read(object, name, false));
			return result;
		});
		return reflectView;
	}
	public function typeFacade():Dynamic {
		if (typeView != null) return typeView;
		typeView = {};
		for (name in Type.getClassFields(Type)) Reflect.setField(typeView, name, Reflect.field(Type, name));
		Reflect.setField(typeView, 'resolveClass', resolveClass);
		Reflect.setField(typeView, 'resolveEnum', resolveEnum);
		Reflect.setField(typeView, 'createInstance', createInstance);
		Reflect.setField(typeView, 'getClass', function(value:Dynamic):Dynamic {
			return sourceObjects != null && sourceObjects.handles(value) ? sourceObjects.classOf(value) : Type.getClass(value);
		});
		Reflect.setField(typeView, 'getClassName', function(type:Dynamic):String {
			if (sourceObjects != null && sourceObjects.isClass(type)) return sourceObjects.className(type);
			for (binding in classNames) if (binding.type == type) return binding.name;
			return Type.getClassName(type);
		});
		Reflect.setField(typeView, 'getEnumName', function(type:Dynamic):String {
			for (binding in enumNames) if (binding.type == type) return binding.name;
			return Type.getEnumName(type);
		});
		return typeView;
	}
	/** Class references obtained through Type remain real; their scoped method
	 * lookup still routes Reflect/Type calls instead of bypassing this scope. */
	public function installReflectionBindings():Void {
		var reflects = reflectFacade();
		for (name in Reflect.fields(reflects)) {
			var method = Reflect.field(reflects, name);
			bindStaticField(Reflect, name, function() return method, function(value) return value);
		}
		var types = typeFacade();
		for (name in Reflect.fields(types)) {
			var method = Reflect.field(types, name);
			bindStaticField(Type, name, function() return method, function(value) return value);
		}
	}
	public function release():Void {
		statics.resize(0); instanceProperties.resize(0); runtimeClasses.clear(); runtimeEnums.clear();
		classNames.resize(0); enumNames.resize(0);
		construct = null; reflectView = null; typeView = null;sourceObjects = null;
	}
}
