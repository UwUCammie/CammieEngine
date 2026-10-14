package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.tweens.FlxTween.FlxTweenType;
import openfl.display.BlendMode;

/**
	The `psychlua.LuaUtils` helpers Psych 0.7 HScript files import for their own
	tweens and cameras. Each one answers through the engine's existing parser or
	camera route, so a script gets the same ease, blend or camera a Lua call with
	the same name would get.
**/
@:access(PlayState)
class PsychLuaUtilsCompat {
	public static function getTweenEaseByString(?ease:String = ''):Float->Float
		return CoolUtil.getEaseFromString(ease);

	public static function getTweenTypeByString(?type:String = ''):FlxTweenType {
		return switch (type == null ? '' : StringTools.trim(type).toLowerCase()) {
			case 'backward': FlxTweenType.BACKWARD;
			case 'looping' | 'loop': FlxTweenType.LOOPING;
			case 'persist': FlxTweenType.PERSIST;
			case 'pingpong': FlxTweenType.PINGPONG;
			default: FlxTweenType.ONESHOT;
		};
	}

	public static function blendModeFromString(blend:String):BlendMode
		return CoolUtil.getBlendFromString(blend);

	/** Game, HUD and Other by their Psych names, then a camera the scripts stored
	 * under that tag, else the game camera. */
	public static function cameraFromString(cam:String):FlxCamera {
		var state = PlayState.instance;
		return state == null ? FlxG.camera : state.compatCameraForName(cam);
	}
}
