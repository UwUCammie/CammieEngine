package;

/** One optional Codename companion script for one live character instance. */
class CodenameCharacterRuntime {
	public var interp(default, null):CodenameScriptInterp;
	public var ready(default, null):Bool = false;
	public var destroyed(default, null):Bool = false;
	var destroying:Bool = false;
	public var diagnostics(default, null):Array<String> = [];
	var origin:String;
	var onRelease:Void->Void;
	var released:Bool = false;
	var failedCallbacks:Map<String, Bool> = new Map();

	/** The owner binds the actor and seeds globals before construction.
	 * create and postCreate are deliberately called by the owner at their actual lifecycle points. */
	public function new(interp:CodenameScriptInterp, source:String, origin:String,
		imports:Map<String, Dynamic>, ?onRelease:Void->Void,
		?onPublicVariables:Array<String>->Void) {
		this.interp = interp;
		this.origin = origin == null ? 'codename-character' : origin;
		this.onRelease = onRelease;
		if (interp == null) {
			diagnostic('missing-interpreter');
			release();
			return;
		}
		// A character with only XML still owns an actor scope, including its cleanup.
		if (source == null) {
			ready = true;
			return;
		}
		try {
			var parsed = CodenameScriptParser.prepare(source, imports, this.origin);
			CodenameScriptParser.reportRecoverableDiagnostics(parsed, this.origin);
			if (parsed.program == null || CodenameScriptParser.hasFatalDiagnostics(parsed)) {
				for (entry in parsed.diagnostics)
					diagnostic(entry.code + ':' + entry.line + ':' + entry.message);
				if (parsed.diagnostics.length == 0) diagnostic('missing-program');
				release();
				return;
			}
			if (imports != null) {
				for (name in imports.keys())
					interp.variables.set(name.substr(name.lastIndexOf('.') + 1), imports.get(name));
			}
			if (onPublicVariables != null) onPublicVariables(parsed.publicVariables);
			interp.execute(parsed.program);
			ready = true;
		} catch (error:Dynamic) {
			diagnostic('execute:' + Std.string(error));
			release();
		}
	}

	function diagnostic(message:String):Void {
		diagnostics.push(message);
		trace('[codename-character-script] ' + origin + ': ' + message);
	}

	/** Missing hooks are successful no-ops. A failed hook cannot block other hooks. */
	public function call(name:String, args:Array<Dynamic>):Bool {
		if (!ready || destroyed || released || name == null || failedCallbacks.exists(name)) return false;
		if (!interp.variables.exists(name)) return true;
		try {
			Reflect.callMethod(null, interp.variables.get(name), args == null ? [] : args);
			return true;
		} catch (error:Dynamic) {
			failedCallbacks.set(name, true);
			diagnostic('callback:' + name + ':' + Std.string(error));
			return false;
		}
	}

	/** Character event callbacks mutate the supplied event object in place. */
	public function event(name:String, payload:Dynamic):Dynamic {
		call(name, [payload]);
		return payload;
	}

	public function setPaused(value:Bool):Void {
		if (ready && !destroyed && !released) interp.setPaused(value);
	}

	public function destroy():Void {
		if (destroyed || destroying) return;
		destroying = true;
		if (ready && !released) call('destroy', []);
		destroyed = true;
		ready = false;
		release();
	}

	function release():Void {
		if (released) return;
		released = true;
		ready = false;
		if (interp != null) try interp.release() catch (error:Dynamic)
			diagnostic('release-interpreter:' + Std.string(error));
		if (onRelease != null) try onRelease() catch (error:Dynamic)
			diagnostic('release-owner:' + Std.string(error));
	}
}
