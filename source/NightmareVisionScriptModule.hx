package;

import crowplexus.hscript.Expr;
import crowplexus.iris.Iris.IrisCall;
import NightmareVisionScriptBindings.NightmareVisionScriptContext;

/** One NMV interpreter. The group owns registration and lifecycle ordering. */
@:keep
class NightmareVisionScriptModule {
	// Reuse the no-argument list used by frequent lifecycle and update callbacks.
	// Iris reads this array but does not mutate it for a zero-parameter callback.
	static final noArguments:Array<Dynamic> = [];

	public static final H_EXTS:Array<String> = ['hx', 'hxs', 'hscript'];
	public var name(default, null):String;
	var sourceInstances:Null<Map<String, NightmareVisionScriptModule>>;
	public var modFolder:Null<String>;
	public var interp(default, null):NightmareVisionScriptInterp;
	public var initialized(default, null):Bool = false;
	public var parsingException:Dynamic = null;
	public var released(default, null):Bool = false;
	final report:String->String->Dynamic->Void;
	var program:Expr;
	var sourceCode:Null<String>;

	public function new(name:String, interp:NightmareVisionScriptInterp,
		report:String->String->Dynamic->Void) {
		this.name = name;
		this.interp = interp;
		this.report = report;
		interp.variables.set('script', this);
		interp.variables.set('addHaxeLibrary', function(libName:String, libPackage:String = ''):Void {
			if (released) return;
			var path = libPackage == '' ? libName : libPackage + '.' + libName;
			try {
				var value = this.interp.resolveSourceImport(path, true);
				// Older NV replaces the short global even when resolution is null.
				this.interp.variables.set(libName, value);
				if (value == null) report(name, 'addHaxeLibrary', 'Unresolved source class: ' + path);
			} catch (error:Dynamic) report(name, 'addHaxeLibrary', error);
		});
	}

	/** Source execute can run the stored program again and returns its value. */
	public static function getPath(path:String, ?context:NightmareVisionScriptContext):String {
		return NightmareVisionScriptBindings.getPath(path, NightmareVisionScriptBindings.requireContext(context).paths);
	}
	public static function isHxFile(path:String, ?context:NightmareVisionScriptContext):Bool {
		var selected = NightmareVisionScriptBindings.requireContext(context);
		for (extension in selected.paths.scriptExtensions) if (StringTools.endsWith(path, extension)) return true;
		return false;
	}
	public static function fromString(code:String, ?name:String = 'Script', autoExecute:Bool = true,
		?shared:Map<String, Dynamic>, ?modFolder:String, ?context:NightmareVisionScriptContext):NightmareVisionScriptModule {
		var selected = NightmareVisionScriptBindings.requireContext(context);
		var module = fromSource(name, code, selected.parent(), shared, selected.configure, selected.report, autoExecute, selected.paths.scriptInstances, modFolder);
		return module;
	}
	public static function fromFile(path:String, ?name:String, autoExecute:Bool = true,
		?shared:Map<String, Dynamic>, ?modFolder:String, ?context:NightmareVisionScriptContext):NightmareVisionScriptModule {
		var selected = NightmareVisionScriptBindings.requireContext(context);
		return fromString(selected.read(path), name == null ? path : name, autoExecute, shared,
			modFolder == null ? selected.paths.getModFolder(path, 'scripts') : modFolder, selected);
	}

	public function execute():Dynamic {
		try {
			if (interp == null) throw 'Attempt to run script failed, script is probably destroyed.';
			if (program == null) program = new NightmareVisionScriptParser().parseString(sourceCode, name);
			if (sourceInstances != null) sourceInstances.set(name, this);
			var result = interp.execute(program);
			initialized = true;
			return result;
		} catch (error:Dynamic) {
			parsingException = error;
			report(name, 'module', error);
			return null;
		}
	}
	/** Internal loaders parse first and only execute their module once. */
	public function executeProgram(value:Expr):Bool {
		if (released || initialized) return false;
		program = value;
		execute();
		return !parsingFailed();
	}

	/** IrisEx fixes the name before execution; only executed handles reserve it. */
	public function bindSourceInstances(instances:Map<String, NightmareVisionScriptModule>):Void {
		if (sourceInstances == instances) return;
		sourceInstances = instances;
		var base = name;
		var suffix = 1;
		while (instances.exists(name)) {name = base + '_' + suffix; suffix++;}
	}

	public function parsingFailed():Bool return parsingException != null;
	public function get(field:String):Dynamic return interp == null ? false : interp.variables.get(field);
	public function set(field:String, value:Dynamic, allowOverride:Bool = true):Void {
		if (interp != null && (allowOverride || !interp.variables.exists(field))) interp.variables.set(field, value);
	}

	/** Standalone source loading does not register or call onLoad. Stage owns
	 * those later phases, including rejection of top-level runtime failures. */
	public static function fromSource(name:String, source:String, parent:Dynamic,
		shared:Map<String, Dynamic>, configure:NightmareVisionScriptInterp->Void,
		report:String->String->Dynamic->Void, autoExecute:Bool = true,
		?instances:Map<String, NightmareVisionScriptModule>, ?modFolder:String):NightmareVisionScriptModule {
		var interp = new NightmareVisionScriptInterp(parent, shared);
		var script = new NightmareVisionScriptModule(name, interp, report);
		script.sourceCode = source;
		script.modFolder = modFolder;
		if (instances != null) script.bindSourceInstances(instances);
		// Source preset failures propagate before execute's parsing-error boundary.
		if (configure != null) configure(interp);
		if (autoExecute) script.execute();
		return script;
	}

	/** The public source call returns the actual Iris result record. */
	public function call(callback:String, ?args:Array<Dynamic>):IrisCall {
		if (interp == null) return null;
		if (!exists(callback)) {
			report(name, callback, 'Function does not exist: ' + callback);
			return null;
		}
		var signature = interp.variables.get(callback);
		if (signature == null || !Reflect.isFunction(signature)) {
			report(name, callback, 'Callback is not a function: ' + callback);
			return null;
		}
		var result = invoke(callback, args, null);
		return result;
	}

	/** Internal gameplay consumers retain raw values and quiet missing hooks. */
	public function callValue(callback:String, ?args:Array<Dynamic>, ?receiver:Dynamic):Dynamic {
		var result = invoke(callback, args, receiver);
		return result == null ? null : result.returnValue;
	}

	/** Source extraVars mutates the caller map with this and restores absent
	 * previous variables as null entries rather than removing those keys. */
	public function executeFunc(callback:String, ?parameters:Array<Dynamic>, ?receiver:Dynamic,
		?extraVars:Map<String, Dynamic>):Dynamic {
		if (extraVars == null) extraVars = [];
		if (!exists(callback)) return null;
		var method = get(callback);
		if (!Reflect.isFunction(method)) return null;
		if (receiver != null) extraVars.set('this', receiver);
		var previous:Map<String, Dynamic> = [];
		for (key in extraVars.keys()) {previous.set(key, get(key)); set(key, extraVars.get(key));}
		var result:Dynamic = null;
		try result = interp.callCallback(method, parameters == null ? noArguments : parameters)
		catch (error:Dynamic) report(name, callback, error);
		for (key in previous.keys()) set(key, previous.get(key));
		return result;
	}

	public function exists(callback:String):Bool {
		return !released && interp != null && interp.variables.exists(callback);
	}

	/** Callback errors stay attributable and do not disable subsequent calls.
	 * `receiver` temporarily supplies the source executeFunc `this` binding. */
	function invoke(callback:String, ?args:Array<Dynamic>, ?receiver:Dynamic):IrisCall {
		if (!exists(callback)) return null;
		var receiverBound = receiver != null;
		var hadPreviousThis = receiverBound && interp.variables.exists('this');
		var previousThis:Dynamic = hadPreviousThis ? interp.variables.get('this') : null;
		try {
			var method = interp.variables.get(callback);
			if (method == null || !Reflect.isFunction(method))
				throw 'Callback is not a function: ' + callback;
			if (receiverBound) interp.variables.set('this', receiver);
			var result = interp.callCallback(method, args == null ? noArguments : args);
			if (receiverBound) {
				if (hadPreviousThis) interp.variables.set('this', previousThis);
				else interp.variables.remove('this');
			}
			return {funName:callback, signature:method, returnValue:result};
		} catch (error:Dynamic) {
			if (receiverBound) {
				if (hadPreviousThis) interp.variables.set('this', previousThis);
				else interp.variables.remove('this');
			}
			report(name, callback, error);
			return null;
		}
	}

	/** onDestroy belongs to the group's clear/call contract, not this release. */
	public function destroy():Void {
		if (released) return;
		released = true;
		if (sourceInstances != null) sourceInstances.remove(name);
		sourceInstances = null;
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
