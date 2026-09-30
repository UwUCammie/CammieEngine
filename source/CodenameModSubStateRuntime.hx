package;

import flixel.FlxBasic;
import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSubState;
import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
#if cpp
import hxvlc.flixel.FlxVideoSprite;
#end

/** Owner-local Codename lifecycle for scripts hosted by native substates.
	Codename pause/game-over scripts use `create(event)` and `update(elapsed)`;
	the host remains the owner of its native display list and this runtime owns
	only interpreter resources and objects explicitly added through its bridge.
*/
class CodenameModSubStateRuntime {
	final host:FlxSubState;
	final ownerRoot:String;
	final scriptPath:String;
	final ownerLabel:String;
	final parentDisabler:Dynamic;
	var interp:CodenameScriptInterp;
	var owned:Array<FlxBasic> = [];
	var failed:Map<String, Bool> = new Map();
	var initialized:Bool = false;
	var released:Bool = false;

	public function new(host:FlxSubState, ownerRoot:String, scriptPath:String,
		ownerLabel:String, ?parentDisabler:Dynamic) {
		this.host = host;
		this.ownerRoot = ownerRoot;
		this.scriptPath = scriptPath;
		this.ownerLabel = ownerLabel;
		this.parentDisabler = parentDisabler;
	}

	public static function hasScript(ownerRoot:String, scriptPath:String):Bool {
		if (!CodenameModRuntime.isActiveOwner(ownerRoot)) return false;
		#if sys
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, scriptPath);
		return resolution.relative != null && FileSystem.exists(Path.join([ownerRoot, resolution.relative]))
			&& !FileSystem.isDirectory(Path.join([ownerRoot, resolution.relative]));
		#else
		return false;
		#end
	}

	/** Load the same-owner module and pass Codename's mutable creation event. */
	public function create(event:Dynamic):Bool {
		if (initialized || released) return false;
		initialized = true;
		if (!CodenameModRuntime.isActiveOwner(ownerRoot)) {
			trace('[codename-substate] ' + ownerLabel + ' ignored because its owner is inactive.');
			return false;
		}
		#if sys
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, scriptPath);
		if (resolution.relative == null) {
			trace('[codename-substate] ' + ownerLabel + ' script is unavailable (' + resolution.status + ').');
			return false;
		}
		var fullPath = Path.join([ownerRoot, resolution.relative]);
		if (!FileSystem.exists(fullPath) || FileSystem.isDirectory(fullPath)) {
			trace('[codename-substate] ' + ownerLabel + ' script is missing: ' + resolution.relative);
			return false;
		}
		var source:String;
		try source = FNFAssets.getText(fullPath) catch (error:Dynamic) {
			trace('[codename-substate] Could not read ' + resolution.relative + ': ' + Std.string(error));
			return false;
		}

		var cameras = hostCameras(host);
		var paths = new CodenamePaths(ownerRoot);
		interp = new CodenameScriptInterp(paths, new CodenameFlxGFacade(cameras, ownerRoot),
			function(name:String):Dynamic return CodenameModBindings.customShader(paths, name));
		interp.flxG.stateSwitch = function(target:Dynamic):Bool
			return CodenameModRuntime.switchTarget(ownerRoot, target);
		var bindings = CodenameModBindings.create(ownerRoot, paths, interp, host);
		#if cpp
		bindings.set('hxvlc.flixel.FlxVideoSprite', FlxVideoSprite);
		#else
		bindings.set('hxvlc.flixel.FlxVideoSprite', CodenameUnavailableApi);
		#end
		var parsed = CodenameScriptParser.prepare(source, bindings, resolution.relative);
		CodenameScriptParser.reportRecoverableDiagnostics(parsed, resolution.relative);
		if (parsed.program == null || CodenameScriptParser.hasFatalDiagnostics(parsed)) {
			for (diagnostic in parsed.diagnostics)
				trace('[codename-script-' + diagnostic.code + '] ' + resolution.relative + ':'
					+ diagnostic.line + ': ' + diagnostic.message);
			interp.release();
			interp = null;
			return false;
		}
		CodenameModBindings.seed(interp, ownerRoot, host, paths);
		for (name in bindings.keys())
			interp.variables.set(name.substr(name.lastIndexOf('.') + 1), bindings.get(name));
		interp.protectImportAliases(bindings);
		interp.variables.set('game', new CodenameModPlayStateFacade(PlayState.instance));
		if (parentDisabler != null)
			interp.variables.set('parentDisabler', parentDisabler);
		bindSceneApi();
		try {
			interp.execute(parsed.program);
			call('create', [event]);
			call('postCreate', []);
			return event != null && (Reflect.field(event, 'cancelled') == true
				|| Reflect.field(event, 'canceled') == true);
		} catch (error:Dynamic) {
			trace('[codename-substate-error] ' + resolution.relative + ': ' + Std.string(error));
			destroy();
			return false;
		}
		#else
		trace('[codename-substate] Imported Codename substates require a filesystem-backed runtime.');
		return false;
		#end
	}

	static function hostCameras(host:FlxSubState):Array<FlxCamera> {
		var result:Array<FlxCamera> = [];
		function add(camera:Dynamic):Void
			if (Std.isOfType(camera, FlxCamera) && result.indexOf(cast camera) < 0)
				result.push(cast camera);
		add(FlxG.camera);
		var play = PlayState.instance;
		if (play != null) {
			add(play.camGame);
			add(play.camHUD);
			add(play.camOther);
		}
		if (host != null) {
			var stateCameras:Dynamic = host.cameras;
			if (Std.isOfType(stateCameras, Array))
				for (camera in (cast stateCameras:Array<Dynamic>)) add(camera);
		}
		return result;
	}

	function bindSceneApi():Void {
		interp.variables.set('add', function(value:Dynamic):Dynamic return place(value, null));
		interp.variables.set('insert', function(index:Int, value:Dynamic):Dynamic return place(value, index));
		interp.variables.set('remove', function(value:Dynamic, ?splice:Bool = false):Dynamic {
			if (Std.isOfType(value, FlxBasic) && owned.indexOf(cast value) >= 0)
				Reflect.callMethod(host, Reflect.field(host, 'remove'), [value, splice]);
			return value;
		});
		interp.variables.set('openSubState', function(value:Dynamic):Dynamic {
			if (Std.isOfType(value, FlxSubState)) host.openSubState(cast value);
			else trace('[codename-substate-api] openSubState requires a native FlxSubState');
			return value;
		});
		interp.variables.set('closeSubState', function():Void host.closeSubState());
		interp.variables.set('close', function():Void host.close());
		interp.variables.set('startTransition', function(target:Dynamic):Bool
			return CodenameModRuntime.switchTarget(ownerRoot, target));
	}

	function place(value:Dynamic, index:Null<Int>):Dynamic {
		if (!Std.isOfType(value, FlxBasic)) {
			trace('[codename-substate-api] add/insert requires a FlxBasic in ' + scriptPath);
			return value;
		}
		var basic:FlxBasic = cast value;
		if (owned.indexOf(basic) < 0) owned.push(basic);
		interp.claimSceneObject(basic);
		if (index == null)
			Reflect.callMethod(host, Reflect.field(host, 'add'), [basic]);
		else
			Reflect.callMethod(host, Reflect.field(host, 'insert'), [index, basic]);
		return value;
	}

	public function update(elapsed:Float):Void call('update', [elapsed]);

	function call(name:String, args:Array<Dynamic>):Bool {
		if (interp == null || failed.exists(name) || !interp.variables.exists(name)) return interp != null;
		var callback:Dynamic = interp.variables.get(name);
		if (callback == null) return true;
		try {
			switch (args.length) {
				case 0: callback();
				case 1: callback(args[0]);
				case 2: callback(args[0], args[1]);
				case 3: callback(args[0], args[1], args[2]);
				default: throw 'unsupported callback arity';
			}
			return true;
		} catch (error:Dynamic) {
			failed.set(name, true);
			trace('[codename-substate-script-error] ' + scriptPath + '.' + name + ': ' + Std.string(error));
			return false;
		}
	}

	public function destroy():Void {
		if (released) return;
		released = true;
		if (interp == null) return;
		call('destroy', []);
		for (object in owned.copy()) {
			if (object == null) continue;
			try {
				if (host.members != null && host.members.indexOf(object) >= 0)
					Reflect.callMethod(host, Reflect.field(host, 'remove'), [object, true]);
				object.destroy();
			} catch (_:Dynamic) {}
		}
		owned.resize(0);
		interp.release();
		interp = null;
	}
}
