package;

import hscript.Interp;

using StringTools;

private typedef PsychRuntimeScope = {var key:String; var interp:Interp;}

/** Psych Lua and plain HScript share Nightmare Vision's source Iris evaluator. */
@:access(PlayState)
class PsychRuntimeBindings {
	final host:PlayState;
	final owner:Interp;
	final origin:String;
	var embedded:SourceIrisBridge;
	final ownerRoot:String;

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
		var run = function(code:String, ?varsToBring:Dynamic, ?funcToRun:String,
			?funcArgs:Array<Dynamic>):Dynamic {
			var target = module();
			var result = target.evaluate(code, origin + '#runHaxeCode', varsToBring);
			return funcToRun == null ? result : target.callFunction(funcToRun, funcArgs == null ? [] : funcArgs);
		};
		owner.variables.set('runHaxeCode', run);
		owner.variables.set('sourceRunHaxeCode', run);
		owner.variables.set('runHaxeFunction', function(name:String, ?args:Array<Dynamic>):Dynamic {
			if (embedded == null) throw '[psych-hscript] runHaxeCode must initialize the module first';
			return embedded.callFunction(name, args == null ? [] : args);
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
				for (target in host.hscriptStates) if (eligible(target, family, owner, ignoreSelf, exclusions))
					target.variables.set(name, value);
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
			for (registration in host.compatScriptScopes) for (entry in registration)
				if (host.hscriptStates.get(entry.scope) == entry.interp
					&& entry.interp.variables.get('__compatClosed') != true
					&& matches(entry.path, path)) return true;
			return false;
		});
		owner.variables.set('callScript', function(path:String, name:String, ?args:Array<Dynamic>):Dynamic {
			for (entry in orderedScopes(host, 'Luas', owner, false, null)) {
				var origin:Dynamic = entry.interp.variables.get('__compatDiagnosticSource');
				if (origin == null || !matches(Std.string(origin), path)) continue;
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
		var luas = family == 'HScript' ? []
			: orderedScopes(host, 'Luas', owner, ignoreSelf, exclusions, excludedScopeKeys);
		var scripts = family == 'Luas' ? []
			: orderedScopes(host, 'HScript', owner, ignoreSelf, exclusions, excludedScopeKeys);
		var scopeName = function(entry:PsychRuntimeScope):String return entry.key;
		var closed = function(entry:PsychRuntimeScope):Bool return entry.interp.variables.get('__compatClosed') == true;
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

	/** Keep each family in source creation order rather than StringMap hash order. */
	static function orderedScopes(host:PlayState, family:String, owner:Interp, ignoreSelf:Bool,
		exclusions:Array<String>, ?excludedScopeKeys:Array<String>):Array<PsychRuntimeScope> {
		var result:Array<PsychRuntimeScope> = [];
		var seen:Map<String, Bool> = [];
		var keys = [for (key in host.hscriptStates.keys()) key];
		for (runtime in host.psychRuntimeBindings) for (key in keys) {
			var interp = host.hscriptStates.get(key);
			if (!seen.exists(key) && !scopeKeyExcluded(key, excludedScopeKeys)
				&& host.hxcPayloadStates.get(key) != true && interp == runtime.owner
				&& eligible(interp, family, owner, ignoreSelf, exclusions)) {
				result.push({key:key, interp:interp}); seen.set(key, true);
			}
		}
		// Read-only host observers have no mutable runtime binding.
		keys.sort(Reflect.compare);
		for (key in keys) if (!seen.exists(key)) {
			var interp = host.hscriptStates.get(key);
			if (!scopeKeyExcluded(key, excludedScopeKeys) && host.hxcPayloadStates.get(key) != true
				&& eligible(interp, family, owner, ignoreSelf, exclusions)) result.push({key:key, interp:interp});
		}
		return result;
	}

	static function scopeKeyExcluded(key:String, excludedScopeKeys:Array<String>):Bool {
		return excludedScopeKeys != null && excludedScopeKeys.indexOf(key) >= 0;
	}

	static function eligible(target:Interp, family:String, owner:Interp, ignoreSelf:Bool,
		exclusions:Array<String>):Bool {
		if (!isPsychScope(target) || (ignoreSelf && target == owner)) return false;
		var lua = Std.isOfType(target, LuaCompatInterp);
		if ((family == 'Luas' && !lua) || (family == 'HScript' && lua)) return false;
		var path:Dynamic = target.variables.get('__compatDiagnosticSource');
		if (path != null && exclusions != null) for (excluded in exclusions)
			if (matches(Std.string(path).toLowerCase(), excluded)) return false;
		return true;
	}

	static function isPsychScope(target:Interp):Bool {
		return target != null && target.variables.get('__compatClosed') != true
			&& target.variables.get('__psychScoreGlobals') == true;
	}

	static function matches(actual:String, requested:String):Bool {
		if (actual == null || requested == null || StringTools.trim(requested) == '') return false;
		actual = StringTools.replace(actual, '\\', '/').toLowerCase();
		var path = StringTools.replace(requested, '\\', '/').toLowerCase();
		return actual == path || actual.endsWith('/' + path)
			|| (haxe.io.Path.extension(path) == '' && (actual.endsWith('/' + path + '.lua')
				|| actual.endsWith('/' + path + '.hx')));
	}

	public function release():Void {
		if (embedded != null) embedded.release();
		embedded = null;
	}
}
