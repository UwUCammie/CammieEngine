package;

import crowplexus.hscript.Expr;

/** NMV ScriptGroup semantics, independent of gameplay binding and discovery. */
class NightmareVisionScriptGroup {
	public static inline var CONTINUE_FUNC:Int = 0;
	public static inline var STOP_FUNC:Int = 1;
	public static inline var HALT_FUNC:Int = 2;

	public var members(default, null):Array<NightmareVisionScriptModule> = [];
	public var sharedFields(default, null):Map<String, Dynamic> = new Map();
	public var scriptShareables(get, set):Map<String, Dynamic>;
	function get_scriptShareables():Map<String, Dynamic> return sharedFields;
	function set_scriptShareables(value:Map<String, Dynamic>):Map<String, Dynamic> return sharedFields = value;
	public var parent(default, set):Dynamic;
	public var released(default, null):Bool = false;
	final report:String->String->Dynamic->Void;

	public function new(?parent:Dynamic, ?report:String->String->Dynamic->Void) {
		this.report = report == null ? function(name, callback, error):Void {
			trace('[nightmare-vision-script-error] ' + name + '#' + callback + ': ' + Std.string(error));
		} : report;
		this.parent = parent;
	}

	function set_parent(value:Dynamic):Dynamic {
		if (value != null && value == parent) return parent;
		parent = value;
		for (script in members) if (script != null && script.interp != null) {
			script.interp.parent = value;
			script.interp.sharedFields = sharedFields;
		}
		return value;
	}

	public function getScript(name:String):NightmareVisionScriptModule {
		for (script in members) if (script != null && script.name == name) return script;
		return null;
	}

	public function exists(name:String):Bool return getScript(name) != null;

	public function addScript(script:NightmareVisionScriptModule, allowDupeNames:Bool = false):Bool {
		if (released || script == null || script.released || (!allowDupeNames && exists(script.name)))
			return false;
		script.interp.parent = parent;
		script.interp.sharedFields = sharedFields;
		members.push(script);
		return true;
	}

	/** Removal transfers ownership without destroying the interpreter. */
	public function removeScript(script:NightmareVisionScriptModule):Bool return members.remove(script);

	public function loadSource(name:String, source:String,
		?configure:NightmareVisionScriptInterp->Void,
		?beforeLoad:NightmareVisionScriptInterp->Void,
		allowDupeNames:Bool = false):NightmareVisionScriptModule {
		if (released || (!allowDupeNames && exists(name))) return null;
		var program:Expr;
		try {
			program = new NightmareVisionScriptParser().parseString(source, name);
		} catch (error:Dynamic) {
			report(name, 'parse', error);
			return null;
		}
		return load(name, program, configure, beforeLoad, allowDupeNames);
	}

	/** Register before execution, as initFunkinScript does, so recursive loads
	 * see the current script. Failed top-level execution removes that module.
	 * The caller supplies the parsed source and source-specific API bindings. */
	public function load(name:String, program:Expr,
		?configure:NightmareVisionScriptInterp->Void,
		?beforeLoad:NightmareVisionScriptInterp->Void,
		allowDupeNames:Bool = false):NightmareVisionScriptModule {
		if (released || (!allowDupeNames && exists(name))) return null;
		var interp = new NightmareVisionScriptInterp(parent, sharedFields);
		var script = new NightmareVisionScriptModule(name, interp, report);
		try {
			if (configure != null) configure(interp);
		} catch (error:Dynamic) {
			report(name, 'bindings', error);
			script.destroy();
			return null;
		}
		addScript(script, allowDupeNames);
		if (!script.executeProgram(program)) {
			members.remove(script);
			script.destroy();
			return null;
		}
		try {
			if (beforeLoad != null) beforeLoad(interp);
		} catch (error:Dynamic) {
			report(name, 'bindings', error);
			members.remove(script);
			script.destroy();
			return null;
		}
		if (script.exists('onLoad')) script.callValue('onLoad');
		return script;
	}

	public function set(name:String, value:Dynamic):Void {
		for (script in members)
			if (script != null && script.interp != null) script.interp.variables.set(name, value);
	}

	/** STOP cancels native work but still broadcasts. HALT ends broadcasting
	 * and retains the preceding result. Non-Int returns never change it. */
	public function call(event:String, ?args:Array<Dynamic>, ignoreStops:Bool = false,
		?exclusions:Array<String>):Dynamic {
		return callFiltered(event, args, ignoreStops, exclusions);
	}

	/** Filter live registry membership at each invocation rather than snapshotting names. */
	public function callFiltered(event:String, ?args:Array<Dynamic>, ignoreStops:Bool = false,
		?exclusions:Array<String>, historical:Bool = false,
		?excluded:NightmareVisionScriptModule->Bool):Dynamic {
		if (released) return CONTINUE_FUNC;
		return NightmareVisionScriptBroadcast.call(members,
			function(script) return script.callValue(event, args), ignoreStops, historical,
			function(script) return (exclusions != null && exclusions.indexOf(script.name) >= 0)
				|| (excluded != null && excluded(script)));
	}

	/** clear can be reused for another song; shared fields persist in source. */
	public function clear(callOnDestroy:Bool = true):Void {
		if (released) return;
		var firstError:Dynamic = null;
		var failed = false;
		if (callOnDestroy) {
			try call('onDestroy', null, true) catch (error:Dynamic) {
				firstError = error;
				failed = true;
			}
		}
		while (members.length > 0) {
			var script = members.shift();
			if (script == null) continue;
			try script.destroy() catch (error:Dynamic) {
				if (!failed) {
					firstError = error;
					failed = true;
				}
			}
		}
		if (failed) throw firstError;
	}

	/** Source group destruction releases interpreters and shared fields.
	 * Gameplay explicitly broadcasts onDestroy before invoking this method. */
	public function destroy():Void {
		if (released) return;
		var firstError:Dynamic = null;
		var failed = false;
		try clear(false) catch (error:Dynamic) {
			firstError = error;
			failed = true;
		}
		try sharedFields.clear() catch (error:Dynamic) {
			if (!failed) {
				firstError = error;
				failed = true;
			}
		}
		try parent = null catch (error:Dynamic) {
			if (!failed) {
				firstError = error;
				failed = true;
			}
		}
		released = true;
		if (failed) throw firstError;
	}
}
