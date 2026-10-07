package;

import flixel.FlxG;
import flixel.FlxBasic;
import flixel.addons.ui.FlxUIState;

typedef NightmareVisionMusicBeatTiming = {
	var step:Int;
	var decimalStep:Float;
}

/** Owner-captured services needed by native states that execute NV state scripts. */
typedef NightmareVisionMusicBeatStateHost = {
	var session:Dynamic;
	var createStateFactory:String->(Void->flixel.FlxState);
	var createScriptGroup:Dynamic->NightmareVisionScriptGroup;
	var createStateScript:(name:String, parent:Dynamic, group:NightmareVisionScriptGroup)->NightmareVisionStateScriptLoadResult;
	var failedScriptState:String->Void;
	var report:(name:String, callback:String, error:Dynamic)->Void;
	var callPlugins:(event:String, args:Array<Dynamic>)->Dynamic;
	var getControls:Void->Dynamic;
	var timing:Void->NightmareVisionMusicBeatTiming;
	var sectionBeats:Int->Float;
	var sectionCount:Void->Int;
	var hasSection:Int->Bool;
	var hasSong:Void->Bool;
	var openTransition:(state:Dynamic, incoming:Bool, ?complete:Void->Void)->Bool;
	var releaseStateResources:Dynamic->Void;
	@:optional var cancelMenuVocals:Void->Void;
	@:optional var getTitleInitialized:Void->Bool;
	@:optional var setTitleInitialized:Bool->Void;
	@:optional var getTitleClosedState:Void->Bool;
	@:optional var setTitleClosedState:Bool->Void;
}

/**
	The host-native base for states adapted from Nightmare Vision's
	funking.backend.MusicBeatState. Script and session ownership remain scoped
	to the captured state host supplied by the source family session.
*/
@:keep
class NightmareVisionMusicBeatState extends FlxUIState {
	public var scripted:Bool = false;
	public var scriptName:String = '';
	public var scriptGroup(default, null):NightmareVisionScriptGroup;
	public var curSection:Int = 0;
	public var curStep:Int = 0;
	public var curBeat:Int = 0;
	public var controls(get, never):Dynamic;

	public var sourceHost(default, null):NightmareVisionMusicBeatStateHost;
	public var sourceSession(default, null):Dynamic;

	var stepsToDo:Int = 0;
	var curDecStep:Float = 0;
	var curDecBeat:Float = 0;
	var stateResourcesReleased:Bool = false;
	var sourceDestroyed:Bool = false;

	public function new(host:NightmareVisionMusicBeatStateHost) {
		super();
		// Source Init owns transition selection. Do not inherit a host default.
		transIn = null;
		transOut = null;
		if (host == null) throw '[nightmare-vision-state] Missing captured source host';
		if (host.createScriptGroup == null || host.createStateScript == null
			|| host.failedScriptState == null || host.report == null
			|| host.callPlugins == null || host.getControls == null || host.timing == null
			|| host.sectionBeats == null || host.sectionCount == null || host.hasSection == null
			|| host.hasSong == null || host.openTransition == null
			|| host.releaseStateResources == null)
			throw '[nightmare-vision-state] Incomplete captured source host';
		sourceHost = host;
		sourceSession = host.session;
		scriptGroup = host.createScriptGroup(this);
		if (scriptGroup == null) throw '[nightmare-vision-state] Host did not create a script group';
		scriptGroup.parent = this;
	}

	function get_controls():Dynamic return sourceHost.getControls();

	/**
		Load and parent one state script. The host resolves the source path and
		creates/configures the interpreter under this state's captured owner.
		The host must not call onLoad; this method owns that lifecycle boundary.
	*/
	public function initStateScript(?requestedName:String, callOnLoad:Bool = true):Bool {
		var selectedName = requestedName;
		if (selectedName == null) {
			var type = Type.getClass(this);
			var fullName = type == null ? null : Type.getClassName(type);
			selectedName = fullName == null ? '???' : fullName.split('.').pop();
		}
		var result = sourceHost.createStateScript(selectedName, this, scriptGroup);
		switch (result) {
			case AlreadyLoaded(_):
				// The donor checks the resolved file path, not the module's source
				// name, and returns before changing scriptName or calling onLoad.
				return true;
			case Missing(_):
				scriptName = selectedName;
				if (callOnLoad) scriptGroup.call('onLoad', []);
				return scripted;
			case ParseFailed(_, handle):
				scriptName = selectedName;
				destroyUnownedScript(handle, selectedName);
				return false;
			case Loaded(_, _, handle):
				scriptName = selectedName;
				if (handle == null || handle.released || !handle.initialized || handle.parsingFailed()) {
					destroyUnownedScript(handle, selectedName);
					return false;
				}
				scriptGroup.parent = this;
				if (scriptGroup.members.indexOf(handle) < 0 && !scriptGroup.addScript(handle))
					destroyUnownedScript(handle, selectedName);
				// The source sets this after finding a valid file even if group
				// registration rejects a duplicate name.
				scripted = true;
				if (callOnLoad) scriptGroup.call('onLoad', []);
				return scripted;
		}
	}

	function destroyUnownedScript(handle:NightmareVisionScriptModule, name:String):Void {
		if (handle == null || handle.released) return;
		try handle.destroy() catch (error:Dynamic) sourceHost.report(name, 'destroy', error);
	}

	/** Source MusicBeatState opens its outgoing transition before plugin create hooks. */
	public override function create():Void {
		super.create();
		sourceHost.openTransition(this, true, null);
		sourceHost.callPlugins('onStateCreate', []);
	}

	/** Source update timing and step events run before onUpdate and child updates. */
	public override function update(elapsed:Float):Void {
		var oldStep = curStep;
		var timing = sourceHost.timing();
		curDecStep = timing.decimalStep;
		curStep = timing.step;
		updateBeat();

		if (curStep > oldStep) {
			for (step in oldStep...curStep) {
				curStep = step + 1;
				updateBeat();
				if (curStep >= 0) stepHit();
			}
			if (sourceHost.hasSong()) updateSection();
		} else if (sourceHost.hasSong()) {
			rollbackSection();
		}

		// STOP and HALT affect the ScriptGroup broadcast only. The donor ignores
		// these return values here and always continues the native update.
		scriptGroup.call('onUpdate', [elapsed]);
		super.update(elapsed);
	}

	function updateBeat():Void {
		curBeat = Math.floor(curStep / 4);
		curDecBeat = curDecStep / 4;
	}

	public function stepHit():Void {
		if (curStep % 4 == 0) beatHit();
		scriptGroup.call('onStepHit', []);
		sourceHost.callPlugins('onStepHit', []);
	}

	public function beatHit():Void {
		scriptGroup.call('onBeatHit', []);
		sourceHost.callPlugins('onBeatHit', []);
	}

	public function sectionHit():Void {
		scriptGroup.call('onSectionHit', []);
		sourceHost.callPlugins('onSectionHit', []);
	}

	function updateSection():Void {
		if (stepsToDo < 1) stepsToDo = Math.round(getBeatsOnSection() * 4);
		while (curStep >= stepsToDo) {
			curSection++;
			stepsToDo += Math.round(getBeatsOnSection() * 4);
			sectionHit();
		}
	}

	function rollbackSection():Void {
		if (curStep < 0) return;
		var lastSection = curSection;
		curSection = 0;
		stepsToDo = 0;
		for (index in 0...sourceHost.sectionCount()) {
			if (!sourceHost.hasSection(index)) continue;
			stepsToDo += Math.round(getBeatsOnSection() * 4);
			if (stepsToDo > curStep) break;
			curSection++;
		}
		if (curSection > lastSection) sectionHit();
	}

	function getBeatsOnSection():Float return sourceHost.sectionBeats(curSection);

	/** Sort a source FlxTypedGroup using the owner-aware zIndex view. */
	@:keep public function refreshZ(?group:Dynamic):Void {
		var target:Dynamic = group == null ? FlxG.state : group;
		if (target == null) return;
		var sort = Reflect.field(target, 'sort');
		if (!Reflect.isFunction(sort))
			throw '[nightmare-vision-state] refreshZ target has no sort method';
		Reflect.callMethod(target, sort, [function(order:Int, a:FlxBasic, b:FlxBasic):Int {
			return flixel.util.FlxSort.byValues(order,
				HxcCompatRuntime.getZIndex(a), HxcCompatRuntime.getZIndex(b));
		}, flixel.util.FlxSort.ASCENDING]);
	}

	/** Source MusicBeatState only broadcasts close, before closing the substate. */
	public override function closeSubState():Void {
		scriptGroup.call('onCloseSubState', []);
		super.closeSubState();
	}

	/**
		Source outro cancels active menu music fades before asking its source
		transition adapter to complete the switch. A false result delegates to
		FlxState's immediate completion path.
	*/
	public override function startOutro(onOutroComplete:Void->Void):Void {
		if (FlxG.sound != null && FlxG.sound.music != null) {
			if (FlxG.sound.music.fadeTween != null) FlxG.sound.music.fadeTween.cancel();
			FlxG.sound.music.onComplete = null;
		}
		if (sourceHost.cancelMenuVocals != null) sourceHost.cancelMenuVocals();
		if (sourceHost.openTransition(this, false, onOutroComplete)) return;
		super.startOutro(onOutroComplete);
	}

	/** State script cleanup never releases the family session retained by the factory. */
	public override function destroy():Void {
		if (sourceDestroyed) return;
		sourceDestroyed = true;
		var firstError:Dynamic = null;
		try scriptGroup.call('onDestroy', []) catch (error:Dynamic) firstError = error;
		try scriptGroup.destroy() catch (error:Dynamic) if (firstError == null) firstError = error;
		if (!stateResourcesReleased) {
			stateResourcesReleased = true;
			try sourceHost.releaseStateResources(this) catch (error:Dynamic) if (firstError == null) firstError = error;
		}
		try super.destroy() catch (error:Dynamic) if (firstError == null) firstError = error;
		if (firstError != null) throw firstError;
	}
}
