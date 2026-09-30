package;

import flixel.math.FlxPoint;

/** Script-visible mutable camera target. FlxPoint.addPoint is inlined by
 * Flixel, so HScript cannot call it through reflection on the native point. */
@:keep
class CodenameCameraMovePoint {
	public var x:Float;
	public var y:Float;

	public function new(point:FlxPoint) {
		x = point.x;
		y = point.y;
	}

	public function set(x:Float, y:Float):CodenameCameraMovePoint {
		this.x = x;
		this.y = y;
		return this;
	}

	public function addPoint(point:Dynamic):CodenameCameraMovePoint {
		if (point != null) {
			x += Reflect.field(point, 'x');
			y += Reflect.field(point, 'y');
		}
		return this;
	}
}
