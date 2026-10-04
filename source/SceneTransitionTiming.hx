package;

import flixel.addons.transition.TransitionData;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;

/** Apply the optional speed multiplier at shared scene-transition boundaries. */
class SceneTransitionTiming {
	public static inline var FAST_FACTOR:Float = 1 / 3;

	public static function enabled():Bool {
		var options:Dynamic = OptionsHandler.options;
		return options != null && Reflect.field(options, 'fastSceneTransitions') == true;
	}

	public static function sceneDuration(duration:Float):Float
		return enabled() ? duration * FAST_FACTOR : duration;

	/** Return the original object when disabled; otherwise copy it before Flixel
		starts its tween because default transition data is shared between states. */
	public static function forStateTransition(data:TransitionData):TransitionData {
		if (data == null || !enabled()) return data;
		var duration = data.duration * FAST_FACTOR;
		if (duration == data.duration) return data;

		var direction = data.direction == null ? null : new FlxPoint(data.direction.x, data.direction.y);
		var region = data.region == null ? null
			: new FlxRect(data.region.x, data.region.y, data.region.width, data.region.height);
		var scaled = new TransitionData(data.type, data.color, duration,
			direction, data.tileData, region, data.cameraMode);
		if (data.tweenOptions == null) {
			scaled.tweenOptions = null;
		} else {
			var options:Dynamic = {};
			for (field in Reflect.fields(data.tweenOptions))
				Reflect.setField(options, field, Reflect.field(data.tweenOptions, field));
			scaled.tweenOptions = cast options;
		}
		return scaled;
	}
}
