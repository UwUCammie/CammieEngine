package;

import Conductor.BPMChangeEvent;
import flixel.FlxG;
import flixel.FlxSubState;

class MusicBeatSubstate extends FlxSubState
{
	public function new()
	{
		super();
	}

	/** Codename states may opt into hosting a transition above this substate. */
	public var canOpenCustomTransition:Bool = false;

	private var lastBeat:Float = 0;
	private var lastStep:Float = 0;

	@:keep private var curStep:Int = 0;
	@:keep private var curBeat:Int = 0;
	/** Read-only timing aliases for isolated imported substate wrappers. */
	public var hxcCurrentStep(get, never):Int;
	public var hxcCurrentBeat(get, never):Int;
	inline function get_hxcCurrentStep():Int return curStep;
	inline function get_hxcCurrentBeat():Int return curBeat;
	private var controls(get, never):Dynamic;

	function get_controls():Dynamic
		return PlayerSettings.player1.controls;

	override function create()
	{
		#if (!web)
		TitleState.soundExt = '.ogg';
		#end

		super.create();
	}

	override function update(elapsed:Float)
	{
		//everyStep();
		var oldStep:Int = curStep;

		updateCurStep();
		curBeat = Math.floor(curStep / 4);

		if (oldStep != curStep && curStep > 0)
			stepHit();


		updateSubstateChildren(elapsed);
	}

	/** Shared native child update for source dialects with their own beat clock. */
	function updateSubstateChildren(elapsed:Float):Void super.update(elapsed);

	private function updateCurStep():Void
	{
		var lastChange:BPMChangeEvent = {
			stepTime: 0,
			songTime: 0,
			bpm: 0
		}
		for (i in 0...Conductor.bpmChangeMap.length)
		{
			if (Conductor.songPosition > Conductor.bpmChangeMap[i].songTime)
				lastChange = Conductor.bpmChangeMap[i];
		}

		curStep = lastChange.stepTime + Math.floor((Conductor.songPosition - lastChange.songTime) / Conductor.stepCrochet);
	}

	public function stepHit():Void
	{
		if (curStep % 4 == 0)
			beatHit();
	}

	public function beatHit():Void
	{
		//do literally nothing dumbass
	}
}
