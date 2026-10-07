package;

/** Interpreter-local routes over real native classes. No process-global statics
 * or class identities are replaced by owner metadata. */
class SourceNativeClassScope {
	var statics:Array<{type:Dynamic, name:String, read:Void->Dynamic, write:Dynamic->Dynamic}> = [];
	var runtimeClasses:Map<String, Dynamic> = new Map();
	var runtimeEnums:Map<String, Dynamic> = new Map();
	var classNames:Array<{type:Dynamic, name:String}> = [];
	var enumNames:Array<{type:Dynamic, name:String}> = [];
	public var construct:Dynamic->Array<Dynamic>->Dynamic;
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
	public function hasBinding(type:Dynamic, name:String):Bool {
		for (binding in statics) if (binding.type == type && binding.name == name) return true;
		return false;
	}
	public function read(type:Dynamic, name:String, property:Bool = true):Dynamic {
		for (binding in statics) if (binding.type == type && binding.name == name) return binding.read();
		return property ? Reflect.getProperty(type, name) : Reflect.field(type, name);
	}
	public function write(type:Dynamic, name:String, value:Dynamic, property:Bool = true):Dynamic {
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

	public function resolveClass(name:String):Dynamic
		return runtimeClasses.exists(name) ? runtimeClasses.get(name) : Type.resolveClass(name);
	public function resolveEnum(name:String):Dynamic
		return runtimeEnums.exists(name) ? runtimeEnums.get(name) : Type.resolveEnum(name);
	public function createInstance(type:Dynamic, args:Array<Dynamic>):Dynamic
		return construct == null ? Type.createInstance(type, args) : construct(type, args);
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
		Reflect.setField(typeView, 'getClassName', function(type:Dynamic):String {
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
		statics.resize(0); runtimeClasses.clear(); runtimeEnums.clear();
		classNames.resize(0); enumNames.resize(0);
		construct = null; reflectView = null; typeView = null;
	}
}
