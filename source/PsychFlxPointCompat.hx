package;

import flixel.math.FlxPoint;
import flixel.math.FlxPoint.FlxBasePoint;

/** Runtime class facade for Psych's FlxPoint import. FlxPoint is a Haxe
	abstract, and its get/weak helpers are inline, so HScript needs a reflectable
	class that still produces native FlxBasePoint values. */
class PsychFlxPointCompat extends FlxBasePoint {
	public function new(x:Float = 0, y:Float = 0) {
		super(x, y);
	}

	public static function get(x:Float = 0, y:Float = 0):FlxPoint {
		return FlxPoint.get(x, y);
	}

	public static function weak(x:Float = 0, y:Float = 0):FlxPoint {
		return FlxPoint.weak(x, y);
	}
}
