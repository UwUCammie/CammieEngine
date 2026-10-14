package;

import hscript.Interp;

using StringTools;

private typedef PsychRuntimeScope = {var key:String; var interp:Interp;}

/** A requested script path normalised once, so matching it against every
	registered script costs only string compares. */
private class PsychScriptPathRequest {
	public final path:String;
	public final slashPath:String;
	public final luaPath:String;
	public final hxPath:String;
	public final bare:Bool;

	public function new(path:String) {
		this.path = path;
		slashPath = '/' + path;
		bare = haxe.io.Path.extension(path) == '';
		luaPath = bare ? slashPath + '.lua' : null;
		hxPath = bare ? slashPath + '.hx' : null;
	}

	public function test(actual:String):Bool {
		return actual == path || actual.endsWith(slashPath)
			|| (bare && (actual.endsWith(luaPath) || actual.endsWith(hxPath)));
	}
}

/** Psych Lua and plain HScript share Nightmare Vision's source Iris evaluator. */
@:access(PlayState)
class PsychRuntimeBindings {
	final host:PlayState;
	final owner:Interp;
	final origin:String;
	var embedded:SourceIrisBridge;
	final ownerRoot:String;

	// Every Psych dispatch (each note hit, sustain piece and spawn) needs the
	// scopes in runtime creation order and then by sorted key. Rebuilding that
	// order meant runtimes x keys map lookups and a sort per call, so the base
	// order is kept here and checked against the live registry on each use:
	// the same map and bindings array, the same runtime owners, and the same
	// keys and interpreters in the same iteration order. Any difference
	// rebuilds it. Per-call filters (closed, family, exclusions) still run on
	// every dispatch because scripts change those flags at any time.
	static var orderStates:Map<String, Interp> = null;
	static var orderBindings:Array<PsychRuntimeBindings> = null;
	static var orderOwners:Array<Interp> = [];
	static var orderRawKeys:Array<String> = [];
	static var orderRawInterps:Array<Interp> = [];
	static var orderEntries:Array<PsychRuntimeScope> = [];
	static final scopeKey = function(entry:PsychRuntimeScope):String return entry.key;
	static final scopeClosed = function(entry:PsychRuntimeScope):Bool
		return entry.interp.variables.get('__compatClosed') == true;

	// Script paths are compared case and separator insensitively. The same few
	// paths are compared on every isRunning/getGlobalFromScript call, so keep
	// their normalised spelling instead of rebuilding two strings per compare.
	static inline var PATH_CACHE_LIMIT:Int = 512;
	static var normalizedPaths:Map<String, String> = new Map();
	static var normalizedPathCount:Int = 0;

	public function new(host:PlayState, owner:Interp, origin:String) {
		this.host = host; this.owner = owner; this.origin = origin;
		var root = host.compatPsychOwnerForScript(origin);
		ownerRoot = root == null ? "assets" : root;
	}

	/** Dispatch a lifecycle callback to the active Psych Lua/HScript scopes. */
	public static function dispatch(host:PlayState, name:String, args:Array<Dynamic>,
		family:String = 'Scripts', ignoreStops:Bool = false, ?hscriptArgs:Array<Dynamic>,
		?excludedScopeKeys:Array<String>):Dynamic {
		if (host == null) return null;
		return dispatchScopes(host, name, args, family, ignoreStops,
			hscriptArgs == null ? args : hscriptArgs, null, false, null, null, excludedScopeKeys);
	}

	/** Shared source-family publication for callbacks and native lifecycle globals. */
	public static function publish(host:PlayState, name:String, value:Dynamic, family:String,
		?owner:Interp, ignoreSelf:Bool = false, ?exclusions:Array<String>):Void {
		var requests = exclusionRequests(exclusions);
		for (target in host.hscriptStates) if (eligible(target, family, owner, ignoreSelf, requests))
			target.variables.set(name, value);
	}

	/** Check for a live Psych scope without building the ordered broadcast arrays. */
	public static function hasScripts(host:PlayState):Bool {
		if (host == null || host.hscriptStates == null) return false;
		for (key in host.hscriptStates.keys())
			if (host.hxcPayloadStates.get(key) != true && isPsychScope(host.hscriptStates.get(key))) return true;
		return false;
	}

	function module():SourceIrisBridge {
		if (embedded == null) {
			embedded = new SourceIrisBridge(host);
			for (name => value in owner.variables) embedded.variables.set(name, value);
			embedded.variables.set('game', host);
			embedded.variables.set('variables', host.psychScriptVariables);
			installHscriptPreset(embedded, Std.isOfType(owner, LuaCompatInterp) ? owner : null);
		}
		return embedded;
	}

	function attachCallbackScope(scope:Interp):Void {
		host.psychSourceCallbacks.attach(ownerRoot, scope, Std.isOfType(scope, LuaCompatInterp),
			function(callback, args) return Std.isOfType(scope, SourceIrisBridge)
				? (cast scope:SourceIrisBridge).callCallback(callback, args) : Reflect.callMethod(null, callback, args));
	}

	function installHscriptPreset(scope:Interp, parent:Interp):Void {
		attachCallbackScope(scope);
		new PsychHscriptSourceBindings(host, scope, origin,
			host.psychSourceCallbacks.bridge(ownerRoot, scope, origin, parent)).install();
	}

	public function install():Void {
		attachCallbackScope(owner);
		if (Std.isOfType(owner, SourceIrisBridge)) installHscriptPreset(owner, null);
		else if (Std.isOfType(owner, LuaCompatInterp)) {
			PsychAchievementsIntegration.installLua(host, owner, origin);
			PsychStandardServices.installLua(host, owner, origin);
		}
		var run = function(code:String, ?varsToBring:Dynamic, ?funcToRun:String,
			?funcArgs:Array<Dynamic>):Dynamic {
			var target = module();
			// Psych reports a failing runHaxeCode and returns nil, so the rest of
			// the Lua callback still runs (later tweens, timers and events).
			try {
				var result = target.evaluate(code, origin + '#runHaxeCode', varsToBring, true);
				return funcToRun == null ? result : target.callFunction(funcToRun, funcArgs == null ? [] : funcArgs);
			} catch (error:Dynamic) {
				trace('[psych-hscript-error] ' + origin + '#runHaxeCode: ' + Std.string(error));
				return null;
			}
		};
		owner.variables.set('runHaxeCode', run);
		owner.variables.set('sourceRunHaxeCode', run);
		owner.variables.set('runHaxeFunction', function(name:String, ?args:Array<Dynamic>):Dynamic {
			// Psych reports a missing module or a failing function and returns nil,
			// the same as runHaxeCode, so the calling Lua callback keeps running.
			if (embedded == null) {
				trace('[psych-hscript-error] ' + origin + '#runHaxeFunction: runHaxeCode must initialize the module first');
				return null;
			}
			try {
				return embedded.callFunction(name, args == null ? [] : args);
			} catch (error:Dynamic) {
				trace('[psych-hscript-error] ' + origin + '#runHaxeFunction: ' + Std.string(error));
				return null;
			}
		});
		owner.variables.set('addHaxeLibrary', function(name:String, packageName:String = ''):Void {
			module().bindLibrary(name, packageName == '' ? name : packageName + '.' + name);
		});
		owner.variables.set('addHScript', function(path:String, ignoreAlreadyRunning:Bool = false):Bool {
			return host.compatAddLuaScript(path, ignoreAlreadyRunning, origin, true);
		});
		owner.variables.set('removeHScript', function(path:String):Bool {
			return host.compatRemoveLuaScript(path, origin, true);
		});
		for (kind in ['Scripts', 'Luas', 'HScript']) {
			var family = kind;
			owner.variables.set('setOn' + family, function(name:String, value:Dynamic,
				ignoreSelf:Bool = false, ?exclusions:Array<String>):Void {
				publish(host, name, value, family, owner, ignoreSelf, exclusions);
			});
			owner.variables.set('callOn' + family, function(name:String, ?args:Array<Dynamic>,
				ignoreStops:Bool = false, ignoreSelf:Bool = true, ?exclusions:Array<String>,
				?excludeValues:Array<Dynamic>):Dynamic {
				return dispatchScopes(host, name, args, family, ignoreStops, args,
					owner, ignoreSelf, exclusions, excludeValues);
			});
		}
		owner.variables.set('getRunningScripts', function():Array<String> {
			var result:Array<String> = [];
			for (entry in orderedScopes(host, 'Luas', owner, false, null)) {
				var path:Dynamic = entry.interp.variables.get('__compatDiagnosticSource');
				if (path != null) result.push(Std.string(path));
			}
			return result;
		});
		owner.variables.set('isRunning', function(path:String):Bool {
			var request = pathRequest(path);
			if (request == null) return false;
			for (registration in host.compatScriptScopes) for (entry in registration)
				if (host.hscriptStates.get(entry.scope) == entry.interp
					&& entry.interp.variables.get('__compatClosed') != true
					&& matchesRequest(entry.path, request)) return true;
			return false;
		});
		owner.variables.set('getGlobalFromScript', function(path:String, name:String):Dynamic {
			var request = pathRequest(path);
			if (request == null) return null;
			for (facade in host.psychSourceCallbacks.luaFacades(ownerRoot))
				if (matchesRequest(facade.scriptName, request)) return facade.get(name);
			return null;
		});
		owner.variables.set('setGlobalFromScript', function(path:String, name:String, value:Dynamic):Void {
			var request = pathRequest(path);
			if (request == null) return;
			for (facade in host.psychSourceCallbacks.luaFacades(ownerRoot))
				if (matchesRequest(facade.scriptName, request)) {facade.set(name, value); return;}
		});
		owner.variables.set('callScript', function(path:String, name:String, ?args:Array<Dynamic>):Dynamic {
			var request = pathRequest(path);
			if (request == null) return null;
			for (entry in orderedScopes(host, 'Luas', owner, false, null)) {
				var origin:Dynamic = entry.interp.variables.get('__compatDiagnosticSource');
				if (origin == null || !matchesRequest(Std.string(origin), request)) continue;
				var called = host.callHscript(name, args == null ? [] : args, entry.key, true, null, true);
				var value:Dynamic = called ? entry.interp.variables.get('__compatLastResult') : null;
				return value == null ? ScriptCallbackResult.CONTINUE : value;
			}
			return null;
		});
	}

	/** Keep each family in source creation order rather than StringMap hash order. */
	static function dispatchScopes(host:PlayState, name:String, args:Array<Dynamic>, family:String,
		ignoreStops:Bool, hscriptArgs:Array<Dynamic>, owner:Interp, ignoreSelf:Bool,
		exclusions:Array<String>, excludeValues:Array<Dynamic>, ?excludedScopeKeys:Array<String>):Dynamic {
		// Only the families this call can reach are built; the shared base order
		// is validated once for both.
		var luas = family == 'HScript' ? null
			: orderedScopes(host, 'Luas', owner, ignoreSelf, exclusions, excludedScopeKeys);
		var scripts = family == 'Luas' ? null
			: orderedScopes(host, 'HScript', owner, ignoreSelf, exclusions, excludedScopeKeys);
		var scopeName = scopeKey;
		var closed = scopeClosed;
		var invoke = function(entry:PsychRuntimeScope, callback:String, callbackArgs:Array<Dynamic>):Dynamic {
			if (host.hscriptStates == null || host.hscriptStates.get(entry.key) != entry.interp) return null;
			return host.callHscript(callback, callbackArgs, entry.key, true, null, true)
				? entry.interp.variables.get('__compatLastResult') : null;
		};
		var invokeHScript = function(entry:PsychRuntimeScope, callback:String,
			callbackArgs:Array<Dynamic>):Dynamic return invoke(entry, callback,
				hscriptArgs == null ? callbackArgs : hscriptArgs);

		return switch (family) {
			case 'Luas': PsychScriptBroadcast.callOnLuas(luas, name, args, scopeName, closed,
				invoke, null, ignoreStops, null, excludeValues);
			case 'HScript': PsychScriptBroadcast.callOnHScript(scripts, name,
				hscriptArgs == null ? args : hscriptArgs, scopeName, invoke, ignoreStops,
				null, excludeValues);
			default: PsychScriptBroadcast.callOnScripts(luas, scripts, name, args, scopeName,
				closed, invoke, invokeHScript, null, ignoreStops, null, excludeValues);
		};
	}

	/** Keep each family in source creation order rather than StringMap hash order.
		The result is a fresh array: callOnLuas removes closed scopes from it. */
	static function orderedScopes(host:PlayState, family:String, owner:Interp, ignoreSelf:Bool,
		exclusions:Array<String>, ?excludedScopeKeys:Array<String>):Array<PsychRuntimeScope> {
		var result:Array<PsychRuntimeScope> = [];
		var requests = exclusionRequests(exclusions);
		for (entry in baseOrder(host)) {
			var key = entry.key;
			if (!scopeKeyExcluded(key, excludedScopeKeys) && host.hxcPayloadStates.get(key) != true
				&& eligible(entry.interp, family, owner, ignoreSelf, requests)) result.push(entry);
		}
		return result;
	}

	/** Runtime-bound scopes in binding order, then read-only host observers (which
		have no mutable runtime binding) by sorted key. Filters are not applied. */
	static function baseOrder(host:PlayState):Array<PsychRuntimeScope> {
		var states = host.hscriptStates;
		var bindings = host.psychRuntimeBindings;
		// A host without runtimes is a torn-down or observer-only song. Do not keep
		// its interpreters alive in the static cache.
		if (bindings == null || bindings.length == 0) {
			clearOrder();
			return buildOrder(states, bindings, [for (key in states.keys()) key]);
		}
		if (!orderCurrent(states, bindings)) {
			var keys = [for (key in states.keys()) key];
			orderStates = states;
			orderBindings = bindings;
			orderOwners = [for (runtime in bindings) runtime.owner];
			orderRawKeys = keys;
			orderRawInterps = [for (key in keys) states.get(key)];
			orderEntries = buildOrder(states, bindings, keys);
		}
		return orderEntries;
	}

	static function orderCurrent(states:Map<String, Interp>, bindings:Array<PsychRuntimeBindings>):Bool {
		if (states != orderStates || bindings != orderBindings || bindings.length != orderOwners.length)
			return false;
		for (index in 0...bindings.length)
			if (bindings[index].owner != orderOwners[index]) return false;
		var index = 0;
		var count = orderRawKeys.length;
		for (key in states.keys()) {
			if (index >= count || orderRawKeys[index] != key || states.get(key) != orderRawInterps[index])
				return false;
			index++;
		}
		return index == count;
	}

	static function buildOrder(states:Map<String, Interp>, bindings:Array<PsychRuntimeBindings>,
		keys:Array<String>):Array<PsychRuntimeScope> {
		var result:Array<PsychRuntimeScope> = [];
		var seen:Map<String, Bool> = [];
		if (bindings != null) for (runtime in bindings) for (key in keys) {
			var interp = states.get(key);
			if (!seen.exists(key) && interp == runtime.owner) {
				result.push({key:key, interp:interp}); seen.set(key, true);
			}
		}
		var sorted = keys.copy();
		sorted.sort(Reflect.compare);
		for (key in sorted) if (!seen.exists(key)) result.push({key:key, interp:states.get(key)});
		return result;
	}

	static function clearOrder():Void {
		if (orderStates == null && orderBindings == null) return;
		orderStates = null;
		orderBindings = null;
		orderOwners = [];
		orderRawKeys = [];
		orderRawInterps = [];
		orderEntries = [];
	}

	static function scopeKeyExcluded(key:String, excludedScopeKeys:Array<String>):Bool {
		return excludedScopeKeys != null && excludedScopeKeys.indexOf(key) >= 0;
	}

	static function exclusionRequests(exclusions:Array<String>):Array<PsychScriptPathRequest> {
		if (exclusions == null) return null;
		var requests:Array<PsychScriptPathRequest> = [];
		for (excluded in exclusions) {
			var request = pathRequest(excluded);
			if (request != null) requests.push(request);
		}
		return requests;
	}

	static function eligible(target:Interp, family:String, owner:Interp, ignoreSelf:Bool,
		exclusions:Array<PsychScriptPathRequest>):Bool {
		if (!isPsychScope(target) || (ignoreSelf && target == owner)) return false;
		var lua = Std.isOfType(target, LuaCompatInterp);
		if ((family == 'Luas' && !lua) || (family == 'HScript' && lua)) return false;
		if (exclusions == null || exclusions.length == 0) return true;
		var path:Dynamic = target.variables.get('__compatDiagnosticSource');
		if (path != null) {
			var actual = normalizedScriptPath(Std.string(path));
			for (excluded in exclusions)
				if (excluded.test(actual)) return false;
		}
		return true;
	}

	static function isPsychScope(target:Interp):Bool {
		return target != null && target.variables.get('__compatClosed') != true
			&& target.variables.get('__psychScoreGlobals') == true;
	}

	public static function matches(actual:String, requested:String):Bool {
		var request = pathRequest(requested);
		return request != null && matchesRequest(actual, request);
	}

	/** Matches exactly, after a '/', or with an implied .lua/.hx extension. */
	static function matchesRequest(actual:String, request:PsychScriptPathRequest):Bool {
		return actual != null && request.test(normalizedScriptPath(actual));
	}

	static function pathRequest(requested:String):PsychScriptPathRequest {
		if (requested == null || StringTools.trim(requested) == '') return null;
		return new PsychScriptPathRequest(normalizedScriptPath(requested));
	}

	static function normalizedScriptPath(path:String):String {
		var cached = normalizedPaths.get(path);
		if (cached != null) return cached;
		var normalized = StringTools.replace(path, '\\', '/').toLowerCase();
		// Paths built from changing values would otherwise grow this forever.
		if (normalizedPathCount >= PATH_CACHE_LIMIT) {
			normalizedPaths.clear();
			normalizedPathCount = 0;
		}
		normalizedPaths.set(path, normalized);
		normalizedPathCount++;
		return normalized;
	}

	public function release():Void {
		if (embedded != null) embedded.release();
		embedded = null;
		// Song teardown releases every runtime; drop the cached order so the
		// finished song's interpreters can be collected.
		clearOrder();
	}
}
