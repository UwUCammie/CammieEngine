package;

import hscript.Interp;
import hscript.Expr;
import hscript.ScriptClass;
import hscript.ScriptClassScope;
import hscript.Tools;
import flixel.FlxG;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxTween.FlxTweenType;
import flixel.FlxBasic;
import flixel.FlxState;
import flixel.util.FlxTimer;
import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.util.FlxColor;
import flixel.addons.display.FlxRuntimeShader;
import openfl.display.DisplayObject;
import openfl.display.ShaderParameterType;
import openfl.events.EventDispatcher;
import CodenameXmlAccess.CodenameXmlFieldAccess;
import openfl.filters.BitmapFilter;
import openfl.filters.ShaderFilter;
#if cpp
import hxvlc.flixel.FlxVideoSprite;
#end

/** Constructor and asynchronous-resource ownership stay interpreter-local. */
@:access(hscript.ScriptClass)
@:access(hscript.AbstractScriptClass)
class CodenameScriptInterp extends Interp {
	/** `disableScript()` applies only to this interpreter and its callbacks. */
	public var scriptDisabled(default, null):Bool = false;
	public function disableScript():Void scriptDisabled = true;
	/** Set only by an imported state during an explicit smoke run. */
	public var runtimeSmokeOwnerRoot:String = '';
	public var runtimeSmokeScriptPath:String = '';
	var codenameNullAccessSeen:Map<String, Bool> = new Map();
	var moduleGlobals:Map<String, Bool> = new Map();
	/** Runtime names registered from imported classes and compatibility facades.
		Haxe rejects assignments to imported type names, but untyped HScript stores
		those bare-name writes in `variables`; keep the registered binding intact. */
	var protectedImportAliases:Map<String, Bool> = new Map();
	var publicModuleGlobals:Map<String, {read:Void->Dynamic, write:Dynamic->Void}> = new Map();
	/** Class declarations imported by this selected Codename owner only. */
	public var scriptClassScope(default, null):ScriptClassScope;
	public function bindScriptClassScope(scope:ScriptClassScope):Void {
		if (scriptClassScope != null && scriptClassScope != scope) scriptClassScope.release();
		scriptClassScope = scope;
	}

	/** Resolve only native scene objects or script-class proxies whose descriptor
	 * belongs to this interpreter's active owner scope. HScript classes compose
	 * their native superclass; they are not native FlxBasic instances themselves. */
	public function nativeFlxBasic(value:Dynamic):Null<FlxBasic> {
		if (value == null) return null;
		if (Std.isOfType(value, FlxBasic)) return cast value;
		if (!Std.isOfType(value, ScriptClass)) return null;
		var proxy:ScriptClass = cast value;
		var expected = ownedScriptClassBasics.get(proxy);
		if (expected == null) return null;
		return nativeFlxBasicInner(proxy, []) == expected ? expected : null;
	}

	function nativeFlxBasicInner(value:Dynamic, seen:Array<ScriptClass>):Null<FlxBasic> {
		if (value == null) return null;
		if (Std.isOfType(value, FlxBasic)) return cast value;
		if (scriptClassScope == null || !scriptClassScope.isActive() || !Std.isOfType(value, ScriptClass))
			return null;
		var proxy:ScriptClass = cast value;
		if (seen.indexOf(proxy) >= 0 || !ownsScriptClassProxy(proxy)) return null;
		seen.push(proxy);
		return nativeFlxBasicInner(proxy.superClass, seen);
	}

	function ownsScriptClassProxy(proxy:ScriptClass):Bool {
		if (proxy == null || proxy._c == null || scriptClassScope == null || !scriptClassScope.isActive())
			return false;
		var packageName = proxy._c.pkg == null ? '' : proxy._c.pkg.join('.');
		var fullName = packageName == '' ? proxy._c.name : packageName + '.' + proxy._c.name;
		return scriptClassScope.findDescriptor(fullName) == proxy._c;
	}

	/** Source `static var` fields need one shared location visible to callback
		closures and the owner-scoped transition handoff. Normal HScript `var`
		declarations live only in a closure-local table. */
	public function retainModuleGlobals(names:Array<String>):Void {
		if (names != null) for (name in names) moduleGlobals.set(name, true);
	}

	/** Public top-level module fields bind to a PlayState-owned slot shared with
	 * the other active song/stage interpreters. */
	public function bindPublicModuleGlobal(name:String, read:Void->Dynamic, write:Dynamic->Void):Void {
		if (name != null && name != '' && read != null && write != null)
			publicModuleGlobals.set(name, {read:read, write:write});
	}
	public function unbindPublicModuleGlobal(name:String):Void publicModuleGlobals.remove(name);

	/** Mark every short name registered in an owner import map as an imported
		class/facade alias. HScript assignment expressions still evaluate to their
		RHS; only the write into the alias slot is ignored, matching Haxe imports. */
	public function protectImportAliases(bindings:Map<String, Dynamic>):Void {
		if (bindings == null) return;
		for (path in bindings.keys()) {
			if (path == null || path == '' || bindings.get(path) == null) continue;
			var alias = path.substr(path.lastIndexOf('.') + 1);
			if (alias != '') protectedImportAliases.set(alias, true);
		}
	}

	override public function expr(expression:Expr):Dynamic {
		if (@:privateAccess this.depth == 0) switch (Tools.expr(expression)) {
			case EVar(name, _, value) if (publicModuleGlobals.exists(name)):
				publicModuleGlobals.get(name).write(value == null ? null : expr(value));
				return null;
			case EVar(name, _, value) if (moduleGlobals.exists(name)):
				variables.set(name, value == null ? null : expr(value));
				return null;
			default:
		}
		return super.expr(expression);
	}

	/** Keep the native null guard's diagnostic, with the selected script and
	 * callback attached so an ignored donor error can be traced to its source. */
	override function nullAccessDiagnose(kind:String, field:String):Void {
		#if sys
		var source = variables == null ? null : variables.get('__compatDiagnosticSource');
		var callback = variables == null ? null : variables.get('__compatDiagnosticCallback');
		var context = source == null ? '' : Std.string(source);
		if (callback != null) context += '#' + Std.string(callback);
		var key = kind + ':' + field + ':' + context;
		if (!codenameNullAccessSeen.exists(key)) {
			codenameNullAccessSeen.set(key, true);
			Sys.println('[hscript-null-access] ' + kind + ' to "' + field
				+ '" on a null object was ignored so the script can continue'
				+ (context == '' ? '' : ' (' + context + ')'));
		}
		#end
	}

	/** Codename scripts pass camFollow (a FlxObject) to focusOn, while
	 * Flixel 6 expects a FlxPoint. Reflect's unchecked native argument cast
	 * can segfault before HScript has a chance to report the mismatch. */
	function callAsyncCallbackWithDiagnosticContext(callback:Dynamic, args:Array<Dynamic>,
		source:Dynamic, callbackName:Dynamic):Dynamic {
		var previousSource = variables.get('__compatDiagnosticSource');
		var previousCallback = variables.get('__compatDiagnosticCallback');
		var scopedCallback = callbackName == null || Std.string(callbackName) == ''
			? 'FlxTimer.start callback' : Std.string(callbackName) + ' -> FlxTimer.start callback';
		variables.set('__compatDiagnosticSource', source);
		variables.set('__compatDiagnosticCallback', scopedCallback);
		try {
			var result = Reflect.callMethod(null, callback, args);
			variables.set('__compatDiagnosticSource', previousSource);
			variables.set('__compatDiagnosticCallback', previousCallback);
			return result;
		} catch (error:Dynamic) {
			variables.set('__compatDiagnosticSource', previousSource);
			variables.set('__compatDiagnosticCallback', previousCallback);
			throw error;
		}
	}

	override function fcall(object:Dynamic, field:String, args:Array<Dynamic>):Dynamic {
		if (Std.isOfType(object, ScriptClass))
			return (cast object:ScriptClass).callFunction(field, args == null ? [] : args);
		// Psych's package-wide `using StringTools` makes these instance-style
		// calls in compiled source classes. HScript resolves methods at runtime,
		// so route the same extension API before treating them as missing fields.
		if (Std.isOfType(object, String)) {
			var value:String = cast object;
			switch (field) {
				case 'trim' if (args == null || args.length == 0): return StringTools.trim(value);
				case 'ltrim' if (args == null || args.length == 0): return StringTools.ltrim(value);
				case 'rtrim' if (args == null || args.length == 0): return StringTools.rtrim(value);
				case 'startsWith' if (args != null && args.length == 1): return StringTools.startsWith(value, Std.string(args[0]));
				case 'endsWith' if (args != null && args.length == 1): return StringTools.endsWith(value, Std.string(args[0]));
				case 'contains' if (args != null && args.length == 1): return StringTools.contains(value, Std.string(args[0]));
				case 'replace' if (args != null && args.length == 2):
					return StringTools.replace(value, Std.string(args[0]), Std.string(args[1]));
				default:
			}
		}
		// Keep the selected script context while an asynchronous timer callback
		// runs. This preserves source attribution for ignored null accesses without
		// changing the timer owner, callback, or FlxTimer argument.
		if (field == 'start' && Std.isOfType(object, FlxTimer) && args != null && args.length >= 2
			&& args[1] != null && Reflect.isFunction(args[1])) {
			var callback:Dynamic = args[1];
			var callbackSource = variables.get('__compatDiagnosticSource');
			var callbackName = variables.get('__compatDiagnosticCallback');
			var smokeTrace = runtimeSmokeOwnerRoot != '' && CodenameStateSmokeTrace.enabled();
			var wrappedArgs = args.copy();
			wrappedArgs[1] = function(timer:FlxTimer):Void {
				if (smokeTrace)
					CodenameStateSmokeTrace.mark('state-timer-fired', runtimeSmokeOwnerRoot,
						runtimeSmokeScriptPath, [CodenameStateSmokeTrace.field('seconds', timer.time),
							CodenameStateSmokeTrace.field('loops', timer.elapsedLoops)]);
				callAsyncCallbackWithDiagnosticContext(callback, [timer], callbackSource, callbackName);
			};
			if (smokeTrace)
				CodenameStateSmokeTrace.mark('state-timer-start', runtimeSmokeOwnerRoot,
					runtimeSmokeScriptPath, [CodenameStateSmokeTrace.field('seconds', args[0]),
						CodenameStateSmokeTrace.field('loops', args.length > 2 ? args[2] : 1)]);
			args = wrappedArgs;
		}
		// Codename chart-event parameters retain JSON numbers. Source event scripts
		// commonly parse them again as text; native Std.parseInt/parseFloat reject
		// a Dynamic number before the script can reach its authored line index.
		if (object == Std && args != null && args.length == 1
			&& (Std.isOfType(args[0], Int) || Std.isOfType(args[0], Float))) {
			if (field == 'parseInt') return Std.parseInt(Std.string(args[0]));
			if (field == 'parseFloat') return Std.parseFloat(Std.string(args[0]));
		}
		if (field == 'focusOn' && Std.isOfType(object, FlxCamera)
			&& args != null && args.length == 1 && Std.isOfType(args[0], FlxObject)) {
			(cast object:FlxCamera).focusOn((cast args[0]:FlxObject).getPosition());
			return null;
		}
		// Codename state scripts often pass `fonts/name.ttf` directly to a
		// FlxText format call. Flixel treats that string as a font family, so
		// resolve/register the selected owner's font before the native call.
		if (field == 'setFormat' && Std.isOfType(object, FlxText)
			&& args != null && args.length > 0 && Std.isOfType(args[0], String)) {
			var ownerFamily = codenameOwnerFontFamily(cast args[0]);
			if (ownerFamily != args[0]) {
				args = args.copy();
				args[0] = ownerFamily;
			}
		}
		var result = super.fcall(object, field, args);
		if (Std.isOfType(object, EventDispatcher) && args != null && args.length >= 2
			&& (field == 'addEventListener' || field == 'removeEventListener')) {
			var dispatcher:EventDispatcher = cast object;
			var eventType = Std.string(args[0]);
			var listener = args[1];
			var useCapture = args.length >= 3 && args[2] == true;
			if (field == 'addEventListener') ownEventListener(dispatcher, eventType, listener, useCapture);
			else forgetEventListener(dispatcher, eventType, listener, useCapture);
		}
		return result;
	}

	function codenameOwnerFontFamily(value:Dynamic):Dynamic {
		if (value == null || !Std.isOfType(value, String) || paths == null) return value;
		var key:String = StringTools.replace(cast value, '\\', '/');
		while (StringTools.startsWith(key, './')) key = key.substr(2);
		var ownerRoot = StringTools.replace(paths.root, '\\', '/');
		var ownerPrefix = ownerRoot + '/fonts/';
		if (StringTools.startsWith(key, ownerPrefix)) key = key.substr(ownerPrefix.length);
		else if (StringTools.startsWith(key, 'fonts/')) key = key.substr('fonts/'.length);
		else return value;
		if (key == '') return value;
		return paths.getFontName(paths.font(key));
	}

	function ownEventListener(dispatcher:EventDispatcher, eventType:String,
		listener:Dynamic, useCapture:Bool):Void {
		for (owned in ownedEventListeners)
			if (owned.dispatcher == dispatcher && owned.type == eventType
				&& owned.listener == listener && owned.useCapture == useCapture) return;
		ownedEventListeners.push({dispatcher:dispatcher, type:eventType,
			listener:listener, useCapture:useCapture});
	}

	function forgetEventListener(dispatcher:EventDispatcher, eventType:String,
		listener:Dynamic, useCapture:Bool):Void {
		var retained:Array<{dispatcher:EventDispatcher, type:String,
			listener:Dynamic, useCapture:Bool}> = [];
		for (owned in ownedEventListeners)
			if (owned.dispatcher != dispatcher || owned.type != eventType
				|| owned.listener != listener || owned.useCapture != useCapture) retained.push(owned);
		ownedEventListeners = retained;
	}
	/** An imported classless script executes inside its caller's top-level
	 * scope. Interp.execute() resets locals, which loses fields already
	 * declared before importScript() and breaks functions declared afterward. */
	public function executeImportedScript(program:Expr):Dynamic {
		return exprReturn(program);
	}
	/** importScript adds another source callback scope to this interpreter. */
	public var importedCallbacks:Map<String, Array<{callback:Dynamic, origin:String}>> = [];

	public final paths:CodenamePaths;
	/** Per-interpreter Codename cache; it owns only the graphics loaded from its
	 * selected namespace and is released with the script scope. */
	public final graphicCache:CodenameGraphicCache;
	public var customShaderFactory:Null<String->Dynamic>;
	/** Native constructors whose instances need selected-owner gameplay context. */
	public var characterFactory:Null<Array<Dynamic>->Dynamic>;
	/** Imported state hosts may route Codename's classless ModState by owner. */
	public var modStateFactory:Null<String->Dynamic>;
	/** Conventional class constructors may name classless states in the selected
		Codename owner. Resolve those before the native class alias. */
	public var ownerStateFactory:Null<String->Dynamic>;
	public final stageBindings:CodenameStageBindings = new CodenameStageBindings();
	public final flxG:CodenameFlxGFacade;
	var ownedTweens:Array<FlxTween> = [];
	var ownedTimers:Array<FlxTimer> = [];
	/** Display objects and listener registrations created by this interpreter.
		Globals can attach overlays directly to Main.instance, so they need
		cleanup even if their authored destroy() fails partway through. */
	var ownedDisplayObjects:Array<DisplayObject> = [];
	var ownedEventListeners:Array<{dispatcher:EventDispatcher, type:String,
		listener:Dynamic, useCapture:Bool}> = [];
	/** Constructor-created scene objects stay in this scope until a state or
		gameplay host explicitly accepts them. */
	var unclaimedBasics:Array<FlxBasic> = [];
	/** Only proxies created by this interpreter may cross the native scene
	 * bridge. This identity map pins each proxy to its original FlxBasic. */
	var ownedScriptClassBasics:Map<ScriptClass, FlxBasic> = new Map();
	var claimedGroups:Array<FlxTypedGroup<FlxBasic>> = [];
	/** Camera filters installed by this interpreter are removed with its scope. */
	var ownedCameraFilters:Array<{camera:FlxCamera, shader:Dynamic, filter:ShaderFilter}> = [];
	/** OpenFL may expose an uninitialized ShaderParameter.value during a native
		frame even after a script assigned the uniform. Keep the authored numeric
		value per interpreter for later tweens of that same shader. */
	var numericShaderValues:Map<FlxRuntimeShader, Map<String, Float>> = [];
	#if cpp
	/** A video constructor attaches its bitmap before a script can call add(). */
	var unclaimedVideos:Array<FlxVideoSprite> = [];
	#end
	var paused:Bool = false;
	var pausedTweens:Map<FlxTween, Bool> = new Map();
	var pausedTimers:Map<FlxTimer, Bool> = new Map();
	var liveGlobals:Map<String, {read:Void->Dynamic, write:Dynamic->Void}> = [];
	/** Explicit state properties stay live without exposing the entire native state
	 * as an interpreter parent or copying mutable values into each script. */
	public function bindLiveGlobal(name:String, read:Void->Dynamic, write:Dynamic->Void):Void {
		liveGlobals.set(name, {read: read, write: write});
	}
	public function hasLiveGlobal(name:String):Bool {
		return liveGlobals.exists(name);
	}
	/** Native role registrations are not authored Codename XML sprites. */
	public function isStageActorAlias(name:String, value:Dynamic):Bool {
		return Std.isOfType(value, Character) && hasLiveGlobal(name);
	}
	var scriptObject:Dynamic;
	var scriptObjectFields:Map<String, Bool> = new Map();
	var scriptObjectAliases:Map<String, String> = new Map();
	/** Each character interpreter binds its own live instance, never an ID registry entry. */
	public function bindScriptObject(object:Dynamic, ?aliases:Map<String, String>):Void {
		scriptObject = object;
		scriptObjectFields.clear();
		scriptObjectAliases = aliases == null ? new Map() : aliases.copy();
		if (object == null) return;
		var type = Type.getClass(object);
		for (field in (type == null ? Reflect.fields(object) : Type.getInstanceFields(type)))
			scriptObjectFields.set(field, true);
	}
	override function resolve(id:String):Dynamic {
		if (locals.get(id) != null) return super.resolve(id);
		if (publicModuleGlobals.exists(id)) return publicModuleGlobals.get(id).read();
		if (variables.exists(id)) return super.resolve(id);
		if (liveGlobals.exists(id)) return liveGlobals.get(id).read();
		if (scriptObject != null) {
			if (id == 'this') return scriptObject;
			if (scriptObjectAliases.exists(id) || scriptObjectFields.exists(id)) return get(scriptObject, id);
			if (scriptObjectFields.exists('get_' + id))
				return Reflect.callMethod(scriptObject, Reflect.field(scriptObject, 'get_' + id), []);
		}
		return super.resolve(id);
	}
	override function setVar(id:String, value:Dynamic):Void {
		if (locals.get(id) == null && protectedImportAliases.exists(id)) return;
		if (locals.get(id) == null && publicModuleGlobals.exists(id)) {
			publicModuleGlobals.get(id).write(value);
			return;
		}
		if (!variables.exists(id) && liveGlobals.exists(id)) {
			liveGlobals.get(id).write(value);
			return;
		}
		if (scriptObject != null && !variables.exists(id)) {
			if (scriptObjectAliases.exists(id) || scriptObjectFields.exists(id)) {
				set(scriptObject, id, value);
				return;
			}
			if (scriptObjectFields.exists('set_' + id)) {
				Reflect.callMethod(scriptObject, Reflect.field(scriptObject, 'set_' + id), [value]);
				return;
			}
		}
		super.setVar(id, value);
	}
	public function new(paths:CodenamePaths, ?flxG:CodenameFlxGFacade,
		?customShaderFactory:String->Dynamic) {
		super();
		this.paths = paths;
		this.flxG = flxG;
		if (flxG != null)
			flxG.onStateSwitchAccepted = transferStateTarget;
		this.customShaderFactory = customShaderFactory;
		graphicCache = new CodenameGraphicCache(paths);
		variables.set('graphicCache', graphicCache);
		// Codename scripts use this top-level helper in songs, stages and menus.
		variables.set('lerp', function(from:Float, to:Float, ratio:Float):Float
			return from + ratio * (to - from));
	}
	function sourceField(object:Dynamic, field:String):String {
		if (object != null && object == scriptObject && scriptObjectAliases.exists(field))
			return scriptObjectAliases.get(field);
		if (Std.isOfType(object, CodenameGameplayAccess)) {
			if (field == 'misses') return 'codenameMisses';
			if (field == 'accuracy') return 'codenameAccuracy';
		}
		// A stage or song can hold any actor, including another instance of the same ID.
		// Keep the native API for characters without an authored Codename identity.
		if (Std.isOfType(object, CodenameCharacterAccess)) {
			// The source Character API uses hasAnim on every character. Native
			// Characters expose the equivalent `hasAnimation`, including borrowed
			// actors that do not have an authored Codename source ID.
			if (field == 'hasAnim') return 'hasAnimation';
			if ((cast object:CodenameCharacterAccess).codenameSourceId != null) {
				return switch (field) {
					case 'curCharacter': 'codenameSourceId';
					case 'playAnim': 'codenamePlayAnim';
					case 'tryDance': 'codenameTryDance';
					case 'singAnims': 'codenameSingAnims';
					case 'getSingAnim': 'codenameGetSingAnim';
					case 'playSingAnim': 'codenamePlaySingAnim';
					case 'playSingAnimUnsafe': 'codenamePlaySingAnimUnsafe';
					default: field;
				};
			}
		}
		return field;
	}
	/** Older Codename global scripts inspect and replace FlxGame's pending
		`_requestedState` field from `preStateSwitch()`. HaxeFlixel 5.6+ renamed
		that slot to `_nextState`. Keep the alias inside this interpreter so
		native callers and other Flixel fields continue to use the real game. */
	inline function isLegacyRequestedStateAlias(object:Dynamic, field:String):Bool
		return flxG != null && field == '_requestedState' && object == FlxG.game;

	override function get(object:Dynamic, field:String):Dynamic {
		field = sourceField(object, field);
		if (Std.isOfType(object, ScriptClass)) {
			var proxy:ScriptClass = cast object;
			if (proxy._interp.variables.exists(field)) return proxy._interp.variables.get(field);
			if (proxy.hasPendingSuperField(field)) return proxy.getPendingSuperField(field);
			if (proxy.superClass != null && Reflect.hasField(proxy.superClass, field))
				return Reflect.getProperty(proxy.superClass, field);
			return (cast proxy:hscript.AbstractScriptClass).resolveField(field);
		}
		if (isLegacyRequestedStateAlias(object, field))
			return CodenameRequestedStateCompat.getRequestedState(object);
		// Codename's public `controls.SWITCHMOD` source property has no
		// counterpart in the legacy engine's original Controls API. Read it via
		// the shared compatibility action rather than reflective fallback.
		if (field == 'SWITCHMOD' && Std.isOfType(object, Controls))
			return CodenameControlsCompat.switchModPressed(cast object);
		// Codename's `player.cpu` asks whether this line is being judged by the
		// engine. Demo/botplay affects that script-facing view without changing
		// the authored ownership bit used by native note scoring and mustPress.
		if (field == 'cpu' && Std.isOfType(object, CodenameInputLine))
			return CodenameInputLineScriptAccess.getEffectiveCpu(cast object);
		// This bridge is consumed by untyped Codename HScript. Keep the filtered,
		// source-owned actor view on a typed accessor instead of relying on the
		// target's reflective property lookup for a generic getter.
		if (field == 'characters' && Std.isOfType(object, CodenameInputLine))
			return CodenameInputLineScriptAccess.getCharacters(cast object);
		if (field == 'notes' && Std.isOfType(object, CodenameInputLine))
			return CodenameInputLineScriptAccess.getNotes(cast object);
		if (Std.isOfType(object, CodenameFlxGFacade) && field == 'save')
			return (cast object:CodenameFlxGFacade).save;
		// HaxeFlixel's camera alpha is a setter-backed property. Dynamic
		// Reflect access does not expose that property reliably on native, so
		// keep reads on the typed camera API just like other camera shims.
		if (Std.isOfType(object, FlxCamera) && field == 'alpha')
			return (cast object:FlxCamera).alpha;
		if (Std.isOfType(object, CodenameOwnerSaveData))
			return (cast object:CodenameOwnerSaveData).getField(field);
		if (Std.isOfType(object, FlxRuntimeShader)) {
			var uniformName = shaderUniformName(object, field);
			var parameter = shaderParameter(object, uniformName);
			if (parameter != null) {
				var values:Dynamic = Reflect.field(parameter, 'value');
				if (Std.isOfType(values, Array) && (cast values:Array<Dynamic>).length == 1)
					return (cast values:Array<Dynamic>)[0];
				return values;
			}
		}
		if (Std.isOfType(object, FlxCamera) && Reflect.field(object, field) == null) {
			var camera:FlxCamera = cast object;
			switch (field) {
				case 'setFilters': return function(filters:Array<Dynamic>):Void {
					if (filters == null) {
						camera.filters = null;
						return;
					}
					var nativeFilters:Array<BitmapFilter> = [];
					for (filter in filters) {
						if (!Std.isOfType(filter, BitmapFilter))
							throw '[codename-camera] setFilters expects BitmapFilter values';
						nativeFilters.push(cast filter);
					}
					camera.filters = nativeFilters;
				};
				case 'addShader': return function(shader:Dynamic):ShaderFilter
					return addCameraShader(camera, shader);
				case 'removeShader': return function(shader:Dynamic):Void
					removeCameraShader(camera, shader);
			}
		}
		if (Std.isOfType(object, FlxSprite) && field == 'makeSolid'
			&& Reflect.field(object, field) == null) {
			var sprite:FlxSprite = cast object;
			return function(width:Int, height:Int, ?color:Dynamic):FlxSprite
				return sprite.makeGraphic(width, height, color == null ? FlxColor.WHITE : cast color);
		}
		if (Std.isOfType(object, CodenameXmlFieldAccess))
			return (cast object:CodenameXmlFieldAccess).getField(field);
		if (Std.isOfType(object, CodenameSongView))
			return (cast object:CodenameSongView).getField(field);
		return super.get(object, field);
	}
	override function set(object:Dynamic, field:String, value:Dynamic):Dynamic {
		field = sourceField(object, field);
		if (field == 'font' && Std.isOfType(object, FlxText))
			value = codenameOwnerFontFamily(value);
		if (Std.isOfType(object, ScriptClass)) {
			var proxy:ScriptClass = cast object;
			if (proxy._interp.variables.exists(field)) {
				proxy._interp.variables.set(field, value);
				return value;
			}
			return (cast proxy:hscript.AbstractScriptClass).fieldWrite(field, value);
		}
		if (isLegacyRequestedStateAlias(object, field)) {
			return CodenameRequestedStateCompat.setRequestedState(object, value);
		}
		if (field == 'characters' && Std.isOfType(object, CodenameInputLine)) {
			CodenameInputLineScriptAccess.setCharacters(cast object, cast value);
			return value;
		}
		// FlxCamera.alpha is public but setter-backed. HScript's generic
		// Reflect.setProperty path treats it as missing on native targets.
		if (Std.isOfType(object, FlxCamera) && field == 'alpha') {
			(cast object:FlxCamera).alpha = value;
			return value;
		}
		if (Std.isOfType(object, CodenameOwnerSaveData))
			return (cast object:CodenameOwnerSaveData).setField(field, value);
		if (Std.isOfType(object, FlxRuntimeShader)) {
			if (setShaderParameter(cast object, field, value)) return value;
			var uniformName = shaderUniformName(object, field);
			var parameter = shaderParameter(object, uniformName);
			if (parameter != null) {
				var parameterType:ShaderParameterType = cast Reflect.getProperty(parameter, 'type');
				if (isUnsupportedShaderMatrix(parameterType))
					throw '[codename-shader] OpenFL does not upload non-square matrix uniform ' + field
						+ ' (' + Std.string(parameterType) + ')';
				throw '[codename-shader] Unsupported value for shader uniform ' + field
					+ ': ' + (value == null ? 'null' : Std.string(Type.typeof(value)));
			}
			throw '[codename-shader] Unknown shader uniform: ' + field;
		}
		if (Std.isOfType(object, CodenameXmlFieldAccess))
			return (cast object:CodenameXmlFieldAccess).setField(field, value);
		if (Std.isOfType(object, CodenameSongView))
			return (cast object:CodenameSongView).setField(field, value);
		return super.set(object, field, value);
	}
	function addCameraShader(camera:FlxCamera, shader:Dynamic):ShaderFilter {
		if (camera == null || shader == null)
			throw '[codename-shader] addShader requires a camera and shader';
		for (owned in ownedCameraFilters)
			if (owned.camera == camera && owned.shader == shader)
				return owned.filter;
		var filter = new ShaderFilter(cast shader);
		var filters:Array<BitmapFilter> = camera.filters == null ? [] : camera.filters.copy();
		filters.push(filter);
		camera.filters = filters;
		ownedCameraFilters.push({camera:camera, shader:shader, filter:filter});
		return filter;
	}
	function removeCameraShader(camera:FlxCamera, shader:Dynamic):Void {
		if (camera == null || shader == null) return;
		var retained:Array<{camera:FlxCamera, shader:Dynamic, filter:ShaderFilter}> = [];
		var removed = new Map<ShaderFilter, Bool>();
		for (owned in ownedCameraFilters) {
			if (owned.camera == camera && owned.shader == shader)
				removed.set(owned.filter, true);
			else retained.push(owned);
		}
		ownedCameraFilters = retained;
		if (removed.keys().hasNext() && camera.filters != null) {
			var filters:Array<BitmapFilter> = [];
			for (filter in camera.filters)
				if (!Std.isOfType(filter, ShaderFilter) || !removed.exists(cast filter))
					filters.push(filter);
			camera.filters = filters.length == 0 ? null : filters;
		}
	}
	static function shaderParameter(shader:Dynamic, name:String):Dynamic {
		// OpenFL Shader.data is a computed property on native targets. Reflect.field
		// bypasses get_data() there and reports no uniforms until a later shader
		// render, although the GLSL declares them. Read the public property so a
		// state update can set uniforms before its first frame is drawn.
		var data:Dynamic = Reflect.getProperty(shader, 'data');
		return data == null ? null : Reflect.field(data, name);
	}
	static function shaderUniformName(shader:Dynamic, name:String):String {
		if (name == null || name == '') return name;
		// Exact declarations take precedence. Codename scripts also address
		// uniforms without the conventional `u` prefix (`mult` -> `uMult`), as
		// they do through the engine's CustomShader facade.
		if (shaderParameter(shader, name) != null) return name;
		var alias = 'u' + name.charAt(0).toUpperCase() + name.substr(1);
		return shaderParameter(shader, alias) != null ? alias : name;
	}
	function setShaderParameter(shader:FlxRuntimeShader, name:String, value:Dynamic):Bool {
		// Only shader-declared uniforms cross this bridge. Unknown HScript fields
		// keep the interpreter's usual error path instead of becoming arbitrary
		// dynamic shader state.
		name = shaderUniformName(shader, name);
		var parameter = shaderParameter(shader, name);
		if (parameter == null) return false;
		var parameterType:ShaderParameterType = cast Reflect.getProperty(parameter, 'type');
		var scalar = shaderNumber(value);
		var values:Array<Dynamic> = Std.isOfType(value, Array) ? cast value : null;
		switch (parameterType) {
			case ShaderParameterType.BOOL:
				if (Std.isOfType(value, Bool)) shader.setBool(name, cast value);
				else {
					var boolValues = shaderBoolArray(values, 1);
					if (boolValues == null) return false;
					shader.setBoolArray(name, boolValues);
				}
			case ShaderParameterType.BOOL2, ShaderParameterType.BOOL3, ShaderParameterType.BOOL4:
				var boolLength = parameterType == ShaderParameterType.BOOL2 ? 2
					: parameterType == ShaderParameterType.BOOL3 ? 3 : 4;
				var boolValues = shaderBoolArray(values, boolLength);
				if (boolValues == null) return false;
				shader.setBoolArray(name, boolValues);
			case ShaderParameterType.FLOAT:
				if (scalar != null) {
					var floatValue:Float = shaderFloat(scalar);
					shader.setFloat(name, floatValue);
					rememberShaderNumber(shader, name, floatValue);
				} else {
					var floatValues = shaderFloatArray(values, 1);
					if (floatValues == null) return false;
					shader.setFloatArray(name, floatValues);
					rememberShaderNumber(shader, name, floatValues[0]);
				}
			case ShaderParameterType.FLOAT2, ShaderParameterType.FLOAT3, ShaderParameterType.FLOAT4,
				ShaderParameterType.MATRIX2X2, ShaderParameterType.MATRIX3X3, ShaderParameterType.MATRIX4X4:
				var floatLength = shaderFloatLength(parameterType);
				var floatValues = shaderFloatArray(values, floatLength);
				if (floatValues == null) return false;
				shader.setFloatArray(name, floatValues);
			case ShaderParameterType.INT:
				if (scalar != null) {
					var intValue = Std.int(shaderFloat(scalar));
					shader.setInt(name, intValue);
					rememberShaderNumber(shader, name, intValue);
				} else {
					var intValues = shaderIntArray(values, 1);
					if (intValues == null) return false;
					shader.setIntArray(name, intValues);
					rememberShaderNumber(shader, name, intValues[0]);
				}
			case ShaderParameterType.INT2, ShaderParameterType.INT3, ShaderParameterType.INT4:
				var intLength = parameterType == ShaderParameterType.INT2 ? 2
					: parameterType == ShaderParameterType.INT3 ? 3 : 4;
				var intValues = shaderIntArray(values, intLength);
				if (intValues == null) return false;
				shader.setIntArray(name, intValues);
			default:
				return false;
		}
		return true;
	}
	static function shaderNumber(value:Dynamic):Null<Dynamic> {
		return switch (Type.typeof(value)) {
			case TInt, TFloat: value;
			default: null;
		};
	}
	static inline function shaderFloat(value:Dynamic):Float return Std.parseFloat(Std.string(value));
	static function shaderFloatArray(values:Array<Dynamic>, length:Int):Null<Array<Float>> {
		if (values == null || values.length != length) return null;
		var result:Array<Float> = [];
		for (value in values) {
			if (shaderNumber(value) == null) return null;
			result.push(shaderFloat(value));
		}
		return result;
	}
	static function shaderIntArray(values:Array<Dynamic>, length:Int):Null<Array<Int>> {
		if (values == null || values.length != length) return null;
		var result:Array<Int> = [];
		for (value in values) {
			if (shaderNumber(value) == null) return null;
			result.push(Std.int(shaderFloat(value)));
		}
		return result;
	}
	static function shaderBoolArray(values:Array<Dynamic>, length:Int):Null<Array<Bool>> {
		if (values == null || values.length != length) return null;
		var result:Array<Bool> = [];
		for (value in values) {
			if (!Std.isOfType(value, Bool)) return null;
			result.push(cast value);
		}
		return result;
	}
static function shaderFloatLength(parameterType:ShaderParameterType):Int {
		return switch (parameterType) {
			case ShaderParameterType.FLOAT2: 2;
			case ShaderParameterType.FLOAT3: 3;
			case ShaderParameterType.FLOAT4: 4;
			case ShaderParameterType.MATRIX2X2: 4;
			case ShaderParameterType.MATRIX3X3: 9;
			case ShaderParameterType.MATRIX4X4: 16;
			default: 0;
		};
	}
	static function isUnsupportedShaderMatrix(parameterType:ShaderParameterType):Bool {
		return switch (parameterType) {
			case ShaderParameterType.MATRIX2X3, ShaderParameterType.MATRIX2X4,
				ShaderParameterType.MATRIX3X2, ShaderParameterType.MATRIX3X4,
				ShaderParameterType.MATRIX4X2, ShaderParameterType.MATRIX4X3: true;
			default: false;
		};
	}
	function rememberShaderNumber(shader:FlxRuntimeShader, name:String, value:Dynamic):Void {
		var values = numericShaderValues.get(shader);
		if (values == null) {
			values = [];
			numericShaderValues.set(shader, values);
		}
		values.set(name, Std.parseFloat(Std.string(value)));
	}
	override function cnew(name:String, args:Array<Dynamic>):Dynamic {
		if (scriptClassScope != null) {
			var scriptClass = scriptClassScope.createInstance(name, args == null ? [] : args);
			if (scriptClass != null) {
				var basic = nativeFlxBasicInner(scriptClass, []);
				if (basic != null) {
					ownedScriptClassBasics.set(cast scriptClass, basic);
					if (unclaimedBasics.indexOf(basic) < 0) unclaimedBasics.push(basic);
					if (Std.isOfType(basic, CodenameMusicBeatGroupCompat))
						(cast basic:CodenameMusicBeatGroupCompat).bindOwnerScript(cast scriptClass);
				}
				CodenameHL17UICompat.bindValue(scriptClass, paths,
					function(basic:FlxBasic):Void claimSceneObject(basic));
				return scriptClass;
			}
			var native = scriptClassScope.tryConstructNative(name, args);
			if (native.handled) return native.value;
		}
		if (flxG != null && (name == 'FlxCamera' || name == 'flixel.FlxCamera'))
			return flxG.cameras.adoptCreated(Type.createInstance(FlxCamera, args));
		if ((name == 'Character' || name == 'funkin.game.Character') && characterFactory != null)
			return characterFactory(args);
		if (name == 'HLTypeText')
			return CodenameHLTypeTextCompat.fromArgs(args, paths);
		if (name == 'ModState' || name == 'funkin.menus.ModState') {
			if (args == null || args.length != 1 || !Std.isOfType(args[0], String))
				throw '[codename-state] ModState requires one state name';
			if (modStateFactory == null)
				throw '[codename-state] ModState is unavailable in this runtime';
			return modStateFactory(args[0]);
		}
		if (ownerStateFactory != null) {
			var ownerState = ownerStateFactory(name);
			if (ownerState != null) return ownerState;
		}
		if (name == 'FunkinText' || name == 'funkin.backend.FunkinText'
			|| name == 'funkin.ui.FunkinText')
			return CodenameFunkinText.fromArgs(args, paths);
		if (name == 'FunkinSprite' || name == 'funkin.backend.FunkinSprite')
			return new CodenameFunkinSprite(args.length > 0 ? args[0] : 0,
				args.length > 1 ? args[1] : 0, args.length > 2 ? args[2] : null, paths);
		if (name == 'CustomShader') {
			if (args.length != 1 || !Std.isOfType(args[0], String))
				throw '[codename-asset] CustomShader requires one scoped shader name';
			if (customShaderFactory == null)
				throw '[codename-asset] CustomShader is unavailable in this interpreter';
			return customShaderFactory(args[0]);
		}
		#if cpp
		if (name == 'FlxVideoSprite' || name == 'hxvlc.flixel.FlxVideoSprite') {
			var video:FlxVideoSprite = Type.createInstance(FlxVideoSprite, args);
			unclaimedVideos.push(video);
			return video;
		}
		#end
		if (name == 'FlxTimer' || name == 'flixel.util.FlxTimer') {
			var timer:FlxTimer = Type.createInstance(FlxTimer, args);
			ownedTimers.push(timer);
			return timer;
		}
		var value:Dynamic;
		var ownerBound3D = name == 'Flx3DView' || name == 'flx3d.Flx3DView'
			|| name == 'CodenameFlx3DView' || name == 'flx3d.CodenameFlx3DView'
			|| name == 'Flx3DCamera' || name == 'flx3d.Flx3DCamera'
			|| name == 'CodenameFlx3DCamera' || name == 'flx3d.CodenameFlx3DCamera';
		if (ownerBound3D) {
			CodenameFlx3DContext.pushOwner(paths);
			try {
				// HScript's base constructor resolves native class paths before
				// consulting bound variables. Force the owner adapters here so an
				// imported flx3d.Flx3DView cannot bypass its selected asset scope.
				var ownerClass:Dynamic = switch (name) {
					case 'Flx3DView' | 'flx3d.Flx3DView' | 'CodenameFlx3DView' | 'flx3d.CodenameFlx3DView':
						flx3d.CodenameFlx3DView;
					case 'Flx3DCamera' | 'flx3d.Flx3DCamera' | 'CodenameFlx3DCamera' | 'flx3d.CodenameFlx3DCamera':
						flx3d.CodenameFlx3DCamera;
					default: null;
				}
				value = ownerClass == null ? super.cnew(name, args)
					: Type.createInstance(ownerClass, args == null ? [] : args);
			} catch (error:Dynamic) {
				CodenameFlx3DContext.popOwner(paths);
				throw error;
			}
			CodenameFlx3DContext.popOwner(paths);
		} else {
			value = super.cnew(name, args);
		}
		CodenameHL17UICompat.bindValue(value, paths, function(basic:FlxBasic):Void claimSceneObject(basic));
		if (Std.isOfType(value, FlxBasic)) unclaimedBasics.push(cast value);
		if (Std.isOfType(value, DisplayObject)) ownedDisplayObjects.push(cast value);
		return value;
	}
	/** A scene scope takes over teardown once add/insert accepts a video. */
	public function claimSceneObject(value:Dynamic):Void {
		var basic = nativeFlxBasic(value);
		if (basic != null) unclaimedBasics.remove(basic);
		if (Std.isOfType(basic, FlxTypedGroup) && claimedGroups.indexOf(cast basic) < 0)
			claimedGroups.push(cast basic);
		#if cpp
		if (Std.isOfType(value, FlxVideoSprite)) unclaimedVideos.remove(cast value);
		#end
	}
	/** A state created by `new PlayState()` is initially owned by this script.
		Once Flixel accepts the navigation request, the outgoing interpreter must
		not destroy that still-uncreated target during its own teardown. */
	public function transferStateTarget(value:Dynamic):Void {
		var basic = nativeFlxBasic(value);
		if (basic != null && Std.isOfType(basic, FlxState))
			unclaimedBasics.remove(basic);
	}
	public function tweenFacade():Dynamic {
		return {
			tween: function(object:Dynamic, properties:Dynamic, duration:Float = 1, ?options:Dynamic):FlxTween {
				if (Std.isOfType(object, FlxRuntimeShader))
					return ownTween(tweenShaderUniforms(cast object, properties, duration, options));
				// HScript-ex classes are owner-local proxies around their native
				// superclass. FlxTween writes with Reflect directly, so passing a
				// proxy (for example a script Bopper extending FlxSprite) bypasses
				// this interpreter's field bridge and fails on native properties.
				var nativeObject = nativeFlxBasic(object);
				if (nativeObject != null) object = nativeObject;
				return ownTween(FlxTween.tween(object, properties, duration, options));
			},
			num: function(from:Float, to:Float, duration:Float = 1, ?options:Dynamic,
				?onValue:Float->Void):FlxTween
				return ownTween(FlxTween.num(from, to, duration, options, onValue)),
			angle: function(sprite:Dynamic, from:Float, to:Float, duration:Float = 1,
				?options:Dynamic):FlxTween
				return ownTween(FlxTween.angle(cast sprite, from, to, duration, options)),
			color: function(sprite:Dynamic, duration:Float, from:Dynamic, to:Dynamic,
				?options:Dynamic):FlxTween
				return ownTween(FlxTween.color(cast sprite, duration, cast from, cast to, options)),
			cancelTweensOf: FlxTween.cancelTweensOf,
			completeTweensOf: FlxTween.completeTweensOf,
			ONESHOT: FlxTweenType.ONESHOT, PERSIST: FlxTweenType.PERSIST,
			LOOPING: FlxTweenType.LOOPING, PINGPONG: FlxTweenType.PINGPONG,
			BACKWARD: FlxTweenType.BACKWARD
		};
	}
	/** FlxTween reflects ordinary fields, while imported CustomShader properties
		are uniforms in shader.data. Tween a real numeric mirror and write each
		frame through the same uniform setter used by script assignments. */
	function tweenShaderUniforms(shader:FlxRuntimeShader, properties:Dynamic,
		duration:Float, options:Dynamic):FlxTween {
		if (properties == null) throw '[codename-shader] Tween needs uniform properties';
		var names = Reflect.fields(properties);
		if (names.length == 0) throw '[codename-shader] Tween needs uniform properties';
		var mirror:Dynamic = {};
		for (name in names) {
			var parameter = shaderParameter(shader, shaderUniformName(shader, name));
			if (parameter == null) throw '[codename-shader] Unknown tween uniform: ' + name;
			var values:Dynamic = Reflect.field(parameter, 'value');
			var current:Dynamic = Std.isOfType(values, Array)
				&& (cast values:Array<Dynamic>).length == 1
				? (cast values:Array<Dynamic>)[0] : null;
			if (!Std.isOfType(current, Float) && !Std.isOfType(current, Int)) {
				var remembered = numericShaderValues.get(shader);
				var uniformName = shaderUniformName(shader, name);
				if (remembered != null && remembered.exists(uniformName))
					current = remembered.get(uniformName);
			}
			if (!Std.isOfType(current, Float) && !Std.isOfType(current, Int))
				throw '[codename-shader] Tween requires a scalar numeric uniform: ' + name;
			Reflect.setField(mirror, name, Std.parseFloat(Std.string(current)));
		}
		var adapted:Dynamic = options == null ? {} : Reflect.copy(options);
		var priorUpdate:Dynamic = Reflect.field(adapted, 'onUpdate');
		var priorComplete:Dynamic = Reflect.field(adapted, 'onComplete');
		var apply = function():Void {
			for (name in names)
				setShaderParameter(shader, name, Reflect.field(mirror, name));
		};
		Reflect.setField(adapted, 'onUpdate', function(tween:FlxTween):Void {
			apply();
			if (priorUpdate != null) Reflect.callMethod(null, priorUpdate, [tween]);
		});
		Reflect.setField(adapted, 'onComplete', function(tween:FlxTween):Void {
			apply();
			if (priorComplete != null) Reflect.callMethod(null, priorComplete, [tween]);
		});
		return FlxTween.tween(mirror, properties, duration, adapted);
	}
	function ownTween(tween:FlxTween):FlxTween {
		ownedTweens.push(tween);
		if (paused) {
			pausedTweens.set(tween, tween.active);
			tween.active = false;
		}
		return tween;
	}
	/** Global Flixel managers update even while a gameplay substate is paused. */
	public function setPaused(value:Bool):Void {
		if (paused == value) return;
		paused = value;
		if (value) {
			for (tween in ownedTweens) if (tween != null) {
				pausedTweens.set(tween, tween.active);
				tween.active = false;
			}
			for (timer in ownedTimers) if (timer != null) {
				pausedTimers.set(timer, timer.active);
				timer.active = false;
			}
		} else {
			for (tween in pausedTweens.keys()) tween.active = pausedTweens.get(tween) && !tween.finished;
			for (timer in pausedTimers.keys()) timer.active = pausedTimers.get(timer) && !timer.finished;
			pausedTweens.clear();
			pausedTimers.clear();
		}
	}
	public function release():Void {
		if (scriptClassScope != null) {
			scriptClassScope.release();
			scriptClassScope = null;
		}
		if (graphicCache != null) graphicCache.release();
		for (owned in ownedEventListeners.copy()) try
			owned.dispatcher.removeEventListener(owned.type, owned.listener, owned.useCapture)
		catch (_:Dynamic) {}
		ownedEventListeners.resize(0);
		for (display in ownedDisplayObjects.copy()) if (display != null && display.parent != null) try
			display.parent.removeChild(display)
		catch (_:Dynamic) {}
		ownedDisplayObjects.resize(0);
		// A group owned by the host also owns members added after the group was
		// claimed. Detach every other group before destroying unclaimed objects,
		// so each constructor-created basic is destroyed at most once here.
		for (group in claimedGroups) claimGroupMembers(group);
		claimedGroups.resize(0);
		for (basic in unclaimedBasics) if (Std.isOfType(basic, FlxTypedGroup)) {
			var group:FlxTypedGroup<FlxBasic> = cast basic;
			if (group.members != null)
				for (member in group.members.copy()) if (member != null) group.remove(member, true);
		}
		for (basic in unclaimedBasics) if (basic != null)
			try basic.destroy() catch (_:Dynamic) {}
		unclaimedBasics.resize(0);
		ownedScriptClassBasics.clear();
		#if cpp
		for (video in unclaimedVideos) if (video != null) video.destroy();
		unclaimedVideos.resize(0);
		#end
		for (tween in ownedTweens) if (tween != null) tween.cancel();
		for (timer in ownedTimers) if (timer != null) timer.cancel();
		ownedTweens.resize(0);
		ownedTimers.resize(0);
		for (owned in ownedCameraFilters.copy())
			try removeCameraShader(owned.camera, owned.shader) catch (_:Dynamic) {}
		ownedCameraFilters.resize(0);
		pausedTweens.clear();
		pausedTimers.clear();
		paused = false;
		liveGlobals.clear();
		publicModuleGlobals.clear();
		protectedImportAliases.clear();
		characterFactory = null;
		modStateFactory = null;
		bindScriptObject(null);
		if (flxG != null) flxG.release();
	}

	function claimGroupMembers(group:FlxTypedGroup<FlxBasic>):Void {
		if (group == null || group.members == null) return;
		for (member in group.members) if (member != null) {
			unclaimedBasics.remove(member);
			if (Std.isOfType(member, FlxTypedGroup)) claimGroupMembers(cast member);
		}
	}
}
