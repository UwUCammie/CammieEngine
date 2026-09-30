package;

import haxe.io.Path;
import hscript.Interp;
import hscript.ParserEx;
import PluginManager.HscriptGlobals;

using StringTools;

/**
	Interpreter host shared by imported HXC states and substates.  It mirrors
	the existing PlayState HScript lifecycle, but keeps all state-local objects
	behind the wrapper passed as `currentState`.
*/
class HxcImportedRuntime {
	public var owner(default, null):Dynamic;
	public var entry(default, null):HxcStateFactory.HxcStateFactoryEntry;
	public var interp(default, null):Interp;
	public var created(default, null):Bool = false;
	public var failed(default, null):Bool = false;
	var owned:Array<Dynamic> = [];
	/** Callbacks which already threw once.  Their required state genuinely never
	 * materialized, so re-dispatching them every frame only burns time and would
	 * flood the log; the first failure keeps the full diagnostic. */
	var poisonedCallbacks:Map<String, Bool> = new Map();

	public function new(owner:Dynamic, entry:HxcStateFactory.HxcStateFactoryEntry) {
		this.owner = owner;
		this.entry = entry;
	}

	public function create():Void {
		if (created || failed || entry == null)
			return;
		try {
			var parser = new ParserEx();
			var source = EngineCompat.rewriteScopedAssetPaths(entry.generatedHscript);
			var program = parser.parseString(source);
			interp = PluginManager.createSimpleInterp();
			seed();
			interp.execute(program);
			created = true;
			call('start', [], true);
			call('createPost', [], true);
		} catch (error:Dynamic) {
			failed = true;
			trace('[hxc-state-runtime-error] ' + entry.path + ': ' + Std.string(error));
		}
	}

	public function update(elapsed:Float):Void {
		if (created && !failed)
			call('update', [elapsed], true);
	}

	public function step(step:Int):Void {
		if (!created || failed)
			return;
		setTiming(step, Std.int(step / 4));
		call('stepHit', [step], true);
	}

	public function beat(beat:Int):Void {
		if (!created || failed)
			return;
		setTiming(beat * 4, beat);
		call('beatHit', [beat], true);
	}

	public function destroy():Void {
		if (interp == null)
			return;
		if (created && !failed)
			call('destroy', [], true);
		try {
			interp.variables.clear();
		} catch (_:Dynamic) {}
		owned.resize(0);
		interp = null;
		owner = null;
		created = false;
	}

	function seed():Void {
		interp.variables.set('currentState', owner);
		interp.variables.set('state', owner);
		interp.variables.set('hxcState', owner);
		interp.variables.set('currentPlayState', owner);
		interp.variables.set('currentFreeplayState', null);
		interp.variables.set('AttractState', null);
		interp.variables.set('currentMenuState', null);
		interp.variables.set('hxcAssetRoot', entry.root == null ? '' : entry.root);
		interp.variables.set('PlayState', PlayState);
		interp.variables.set('SONG', PlayState.SONG);
		interp.variables.set('songData', PlayState.SONG);
		interp.variables.set('hscriptPath', Path.directory(entry.path) + '/');
		interp.variables.set('hxcPaths', HxcStateAssetScope.paths(entry.root));
		interp.variables.set('hxcAssets', HxcStateAssetScope.assets(entry.root));
		// HXC source which names FNFAssets directly receives the same scoped
		// surface; the donor cannot bypass the selected manifest through a second
		// global asset reader.
		interp.variables.set('FNFAssets', HxcStateAssetScope.assets(entry.root));
		interp.variables.set('hxcStateInit', function(name:Dynamic):Dynamic
			return HxcStateFactory.stateInit(entry.root, name));
		interp.variables.set('hxcSubStateInit', function(name:Dynamic):Dynamic
			return HxcStateFactory.subStateInit(entry.root, name));
		interp.variables.set('hxcStateFactory', function(name:Dynamic, ?args:Array<Dynamic>):Dynamic
			return HxcStateFactory.stateFactory(entry.root, name, args));
		interp.variables.set('hxcSwitchState', function(target:Dynamic):Bool
			return HxcStateFactory.switchStateScoped(entry.root, target));
		interp.variables.set('hxcStartExitState', function(target:Dynamic):Bool
			return HxcStateFactory.startExitState(entry.root, target));
		interp.variables.set('hxcOpenSubState', function(value:Dynamic):Bool
			return HxcStateFactory.openSubStateScoped(entry.root, owner, value));
		interp.variables.set('hxcOpenSubStateOn', function(host:Dynamic, value:Dynamic):Bool
			return HxcStateFactory.openSubStateScoped(entry.root, host, value));
		interp.variables.set('hxcBack', function():Bool
			return HxcStateFactory.back(owner));
		interp.variables.set('hxcResetState', function():Bool
			return HxcStateFactory.resetState());
		interp.variables.set('hxcGetModule', function(name:Dynamic):Dynamic
			return HxcFreeplayRuntime.moduleProxyForRoot(entry.root, name));
		interp.variables.set('onEvent', function(_name:Dynamic, _v1:Dynamic, _v2:Dynamic, _v3:Dynamic):Void {});
		interp.variables.set('add', function(value:Dynamic):Dynamic {
			owned.push(value);
			return ownerCall('add', [value]);
		});
		interp.variables.set('remove', function(value:Dynamic):Dynamic {
			owned.remove(value);
			return ownerCall('remove', [value]);
		});
		interp.variables.set('insert', function(position:Int, value:Dynamic):Dynamic {
			owned.push(value);
			return ownerCall('insert', [position, value]);
		});
		interp.variables.set('addSprite', function(value:Dynamic, ?_position:Int):Dynamic {
			owned.push(value);
			return ownerCall('add', [value]);
		});
		interp.variables.set('removeSprite', function(value:Dynamic):Dynamic {
			owned.remove(value);
			return ownerCall('remove', [value]);
		});
		interp.variables.set('openSubState', function(value:Dynamic):Dynamic
			return HxcStateFactory.openSubStateScoped(entry.root, owner, value));
		interp.variables.set('closeSubState', function():Dynamic
			return ownerCall('closeSubState', []));
		// Donor substates call their own `close()` (FlxSubState.close) to dismiss
		// themselves; without this seed the generated body dies on
		// EUnknownVariable(close) and the popup can never be dismissed.
		interp.variables.set('close', function():Dynamic
			return ownerCall('close', []));
		interp.variables.set('controls', PlayerSettings.player1.controls);
		interp.variables.set('curStep', 0);
		interp.variables.set('curBeat', 0);
		interp.variables.set('debugPrint', function(value:Dynamic):Void trace(value));
		interp.variables.set('soundPlaySafe', function(_path:Dynamic, ?_volume:Float = 1):Dynamic return null);
		interp.variables.set('preloadSound', function(_path:Dynamic):Dynamic return null);
		interp.variables.set('LoadingState', LoadingState);
		interp.variables.set('MainMenuState', MainMenuState);
		interp.variables.set('StoryMenuState', StoryMenuState);
		interp.variables.set('FreeplayState', FreeplayState);
		interp.variables.set('TitleState', TitleState);
		interp.variables.set('CreditsState', CreditsState);
		interp.variables.set('SaveDataState', SaveDataState);
		interp.variables.set('FlxG', HscriptGlobals);
		interp.variables.set('HxcStateFactory', HxcStateFactory);
	}

	function setTiming(step:Int, beat:Int):Void {
		if (interp == null)
			return;
		interp.variables.set('curStep', step);
		interp.variables.set('curBeat', beat);
	}

	function call(name:String, args:Array<Dynamic>, optional:Bool):Bool {
		if (interp == null || name == null || name == '')
			return false;
		var selected:String = null;
		for (candidate in EngineCompat.callbackNames(name))
			if (interp.variables.exists(candidate)) {
				selected = candidate;
				break;
			}
		if (selected == null)
			return false;
		var method:Dynamic = interp.variables.get(selected);
		if (method == null)
			return false;
		// A callback which threw once is skipped for the rest of this runtime's
		// life: whatever it needed genuinely never materialized, so the
		// per-frame dispatch must not retry it (silent per-frame spam and
		// repeated script breakage).  The first failure keeps one clear
		// diagnostic; recovery is a state reload, like the donor engine.
		if (poisonedCallbacks.exists(name))
			return false;
		var callArgs = EngineCompat.callbackArguments(name, selected, args, true);
		try {
			switch (callArgs.length) {
				case 0: method();
				case 1: method(callArgs[0]);
				case 2: method(callArgs[0], callArgs[1]);
				case 3: method(callArgs[0], callArgs[1], callArgs[2]);
				default: method(callArgs[0], callArgs[1], callArgs[2], callArgs[3]);
			}
			return true;
		} catch (error:Dynamic) {
			poisonedCallbacks.set(name, true);
			trace('[hxc-state-callback-error] ' + entry.path + ' .' + name + ': ' + Std.string(error)
				+ ' (this callback will be skipped until the state reloads)');
			return false;
		}
	}

	function ownerCall(name:String, args:Array<Dynamic>):Dynamic {
		if (owner == null)
			return null;
		try {
			var method = Reflect.field(owner, name);
			return method == null ? null : Reflect.callMethod(owner, method, args);
		} catch (error:Dynamic) {
			trace('[hxc-state-owner-call-error] ' + entry.path + ' .' + name + ': ' + Std.string(error));
			return null;
		}
	}
}
