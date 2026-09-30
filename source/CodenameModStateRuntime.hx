package;

import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxSubState;
import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

/** Owner-scoped lifecycle executor for imported Codename state scripts. */
class CodenameModStateRuntime {
	final host:CodenameImportedState;
	final ownerRoot:String;
	final scriptPath:String;
	var interp:CodenameScriptInterp;
	var owned:Array<FlxBasic> = [];
	var failed:Map<String, Bool> = new Map();
	var created:Bool = false;

	public function new(host:CodenameImportedState, ownerRoot:String, scriptPath:String) {
		this.host = host;
		this.ownerRoot = ownerRoot;
		this.scriptPath = scriptPath;
	}

	public function create():Void {
		if (created) return;
		created = true;
		if (!CodenameModRuntime.isActiveOwner(ownerRoot)) {
			host.showRuntimeDiagnostic('This state is no longer owned by the active imported mod.');
			return;
		}
		#if sys
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, scriptPath);
		if (resolution.relative == null) {
			host.showRuntimeDiagnostic('The installed state file could not be resolved safely (' + resolution.status + ').');
			return;
		}
		var fullPath = Path.join([ownerRoot, resolution.relative]);
		if (!FileSystem.exists(fullPath) || FileSystem.isDirectory(fullPath)) {
			host.showRuntimeDiagnostic('The installed state file is missing.');
			return;
		}
		var source:String;
		try source = FNFAssets.getText(fullPath) catch (error:Dynamic) {
			host.showRuntimeDiagnostic('Could not read the installed state script: ' + Std.string(error));
			return;
		}
		var paths = new CodenamePaths(ownerRoot);
		interp = new CodenameScriptInterp(paths, new CodenameFlxGFacade([FlxG.camera], ownerRoot),
			function(name:String):Dynamic return CodenameModBindings.customShader(paths, name));
		if (RuntimeSmokeHarness.enabled()) {
			interp.runtimeSmokeOwnerRoot = ownerRoot;
			interp.runtimeSmokeScriptPath = resolution.relative;
		}
		interp.flxG.stateSwitch = function(target:Dynamic):Bool return switchState(target);
		var bindings = CodenameModBindings.create(ownerRoot, paths, interp, host);
		CodenameModBindings.seed(interp, ownerRoot, host, paths);
		for (name in bindings.keys())
			interp.variables.set(name.substr(name.lastIndexOf('.') + 1), bindings.get(name));
		bindSceneApi();
		var classLoad = CodenameScriptClassLoader.load(ownerRoot,
			CodenameScriptParser.importPaths(source), bindings, interp.variables);
		interp.bindScriptClassScope(classLoad.scope);
		for (name in classLoad.imports.keys()) {
			bindings.set(name, classLoad.imports.get(name));
			interp.variables.set(name.substr(name.lastIndexOf('.') + 1), classLoad.imports.get(name));
		}
		interp.protectImportAliases(bindings);
		for (diagnostic in classLoad.diagnostics)
			trace('[codename-class-module] ' + diagnostic);
		for (diagnostic in classLoad.sourceUseDiagnostics)
			trace(diagnostic);
		var parsed = CodenameScriptParser.prepare(source, bindings, resolution.relative);
		CodenameScriptParser.reportRecoverableDiagnostics(parsed, resolution.relative);
		if (parsed.program == null || CodenameScriptParser.hasFatalDiagnostics(parsed)) {
			var messages:Array<String> = [];
			for (diagnostic in parsed.diagnostics) {
				messages.push(diagnostic.code + ' line ' + diagnostic.line + ': ' + diagnostic.message);
				trace('[codename-script-' + diagnostic.code + '] ' + resolution.relative + ':'
					+ diagnostic.line + ': ' + diagnostic.message);
			}
			interp.release();
			interp = null;
			host.showRuntimeDiagnostic(messages.join('\n'));
			return;
		}
		try {
			executeModule(parsed.program);
			call('start', []);
			call('create', []);
			call('createPost', []);
			call('postCreate', []);
		} catch (error:Dynamic) {
			host.showRuntimeDiagnostic('Script initialization failed: ' + Std.string(error));
			destroy();
		}
		#else
		host.showRuntimeDiagnostic('Imported Codename states require a filesystem-backed runtime.');
		#end
	}

	function bindSceneApi():Void {
		interp.variables.set('add', function(value:Dynamic):Dynamic return place(value, null));
		interp.variables.set('insert', function(index:Int, value:Dynamic):Dynamic return place(value, index));
		interp.variables.set('remove', function(value:Dynamic):Dynamic {
			var basic = interp.nativeFlxBasic(value);
			if (basic != null && owned.indexOf(basic) >= 0)
				host.remove(basic, true);
			return value;
		});
		interp.variables.set('addSprite', function(value:Dynamic, ?_position:Int):Dynamic return place(value, null));
		interp.variables.set('removeSprite', interp.variables.get('remove'));
		interp.variables.set('openSubState', function(value:Dynamic):Dynamic {
			if (Std.isOfType(value, FlxSubState)) host.openSubState(cast value);
			else trace('[codename-state-api] openSubState requires a native FlxSubState');
			return value;
		});
		interp.variables.set('closeSubState', function():Void host.closeSubState());
		interp.variables.set('close', function():Void host.closeSubState());
		interp.variables.set('startTransition', function(target:Dynamic):Bool return switchState(target));
		interp.variables.set('resetState', function():Void FlxG.resetState());
	}

	/** Attach the selected owner module and current lifecycle callback to null
	 * access diagnostics emitted while imported HScript executes. */
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

	function executeModule(program:Dynamic):Void {
		withDiagnosticContext('module', function():Void interp.execute(program));
	}

	function place(value:Dynamic, index:Null<Int>):Dynamic {
		var basic = interp.nativeFlxBasic(value);
		if (basic == null) {
			trace('[codename-state-api] add/insert requires a native FlxBasic or a class proxy from this owner in ' + scriptPath);
			return value;
		}
		if (owned.indexOf(basic) < 0) owned.push(basic);
		interp.claimSceneObject(value);
		if (index == null) host.add(basic); else host.insert(index, basic);
		return value;
	}

	function switchState(target:Dynamic):Bool {
		CodenameStateSmokeTrace.mark('state-switch-request', ownerRoot, scriptPath,
			[CodenameStateSmokeTrace.field('target', CodenameStateSmokeTrace.stateName(target))]);
		if (target == null) {
			trace('[codename-mod-state-switch] Refused a null state target.');
			CodenameStateSmokeTrace.mark('state-switch-refused', ownerRoot, scriptPath,
				[CodenameStateSmokeTrace.field('reason', 'null-target')]);
			return false;
		}
		// Keep validation, target ownership transfer, and custom-transition
		// destination capture on the same owner-scoped switch path used by menus.
		if (!CodenameModRuntime.switchTarget(ownerRoot, target)) {
			CodenameStateSmokeTrace.mark('state-switch-refused', ownerRoot, scriptPath,
				[CodenameStateSmokeTrace.field('reason', 'owner-switch-validation')]);
			return false;
		}
		CodenameStateSmokeTrace.mark('state-switch-accepted', ownerRoot, scriptPath,
			[CodenameStateSmokeTrace.field('target', CodenameStateSmokeTrace.stateName(target))]);
		return true;
	}

	public function update(elapsed:Float):Void {
		if (interp == null) return;
		interp.variables.set('curStep', host.hxcCurrentStep);
		interp.variables.set('curBeat', host.hxcCurrentBeat);
		call('update', [elapsed]);
	}

	public function postUpdate(elapsed:Float):Void {
		if (interp == null) return;
		interp.variables.set('curStep', host.hxcCurrentStep);
		interp.variables.set('curBeat', host.hxcCurrentBeat);
		call('postUpdate', [elapsed]);
	}

	public function step(step:Int):Void {
		if (interp == null) return;
		interp.variables.set('curStep', step);
		interp.variables.set('curBeat', host.hxcCurrentBeat);
		call('stepHit', [step]);
	}

	public function beat(beat:Int):Void {
		if (interp == null) return;
		interp.variables.set('curStep', host.hxcCurrentStep);
		interp.variables.set('curBeat', beat);
		call('beatHit', [beat]);
	}

	function call(name:String, args:Array<Dynamic>):Bool {
		if (interp == null || failed.exists(name) || !interp.variables.exists(name)) return interp != null;
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
			failed.set(name, true);
			trace('[codename-state-script-error] ' + scriptPath + '.' + name + ': ' + Std.string(error));
			return false;
		}
	}

	public function destroy():Void {
		if (interp == null) return;
		call('destroy', []);
		for (object in owned.copy()) {
			if (object == null) continue;
			try {
				if (host.members.indexOf(object) >= 0) host.remove(object, true);
				object.destroy();
			} catch (_:Dynamic) {}
		}
		owned.resize(0);
		interp.release();
		interp = null;
	}
}
