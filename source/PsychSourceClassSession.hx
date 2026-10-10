package;

import hscript.ScriptClass;
import hscript.ScriptClassSymbol;
import hscript.ScriptClassScope;

/** State-owned source classes shared by ordinary and embedded Psych HScript. */
@:access(hscript.ScriptClass)
@:access(hscript.InterpEx)
class PsychSourceClassSession implements SourceClassAccess {
	public final loader:CodenameScriptClassLoader;
	final bindings:Map<String, Dynamic>;
	final construction:PsychStageConstruction;

	public function new(root:String, host:Dynamic, bindings:Map<String, Dynamic>, ?context:SourceStageContext) {
		this.bindings = bindings == null ? new Map() : bindings.copy();
		loader = CodenameScriptClassLoader.open(root, this.bindings, new Map());
		construction = new PsychStageConstruction(host, context);
		construction.bind(loader.scope);
	}

	public function importClass(path:String):Dynamic {
		if (!loader.scope.isActive()) throw '[psych-source-class] Owner session has been released';
		if (bindings.exists(path)) return null;
		var existing = loader.scope.resolveClassSymbol(path);
		if (existing != null) return existing;
		if (!loader.hasSourceModule(path)) return null;
		var loaded = loader.importClasses([path]);
		if (loaded.diagnostics.length > 0) throw '[psych-source-class] ' + loaded.diagnostics.join('; ');
		return loader.scope.resolveClassSymbol(path);
	}

	public function handles(value:Dynamic):Bool
		return Std.isOfType(value, ScriptClass) || Std.isOfType(value, ScriptClassSymbol);
	public function isClass(value:Dynamic):Bool return Std.isOfType(value, ScriptClassSymbol);

	function scopeOf(value:Dynamic):ScriptClassScope {
		var scope = isClass(value) ? (cast value:ScriptClassSymbol).scope : (cast value:ScriptClass)._classScope;
		if (scope == null || !scope.isActive()) throw '[psych-source-class] Source object owner has been released';
		return scope;
	}

	public function construct(type:Dynamic, args:Array<Dynamic>):Dynamic
		return scopeOf(type).createInstance((cast type:ScriptClassSymbol).fullName, args);
	public function read(value:Dynamic, field:String):Dynamic return scopeOf(value).accessInterpreter().get(value, field);
	public function write(value:Dynamic, field:String, item:Dynamic):Dynamic return scopeOf(value).accessInterpreter().set(value, field, item);
	public function call(value:Dynamic, field:String, args:Array<Dynamic>):Dynamic
		return scopeOf(value).accessInterpreter().fcall(value, field, args == null ? [] : args);
	public function nativeMethod(value:Dynamic, field:String, method:Dynamic):Dynamic
		return loader.scope.bindNativeMethod(value, field, method);
	public function nativeValue(value:Dynamic):Dynamic return loader.scope.unwrapIndexedMember(value);
	public function nativePropertyValue(receiver:Dynamic, name:String, value:Dynamic):Dynamic return loader.scope.nativePropertyValue(receiver, name, value);
	public function nativeArrayValue(collection:Dynamic, value:Dynamic):Dynamic return loader.scope.nativeArrayValue(collection, value);
	public function classOf(value:Dynamic):Dynamic {
		if (isClass(value)) return null;
		var descriptor = (cast value:ScriptClass)._c;
		var full = descriptor.pkg == null || descriptor.pkg.length == 0 ? descriptor.name : descriptor.pkg.join('.') + '.' + descriptor.name;
		return scopeOf(value).resolveClassSymbol(full);
	}
	public function className(value:Dynamic):String {scopeOf(value);return (cast value:ScriptClassSymbol).fullName;}

	/** Called after the state's ordered stage destruction, never on script close. */
	public function release():Void {
		for (adapter in construction.adapters) adapter.exists = false;
		loader.scope.release();
	}
}
