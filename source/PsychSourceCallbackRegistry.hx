package;

import hscript.Interp;

private typedef PsychCallbackScope = {
	var ownerRoot:String;
	var interp:Interp;
	var lua:Bool;
	var invoke:Dynamic->Array<Dynamic>->Dynamic;
	var facade:PsychLuaCallbackFacade;
}

/** Callback registrations belong to a mod in this host state, never the process. */
class PsychSourceCallbackRegistry {
	var scopes:Array<PsychCallbackScope> = [];
	var globals:Map<String, Map<String, Dynamic>> = [];
	var released:Bool = false;

	public function new() {}

	public function attach(ownerRoot:String, interp:Interp, lua:Bool,
		invoke:Dynamic->Array<Dynamic>->Dynamic):Void {
		ensureAlive();
		if (find(interp) != null) return;
		var scope:PsychCallbackScope = {ownerRoot:ownerRoot, interp:interp, lua:lua, invoke:invoke, facade:null};
		if (lua) scope.facade = new PsychLuaCallbackFacade(scope);
		scopes.push(scope);
		if (lua && globals.exists(ownerRoot)) for (name => callback in globals.get(ownerRoot))
			interp.variables.set(name, callback);
	}

	public function bridge(ownerRoot:String, interp:Interp, origin:String, ?parent:Interp):Dynamic {
		ensureAlive();
		var scope = find(interp);
		if (scope == null || scope.ownerRoot != ownerRoot) throw '[psych-hscript] Unregistered callback owner';
		var parentScope = parent == null ? null : find(parent);
		if (parentScope != null && (!parentScope.lua || parentScope.ownerRoot != ownerRoot))
			throw '[psych-hscript] Parent callback scope belongs to another owner';
		var parentFacade:Dynamic = parentScope == null ? null : parentScope.facade;
		return {
			parentFacade:function(_origin:String, _interp:Interp):Dynamic return parentFacade,
			selfFacade:function(_origin:String, _interp:Interp, parentLua:Dynamic):Dynamic return {
				origin:origin, parentLua:parentLua, variables:interp.variables
			},
			registerLocal:function(_origin:String, name:String, callback:Dynamic, target:Dynamic):Dynamic {
				ensureAlive();
				if (!Std.isOfType(target, PsychLuaCallbackFacade)) throw '[psych-hscript] Invalid parent Lua scope';
				var facade:PsychLuaCallbackFacade = cast target;
				var destination = facade.scope;
				if (scopes.indexOf(destination) < 0 || destination.ownerRoot != ownerRoot || !destination.lua)
					throw '[psych-hscript] Parent callback scope belongs to another owner';
				destination.interp.variables.set(name, wrap(scope, callback));
				return null;
			},
			registerGlobal:function(_origin:String, name:String, callback:Dynamic):Dynamic {
				ensureAlive();
				var wrapper = wrap(scope, callback);
				if (!globals.exists(ownerRoot)) globals.set(ownerRoot, []);
				globals.get(ownerRoot).set(name, wrapper);
				for (destination in scopes) if (destination.lua && destination.ownerRoot == ownerRoot)
					destination.interp.variables.set(name, wrapper);
				return null;
			}
		};
	}

	function wrap(scope:PsychCallbackScope, callback:Dynamic):Dynamic {
		if (!Reflect.isFunction(callback)) throw '[psych-hscript] Callback must be a function';
		return Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
			ensureAlive();
			if (scope.interp.variables.get('__compatClosed') == true)
				throw '[psych-hscript] Callback source is closed';
			return scope.invoke(callback, args);
		});
	}

	function find(interp:Interp):PsychCallbackScope {
		for (scope in scopes) if (scope.interp == interp) return scope;
		return null;
	}
	function ensureAlive():Void if (released) throw '[psych-hscript] Callback owner was released';
	public function release():Void {
		if (released) return;
		released = true;
		globals.clear();
		for (scope in scopes) if (scope.lua) scope.interp.variables.set('__compatClosed', true);
		scopes.resize(0);
	}
}

/** Source parentLua facade bound to exactly one live translated Lua scope. */
class PsychLuaCallbackFacade {
	@:allow(PsychSourceCallbackRegistry) final scope:PsychCallbackScope;
	public var scriptName(get, never):String;
	function get_scriptName():String return Std.string(scope.interp.variables.get('__compatDiagnosticSource'));
	public var closed(get, never):Bool;
	function get_closed():Bool return scope.interp.variables.get('__compatClosed') == true;
	public function new(scope:PsychCallbackScope) this.scope = scope;
	public function get(name:String):Dynamic return scope.interp.variables.get(name);
	public function set(name:String, value:Dynamic):Void scope.interp.variables.set(name, value);
	public function call(name:String, ?args:Array<Dynamic>):Dynamic {
		if (closed) return ScriptCallbackResult.CONTINUE;
		var callback = get(name);
		return Reflect.isFunction(callback) ? scope.invoke(callback, args == null ? [] : args) : ScriptCallbackResult.CONTINUE;
	}
	public function stop():Void scope.interp.variables.set('__compatClosed', true);
}
