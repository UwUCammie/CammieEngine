package hscript;

import hscript.Expr.ModuleDecl;
import hscript.Expr.FieldAccess;
import hscript.Expr.FieldDecl;
import hscript.Expr.FieldKind;
import hscript.Expr.Expr;
import hscript.Expr.CType;
#if flixel
import PsychScriptClassBasicBridge;
import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.tweens.FlxTween;
#end

@:access(hscript.ScriptClass)
/**
	Per-owner registry for HScript-ex classes.

	The upstream HScript-ex registry is static, so importing classes from two
	mods with the same type name lets the later import replace the first one.
	Codename supplies one scope per imported owner and releases it with the
	owner's script interpreter. No descriptor is published process-wide.
*/
class ScriptClassScope {
	static inline var MAX_CLASS_DEPTH:Int = 64;
	static final NATIVE_TWEEN_TARGET_METHODS:Array<String> = [
		'tween', 'flicker', 'isFlickering', 'stopFlickering', 'shake', 'angle', 'color',
		'linearMotion', 'quadMotion', 'cubicMotion', 'circularMotion', 'linearPath',
		'quadPath', 'cancelTweensOf', 'completeTweensOf'
	];

	final descriptors:Map<String, ClassDeclEx> = new Map();
	final aliases:Map<String, String> = new Map();
	final ambiguousAliases:Map<String, Bool> = new Map();
	final classSymbols:Map<String, ScriptClassSymbol> = new Map();
	/** Static source fields are shared by every class object in this owner only. */
	final ownerStaticValues:Map<String, Dynamic> = new Map();
	final bindings:Map<String, Dynamic> = new Map();
	final ambiguousBindings:Map<String, Bool> = new Map();
	final unavailableImports:Map<String, String> = new Map();
	#if flixel
	final nativeBasicBridges:haxe.ds.ObjectMap<ScriptClass, PsychScriptClassBasicBridge> = new haxe.ds.ObjectMap();
	final ownedNativeBasicBridges:Array<PsychScriptClassBasicBridge> = [];
	#end
	final nativeConstructionHooks:haxe.ds.ObjectMap<Dynamic, {
		before:ScriptClass->Void, after:ScriptClass->Dynamic->Void, initializedFields:Array<String>, prepare:Dynamic->Void
	}> = new haxe.ds.ObjectMap();
	final nativeFactories:haxe.ds.ObjectMap<Dynamic, Array<Dynamic>->Dynamic> = new haxe.ds.ObjectMap();
	var active:Bool = true;

	public function new() {}

	/** Observe a native super constructor without replacing its class identity. */
	public function bindNativeConstruction(type:Dynamic, before:ScriptClass->Void,
		after:ScriptClass->Dynamic->Void, ?initializedFields:Array<String>, ?prepare:Dynamic->Void):Void {
		ensureActive();
		nativeConstructionHooks.set(type, {before: before, after: after, initializedFields: initializedFields, prepare: prepare});
	}

	/** Direct native construction uses the same explicit imported class identity. */
	public function bindNativeFactory(type:Dynamic, create:Array<Dynamic>->Dynamic):Void {
		ensureActive();
		nativeFactories.set(type, create);
	}

	public function tryConstructNative(name:String, args:Array<Dynamic>, ?requester:ClassDeclEx):{handled:Bool, value:Dynamic} {
		var type = findBinding(name, requester);
		var factory = type == null ? null : nativeFactories.get(type);
		return factory == null ? {handled:false, value:null} : {handled:true, value:factory(args == null ? [] : args)};
	}

	public function constructNativeSuper(owner:ScriptClass, type:Dynamic, args:Array<Dynamic>):Void {
		ensureActive();
		var hooks = nativeConstructionHooks.get(type);
		var root = owner.constructionRoot();
		if (hooks != null && hooks.before != null) hooks.before(root);
		owner.superClass = Type.createInstance(type, args);
		if (hooks != null) {
			if (hooks.prepare != null) hooks.prepare(owner.superClass);
			// A virtual callback inside super() can observe pre-super assignments
			// from every source class, including the most derived constructor.
			var current = owner;
			while (current != null) {
				// Native field initializers run during super(), overwriting
				// earlier assignments. Forwarding properties are not reset.
				if (hooks.initializedFields != null)
					for (name in hooks.initializedFields) current.pendingSuperFields.remove(name);
				current.applyPendingSuperFields();
				current = current.derivedClass;
			}
			if (hooks.after != null) hooks.after(root, owner.superClass);
		}
	}

	public function seed(name:String, value:Dynamic):Void {
		if (!active || name == null || name == '') return;
		bindings.set(name, value);
	}

	/** Copy the host's already-validated owner symbols before class fields run. */
	public function seedFrom(values:Map<String, Dynamic>):Void {
		if (!active || values == null) return;
		for (name in values.keys()) seed(name, values.get(name));
	}

	/** Add a Haxe import value and its unqualified name when that alias is unique. */
	public function bindImport(path:Array<String>, value:Dynamic):Void {
		if (!active || path == null || path.length == 0 || value == null) return;
		var full = path.join('.');
		bindings.set(full, value);
		var shortName = path[path.length - 1];
		if (ambiguousBindings.exists(shortName)) return;
		if (bindings.exists(shortName) && bindings.get(shortName) != value) {
			bindings.remove(shortName);
			ambiguousBindings.set(shortName, true);
		} else {
			bindings.set(shortName, value);
		}
	}

	/** Atomic descriptor/binding registration, before any class code executes.
	 * Existing instances, symbols and static storage retain their identities. */
	public function registerImports(action:Void->Bool):Bool {
		ensureActive();
		var oldDescriptors = descriptors.copy(), oldAliases = aliases.copy();
		var oldAmbiguousAliases = ambiguousAliases.copy(), oldBindings = bindings.copy();
		var oldAmbiguousBindings = ambiguousBindings.copy(), oldUnavailable = unavailableImports.copy();
		var rollback = function() {
			restoreImports(descriptors, oldDescriptors);restoreImports(aliases, oldAliases);
			restoreImports(ambiguousAliases, oldAmbiguousAliases);restoreImports(bindings, oldBindings);
			restoreImports(ambiguousBindings, oldAmbiguousBindings);restoreImports(unavailableImports, oldUnavailable);
		};
		try {
			if (action()) return true;
		} catch (error:Dynamic) {rollback();throw error;}
		rollback();
		return false;
	}

	static function restoreImports<T>(target:Map<String, T>, previous:Map<String, T>):Void {
		target.clear();
		for (key => value in previous) target.set(key, value);
	}

	public function registerModule(module:Array<ModuleDecl>):Void {
		ensureActive();
		if (module == null) throw 'HScript class module is missing';
		var pkg:Array<String> = null;
		var imports:Map<String, Array<String>> = new Map();
		for (decl in module) switch (decl) {
			case DPackage(path):
				pkg = path;
			case DImport(path, _):
				if (path != null && path.length > 0) imports.set(path[path.length - 1], path);
			case DClass(c):
				var extend = c.extend;
				if (extend != null) {
					var superPath = new Printer().typeToString(extend);
					if (imports.exists(superPath)) switch (extend) {
						case CTPath(_, params): extend = CTPath(imports.get(superPath), params);
						case _:
					}
				}
				var classDecl:ClassDeclEx = {
					imports:imports.copy(), pkg:pkg == null ? null : pkg.copy(),
					name:c.name, params:c.params, meta:c.meta, isPrivate:c.isPrivate,
					extend:extend, implement:c.implement, fields:c.fields, isExtern:c.isExtern
				};
				registerClass(classDecl);
			case DTypedef(_):
				// ParserEx accepts typedefs; HScript-ex does not materialize them.
				// They do not add a runtime class descriptor.
		}
	}

	/** Keep a source import parse failure attached to this owner until its use. */
	public function markUnavailableImport(name:String, diagnostic:String):Void {
		if (!active || name == null || name == '') return;
		unavailableImports.set(name, diagnostic == null ? 'class module could not be loaded' : diagnostic);
		var shortName = name.substr(name.lastIndexOf('.') + 1);
		if (!unavailableImports.exists(shortName)) unavailableImports.set(shortName, unavailableImports.get(name));
	}

	function registerClass(declaration:ClassDeclEx):Void {
		var full = declaration.pkg == null || declaration.pkg.length == 0
			? declaration.name : declaration.pkg.join('.') + '.' + declaration.name;
		if (descriptors.exists(full))
			throw 'Duplicate owner class declaration: ' + full;
		descriptors.set(full, declaration);
		if (!aliases.exists(declaration.name) && !ambiguousAliases.exists(declaration.name))
			aliases.set(declaration.name, full);
		else if (aliases.exists(declaration.name) && aliases.get(declaration.name) != full) {
			aliases.remove(declaration.name);
			ambiguousAliases.set(declaration.name, true);
		}
	}

	public function findDescriptor(name:String, ?requester:ClassDeclEx):Null<ClassDeclEx> {
		ensureActive();
		if (name == null || name == '') return null;
		if (descriptors.exists(name)) return descriptors.get(name);
		if (requester != null) {
			if (requester.imports != null && requester.imports.exists(name)) {
				var imported = requester.imports.get(name).join('.');
				if (descriptors.exists(imported)) return descriptors.get(imported);
			}
			if (requester.pkg != null && requester.pkg.length > 0) {
				var local = requester.pkg.join('.') + '.' + name;
				if (descriptors.exists(local)) return descriptors.get(local);
				// HScript-ex qualifies an unqualified superclass with its own
				// package before asking the scope to resolve it. Haxe's implicit
				// source/import.hx may instead bind that name to a class in another
				// package. Use the requester's explicit imported descriptor when the
				// package-relative class does not exist.
				var localPrefix = requester.pkg.join('.') + '.';
				if (name.substr(0, localPrefix.length) == localPrefix) {
					var shortName = name.substr(localPrefix.length);
					if (shortName.indexOf('.') < 0 && requester.imports != null
						&& requester.imports.exists(shortName)) {
						var imported = requester.imports.get(shortName).join('.');
						if (descriptors.exists(imported)) return descriptors.get(imported);
					}
					if (shortName.indexOf('.') < 0 && !ambiguousAliases.exists(shortName)
						&& aliases.exists(shortName)) return descriptors.get(aliases.get(shortName));
				}
			}
		}
		if (!ambiguousAliases.exists(name) && aliases.exists(name))
			return descriptors.get(aliases.get(name));
		return null;
	}

	/** Resolve an imported source class as a value without publishing it globally. */
	public function resolveClassSymbol(name:String, ?requester:ClassDeclEx):Null<ScriptClassSymbol> {
		ensureActive();
		if (requester != null && name != null && name.indexOf('.') < 0) {
			var explicitImport = requester.imports != null && requester.imports.exists(name);
			var samePackage = requester.pkg != null && requester.pkg.length > 0
				&& descriptors.exists(requester.pkg.join('.') + '.' + name);
			if (!explicitImport && !samePackage) return null;
		}
		var descriptor = findDescriptor(name, requester);
		if (descriptor == null) return null;
		var packageName = descriptor.pkg == null ? '' : descriptor.pkg.join('.');
		var fullName = packageName == '' ? descriptor.name : packageName + '.' + descriptor.name;
		var existing = classSymbols.get(fullName);
		if (existing != null) return existing;
		var symbol = new ScriptClassSymbol(this, descriptor, fullName);
		classSymbols.set(fullName, symbol);
		return symbol;
	}

	/** Resolve only the lexical class: Haxe does not inherit static fields. */
	public function findStaticFieldSymbol(name:String, requester:ClassDeclEx):Null<ScriptClassSymbol> {
		ensureActive();
		if (requester == null) return null;
		for (field in requester.fields) if (field.name == name) {
			if (field.access.indexOf(AStatic) < 0) return null;
			switch (field.kind) {
				case KVar(_):
					var full = requester.pkg == null || requester.pkg.length == 0 ? requester.name
						: requester.pkg.join('.') + '.' + requester.name;
					return resolveClassSymbol(full);
				case _: return null;
			}
		}
		return null;
	}

	/** Read a declared static var from an owner source class, initializing it once. */
	public function getStaticField(symbol:ScriptClassSymbol, fieldName:String,
		evaluate:Expr->Dynamic):{handled:Bool, value:Dynamic} {
		var field = staticVar(symbol, fieldName);
		if (field == null) return {handled:false, value:null};
		var key = staticFieldKey(symbol, fieldName);
		if (ownerStaticValues.exists(key)) return {handled:true, value:ownerStaticValues.get(key)};

		var initial = defaultStaticValue(field.type);
		// Publish the Haxe default before evaluating the initializer so a
		// recursive read observes the default instead of recursing forever.
		ownerStaticValues.set(key, initial);
		if (field.expr != null) {
			try {
				initial = evaluate == null ? null : evaluate(field.expr);
				ownerStaticValues.set(key, initial);
			} catch (error:Dynamic) {
				ownerStaticValues.remove(key);
				throw error;
			}
		}
		return {handled:true, value:initial};
	}

	/** Write an owner source static var through its resolved class symbol. */
	public function setStaticField(symbol:ScriptClassSymbol, fieldName:String, value:Dynamic):Bool {
		if (staticVar(symbol, fieldName) == null) return false;
		ownerStaticValues.set(staticFieldKey(symbol, fieldName), value);
		return true;
	}

	/**
		Set a loaded owner's source static field from native compatibility code.
		`className` may be its full source path or an unambiguous owner-local alias.
		Returns false when the class or declared static var is absent.
	*/
	public function setOwnerStaticField(className:String, fieldName:String, value:Dynamic):Bool {
		ensureActive();
		var symbol = resolveClassSymbol(className);
		return symbol != null && setStaticField(symbol, fieldName, value);
	}

	function staticVar(symbol:ScriptClassSymbol, fieldName:String):Null<hscript.Expr.VarDecl> {
		ensureActive();
		if (symbol == null || fieldName == null || fieldName == '') return null;
		if (symbol.scope != this)
			throw '[hscript-class-scope] static field access crossed owner scopes';
		if (descriptors.get(symbol.fullName) != symbol.descriptor) return null;
		for (field in symbol.descriptor.fields) {
			if (field.name != fieldName || field.access.indexOf(AStatic) < 0) continue;
			switch (field.kind) {
				case KVar(value): return value;
				case _: return null;
			}
		}
		return null;
	}

	inline function staticFieldKey(symbol:ScriptClassSymbol, fieldName:String):String
		return symbol.fullName + '\x00' + fieldName;

	static function defaultStaticValue(type:Null<CType>):Dynamic {
		if (type == null) return null;
		var typeName = new Printer().typeToString(type);
		return switch (typeName) {
			case 'Int', 'Float': 0;
			case 'Bool': false;
			default: null;
		};
	}

	/** Resolve an explicit Haxe import for a native superclass. */
	public function findBinding(name:String, ?requester:ClassDeclEx):Dynamic {
		ensureActive();
		if (name == null || name == '') return null;
		if (bindings.exists(name)) return bindings.get(name);
		if (requester != null && requester.imports != null && requester.imports.exists(name)) {
			var imported = requester.imports.get(name).join('.');
			if (bindings.exists(imported)) return bindings.get(imported);
		}
		// A Haxe source/import.hx import is visible to modules in its source
		// tree, but it is not repeated in each parsed module's import list. When
		// resolving a package-qualified superclass, allow its unqualified name
		// to use an explicitly seeded compatibility binding after owner classes
		// in that package have already had a chance to resolve as descriptors.
		// Keep this limited to a one-segment local name and an unambiguous alias;
		// class descriptors still win and no process-wide Type.resolve fallback
		// is introduced.
		if (requester != null && requester.pkg != null && requester.pkg.length > 0) {
			var localPrefix = requester.pkg.join('.') + '.';
			if (name.substr(0, localPrefix.length) == localPrefix) {
				var shortName = name.substr(localPrefix.length);
				if (shortName.indexOf('.') < 0 && !ambiguousBindings.exists(shortName)) {
					if (requester.imports != null && requester.imports.exists(shortName)) {
						var imported = requester.imports.get(shortName).join('.');
						if (bindings.exists(imported)) return bindings.get(imported);
					}
					if (bindings.exists(shortName)) return bindings.get(shortName);
				}
			}
		}
		if (!ambiguousBindings.exists(name) && bindings.exists(name)) return bindings.get(name);
		return null;
	}

	public function createInstance(name:String, args:Array<Dynamic> = null,
		?requester:ClassDeclEx):Null<AbstractScriptClass> {
		ensureActive();
		var descriptor = findDescriptor(name, requester);
		if (descriptor == null) {
			var unavailable = unavailableImports.get(name);
			if (unavailable == null && requester != null && requester.imports != null
				&& requester.imports.exists(name))
				unavailable = unavailableImports.get(requester.imports.get(name).join('.'));
			if (unavailable != null)
				throw '[codename-class-module] ' + unavailable;
			return null;
		}
		return new ScriptClass(descriptor, args == null ? [] : args, this);
	}

	/** Adapt a selected-owner source class passed to FlxTypedGroup.recycle. */
	public function recycleScriptClass(receiver:Dynamic, args:Array<Dynamic>):{handled:Bool, value:Dynamic} {
		#if flixel
		if (!active || !Std.isOfType(receiver, FlxTypedGroup) || args == null || args.length == 0
			|| !Std.isOfType(args[0], ScriptClassSymbol)) return {handled:false, value:null};
		var symbol:ScriptClassSymbol = cast args[0];
		if (symbol.scope != this)
			throw '[hscript-class-scope] recycle received a source class from another owner';
		var group:FlxTypedGroup<Dynamic> = cast receiver;
		var objectFactory:Dynamic = args.length > 1 ? args[1] : null;
		var force = args.length > 2 && args[2] == true;
		var revive = args.length <= 3 || args[3] != false;
		var factory:Void->Dynamic = function():Dynamic {
			var value:Dynamic = objectFactory == null
				? createInstance(symbol.fullName, [])
				: Reflect.callMethod(null, objectFactory, []);
			if (Std.isOfType(value, ScriptClass)) {
				var proxy:ScriptClass = cast value;
				if (!ownsScriptClassProxy(proxy))
					throw '[hscript-class-scope] recycle factory returned a source object from another owner';
				return bridgeOwnedFlxBasic(proxy);
			}
			return value;
		};

		// Preserve FlxGroup's rotating behavior at positive capacity. It ignores
		// the class filter once full, and the factory supplies a native bridge
		// only when the group needs a new owner object.
		if (group.maxSize > 0) {
			var result:Dynamic = group.recycle(cast PsychScriptClassBasicBridge, factory, force, revive);
			return {handled:true, value:ownerForRecycleResult(result)};
		}

		for (member in group.members) {
			if (member == null || member.exists || !Std.isOfType(member, PsychScriptClassBasicBridge)) continue;
			var bridge:PsychScriptClassBasicBridge = cast member;
			var owner = bridge.scriptOwner();
			if (owner == null || nativeBasicBridges.get(owner) != bridge
				|| !matchesRecycleClass(owner, symbol.descriptor, force)) continue;
			if (revive) bridge.revive();
			return {handled:true, value:owner};
		}

		var created = factory();
		if (created != null) group.add(cast created);
		return {handled:true, value:ownerForRecycleResult(created)};
		#else
		return {handled:false, value:null};
		#end
	}

	#if flixel
	function ownerForRecycleResult(value:Dynamic):Dynamic {
		if (!Std.isOfType(value, PsychScriptClassBasicBridge)) return value;
		var bridge:PsychScriptClassBasicBridge = cast value;
		var owner = bridge.scriptOwner();
		return owner != null && nativeBasicBridges.get(owner) == bridge ? owner : value;
	}

	function matchesRecycleClass(owner:ScriptClass, requested:ClassDeclEx, force:Bool):Bool {
		var current:ClassDeclEx = owner._c;
		if (force) return current == requested;
		var remaining = 0;
		while (current != null && remaining++ < MAX_CLASS_DEPTH) {
			if (current == requested) return true;
			if (current.extend == null) break;
			var parentName = new Printer().typeToString(current.extend);
			current = findDescriptor(parentName, current);
		}
		return false;
	}
	#end

	/**
	 * HScript-ex classes compose a native Flixel superclass instead of being
	 * instances of it. Convert owner-local script objects at native Flixel
	 * group mutation and sprite drawing calls that take a FlxBasic argument.
	 * Leave other calls and values untouched.
	 */
	public function unwrapNativeGroupArguments(receiver:Dynamic, method:String,
		args:Array<Dynamic>):Array<Dynamic> {
		#if flixel
		if (!active || receiver == null || args == null || args.length == 0) return args;
		var nativeGroup = Std.isOfType(receiver, FlxTypedGroup)
			|| Std.isOfType(receiver, FlxTypedSpriteGroup);
		if (nativeGroup && (method == 'forEach' || method == 'forEachAlive'
			|| method == 'forEachDead' || method == 'forEachExists')
			&& Reflect.isFunction(args[0])) {
			var callback = args[0];
			var adapted = args.copy();
			adapted[0] = function(member:Dynamic):Void {
				var value:Dynamic = member;
				if (Std.isOfType(member, PsychScriptClassBasicBridge)) {
					var bridge:PsychScriptClassBasicBridge = cast member;
					var owner = bridge.scriptOwner();
					if (owner != null && nativeBasicBridges.get(owner) == bridge)
						value = owner;
				}
				Reflect.callMethod(null, callback, [value]);
			};
			return adapted;
		}
		if ((method != 'add' && method != 'insert' && method != 'remove')
			|| !nativeGroup) return args;

		var result = args.copy();
		for (index in 0...result.length) {
			var value = result[index];
			if (Std.isOfType(value, ScriptClass)) {
				var proxy:ScriptClass = cast value;
				if (Std.isOfType(receiver, FlxTypedGroup) && method != 'remove')
					result[index] = bridgeOwnedFlxBasic(proxy);
				else if (Std.isOfType(receiver, FlxTypedGroup) && method == 'remove')
					result[index] = nativeBasicBridges.get(proxy) == null
						? unwrapOwnedFlxBasic(proxy) : nativeBasicBridges.get(proxy);
				else
					result[index] = unwrapOwnedFlxBasic(proxy);
			}
		}
		return result;
		#else
		return args;
		#end
	}

	/** Indexed reads from a native Flixel group's `members` array expose its
	 * owner bridge. Return the matching owner ScriptClass to HScript so inherited
	 * sprite fields remain available without replacing or copying group storage.
	 */
	public function unwrapIndexedMember(value:Dynamic):Dynamic {
		#if flixel
		if (!active || !Std.isOfType(value, PsychScriptClassBasicBridge)) return value;
		var bridge:PsychScriptClassBasicBridge = cast value;
		var owner = bridge.scriptOwner();
		return owner != null && nativeBasicBridges.get(owner) == bridge ? owner : value;
		#else
		return value;
		#end
	}

	/** Adapt one owner object at the Psych BaseStage scene-insertion boundary. */
	public function nativeFlixelSceneObject(value:Dynamic, adding:Bool):Dynamic {
		#if flixel
		if (!active || !Std.isOfType(value, ScriptClass)) return value;
		var proxy:ScriptClass = cast value;
		if (adding) return bridgeOwnedFlxBasic(proxy);
		var bridge = nativeBasicBridges.get(proxy);
		return bridge == null ? unwrapOwnedFlxBasic(proxy) : bridge;
		#else
		return value;
		#end
	}

	/** Native static helpers can be invoked by HScript's direct call path, which
	 * does not pass through InterpEx.fcall. Resolve a script object's native base
	 * within its own owner scope before such a helper receives it. */
	public function unwrapNativeArgument(value:Dynamic):Dynamic {
		ensureActive();
		if (!Std.isOfType(value, ScriptClass)) return value;
		var current:Dynamic = value;
		var seen:Array<ScriptClass> = [];
		while (Std.isOfType(current, ScriptClass)) {
			var proxy:ScriptClass = cast current;
			if (seen.indexOf(proxy) >= 0)
				throw '[hscript-class-scope] cyclic script superclass in native helper call';
			if (!ownsScriptClassProxy(proxy))
				throw '[hscript-class-scope] native helper call received a script object outside its owner scope';
			seen.push(proxy);
			current = proxy.superClass;
		}
		return current;
	}

	/** FlxTween keeps and reflects on its first target argument after the call
	 * returns. Owner script classes compose native FlxBasic instances, so unwrap
	 * only same-scope script targets at these exact native tween target methods.
	 * Other FlxTween arguments and ordinary calls retain their original values.
	 */
	public function unwrapNativeTweenArguments(receiver:Dynamic, method:String,
		args:Array<Dynamic>):Array<Dynamic> {
		#if flixel
		if (!active || receiver != FlxTween || args == null || args.length == 0
			|| NATIVE_TWEEN_TARGET_METHODS.indexOf(method) < 0
			|| !Std.isOfType(args[0], ScriptClass)) return args;

		var result = args.copy();
		result[0] = unwrapOwnedFlxBasic(args[0]);
		return result;
		#else
		return args;
		#end
	}

	#if flixel
	function bridgeOwnedFlxBasic(proxy:ScriptClass):FlxBasic {
		var existing = nativeBasicBridges.get(proxy);
		if (existing != null) return existing;
		var basic:FlxBasic = cast unwrapOwnedFlxBasic(proxy);
		var bridge = new PsychScriptClassBasicBridge(proxy, basic, this);
		nativeBasicBridges.set(proxy, bridge);
		ownedNativeBasicBridges.push(bridge);
		return bridge;
	}

	/** A ScriptClass's own destroy method can run before Flixel destroys its
	 * native group member (for example, a cutscene removes itself after finishing).
	 */
	public function noteScriptClassDestroy(proxy:ScriptClass):Void {
		if (!active || proxy == null) return;
		var bridge = nativeBasicBridges.get(proxy);
		if (bridge != null) bridge.noteOwnerDestroyCalled();
	}

	/** Called by the bridge when Flixel or the owner scope disposes it. */
	public function forgetNativeBasicBridge(bridge:PsychScriptClassBasicBridge):Void {
		if (bridge == null) return;
		ownedNativeBasicBridges.remove(bridge);
		var owner = bridge.scriptOwner();
		if (owner != null && nativeBasicBridges.get(owner) == bridge) nativeBasicBridges.remove(owner);
	}

	function unwrapOwnedFlxBasic(value:Dynamic):Dynamic {
		if (value == null || Std.isOfType(value, FlxBasic)) return value;
		if (!Std.isOfType(value, ScriptClass)) return value;

		var current:Dynamic = value;
		var seen:Array<ScriptClass> = [];
		while (Std.isOfType(current, ScriptClass)) {
			var proxy:ScriptClass = cast current;
			if (seen.indexOf(proxy) >= 0)
				throw '[hscript-class-scope] cyclic script superclass in native group call';
			if (!ownsScriptClassProxy(proxy))
				throw '[hscript-class-scope] native group call received a script object outside its owner scope';
			seen.push(proxy);
			current = proxy.superClass;
		}
		if (!Std.isOfType(current, FlxBasic))
			throw '[hscript-class-scope] native group member does not wrap a FlxBasic';
		return current;
	}
	#end

	function ownsScriptClassProxy(proxy:ScriptClass):Bool {
		if (proxy == null || proxy._c == null || proxy._classScope != this || !active) return false;
		var packageName = proxy._c.pkg == null ? '' : proxy._c.pkg.join('.');
		var fullName = packageName == '' ? proxy._c.name : packageName + '.' + proxy._c.name;
		return descriptors.exists(fullName) && descriptors.get(fullName) == proxy._c;
	}

	public function seedInterpreter(interp:Interp):Void {
		ensureActive();
		if (interp == null) return;
		for (name in bindings.keys()) interp.variables.set(name, bindings.get(name));
	}

	public function isActive():Bool return active;

	public function release():Void {
		if (!active) return;
		#if flixel
		var firstBridgeFailure:Dynamic = null;
		#end
		#if flixel
		// Keep the owner interpreter alive while its authored cleanup callbacks
		// run, then make every retained native wrapper inert and release it.
		for (bridge in ownedNativeBasicBridges.copy()) {
			try bridge.destroy() catch (error:Dynamic) {
				if (firstBridgeFailure == null) firstBridgeFailure = error;
			}
		}
		ownedNativeBasicBridges.resize(0);
		nativeBasicBridges.clear();
		#end
		active = false;
		nativeConstructionHooks.clear();
		nativeFactories.clear();
		descriptors.clear();
		aliases.clear();
		ambiguousAliases.clear();
		classSymbols.clear();
		ownerStaticValues.clear();
		bindings.clear();
		ambiguousBindings.clear();
		unavailableImports.clear();
		#if flixel
		if (firstBridgeFailure != null)
			trace('[hscript-class-scope] native member cleanup failed: ' + Std.string(firstBridgeFailure));
		#end
	}

	function ensureActive():Void {
		if (!active) throw '[hscript-class-scope] owner class scope has been released';
	}
}
