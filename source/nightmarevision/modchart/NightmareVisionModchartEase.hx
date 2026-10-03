package nightmarevision.modchart;

import flixel.tweens.FlxEase;

using StringTools;

/**
	The source CoolUtil.getEaseFromString dispatch table, backed by the exact
	FlxEase implementation used by the 6.1.2 game/toolchain.
*/
class NightmareVisionModchartEase {
	public static function apply(ease:Dynamic, time:Float):Float {
		if (ease == null) return FlxEase.linear(time);
		if (Reflect.isFunction(ease))
			return cast Reflect.callMethod(null, ease, [time]);
		if (!Std.isOfType(ease, String))
			throw 'Nightmare Vision ease must be a name or a function';
		var name:String = cast ease;
		return switch (name.toLowerCase().trim()) {
			case 'backin': FlxEase.backIn(time);
			case 'backinout': FlxEase.backInOut(time);
			case 'backout': FlxEase.backOut(time);
			case 'bouncein': FlxEase.bounceIn(time);
			case 'bounceinout': FlxEase.bounceInOut(time);
			case 'bounceout': FlxEase.bounceOut(time);
			case 'circin': FlxEase.circIn(time);
			case 'circinout': FlxEase.circInOut(time);
			case 'circout': FlxEase.circOut(time);
			case 'cubein': FlxEase.cubeIn(time);
			case 'cubeinout': FlxEase.cubeInOut(time);
			case 'cubeout': FlxEase.cubeOut(time);
			case 'elasticin': FlxEase.elasticIn(time);
			case 'elasticinout': FlxEase.elasticInOut(time);
			case 'elasticout': FlxEase.elasticOut(time);
			case 'expoin': FlxEase.expoIn(time);
			case 'expoinout': FlxEase.expoInOut(time);
			case 'expoout': FlxEase.expoOut(time);
			case 'quadin': FlxEase.quadIn(time);
			case 'quadinout': FlxEase.quadInOut(time);
			case 'quadout': FlxEase.quadOut(time);
			case 'quartin': FlxEase.quartIn(time);
			case 'quartinout': FlxEase.quartInOut(time);
			case 'quartout': FlxEase.quartOut(time);
			case 'quintin': FlxEase.quintIn(time);
			case 'quintinout': FlxEase.quintInOut(time);
			case 'quintout': FlxEase.quintOut(time);
			case 'sinein': FlxEase.sineIn(time);
			case 'sineinout': FlxEase.sineInOut(time);
			case 'sineout': FlxEase.sineOut(time);
			case 'smoothstepin': FlxEase.smoothStepIn(time);
			case 'smoothstepinout': FlxEase.smoothStepInOut(time);
			case 'smoothstepout': FlxEase.smoothStepOut(time);
			case 'smootherstepin': FlxEase.smootherStepIn(time);
			case 'smootherstepinout': FlxEase.smootherStepInOut(time);
			case 'smootherstepout': FlxEase.smootherStepOut(time);
			default: FlxEase.linear(time);
		};
	}
}
