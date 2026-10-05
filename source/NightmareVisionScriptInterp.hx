package;

import crowplexus.hscript.Expr;
import crowplexus.hscript.Interp;
import crowplexus.hscript.Tools;
import crowplexus.iris.utils.UsingEntry.UsingCall;
#if flixel
import PsychFlxCameraCompat.PsychFlxCameraCompat;
import PsychFlxCameraCompat.PsychFlxGCompat;
#end

private typedef NightmareVisionConstructorBinding = {
	var type:Dynamic;
	var create:Array<Dynamic>->Dynamic;
	var owner:Dynamic;
}

/**
	The Nightmare Vision script-scope semantics layered on its namespaced,
	pinned Iris interpreter. Parsing and engine bindings remain the caller's
	responsibility; this class only implements name lookup/write-through and the
	`public` metadata marker emitted by the Nightmare Vision parser.
*/
@:access(crowplexus.hscript.Interp)
class NightmareVisionScriptInterp extends Interp {
	/** Fully qualified host adapters belonging to this interpreter's owner. */
	public var importBindings(default, null):Map<String, Dynamic> = new Map();
	/** Owner-local constructor factories keyed by the imported class identity. */
	var constructorBindings:Array<NightmareVisionConstructorBinding> = [];
	var liveValues:Map<String, {read:Void->Dynamic, write:Dynamic->Dynamic, target:Void->Dynamic}> = new Map();

	/** Source properties that differ from the native parent remain live and owner-local. */
	public function bindLiveValue(name:String, read:Void->Dynamic, ?write:Dynamic->Dynamic,
		?target:Void->Dynamic):Void {
		liveValues.set(name, {read:read, write:write, target:target});
	}
	function liveField(object:Dynamic, field:String):Bool {
		if (!liveValues.exists(field)) return false;
		var binding = liveValues.get(field);
		return binding.target != null && binding.target() == object;
	}
	function writeLiveValue(name:String, value:Dynamic):Dynamic {
		var binding = liveValues.get(name);
		if (binding.write == null) throw '[nightmare-vision-script] Read-only source property: ' + name;
		return binding.write(value);
	}
	var usingBindings:Map<String, UsingCall> = new Map();
	var boundUsings:Map<String, Bool> = new Map();
	/** Imported scripts can address current-state fields through their state class.
	 * Keep that fallback local to this script's live parent, with statics first. */
	var classParents:Array<{type:Dynamic, fields:Array<String>}> = [];

	public function bindClassParent(type:Dynamic):Void {
		for (binding in classParents) if (binding.type == type) return;
		classParents.push({type:type, fields:Type.getClassFields(type)});
	}

	function usesClassParent(object:Dynamic, field:String, write:Bool):Bool {
		for (binding in classParents) if (object == binding.type) {
			if (binding.fields.indexOf(field) >= 0 || binding.fields.indexOf('get_' + field) >= 0
				|| binding.fields.indexOf('set_' + field) >= 0) return false;
			return write ? hasParentWriteField(field) : hasParentReadField(field);
		}
		return false;
	}
	/** Camera API bridge supplied only by the native gameplay host. Keeping it
	 * dynamic leaves the owner-local Iris interpreter usable in headless tools. */
	public var cameraShaders:Dynamic;
	/** Optional state object exposed as bare script identifiers. */
	public var parentFields:Array<String> = [];
	/** Cross-script values declared with Nightmare Vision's `public` syntax. */
	public var sharedFields:Map<String, Dynamic>;
	/** Save adapter owned by this interpreter's selected imported root. */
	public var ownerSave(default, null):Null<NightmareVisionSaveFacade>;
	/** Asset resolver captured by this interpreter's source-shaped factories. */
	public var ownerPaths(default, null):Dynamic;
	public var parent(default, set):Dynamic;

	public function new(?parent:Dynamic, ?sharedFields:Map<String, Dynamic>) {
		super();
		this.sharedFields = sharedFields;
		if (parent != null) this.parent = parent;
	}

	public function bindImport(path:String, value:Dynamic):Void importBindings.set(path, value);

	/** Route construction for one exact imported value without intercepting a
	 * different class that happens to use the same source name. */
	public function bindConstructorFactory(type:Dynamic,
		create:Array<Dynamic>->Dynamic, owner:Dynamic):Void {
		if (type == null || create == null) throw '[nightmare-vision-script] Invalid constructor binding';
		for (binding in constructorBindings) if (binding.type == type) {
			binding.create = create;
			binding.owner = owner;
			return;
		}
		constructorBindings.push({type:type, create:create, owner:owner});
	}

	/** Remove one identity binding when its owner-local API is replaced. */
	public function unbindConstructorFactory(type:Dynamic):Void {
		for (index in 0...constructorBindings.length) if (constructorBindings[index].type == type) {
			constructorBindings.splice(index, 1);
			return;
		}
	}

	/** Bind constructors to the same owner as Paths for this script only. */
	public function bindOwnerPaths(paths:Dynamic):Void {
		if (paths == null) throw '[nightmare-vision-asset] Missing interpreter owner paths';
		if (ownerPaths != null && Reflect.field(ownerPaths, 'root') != Reflect.field(paths, 'root'))
			throw '[nightmare-vision-asset] Cannot switch an interpreter to another owner';
		ownerPaths = paths;
	}

	/** Create a script-local facade over the selected owner's private storage.
	 * The host should seed `FlxG` with `new NightmareVisionFlxGView(FlxG, facade)`
	 * before executing plugin `onLoad` callbacks. */
	public function bindOwnerSave(ownerRoot:String, storage:Dynamic):NightmareVisionSaveFacade {
		if (ownerSave != null) ownerSave.release();
		ownerSave = new NightmareVisionSaveFacade(ownerRoot, storage);
		return ownerSave;
	}

	/** Preserve Iris's native-class fallback without consulting another
	 * imported owner's process-global proxy table. */
	override public function getOrImportClass(name:String):Dynamic {
		if (name == 'FunkinVideoSprite' || name == 'funkin.video.FunkinVideoSprite')
			return Type.resolveClass('NightmareVisionVideoSprite');
		return importBindings.exists(name) ? importBindings.get(name) : Tools.getClass(name);
	}

	/** Custom extension adapters stay local; built-in native extensions retain
	 * Iris's normal dispatch. Never register an owner closure in Iris's globals. */
	public function bindUsing(path:String, callback:UsingCall):Void usingBindings.set(path, callback);

	override function useUsing(name:String):Void {
		if (!usingBindings.exists(name)) {
			super.useUsing(name);
			return;
		}
		if (boundUsings.exists(name)) return;
		registerUsingLocal(name, usingBindings.get(name));
		boundUsings.set(name, true);
	}

	function set_parent(value:Dynamic):Dynamic {
		parent = value;
		if (value == null) {
			parentFields = [];
		} else {
			var parentClass = Type.getClass(value);
			parentFields = parentClass == null
				? Reflect.fields(value)
				: Type.getInstanceFields(parentClass);
		}
		return parent;
	}

	/** Break all interpreter-owned references at the end of a script lifetime. */
	public function release():Void {
		var saveError:Dynamic = null;
		for (binding in constructorBindings) {
			var releaseOwner:Dynamic = binding.owner == null ? null : Reflect.field(binding.owner, 'release');
			if (Reflect.isFunction(releaseOwner)) {
				try Reflect.callMethod(binding.owner, releaseOwner, []) catch (error:Dynamic) {
					if (saveError == null) saveError = error;
				}
			}
		}
		constructorBindings.resize(0);
		liveValues.clear();
		if (cameraShaders != null) {
			cameraShaders.release();
			cameraShaders = null;
		}
		if (ownerSave != null) {
			try ownerSave.release() catch (error:Dynamic) saveError = error;
			ownerSave = null;
		}
		parent = null;
		sharedFields = null;
		ownerPaths = null;
		parentFields = [];
		imports.clear();
		importBindings.clear();
		classParents.resize(0);
		usingBindings.clear();
		boundUsings.clear();
		usings.resize(0);
		variables.clear();
		locals.clear();
		declared.resize(0);
		returnValue = null;
		depth = 0;
		inTry = false;
		if (saveError != null) throw saveError;
	}

	/** Keep NMV source constructors owner-local without changing FlxSprite's
	 * process-global loader or appending hidden arguments to script calls. */
	override function cnew(cl:String, args:Array<Dynamic>):Dynamic {
		// Follow Iris's normal constructor lookup first so script locals, seeded
		// variables and imported aliases keep their ordinary shadowing behavior.
		var requestedType:Dynamic = null;
		if (cl != null && cl.indexOf('.') >= 0 && importBindings.exists(cl))
			requestedType = importBindings.get(cl);
		else {
			try requestedType = resolve(cl) catch (_:Dynamic) {}
			if (requestedType == null) requestedType = Type.resolveClass(cl);
		}
		if (requestedType != null) for (binding in constructorBindings)
			if (binding.type == requestedType) return binding.create(args);

		if (ownerPaths != null) {
			var className = cl == null ? '' : cl.substr(cl.lastIndexOf('.') + 1);
			switch (className) {
				case 'FlxSprite':
					var spriteType = Type.resolveClass('NightmareVisionFlxSprite');
					if (spriteType != null) return Type.createInstance(spriteType, [argumentFloat(args, 0, 0),
						argumentFloat(args, 1, 0), argument(args, 2), ownerPaths]);
				case 'Bopper':
					var bopperType = Type.resolveClass('NightmareVisionBopper');
					if (bopperType != null) return Type.createInstance(bopperType, [argumentFloat(args, 0, 0),
							argumentFloat(args, 1, 0), Std.int(argumentFloat(args, 2, 2)), ownerPaths]);
				case 'BGSprite':
					var bgType = Type.resolveClass('NightmareVisionBGSprite');
					if (bgType != null) return Type.createInstance(bgType, [argument(args, 0),
						argumentFloat(args, 1, 0), argumentFloat(args, 2, 0),
						argumentFloat(args, 3, 1), argumentFloat(args, 4, 1),
						argument(args, 5), argument(args, 6) == true, ownerPaths]);
				case 'FunkinVideoSprite':
					var videoType = Type.resolveClass('NightmareVisionVideoSprite');
					if (videoType != null) return Type.createInstance(videoType, [parent, ownerPaths,
						argumentFloat(args, 0, 0), argumentFloat(args, 1, 0),
						argumentBool(args, 2, true), argumentBool(args, 3, false)]);
			}
		}
		// A qualified import can name a real Haxe runtime class without a bare
		// alias in Iris's `imports` map. Instantiate only an actual Class value;
		// owner facades and other imported objects remain on their own APIs.
		if (cl != null && cl.indexOf('.') >= 0 && importBindings.exists(cl)) {
			var importedType = importBindings.get(cl);
			if (isRuntimeClass(importedType)) return Type.createInstance(importedType, args);
		}
		return super.cnew(cl, args);
	}

	static function isRuntimeClass(value:Dynamic):Bool {
		if (value == null) return false;
		var name:String = null;
		try name = Type.getClassName(cast value) catch (_:Dynamic) return false;
		if (name == null || name == '') return false;
		return Type.resolveClass(name) == value;
	}

	static function argument(args:Array<Dynamic>, index:Int):Dynamic
		return args != null && index >= 0 && index < args.length ? args[index] : null;

	static function argumentFloat(args:Array<Dynamic>, index:Int, fallback:Float):Float {
		var value = argument(args, index);
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? fallback : parsed;
	}

	static function argumentBool(args:Array<Dynamic>, index:Int, fallback:Bool):Bool {
		var value = argument(args, index);
		return value == null ? fallback : value == true;
	}

	function setTo(id:String, value:Dynamic, canDefine:Bool = false):Dynamic {
		if (locals.exists(id)) {
			var local = locals.get(id);
			if (local.const != true) local.r = value;
			else warn(ECustom('Cannot reassign final, for constant expression -> ' + id));
		} else if (variables.exists(id)) {
			// HScript presets (including false, zero, and null values) shadow
			// imports and parent members, just as they do during resolve().
			setVar(id, value);
			return value;
		} else if (liveValues.exists(id)) {
			return writeLiveValue(id, value);
		} else if (hasParentWriteField(id)) {
			Reflect.setProperty(parent, id, value);
			return value;
		} else if (sharedFields != null && sharedFields.exists(id)) {
			sharedFields.set(id, value);
		}

		// Match the source interpreter: plain `=` may materialize a variable
		// after a local/shared write, while compound/inc writes do not.
		if (canDefine) {
			setVar(id, value);
		}
		return value;
	}

	function hasParentWriteField(id:String):Bool {
		return parent != null && (parentFields.indexOf(id) >= 0 || parentFields.indexOf('set_' + id) >= 0);
	}

	function hasParentReadField(id:String):Bool {
		return parent != null && (parentFields.indexOf(id) >= 0 || parentFields.indexOf('get_' + id) >= 0);
	}

	/** Iris 1.1.3 restores absent bindings as null map entries, but its own
	 * resolver (and NMV's) treats map presence as a live LocalVar. Remove the
	 * absent slot so a finished block/loop reveals the outer scope again. */
	override function restore(old:Int):Void {
		while (declared.length > old) {
			var declaration = declared.pop();
			if (declaration.old == null) locals.remove(declaration.n);
			else locals.set(declaration.n, declaration.old);
		}
	}

	/** Keep a failed callback from retaining its execution frame. Captured
	 * values and mutations survive, while scope bookkeeping returns to the
	 * caller's frame, including re-entrant calls through a host binding. */
	public function callCallback(method:Dynamic, args:Array<Dynamic>):Dynamic {
		var oldLocals = locals;
		var oldDepth = depth;
		var oldDeclared = declared.length;
		var oldTry = inTry;
		var oldReturn = returnValue;
		try {
			return Reflect.callMethod(null, method, args);
		} catch (error:Dynamic) {
			locals = oldLocals;
			depth = oldDepth;
			declared.resize(oldDeclared);
			inTry = oldTry;
			returnValue = oldReturn;
			throw error;
		}
	}

	/** hxcpp can match a typed enum catch to another enum. Check the actual
	 * enum identity before interpreting an exception as script control flow. */
	static function controlSignal(signal:Dynamic):String {
		return switch (Type.typeof(signal)) {
			case TEnum(kind) if (Type.getEnumName(kind) == 'crowplexus.hscript._Interp.Stop'):
				Type.enumConstructor(signal);
			default: '';
		};
	}

	override function exprReturn(expression:Expr):Dynamic {
		try return expr(expression) catch (signal:Dynamic) {
			switch (controlSignal(signal)) {
				case 'SBreak': throw 'Invalid break';
				case 'SContinue': throw 'Invalid continue';
				case 'SReturn':
					var value = returnValue;
					returnValue = null;
					return value;
				default: throw signal;
			}
		}
	}

	override function whileLoop(condition:Expr, body:Expr):Void {
		var old = declared.length;
		while (expr(condition) == true) {
			try expr(body) catch (signal:Dynamic) {
				switch (controlSignal(signal)) {
					case 'SContinue':
					case 'SBreak': break;
					default: throw signal;
				}
			}
		}
		restore(old);
	}

	override function doWhileLoop(condition:Expr, body:Expr):Void {
		var old = declared.length;
		do {
			try expr(body) catch (signal:Dynamic) {
				switch (controlSignal(signal)) {
					case 'SContinue':
					case 'SBreak': break;
					default: throw signal;
				}
			}
		} while (expr(condition) == true);
		restore(old);
	}

	override function resolve(id:String):Dynamic {
		if (locals.exists(id)) return locals.get(id).r;
		if (variables.exists(id)) return variables.get(id);
		if (imports.exists(id)) return imports.get(id);
		if (liveValues.exists(id)) return liveValues.get(id).read();
		if (ownerPaths != null && id == 'FunkinVideoSprite') {
			var videoType = Type.resolveClass('NightmareVisionVideoSprite');
			if (videoType != null) return videoType;
		}
		if (hasParentReadField(id)) return Reflect.getProperty(parent, id);
		if (sharedFields != null && sharedFields.exists(id)) return sharedFields.get(id);
		return super.resolve(id);
	}

	/** Flixel sprites do not carry the source engine's display-order field.
	 * Keep reads and writes on the same owner-aware compatibility side table used
	 * by HXC and V-Slice scripts. */
	override function get(object:Dynamic, field:String):Dynamic {
		if (object == null)
			throw '[nightmare-vision-script-null-access] Cannot read ' + field + ' on null';
		#if flixel
		if (object == PsychFlxGCompat) return PsychFlxGCompat.getField(field);
		if (Std.isOfType(object, PsychFlxCameraCompat))
			return (cast object:PsychFlxCameraCompat).getField(field);
		#end
		if (liveField(object, field)) return liveValues.get(field).read();
		if (usesClassParent(object, field, false)) return Reflect.getProperty(parent, field);
		#if flixel
		if (ownerPaths != null && (field == 'audio' || field == 'vocals')
			&& Std.isOfType(object, NightmareVisionPlayableSongOwner))
			return (cast object:NightmareVisionPlayableSongOwner).nightmareVisionAudioView();
		// NMV Bopper signals carry animation names; the legacy Character finish
		// signal deliberately has no arguments, so preserve both APIs.
		if (Std.isOfType(object, Character)) {
			var actor:Character = cast object;
			switch (field) {
				case 'onAnimationFrameChange': return actor.animation.onFrameChange;
				case 'onAnimationFinish': return actor.animation.onFinish;
				case 'onAnimationLoop': return actor.animation.onLoop;
				default:
			}
		}
		#end
		if (Std.isOfType(object, PsychBaseStageActorGroupCompat) && field == 'zIndex')
			return Reflect.getProperty(object, field);
		if (object != null && field == 'zIndex') return HxcCompatRuntime.getZIndex(object);
		if (Std.isOfType(object, NightmareVisionFlxGView))
			return (cast object:NightmareVisionFlxGView).getField(field);
		if (Std.isOfType(object, NightmareVisionSaveData))
			return (cast object:NightmareVisionSaveData).getField(field);
		// This is host lifecycle plumbing, not part of the source FlxSave API.
		if (Std.isOfType(object, NightmareVisionSaveFacade) && field == 'release') return null;
		return super.get(object, field);
	}

	override function set(object:Dynamic, field:String, value:Dynamic):Dynamic {
		if (object == null)
			throw '[nightmare-vision-script-null-access] Cannot write ' + field + ' on null';
		#if flixel
		if (object == PsychFlxGCompat) return PsychFlxGCompat.setField(field, value);
		if (Std.isOfType(object, PsychFlxCameraCompat))
			return (cast object:PsychFlxCameraCompat).setField(field, value);
		#end
		if (liveField(object, field)) return writeLiveValue(field, value);
		if (usesClassParent(object, field, true)) {
			Reflect.setProperty(parent, field, value);
			return value;
		}
		if (Std.isOfType(object, PsychBaseStageActorGroupCompat) && field == 'zIndex') {
			Reflect.setProperty(object, field, value);
			return value;
		}
		if (object != null && field == 'zIndex') return HxcCompatRuntime.setZIndex(object, value);
		if (Std.isOfType(object, NightmareVisionFlxGView))
			return (cast object:NightmareVisionFlxGView).setField(field, value);
		if (Std.isOfType(object, NightmareVisionSaveData))
			return (cast object:NightmareVisionSaveData).setField(field, value);
		if (Std.isOfType(object, NightmareVisionSaveFacade) && field == 'data')
			throw '[nightmare-vision-save] Refused to replace owner save data';
		return super.set(object, field, value);
	}

	override function assign(left:Expr, right:Expr):Dynamic {
		switch (Tools.expr(left)) {
			case EIdent(id):
				return setTo(id, expr(right), true);
			case EArray(collectionExpr, indexExpr):
				// Iris evaluates the assigned value before evaluating the indexed
				// receiver and index. Keep that order, but fail before native array
				// plumbing dereferences a null receiver.
				var value = expr(right);
				var collection:Dynamic = expr(collectionExpr);
				var index:Dynamic = expr(indexExpr);
				requireIndexedCollection(collection, 'write');
				if (isMap(collection))
					setMapValue(collection, index, value);
				else
					collection[index] = value;
				return value;
			default:
				return super.assign(left, right);
		}
	}

	override function evalAssignOp(op:String, operation:Dynamic->Dynamic->Dynamic,
		left:Expr, right:Expr):Dynamic {
		switch (Tools.expr(left)) {
			case EIdent(id):
				return setTo(id, operation(expr(left), expr(right)));
			case EArray(collectionExpr, indexExpr):
				// Iris reads the old value before evaluating the right-hand side.
				var collection:Dynamic = expr(collectionExpr);
				var index:Dynamic = expr(indexExpr);
				requireIndexedCollection(collection, 'update');
				var oldValue:Dynamic = isMap(collection)
					? getMapValue(collection, index) : collection[index];
				var value:Dynamic = operation(oldValue, expr(right));
				if (isMap(collection))
					setMapValue(collection, index, value);
				else
					collection[index] = value;
				return value;
			default:
				return super.evalAssignOp(op, operation, left, right);
		}
	}

	override function increment(expression:Expr, prefix:Bool, delta:Int):Dynamic {
		#if hscriptPos
		curExpr = expression;
		#end
		switch (Tools.expr(expression)) {
			case EIdent(id):
				var previous:Dynamic = resolve(id);
				var updated:Dynamic = previous + delta;
				setTo(id, updated);
			return prefix ? updated : previous;
			case EArray(collectionExpr, indexExpr):
				var collection:Dynamic = expr(collectionExpr);
				var index:Dynamic = expr(indexExpr);
				requireIndexedCollection(collection, delta > 0 ? 'increment' : 'decrement');
				var previous:Dynamic = isMap(collection)
					? getMapValue(collection, index) : collection[index];
				var updated:Dynamic = previous + delta;
				if (isMap(collection))
					setMapValue(collection, index, updated);
				else
					collection[index] = updated;
				return prefix ? updated : previous;
			default:
				return super.increment(expression, prefix, delta);
		}
	}

	function requireIndexedCollection(collection:Dynamic, operation:String):Void {
		if (collection == null)
			throw '[nightmare-vision-script-null-access] Cannot ' + operation
				+ ' an indexed value because its collection evaluated to null; initialize it or guard the access first';
	}

	override function makeIterator(value:Dynamic):Iterator<Dynamic> {
		if (Std.isOfType(value, Array)) return (cast value:Array<Dynamic>).iterator();
		var method:Dynamic = value.iterator;
		var iterator:Dynamic = method == null ? value : Reflect.callMethod(value, method, []);
		if (iterator.hasNext == null || iterator.next == null) error(EInvalidIterator(iterator));
		return iterator;
	}

	override function fcall(object:Dynamic, field:String, args:Array<Dynamic>):Dynamic {
		if ((field == 'addShader' || field == 'removeShader') && cameraShaders != null
			&& cameraShaders.isCamera(object)) {
			switch (field) {
				case 'addShader':
					cameraShaders.add(object, args.length > 0 ? args[0] : null);
					return null;
				case 'removeShader':
					return cameraShaders.remove(object, args.length > 0 ? args[0] : null);
				default:
			}
		}
		for (extension in usings) {
			var result = extension.call(object, field, args);
			if (result != null) return result;
		}
		var method = get(object, field);
		if (method == null) {
			var details = isStringMethod(field) ? stringReceiverDetails(object) : '';
			crowplexus.iris.Iris.error('Unknown function: ' + field + details, posInfos());
			return null;
		}
		return call(object, method, args);
	}

	/** Add evidence for the common String-call failure without changing lookup
	 * or coercing a non-String receiver into one. */
	static function isStringMethod(field:String):Bool {
		return switch (field) {
			case 'charAt' | 'charCodeAt' | 'indexOf' | 'lastIndexOf' | 'split'
				| 'substr' | 'substring' | 'toLowerCase' | 'toUpperCase' | 'toString': true;
			default: false;
		};
	}

	static function stringReceiverDetails(object:Dynamic):String {
		var isString = Std.isOfType(object, String);
		var value = isString ? (cast object:String) : '<non-string>';
		return ' (receiverType=' + Std.string(Type.typeof(object))
			+ ', isString=' + isString + ', value=' + value + ')';
	}

	function makeKeyValueIterator(value:Dynamic):KeyValueIterator<Dynamic, Dynamic> {
		if (Std.isOfType(value, haxe.Constraints.IMap))
			return (cast value:haxe.Constraints.IMap<Dynamic, Dynamic>).keyValueIterator();
		if (Std.isOfType(value, Array)) return (cast value:Array<Dynamic>).keyValueIterator();
		var method:Dynamic = value.keyValueIterator;
		var iterator:Dynamic = method == null ? value : Reflect.callMethod(value, method, []);
		if (iterator.hasNext == null || iterator.next == null) error(EInvalidIterator(iterator));
		return iterator;
	}

	/** Source InterpEx binds native iterator methods once and catches loop
	 * control separately from script errors, including key/value iterators. */
	override function forLoop(name:String, iteratorExpr:Expr, body:Expr):Void {
		var valueName:Null<String> = null;
		switch (Tools.expr(iteratorExpr)) {
			case EMeta(':nmvKeyValue', [binding], iterable):
				switch (Tools.expr(binding)) {
					case EIdent(value): valueName = value;
					default: error(ECustom('Invalid key/value loop binding'));
				}
				iteratorExpr = iterable;
			default:
		}
		var old = declared.length;
		declared.push({n:name, old:locals.get(name)});
		if (valueName != null) declared.push({n:valueName, old:locals.get(valueName)});
		var iterator:Dynamic = valueName == null
			? makeIterator(expr(iteratorExpr)) : makeKeyValueIterator(expr(iteratorExpr));
		var next:Void->Dynamic = iterator.next;
		var hasNext:Void->Bool = iterator.hasNext;
		while (hasNext()) {
			var value:Dynamic = next();
			if (valueName == null) locals.set(name, {r:value, const:false});
			else {
				// These checks deliberately follow the source's null rejection.
				if (value.key == null) error(ECustom(valueName + ' has no field key'));
				if (value.value == null) error(ECustom(valueName + ' has no field value'));
				locals.set(name, {r:value.key, const:false});
				locals.set(valueName, {r:value.value, const:false});
			}
			try expr(body) catch (signal:Dynamic) {
				switch (controlSignal(signal)) {
					case 'SContinue':
					case 'SBreak': break;
					default: throw signal;
				}
			}
		}
		restore(old);
	}

	override public function expr(expression:Expr):Dynamic {
		#if hscriptPos
		curExpr = expression;
		#end
		switch (Tools.expr(expression)) {
			case ETry(body, name, _, handler):
				var old = declared.length;
				var oldTry = inTry;
				try {
					inTry = true;
					var value = expr(body);
					restore(old);
					inTry = oldTry;
					return value;
				} catch (signal:Dynamic) {
					inTry = oldTry;
					if (controlSignal(signal) != '') throw signal;
					restore(old);
					declared.push({n:name, old:locals.get(name)});
					locals.set(name, {r:signal, const:false});
					var value = expr(handler);
					restore(old);
					return value;
				}
			case EMeta(':sharable', _, wrapped) if (sharedFields != null):
				switch (Tools.expr(wrapped)) {
					case EFunction(_, _, name, _) if (depth == 0 && name != null):
						var functionValue = expr(wrapped);
						sharedFields.set(name, functionValue);
						return functionValue;
					case EVar(name, _, initialValue, _) if (depth == 0):
						var value = initialValue == null ? null : expr(initialValue);
						sharedFields.set(name, value);
						return value;
					default:
						return expr(wrapped);
				}
			case EArray(collectionExpr, indexExpr):
				// Evaluate both operands once and in Iris order, then guard before
				// direct array access. Keep native bounds behavior unchanged.
				var collection:Dynamic = expr(collectionExpr);
				var index:Dynamic = expr(indexExpr);
				requireIndexedCollection(collection, 'read');
				return isMap(collection) ? getMapValue(collection, index) : collection[index];
			default:
				return super.expr(expression);
		}
	}
}
