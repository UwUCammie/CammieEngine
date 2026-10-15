package;

import flixel.FlxCamera;
import flixel.util.FlxTimer;
import openfl.filters.ColorMatrixFilter;

/**
	V-Slice's stepped camera fade (funkin.effects.RetroCameraFade), used by
	pixel songs and menus. The camera brightens or darkens in a few hard steps
	instead of a smooth tween by replacing the camera's filters with one colour
	offset filter per step, exactly as V-Slice does, so the result looks the
	same. Like V-Slice it owns the camera's filter list while it runs.
**/
@:keep
class RetroCameraFade {
	/** Step from normal colours to white. */
	public static function fadeWhite(camera:FlxCamera, camSteps:Int = 5, time:Float = 1):Void
		run(camera, camSteps, time, 1, false, camSteps + 1);

	/** Start at white and step back to normal colours. */
	public static function fadeFromWhite(camera:FlxCamera, camSteps:Int = 5, time:Float = 1):Void
		run(camera, camSteps, time, 1, true, camSteps);

	/** Step from normal colours to black. */
	public static function fadeToBlack(camera:FlxCamera, camSteps:Int = 5, time:Float = 1):Void
		run(camera, camSteps, time, -1, false, camSteps);

	/** Start at black and step back to normal colours. */
	public static function fadeBlack(camera:FlxCamera, camSteps:Int = 5, time:Float = 1):Void
		run(camera, camSteps, time, -1, true, camSteps + 1);

	/**
		The colour matrix V-Slice applies at one step: every channel shifted by
		`level` (0 to 1) of full brightness, upwards for white and downwards for
		black.
	**/
	public static function stepMatrix(level:Float, direction:Float):Array<Float> {
		var offset = direction * level * 255;
		return [
			1, 0, 0, 0, offset,
			0, 1, 0, 0, offset,
			0, 0, 1, 0, offset,
			0, 0, 0, 1, 0
		];
	}

	/**
		`reverse` counts the step down from full strength (the "from" fades),
		otherwise it counts up from none. The loop counts are V-Slice's own,
		including the extra tick on fadeWhite and fadeBlack.
	**/
	static function run(camera:FlxCamera, camSteps:Int, time:Float, direction:Float, reverse:Bool, loops:Int):Void {
		if (camera == null || camSteps <= 0)
			return;
		var stepsTotal = camSteps;
		var steps = reverse ? camSteps : 0;
		if (reverse)
			camera.filters = [new ColorMatrixFilter(stepMatrix(1, direction))];
		new FlxTimer().start(time / stepsTotal, function(_) {
			var level:Float = (1 / stepsTotal) * steps;
			if (steps == stepsTotal)
				level = 1;
			camera.filters = [new ColorMatrixFilter(stepMatrix(level, direction))];
			if (reverse)
				steps--;
			else
				steps++;
		}, loops);
	}
}
