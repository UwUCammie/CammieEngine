package;

import hscript.Expr;

/** Runs one imported Codename global module and owns its lifecycle callbacks. */
class CodenameGlobalScriptRuntime {
	public final interp:CodenameScriptInterp;
	final scriptPath:String;
	final failedCallbacks:Map<String, Bool> = new Map();
	public var failure(default, null):String = '';
	var initialized:Bool = false;
	var newSucceeded:Bool = false;
	var released:Bool = false;

	public function new(interp:CodenameScriptInterp, scriptPath:String) {
		this.interp = interp;
		this.scriptPath = scriptPath;
	}

	/** Execute globals and then their authored constructor. A failed `new()` is
		cleaned by interpreter ownership; donor destroy() is valid only after a
		successful constructor. */
	public function initialize(program:Expr):Bool {
		if (released || initialized) return false;
		try withDiagnosticContext('module', function():Void interp.execute(program)) catch (error:Dynamic) {
			report('module', error);
			release();
			return false;
		}
		initialized = true;
		if (interp.variables.exists('new') && interp.variables.get('new') != null) {
			if (!call('new', [])) {
				release();
				return false;
			}
			newSucceeded = true;
		}
		return true;
	}

	public function update(elapsed:Float):Void {
		if (initialized && !released) call('update', [elapsed]);
	}

	public function preStateSwitch():Void {
		if (initialized && !released) call('preStateSwitch', []);
	}

	public function postStateSwitch():Void {
		if (initialized && !released) call('postStateSwitch', []);
	}

	/** Invoke destroy at most once after successful new(), then always release
		interpreter-owned Flx objects, display children, listeners and timers. */
	public function destroy():Void {
		if (released) return;
		if (newSucceeded) call('destroy', []);
		release();
	}

	function call(name:String, args:Array<Dynamic>):Bool {
		if (released || failedCallbacks.exists(name) || !interp.variables.exists(name)) return true;
		var callback:Dynamic = interp.variables.get(name);
		if (callback == null) return true;
		try {
			withDiagnosticContext(name, function():Void {
				switch (args.length) {
					case 0: callback();
					case 1: callback(args[0]);
					case 2: callback(args[0], args[1]);
					case 3: callback(args[0], args[1], args[2]);
					default: throw 'unsupported callback arity';
				}
			});
			return true;
		} catch (error:Dynamic) {
			failedCallbacks.set(name, true);
			report(name, error);
			return false;
		}
	}

	/** Keep global callbacks attributable when they call external APIs or
	 * schedule asynchronous HScript callbacks such as FlxTimer.start. */
	function withDiagnosticContext(callbackName:String, action:Void->Void):Void {
		if (interp == null || action == null) return;
		var previousSource = interp.variables.get('__compatDiagnosticSource');
		var previousCallback = interp.variables.get('__compatDiagnosticCallback');
		interp.variables.set('__compatDiagnosticSource', scriptPath);
		interp.variables.set('__compatDiagnosticCallback', callbackName);
		try action() catch (error:Dynamic) {
			interp.variables.set('__compatDiagnosticSource', previousSource);
			interp.variables.set('__compatDiagnosticCallback', previousCallback);
			throw error;
		}
		interp.variables.set('__compatDiagnosticSource', previousSource);
		interp.variables.set('__compatDiagnosticCallback', previousCallback);
	}

	function report(callback:String, error:Dynamic):Void {
		if (failure != '') return;
		failure = scriptPath + (callback == '' ? '' : '.' + callback) + ': ' + Std.string(error);
		trace('[codename-global-error] ' + failure);
	}

	function release():Void {
		if (released) return;
		released = true;
		try interp.release() catch (error:Dynamic) report('release', error);
	}
}
