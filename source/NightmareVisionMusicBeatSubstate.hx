package;

import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxSubState;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatStateHost;

/** Owner-captured services needed by source MusicBeatSubstate scripts. */
typedef NightmareVisionMusicBeatSubstateHost = {
	> NightmareVisionMusicBeatStateHost,
	var createSubstateScript:(prefix:String, name:String, parent:Dynamic,
		group:NightmareVisionScriptGroup)->NightmareVisionStateScriptLoadResult;
}

/** Native base for Nightmare Vision's MusicBeatSubstate lifecycle. */
@:keep
class NightmareVisionMusicBeatSubstate extends FlxSubState {
	public var scripted:Bool = false;
	public var scriptName:String = '';
	public var scriptPrefix:String = 'substates';
	public var scriptGroup(default, null):NightmareVisionScriptGroup;
	public var curSection:Int = 0;
	public var curStep:Int = 0;
	public var curBeat:Int = 0;
	public var controls(get, never):Dynamic;

	public var sourceHost(default, null):NightmareVisionMusicBeatSubstateHost;
	var curDecStep:Float = 0;
	@:keep var curDecBeat:Float = 0;
	var stepsToDo:Int = 0;
	var sourceDestroyed:Bool = false;

	public function new(host:NightmareVisionMusicBeatSubstateHost) {
		super();
		if (host == null || host.createScriptGroup == null || host.createSubstateScript == null
			|| host.getControls == null || host.timing == null || host.sectionBeats == null || host.sectionCount == null
			|| host.hasSection == null || host.hasSong == null || host.report == null)
			throw '[nightmare-vision-substate] Incomplete captured source host';
		sourceHost = host;
		scriptGroup = host.createScriptGroup(this);
		if (scriptGroup == null) throw '[nightmare-vision-substate] Host did not create a script group';
		scriptGroup.parent = this;
	}

	function get_controls():Dynamic return sourceHost.getControls();

	/**
		Load one source substate script. The default prefix and callback timing
		match MusicBeatSubstate; ScriptedTransition may select "transitions".
	*/
	public function initStateScript(?requestedName:String, callOnLoad:Bool = true):Bool {
		var selectedName = requestedName;
		if (selectedName == null) {
			var type = Type.getClass(this);
			var fullName = type == null ? null : Type.getClassName(type);
			selectedName = fullName == null ? '???' : fullName.split('.').pop();
		}
		scriptName = selectedName;

		var result = sourceHost.createSubstateScript(scriptPrefix, selectedName, this, scriptGroup);
		switch (result) {
			case Missing(_):
				if (callOnLoad) scriptGroup.call('onLoad', []);
				return scripted;
			case AlreadyLoaded(_):
				// MusicBeatSubstate does not check scriptGroup.exists before loading.
				if (callOnLoad) scriptGroup.call('onLoad', []);
				return scripted;
			case ParseFailed(_, handle):
				destroyUnownedScript(handle, selectedName);
				return false;
			case Loaded(_, _, handle):
				if (handle == null || handle.released || !handle.initialized || handle.parsingFailed()) {
					destroyUnownedScript(handle, selectedName);
					return false;
				}
				scriptGroup.parent = this;
				if (scriptGroup.members.indexOf(handle) < 0 && !scriptGroup.addScript(handle))
					destroyUnownedScript(handle, selectedName);
				// The donor retains scripted=true when addScript rejects a duplicate.
				scripted = true;
				if (callOnLoad) scriptGroup.call('onLoad', []);
				return scripted;
		}
	}

	function destroyUnownedScript(handle:NightmareVisionScriptModule, name:String):Void {
		if (handle == null || handle.released) return;
		try handle.destroy() catch (error:Dynamic) sourceHost.report(name, 'destroy', error);
	}

	/** MusicBeatSubstate dispatches once when its step changes, even after a jump. */
	public override function update(elapsed:Float):Void {
		var oldStep:Int = curStep;
		var timing = sourceHost.timing();
		curDecStep = timing.decimalStep;
		curStep = timing.step;
		updateBeat();

		if (oldStep != curStep) {
			if (curStep > 0) stepHit();
			if (sourceHost.hasSong()) {
				if (oldStep < curStep) updateSection();
				else rollbackSection();
			}
		}

		scriptGroup.call('onUpdate', [elapsed]);
		super.update(elapsed);
	}

	function updateBeat():Void {
		curBeat = Math.floor(curStep / 4);
		curDecBeat = curDecStep / 4;
	}

	public function stepHit():Void {
		if (curStep % 4 == 0) beatHit();
		scriptGroup.call('onStepHit', [curStep]);
	}

	public function beatHit():Void scriptGroup.call('onBeatHit', [curBeat]);

	public function sectionHit():Void scriptGroup.call('onSectionHit', []);

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
		var lastSection:Int = curSection;
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

	/** Sort source script groups with the same owner-aware zIndex view as states. */
	@:keep public function refreshZ(?group:Dynamic):Void {
		var target:Dynamic = group == null ? FlxG.state : group;
		if (target == null) return;
		var sort = Reflect.field(target, 'sort');
		if (!Reflect.isFunction(sort))
			throw '[nightmare-vision-substate] refreshZ target has no sort method';
		Reflect.callMethod(target, sort, [function(order:Int, a:FlxBasic, b:FlxBasic):Int {
			return flixel.util.FlxSort.byValues(order,
				HxcCompatRuntime.getZIndex(a), HxcCompatRuntime.getZIndex(b));
		}, flixel.util.FlxSort.ASCENDING]);
	}

	/** Keep source callbacks ahead of interpreter and state-local teardown. */
	public override function destroy():Void {
		if (sourceDestroyed) return;
		sourceDestroyed = true;
		var firstError:Dynamic = null;
		try scriptGroup.call('onDestroy', []) catch (error:Dynamic) firstError = error;
		try scriptGroup.destroy() catch (error:Dynamic) if (firstError == null) firstError = error;
		try sourceHost.releaseStateResources(this) catch (error:Dynamic) if (firstError == null) firstError = error;
		try super.destroy() catch (error:Dynamic) if (firstError == null) firstError = error;
		if (firstError != null) throw firstError;
	}
}
