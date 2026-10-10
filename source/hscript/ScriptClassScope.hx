package hscript;

import hscript.Expr.ModuleDecl;
import hscript.Expr.FieldAccess;
import hscript.Expr.FieldDecl;
import hscript.Expr.FieldKind;
import hscript.Expr.Expr;
import hscript.Expr.CType;
#if flixel
import PsychScriptClassBasicBridge;
import PsychScriptClassSprite;
import PsychScriptClassBasic;
import PsychScriptClassObject;
import PsychScriptClassGroup;
import PsychScriptClassText;
import PsychScriptClassSpriteGroup;
import SourceNativeClassAdapter;
import SourceNativeClassLifecycle;
import flixel.text.FlxText;
import flixel.FlxSprite;
import flixel.FlxBasic;
import flixel.FlxObject;
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
	final nativeAdapters:haxe.ds.ObjectMap<ScriptClass, SourceNativeClassLifecycle> = new haxe.ds.ObjectMap();
	final nativeMemberArrays:haxe.ds.ObjectMap<Dynamic, Bool> = new haxe.ds.ObjectMap();
	#end
	final nativeConstructionHooks:haxe.ds.ObjectMap<Dynamic, {
		before:ScriptClass->Void, after:ScriptClass->Dynamic->Void, initializedFields:Array<String>, prepare:Dynamic->Void
	}> = new haxe.ds.ObjectMap();
	final nativeFactories:haxe.ds.ObjectMap<Dynamic, Array<Dynamic>->Dynamic> = new haxe.ds.ObjectMap();
	var active:Bool = true;
	var releasing:Bool = false;
	var nativeCallbackDepth:Int = 0;
	var releaseRequested:Bool = false;
	var valueAccess:InterpEx;
	final nativeMethods:haxe.ds.ObjectMap<Dynamic, Map<String, {method:Dynamic, wrapped:Dynamic}>> = new haxe.ds.ObjectMap();

	public function new() {}

	/** Observe a native super constructor without replacing its class identity. */
	public function bindNativeConstruction(type:Dynamic, before:ScriptClass->Void,
		after:ScriptClass->Dynamic->Void, ?initializedFields:Array<String>, ?prepare:Dynamic->Void):Void {
		ensureActive();
		nativeConstructionHooks.set(type, {before: before, after: after, initializedFields: initializedFields, prepare: prepare});
	}

	/** Restore a temporary native constructor policy without replacing class identity. */
	public function captureNativeConstruction(type:Dynamic):Void->Void {
		ensureActive();
		var hook = nativeConstructionHooks.get(type), factory = nativeFactories.get(type);
		return function():Void {
			if (!active) return;
			if (hook == null) nativeConstructionHooks.remove(type); else nativeConstructionHooks.set(type, hook);
			if (factory == null) nativeFactories.remove(type); else nativeFactories.set(type, factory);
		};
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
		#if flixel
		var adapter:Dynamic = type == FlxSprite ? PsychScriptClassSprite
			: type == FlxText ? PsychScriptClassText
			: type == FlxTypedSpriteGroup ? PsychScriptClassSpriteGroup
			: type == FlxBasic ? PsychScriptClassBasic
			: type == FlxObject ? PsychScriptClassObject
			: type == FlxTypedGroup ? PsychScriptClassGroup : null;
		if (adapter != null) {
			var bind = function(instance:SourceNativeClassAdapter):Void {
				owner.superClass = instance;
				instance.bind(root, this);
				nativeAdapters.set(root, instance.sourceLifecycle);
			};
			var nativeArgs:Array<Dynamic> = [bind];
			if (args != null) nativeArgs = nativeArgs.concat(args);
			Type.createInstance(adapter, nativeArgs);
		} else
		#end
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
		var instance:AbstractScriptClass = cast withNativeLifetime(function():Dynamic {
			return new ScriptClass(descriptor, args == null ? [] : args, this);
		});
		// A constructor may request owner teardown. Do not publish a disposed object.
		ensureActive();
		return instance;
	}

	/** Recycle through one source/native class matcher while keeping native capacity rotation. */
	public function recycleScriptClass(receiver:Dynamic, args:Array<Dynamic>):{handled:Bool, value:Dynamic} {
		#if flixel
		if (!Std.isOfType(receiver, FlxTypedGroup) && !Std.isOfType(receiver, FlxTypedSpriteGroup)) return {handled:false, value:null};
		ensureActive();
		if (args == null) args = [];
		var requested:Dynamic = args.length > 0 ? args[0] : null;
		validateMemberClass(requested);
		var sprites = Std.isOfType(receiver, FlxTypedSpriteGroup);
		var group:FlxTypedGroup<Dynamic> = sprites ? (cast receiver:FlxTypedSpriteGroup<FlxSprite>).group : cast receiver;
		var objectFactory:Dynamic = args.length > 1 ? args[1] : null;
		var force = args.length > 2 && args[2] == true;
		var revive = args.length <= 3 || args[3] != false;
		var factory:Void->Dynamic = function():Dynamic {
			var value:Dynamic = null;
			if (objectFactory != null) value = Reflect.callMethod(null, objectFactory, []);
			else if (Std.isOfType(requested, ScriptClassSymbol)) {
				var symbol:ScriptClassSymbol = cast requested;
				value = symbol.scope.createInstance(symbol.fullName, []);
			} else if (requested != null) value = Type.createInstance(cast requested, []);
			ensureActive();validateMemberClass(requested);
			return nativeGroupValue(value, sprites, true);
		};
		if (group.maxSize > 0)
			return {handled:true, value:unwrapIndexedMember(group.recycle(null, factory, force, revive))};
		var available = firstAvailableMember(group, requested, force);
		if (available != null) {
			if (revive) available.revive();
			return {handled:true, value:unwrapIndexedMember(available)};
		}
		var created = factory();
		return {handled:true, value:unwrapIndexedMember(created == null ? null : group.add(cast created))};
		#else
		return {handled:false, value:null};
		#end
	}

	#if flixel

	function validateMemberClass(requested:Dynamic):Void {
		if (!Std.isOfType(requested, ScriptClassSymbol)) return;
		var symbol:ScriptClassSymbol = cast requested;
		if (symbol.scope == null || !symbol.scope.isActive() || symbol.scope.findDescriptor(symbol.fullName) != symbol.descriptor)
			throw '[hscript-class-scope] Native group received an unowned or released source class';
	}

	function nativeMemberBase(member:Dynamic):Dynamic {
		var value = unwrapIndexedMember(member);
		return Std.isOfType(value, ScriptClass) ? actualOwner(cast value).unwrapOwnedFlxBasic(cast value) : member;
	}

	function memberMatchesClass(member:Dynamic, requested:Dynamic, force:Bool):Bool {
		if (requested == null) return !force;
		var value = unwrapIndexedMember(member);
		if (Std.isOfType(requested, ScriptClassSymbol)) {
			if (!Std.isOfType(value, ScriptClass)) return false;
			return actualOwner(cast value).matchesRecycleClass(cast value, (cast requested:ScriptClassSymbol).descriptor, force);
		}
		if (Std.isOfType(value, ScriptClass))
			return !force && Std.isOfType(nativeMemberBase(member), requested);
		return Std.isOfType(member, requested)
			&& (!force || Type.getClassName(Type.getClass(member)) == Type.getClassName(requested));
	}

	function firstAvailableMember(group:FlxTypedGroup<Dynamic>, requested:Dynamic, force:Bool):Dynamic {
		return group.getFirst(function(member:Dynamic):Bool {
			var basic:FlxBasic = cast nativeMemberBase(member);
			return !basic.exists && memberMatchesClass(member, requested, force);
		});
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

	/** Capture a native method once so direct, reflected and borrowed calls use
	 * the same argument conversion and return the authored member identity. */
	public function bindNativeMethod(receiver:Dynamic, name:String, method:Dynamic):Dynamic {
		#if flixel
		var sprites = Std.isOfType(receiver, FlxTypedSpriteGroup);
		var group = Std.isOfType(receiver, FlxTypedGroup) || sprites;
		if (group && name == 'members' && Std.isOfType(method, Array))
			nativeMemberArrays.set(method, sprites || nativeMemberArrays.get(method) == true);
		else if (sprites && name == 'group' && Std.isOfType(method, FlxTypedGroup))
			nativeMemberArrays.set((cast method:FlxTypedGroup<Dynamic>).members, true);
		if (!Reflect.isFunction(method)) return method;
		var arrayMethod = Std.isOfType(receiver, Array) && nativeMemberArrays.exists(receiver)
			&& ['push', 'unshift', 'insert', 'remove', 'contains', 'indexOf', 'lastIndexOf', 'pop', 'shift',
				'splice', 'slice', 'copy', 'concat', 'filter', 'map', 'sort', 'reverse', 'resize', 'iterator', 'keyValueIterator'].indexOf(name) >= 0;
		var supported = arrayMethod || group && ['add', 'insert', 'remove', 'replace', 'forEach', 'forEachAlive', 'forEachDead', 'forEachExists', 'forEachOfType', 'recycle',
			'getFirstAvailable', 'getFirstExisting', 'getFirstAlive', 'getFirstDead', 'getFirst', 'getLast', 'getFirstIndex', 'getLastIndex',
			'any', 'every', 'getRandom', 'iterator', 'keyValueIterator', 'sort'].indexOf(name) >= 0;
		if (!supported && !(receiver == FlxTween && NATIVE_TWEEN_TARGET_METHODS.indexOf(name) >= 0)) return method;
		ensureActive();
		var methods = nativeMethods.get(receiver);
		if (methods == null) {methods = new Map();nativeMethods.set(receiver, methods);}
		var previous = methods.get(name);
		if (previous != null && Reflect.compareMethods(previous.method, method)) return previous.wrapped;
		var wrapped = Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			ensureActive();
			if (arrayMethod) return callNativeMemberArray(receiver, name, method, args);
			if (name == 'recycle') {
				var result = recycleScriptClass(receiver, args);
				if (result.handled) return result.value;
			}
			if (group && (name == 'getFirstAvailable' || name == 'forEachOfType')) {
				var requested:Dynamic = args.length > 0 ? args[0] : null;
				validateMemberClass(requested);
				var native:FlxTypedGroup<Dynamic> = sprites ? (cast receiver:FlxTypedSpriteGroup<FlxSprite>).group : cast receiver;
				if (name == 'getFirstAvailable') return unwrapIndexedMember(firstAvailableMember(native, requested, args.length > 1 && args[1] == true));
				var callback = args[1];
				native.forEach(function(member:Dynamic):Void {
					ensureActive();validateMemberClass(requested);
					if (requested != null && memberMatchesClass(member, requested, false))
						Reflect.callMethod(null, callback, [unwrapIndexedMember(member)]);
				}, args.length > 2 && args[2] == true);
				return null;
			}
			if (group && ['getFirstExisting', 'getFirstAlive', 'getFirstDead'].indexOf(name) >= 0) {
				var native:FlxTypedGroup<Dynamic> = sprites ? (cast receiver:FlxTypedSpriteGroup<FlxSprite>).group : cast receiver;
				return unwrapIndexedMember(native.getFirst(function(member:Dynamic):Bool {
					var basic:FlxBasic = cast nativeMemberBase(member);
					return name == 'getFirstDead' ? !basic.alive : basic.exists && (name != 'getFirstAlive' || basic.alive);
				}));
			}
			var adapted = unwrapNativeGroupArguments(receiver, name, args);
			adapted = unwrapNativeTweenArguments(receiver, name, adapted);
			var result = Reflect.callMethod(receiver, method, adapted);
			return group && (name == 'iterator' || name == 'keyValueIterator')
				? nativeMemberIterator(result, name == 'keyValueIterator') : unwrapIndexedMember(result);
		});
		methods.set(name, {method:method, wrapped:wrapped});
		return wrapped;
		#else
		return method;
		#end
	}

	function actualOwner(proxy:ScriptClass):ScriptClassScope {
		var scope = proxy._classScope;
		if (scope == null || !scope.isActive() || !scope.ownsScriptClassProxy(proxy))
			throw '[hscript-class-scope] Native call received an unowned or released source object';
		return scope;
	}

	/**
	 * HScript-ex classes compose a native Flixel superclass instead of being
	 * instances of it. Convert explicitly supplied source objects through their actual owner at native Flixel
	 * group mutation and sprite drawing calls that take a FlxBasic argument.
	 * Leave other calls and values untouched.
	 */
	public function unwrapNativeGroupArguments(receiver:Dynamic, method:String,
		args:Array<Dynamic>):Array<Dynamic> {
		#if flixel
		if (!active || receiver == null || args == null || args.length == 0) return args;
		var nativeGroup = Std.isOfType(receiver, FlxTypedGroup)
			|| Std.isOfType(receiver, FlxTypedSpriteGroup);
		if (nativeGroup && ['forEach', 'forEachAlive', 'forEachDead', 'forEachExists', 'getFirst', 'getLast',
			'getFirstIndex', 'getLastIndex', 'any', 'every', 'iterator'].indexOf(method) >= 0
			&& Reflect.isFunction(args[0])) {
			var callback = args[0];
			var adapted = args.copy();
			adapted[0] = function(member:Dynamic):Dynamic {
				ensureActive();
				return Reflect.callMethod(null, callback, [unwrapIndexedMember(member)]);
			};
			return adapted;
		}
		if (nativeGroup && method == 'sort' && Reflect.isFunction(args[0])) {
			var callback = args[0], adapted = args.copy();
			adapted[0] = function(order:Int, left:Dynamic, right:Dynamic):Int {
				ensureActive();
				return Reflect.callMethod(null, callback, [order, unwrapIndexedMember(left), unwrapIndexedMember(right)]);
			};
			return adapted;
		}
		if ((method != 'add' && method != 'insert' && method != 'remove' && method != 'replace')
			|| !nativeGroup) return args;

		var result = args.copy();
		var sprites = Std.isOfType(receiver, FlxTypedSpriteGroup);
		for (index in 0...result.length) {
			if (Std.isOfType(result[index], ScriptClass))
				result[index] = nativeGroupValue(result[index], sprites,
					method != 'remove' && !(method == 'replace' && index == 0));
		}
		return result;
		#else
		return args;
		#end
	}

	#if flixel
	function nativeGroupValue(value:Dynamic, sprites:Bool, adding:Bool):Dynamic {
		if (Std.isOfType(value, ScriptClass)) {
			var owner:ScriptClass = cast value;
			var scope = actualOwner(owner);
			if (sprites) value = scope.unwrapOwnedFlxBasic(owner);
			else if (adding) value = scope.bridgeOwnedFlxBasic(owner);
			else value = scope.nativeBasicBridges.get(owner) == null
				? scope.unwrapOwnedFlxBasic(owner) : scope.nativeBasicBridges.get(owner);
		}
		if (sprites && value != null && !Std.isOfType(value, FlxSprite))
			throw '[hscript-class-scope] Sprite group member must have a native FlxSprite base';
		return value;
	}
	#end

	#if flixel
	function nativeMemberIterator(iterator:Dynamic, keyValue:Bool):Dynamic {
		return {hasNext:function():Bool {ensureActive();return iterator.hasNext();}, next:function():Dynamic {
			ensureActive();
			var value:Dynamic = iterator.next();
			if (keyValue) {value.value = unwrapIndexedMember(value.value);return value;}
			return unwrapIndexedMember(value);
		}};
	}

	function callNativeMemberArray(receiver:Dynamic, name:String, method:Dynamic, args:Array<Dynamic>):Dynamic {
		var sprites = nativeMemberArrays.get(receiver);
		var adapted = args.copy();
		switch (name) {
			case 'push' | 'unshift' | 'insert':
				var index = name == 'insert' ? 1 : 0;
				if (adapted.length > index) adapted[index] = nativeGroupValue(adapted[index], sprites, true);
			case 'remove' | 'contains' | 'indexOf' | 'lastIndexOf':
				if (adapted.length > 0) adapted[0] = nativeGroupValue(adapted[0], sprites, false);
			case 'map' | 'filter':
				var callback = adapted[0];
				adapted[0] = function(value:Dynamic):Dynamic {
					ensureActive();
					return Reflect.callMethod(null, callback, [unwrapIndexedMember(value)]);
				};
			case 'sort':
				var callback = adapted[0];
				adapted[0] = function(left:Dynamic, right:Dynamic):Int {
					ensureActive();
					return Reflect.callMethod(null, callback, [unwrapIndexedMember(left), unwrapIndexedMember(right)]);
				};
			default:
		}
		var result:Dynamic = Reflect.callMethod(receiver, method, adapted);
		switch (name) {
			case 'pop' | 'shift': return unwrapIndexedMember(result);
			case 'splice' | 'slice' | 'copy' | 'concat' | 'filter':
				var values:Array<Dynamic> = cast result;
				return [for (value in values) unwrapIndexedMember(value)];
			case 'iterator' | 'keyValueIterator':
				return nativeMemberIterator(result, name == 'keyValueIterator');
			default:
		}
		return result;
	}
	#end

	/** Only explicit native accessor hooks expose their lexical backing storage. */
	public function nativeAccessorBacking(value:Dynamic, field:String):Dynamic {
		ensureActive();
		#if flixel
		var receiver = unwrapNativeArgument(value);
		if (Std.isOfType(receiver, SourceNativeClassAdapter)) {
			var adapter:SourceNativeClassAdapter = cast receiver;
			if (adapter.supportsNativeSuper('set_' + field) || adapter.supportsNativeSuper('get_' + field)) return receiver;
		}
		#end
		return null;
	}

	/** Preserve native property semantics and array identity during reflected writes. */
	public function nativePropertyValue(receiver:Dynamic, name:String, value:Dynamic):Dynamic {
		ensureActive();
		#if flixel
		if (name == 'members' && Std.isOfType(receiver, FlxTypedGroup) && Std.isOfType(value, Array)) {
			var group:FlxTypedGroup<Dynamic> = cast receiver;
			var sprites = nativeMemberArrays.get(group.members) == true;
			var values:Array<Dynamic> = cast value;
			var converted = [for (item in values) nativeGroupValue(item, sprites, true)];
			for (index in 0...values.length) values[index] = converted[index];
			nativeMemberArrays.set(values, sprites);
		}
		#end
		return value;
	}

	/** A tracked members array retains its original storage and native element type. */
	public function nativeArrayValue(collection:Dynamic, value:Dynamic):Dynamic {
		ensureActive();
		#if flixel
		if (collection != null && nativeMemberArrays.exists(collection))
			return nativeGroupValue(value, nativeMemberArrays.get(collection), true);
		#end
		return value;
	}

	/** Indexed reads from a native Flixel group's `members` array expose its
	 * owner bridge. Return the matching owner ScriptClass to HScript so inherited
	 * sprite fields remain available without replacing or copying group storage.
	 */
	public function unwrapIndexedMember(value:Dynamic):Dynamic {
		#if flixel
		if (!active) return value;
		if (Std.isOfType(value, SourceNativeClassAdapter)) {
			var sprite:SourceNativeClassAdapter = cast value;
			var owner = sprite.scriptOwner();
			if (owner == null) return value;
			return actualOwner(owner).nativeAdapters.get(owner) == sprite.sourceLifecycle ? owner : value;
		}
		if (!Std.isOfType(value, PsychScriptClassBasicBridge)) return value;
		var bridge:PsychScriptClassBasicBridge = cast value;
		var owner = bridge.scriptOwner();
		if (owner == null) return value;
		var scope = actualOwner(owner);
		return scope.nativeBasicBridges.get(owner) == bridge ? owner : value;
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
	 * script targets through their actual owner at these exact native tween target methods.
	 * Other FlxTween arguments and ordinary calls retain their original values.
	 */
	public function unwrapNativeTweenArguments(receiver:Dynamic, method:String,
		args:Array<Dynamic>):Array<Dynamic> {
		#if flixel
		if (!active || receiver != FlxTween || args == null || args.length == 0
			|| NATIVE_TWEEN_TARGET_METHODS.indexOf(method) < 0
			|| !Std.isOfType(args[0], ScriptClass)) return args;

		var result = args.copy();
		result[0] = actualOwner(args[0]).unwrapOwnedFlxBasic(args[0]);
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
		if (Std.isOfType(basic, SourceNativeClassAdapter)) return basic;
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
		var sprite = nativeAdapters.get(proxy.constructionRoot());
		if (sprite != null) sprite.noteOwnerDestroyCalled();
	}

	/** Called by the bridge when Flixel or the owner scope disposes it. */
	public function forgetNativeBasicBridge(bridge:PsychScriptClassBasicBridge):Void {
		if (bridge == null) return;
		ownedNativeBasicBridges.remove(bridge);
		var owner = bridge.scriptOwner();
		if (owner != null && nativeBasicBridges.get(owner) == bridge) nativeBasicBridges.remove(owner);
	}

	public function forgetNativeAdapter(sprite:SourceNativeClassLifecycle):Void {
		var owner = sprite.owner;
		if (owner != null && nativeAdapters.get(owner) == sprite) nativeAdapters.remove(owner);
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

	/** Other interpreters delegate source-object semantics to the same evaluator. */
	public function accessInterpreter():InterpEx {
		ensureActive();
		if (valueAccess == null) {valueAccess = new InterpEx(null, this);seedInterpreter(valueAccess);}
		return valueAccess;
	}

	/** Only adapter lifecycle methods need a nonvirtual native super entry. */
	public function nativeSuperMethod(receiver:Dynamic, name:String):Dynamic {
		#if flixel
		if (Std.isOfType(receiver, SourceNativeClassAdapter) && (cast receiver:SourceNativeClassAdapter).supportsNativeSuper(name)) {
			ensureActive();
			return Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
				ensureActive();
				return (cast receiver:SourceNativeClassAdapter).callNativeSuper(name, args);
			});
		}
		#end
		return null;
	}
	public function callNativeSuper(receiver:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		var method = nativeSuperMethod(receiver, name);
		return method == null ? Reflect.callMethod(receiver, Reflect.field(receiver, name), args)
			: Reflect.callMethod(null, method, args);
	}

	/** Finish the current native lifecycle traversal before releasing its owner. */
	public function callNativeLifecycle(owner:ScriptClass, name:String, args:Array<Dynamic>, nativeResult:Bool = false):Dynamic {
		return withNativeLifetime(function():Dynamic {
			var result = owner.callFunction(name, args);
			return nativeResult ? unwrapNativeArgument(result) : result;
		});
	}

	/** Source constructors and native callbacks share one deferred-release boundary. */
	function withNativeLifetime(callback:Void->Dynamic):Dynamic {
		ensureActive();
		nativeCallbackDepth++;
		var result:Dynamic = null, failure:Dynamic = null;
		var failed = false;
		try result = callback() catch (error:Dynamic) {failed = true;failure = error;}
		nativeCallbackDepth--;
		if (nativeCallbackDepth == 0 && releaseRequested) {releaseRequested = false;release();}
		if (failed) throw failure;
		return result;
	}

	public function isActive():Bool return active;

	public function release():Void {
		if (!active || releasing) return;
		if (nativeCallbackDepth > 0) {releaseRequested = true;return;}
		releasing = true;
		releaseRequested = false;
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
		var adapters = [for (lifecycle in nativeAdapters) lifecycle];
		for (lifecycle in adapters) {
			try lifecycle.destroy() catch (error:Dynamic) {
				if (firstBridgeFailure == null) firstBridgeFailure = error;
			}
		}
		nativeAdapters.clear();
		nativeMemberArrays.clear();
		ownedNativeBasicBridges.resize(0);
		nativeBasicBridges.clear();
		#end
		active = false;
		if (valueAccess != null) valueAccess.variables.clear();
		valueAccess = null;
		nativeMethods.clear();
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
