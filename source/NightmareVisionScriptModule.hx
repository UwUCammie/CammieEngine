package;

import crowplexus.hscript.Expr;

/** One NMV interpreter. The group owns registration and lifecycle ordering. */
class NightmareVisionScriptModule {
	public final name:String;
	public var interp(default, null):NightmareVisionScriptInterp;
	public var initialized(default, null):Bool = false;
	public var released(default, null):Bool = false;
	final report:String->String->Dynamic->Void;

	public function new(name:String, interp:NightmareVisionScriptInterp,
		report:String->String->Dynamic->Void) {
		this.name = name;
		this.interp = interp;
		this.report = report;
	}

	public function execute(program:Expr):Bool {
		if (released || initialized) return false;
		try {
			interp.execute(program);
			initialized = true;
			return true;
		} catch (error:Dynamic) {
			report(name, 'module', error);
			return false;
		}
	}

	public function exists(callback:String):Bool {
		return !released && interp != null && interp.variables.exists(callback);
	}

	/** Callback errors stay attributable and do not disable subsequent calls. */
	public function call(callback:String, ?args:Array<Dynamic>):Dynamic {
		if (!exists(callback)) return null;
		try {
			var method = interp.variables.get(callback);
			if (method == null || !Reflect.isFunction(method))
				throw 'Callback is not a function: ' + callback;
			return interp.callCallback(method, args == null ? [] : args);
		} catch (error:Dynamic) {
			report(name, callback, error);
			return null;
		}
	}

	/** onDestroy belongs to the group's clear/call contract, not this release. */
	public function destroy():Void {
		if (released) return;
		released = true;
		var ownedInterp = interp;
		interp = null;
		if (ownedInterp == null) return;
		try {
			ownedInterp.release();
		} catch (error:Dynamic) {
			// Keep the module detached, but report and propagate the flush failure.
			report(name, 'destroy', error);
			throw error;
		}
	}
}
