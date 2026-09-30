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

/** Per-transition HScript host. The interpreter is short lived, while the
	CodenameTransitionScope keeps source-declared top-level static variables
	(owner and script scoped) across the outgoing and incoming transition pair.
*/
class CodenameMusicBeatTransitionRuntime {
	final host:CodenameMusicBeatTransition;
	final ownerRoot:String;
	final scriptPath:String;
	final ownerLabel:String;
	var resolvedScriptPath:String;
	var interp:CodenameScriptInterp;
	var owned:Array<FlxBasic> = [];
	var staticNames:Array<String> = [];
	var failed:Map<String, Bool> = new Map();
	var initialized:Bool = false;
	var createdSuccessfully:Bool = false;
	var released:Bool = false;

	public function new(host:CodenameMusicBeatTransition, ownerRoot:String, scriptPath:String) {
		this.host = host;
		this.ownerRoot = ownerRoot;
		this.scriptPath = scriptPath;
		ownerLabel = scriptPath;
	}

	public function create(event:CodenameMusicBeatTransitionEvent):Bool {
		if (initialized || released) return false;
		initialized = true;
		if (!CodenameMusicBeatTransition.canRunOwner(ownerRoot)) {
			trace('[codename-transition] ' + ownerLabel + ' ignored because its owner is inactive.');
			return false;
		}
		#if sys
		// Codename selectors commonly omit .hx, while the installed owner keeps
		// the authored filename. Resolve the same path the importer followed.
		var requestedPath = scriptPath;
		if (requestedPath != null && haxe.io.Path.extension(requestedPath) == '')
			requestedPath += '.hx';
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, requestedPath);
		if (resolution.relative == null) {
			trace('[codename-transition] ' + ownerLabel + ' script is unavailable (' + resolution.status + ').');
			return false;
		}
		resolvedScriptPath = resolution.relative;
		var fullPath = Path.join([ownerRoot, resolution.relative]);
		if (!FileSystem.exists(fullPath) || FileSystem.isDirectory(fullPath)) {
			trace('[codename-transition] ' + ownerLabel + ' script is missing: ' + resolution.relative);
			return false;
		}
		var source:String;
		try source = FNFAssets.getText(fullPath) catch (error:Dynamic) {
			trace('[codename-transition] Could not read ' + resolution.relative + ': ' + Std.string(error));
			return false;
		}

		var paths = new CodenamePaths(ownerRoot);
		interp = new CodenameScriptInterp(paths,
			new CodenameFlxGFacade(hostCameras(host), ownerRoot),
			function(name:String):Dynamic return CodenameModBindings.customShader(paths, name));
		interp.flxG.stateSwitch = function(target:Dynamic):Bool
			return CodenameModRuntime.switchTarget(ownerRoot, target);
		var bindings = CodenameModBindings.create(ownerRoot, paths, interp, host);
		bindings.set('CoolUtil', transitionCoolUtil(paths));
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
		interp.variables.set('CoolUtil', transitionCoolUtil(paths));
		interp.variables.set('game', new CodenameModPlayStateFacade(PlayState.instance));
		interp.variables.set('currentState', host);
		interp.variables.set('currentMenuState', host);
		interp.variables.set('state', host);
		// The native host retains a null newState for callback-based FlxG
		// switching. Expose the concrete destination captured by the owner scope
		// to donor source code through the expected field name.
		interp.variables.set('newState', host.scriptNewState);
		interp.variables.set('parentDisabler', host.parentDisabler);
		staticNames = declaredStaticVariables(source);
		interp.retainModuleGlobals(staticNames);
		bindSceneApi();
		try {
			if (RuntimeSmokeHarness.enabled()) RuntimeSmokeHarness.markStep('transition-create:' + resolvedScriptPath);
			CodenameTransitionScope.pushExecutingTransition(ownerRoot);
			try interp.execute(parsed.program) catch (error:Dynamic) {
				CodenameTransitionScope.popExecutingTransition(ownerRoot);
				throw error;
			}
			CodenameTransitionScope.popExecutingTransition(ownerRoot);
			CodenameTransitionScope.restoreStaticVariables(ownerRoot, resolvedScriptPath,
				staticNames, interp.variables);
			if (!call('create', [event])) {
				destroy();
				return false;
			}
			createdSuccessfully = true;
			// Keep an in-progress outgoing transition visible to an incoming
			// lifecycle half when the user resumes before its last timer fires.
			captureStaticVariables();
			if (RuntimeSmokeHarness.enabled()) RuntimeSmokeHarness.markStep('transition-created:'
				+ resolvedScriptPath + ':cancelled=' + Std.string(event != null && event.cancelled));
			return event != null && event.cancelled;
		} catch (error:Dynamic) {
			trace('[codename-transition-error] ' + resolution.relative + ': ' + Std.string(error));
			destroy();
			return false;
		}
		#else
		trace('[codename-transition] Imported Codename transitions need a filesystem-backed runtime.');
		return false;
		#end
	}

	public function postCreate(event:CodenameMusicBeatTransitionEvent):Void call('postCreate', [event]);
	public function update(elapsed:Float):Void call('update', [elapsed]);
	public function postUpdate(elapsed:Float):Void call('postUpdate', [elapsed]);
	public function skip(event:CodenameMusicBeatTransitionEvent):Bool return call('onSkip', [event]);
	public function finish(event:CodenameMusicBeatTransitionEvent):Bool return call('onFinish', [event]);
	public function postFinish():Void call('onPostFinish', []);
	public function resize(event:CodenameMusicBeatTransitionEvent):Void call('onResize', [event]);
	public function debugStatus():String {
		if (interp == null) return 'released';
		var stickers:Dynamic = interp.variables.get('lastStickers');
		var group:Dynamic = interp.variables.get('grpStickers');
		var manager:Dynamic = interp.variables.get('timerManager');
		var members:Dynamic = group == null ? null : Reflect.field(group, 'members');
		var timers:Dynamic = manager == null ? null : Reflect.field(manager, '_timers');
		return 'stickers=' + (Std.isOfType(stickers, Array) ? (cast stickers:Array<Dynamic>).length : -1)
			+ ':sprites=' + (Std.isOfType(members, Array) ? (cast members:Array<Dynamic>).length : -1)
			+ ':timers=' + (Std.isOfType(timers, Array) ? (cast timers:Array<Dynamic>).length : -1);
	}

	/** The incoming half may be created before Flixel destroys the outgoing
		closed substate. Publish its source static values during the handoff. */
	public function captureStaticVariables():Void {
		if (interp != null && resolvedScriptPath != null)
			CodenameTransitionScope.captureStaticVariables(ownerRoot, resolvedScriptPath,
				staticNames, interp.variables);
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
				host.remove(cast value, splice);
			return value;
		});
		interp.variables.set('openSubState', function(value:Dynamic):Dynamic {
			if (Std.isOfType(value, FlxSubState)) host.openSubState(cast value);
			else trace('[codename-transition-api] openSubState requires a native FlxSubState');
			return value;
		});
		interp.variables.set('closeSubState', function():Void host.closeSubState());
		interp.variables.set('close', function():Void host.close());
		interp.variables.set('startTransition', function(target:Dynamic):Bool
			return CodenameMusicBeatTransition.openForOwner(ownerRoot, target, true, null));
	}

	function place(value:Dynamic, index:Null<Int>):Dynamic {
		if (!Std.isOfType(value, FlxBasic)) {
			trace('[codename-transition-api] add/insert requires a FlxBasic in ' + scriptPath);
			return value;
		}
		var basic:FlxBasic = cast value;
		if (owned.indexOf(basic) < 0) owned.push(basic);
		interp.claimSceneObject(basic);
		if (index == null) host.add(basic) else host.insert(index, basic);
		return value;
	}

	function call(name:String, args:Array<Dynamic>):Bool {
		if (interp == null || failed.exists(name) || !interp.variables.exists(name)) return interp != null;
		var callback:Dynamic = interp.variables.get(name);
		if (callback == null) return true;
		var succeeded = true;
		CodenameTransitionScope.pushExecutingTransition(ownerRoot);
		try {
			switch (args.length) {
				case 0: callback();
				case 1: callback(args[0]);
				case 2: callback(args[0], args[1]);
				case 3: callback(args[0], args[1], args[2]);
				default: throw 'unsupported callback arity';
			}
		} catch (error:Dynamic) {
			failed.set(name, true);
			trace('[codename-transition-script-error] ' + scriptPath + '.' + name + ': ' + Std.string(error));
			if (RuntimeSmokeHarness.enabled()) RuntimeSmokeHarness.markStep('transition-error:'
				+ scriptPath + '.' + name + ':' + Std.string(error));
			succeeded = false;
		}
		CodenameTransitionScope.popExecutingTransition(ownerRoot);
		return succeeded;
	}

	public function destroy():Void {
		if (released) return;
		released = true;
		if (interp == null) return;
		call('destroy', []);
		if (createdSuccessfully) captureStaticVariables();
		for (object in owned.copy()) {
			if (object == null) continue;
			try {
				if (host.members != null && host.members.indexOf(object) >= 0)
					host.remove(object, true);
				object.destroy();
			} catch (_:Dynamic) {}
		}
		owned.resize(0);
		interp.release();
		interp = null;
	}

	static function declaredStaticVariables(source:String):Array<String> {
		var result:Array<String> = [];
		var declaration = new EReg('(?m)^\\s*(?:(?:public|private)\\s+)?static\\s+var\\s+([A-Za-z_][A-Za-z0-9_]*)', 'g');
		var cursor = 0;
		while (source != null && declaration.matchSub(source, cursor)) {
			var name = declaration.matched(1);
			if (result.indexOf(name) < 0) result.push(name);
			var matched = declaration.matchedPos();
			cursor = matched.pos + matched.len;
		}
		return result;
	}

	static function transitionCoolUtil(paths:CodenamePaths):Dynamic {
		var base = CodenameModBindings.coolUtil(paths);
		var animatedCount = 0;
		return {
			fpsLerp: Reflect.field(base, 'fpsLerp'),
			quantize: Reflect.field(base, 'quantize'),
			playMenuSFX: Reflect.field(base, 'playMenuSFX'),
			playMenuSong: Reflect.field(base, 'playMenuSong'),
			playMusic: Reflect.field(base, 'playMusic'),
			loadAnimatedGraphic: function(sprite:Dynamic, graphic:Dynamic):Dynamic {
				var loaded = Reflect.callMethod(base, Reflect.field(base, 'loadAnimatedGraphic'), [sprite, graphic]);
				if (RuntimeSmokeHarness.enabled() && animatedCount++ < 4)
					RuntimeSmokeHarness.markStep('transition-graphic-width:' + Std.string(Reflect.field(sprite, 'frameWidth')));
				return loaded;
			}
		};
	}
}
