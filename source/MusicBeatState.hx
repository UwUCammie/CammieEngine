package;

import Conductor.BPMChangeEvent;
import flixel.FlxG;
import flixel.FlxState;
import flixel.addons.transition.FlxTransitionableState;
import flixel.addons.ui.FlxUIState;
import flixel.math.FlxRect;
import flixel.util.FlxTimer;

class MusicBeatState extends FlxUIState {
	@:keep public static var timePassedOnState:Float = 0;
	/** One native variable registry per state, shared by source scripts and host adapters. */
	@:keep public var variables:Map<String, Dynamic> = [];
	@:keep public static function getState():MusicBeatState {
		return cast (FlxG.state, MusicBeatState);
	}
	@:keep public static function getVariables():Map<String, Dynamic> {
		return getState().variables;
	}

	private var lastBeat:Float = 0;
	private var lastStep:Float = 0;

	@:keep private var curStep:Int = 0;
	@:keep private var curBeat:Int = 0;
	/** Only source-constructed Psych states use the source clock. Gameplay keeps catch-up. */
	@:keep public var psychSourceTiming:Bool = false;
	@:keep public var curSection:Int = 0;
	@:keep public var curDecStep:Float = 0;
	@:keep public var curDecBeat:Float = 0;
	@:keep var stepsToDo:Int = 0;
	/** Read-only timing aliases for isolated imported state wrappers. */
	public var hxcCurrentStep(get, never):Int;
	public var hxcCurrentBeat(get, never):Int;
	inline function get_hxcCurrentStep():Int return curStep;
	inline function get_hxcCurrentBeat():Int return curBeat;
	// Zero allows all crossed steps during accelerated demo playback.
	public var maxStepCatchUp:Int = 32;
	private var controls(get, never):Controls;
	private var controlsPlayerTwo(get, never):Controls;
	inline function get_controls():Controls
		return PlayerSettings.player1.controls;
	inline function get_controlsPlayerTwo():Controls
		return PlayerSettings.player2.controls;
	override function create() {
		if (transIn != null)
			trace('reg ' + transIn.region);

		#if (!web)
		TitleState.soundExt = '.ogg';
		#end

		super.create();
		CodenameMusicBeatTransition.startPendingIncoming(this);
		NightmareVisionPluginHost.callActive('onStateCreate');
		timePassedOnState = 0;
	}

	/** Start the source-compatible Codename transition for this active owner.
		Without a selected owner and explicit transition script, defer to the
		existing FlxTransitionableState behavior unchanged.
	*/
	public function startTransition(?newState:FlxState, skipSubStates:Bool = false):Bool
		return CodenameMusicBeatTransition.openForOwner(CodenameMusicBeatTransition.currentOwnerRoot(),
			newState, skipSubStates, null);

	/** Scale only the data Flixel snapshots into this scene's transition.
		The state's original reference may be a global default shared by every
		state, so restore it immediately after transition construction. */
	override public function transitionIn():Void {
		var original = transIn;
		var scaled = SceneTransitionTiming.forStateTransition(original);
		if (scaled == original) {
			super.transitionIn();
			return;
		}
		transIn = scaled;
		try {
			super.transitionIn();
		} catch (error:Dynamic) {
			if (transIn == scaled) transIn = original;
			throw error;
		}
		if (transIn == scaled) transIn = original;
	}

	override public function transitionOut(?onExit:Void->Void):Void {
		var original = transOut;
		var scaled = SceneTransitionTiming.forStateTransition(original);
		if (scaled == original) {
			super.transitionOut(onExit);
			return;
		}
		transOut = scaled;
		try {
			super.transitionOut(onExit);
		} catch (error:Dynamic) {
			if (transOut == scaled) transOut = original;
			throw error;
		}
		if (transOut == scaled) transOut = original;
	}

	override public function startOutro(onOutroComplete:Void->Void):Void {
		if (CodenameMusicBeatTransition.completeTransitionSwitch(this, onOutroComplete)) return;
		if (CodenameMusicBeatTransition.startOwnerOutro(this, onOutroComplete)) return;
		super.startOutro(onOutroComplete);
	}

	override function update(elapsed:Float) {
		timePassedOnState += elapsed;
		//everyStep();
		var oldStep:Int = curStep;

		updateCurStep();
		updateBeat();

		if (psychSourceTiming) {
			if (oldStep != curStep) {
				if (curStep > 0) stepHit();
				if (PlayState.SONG != null) {
					if (oldStep < curStep) updateSection(); else rollbackSection();
				}
			}
			if (FlxG.save.data != null) FlxG.save.data.fullscreen = FlxG.fullscreen;
			super.update(elapsed);
			return;
		}

		if (FlxG.keys.justPressed.ESCAPE && FlxG.keys.pressed.SHIFT) {
			TitleState.initialized = false;
			FlxG.resetGame();
		}

		if (oldStep != curStep && curStep > 0) {
			// fire every step we crossed, not just the latest one: a laggy
			// frame can hop a whole step (83ms at 180bpm) and single-step
			// modchart events (Illusion New's final zoom-out) get eaten
			var target:Int = curStep;
			var from:Int = oldStep + 1;
			if (from < 1)
				from = 1;
			if (maxStepCatchUp > 0 && target - from > maxStepCatchUp)
				from = target - maxStepCatchUp;
			for (s in from...target + 1) {
				curStep = s;
				updateBeat();
				stepHit();
			}
			curStep = target;
			updateBeat();
		}

		super.update(elapsed);
	}

	private function updateBeat():Void {
		curBeat = Math.floor(curStep / 4);
		if (psychSourceTiming) curDecBeat = curDecStep / 4;
	}

	private function updateCurStep():Void {
		if (psychSourceTiming) {PsychBeatClock.updateStep(this);return;}
		var lastChange:BPMChangeEvent = {
			stepTime: 0,
			songTime: 0,
			bpm: 0
		}
		for (i in 0...Conductor.bpmChangeMap.length) {
			if (Conductor.songPosition >= Conductor.bpmChangeMap[i].songTime)
				lastChange = Conductor.bpmChangeMap[i];
		}

		curStep = lastChange.stepTime + Math.floor((Conductor.songPosition - lastChange.songTime) / Conductor.stepCrochet);
	}

	@:keep function updateSection():Void SourceBeatSections.advance(this, getBeatsOnSection, sectionHit);
	@:keep function rollbackSection():Void SourceBeatSections.rollback(this,
		function() return PlayState.SONG.notes.length,
		function(index) return PlayState.SONG.notes[index] != null, getBeatsOnSection, sectionHit);
	@:keep function getBeatsOnSection():Float return PsychBeatClock.sectionBeats(curSection);
	@:keep public function sectionHit():Void {}

	public function stepHit():Void {
		if (curStep % 4 == 0)
			beatHit();
		if (!psychSourceTiming) NightmareVisionPluginHost.callActive('onStepHit');
	}

	public function beatHit():Void {
		if (!psychSourceTiming) NightmareVisionPluginHost.callActive('onBeatHit');
	}
}
