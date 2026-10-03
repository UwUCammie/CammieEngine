package nightmarevision.modchart;

/** Small mutable vector matching the donor modchart's Vector3 math surface. */
class NightmareVisionModchartVector {
	public var x:Float;
	public var y:Float;
	public var z:Float;

	public function new(x:Float = 0, y:Float = 0, z:Float = 0) {
		this.x = x;
		this.y = y;
		this.z = z;
	}

	public function copy():NightmareVisionModchartVector return new NightmareVisionModchartVector(x, y, z);

	public function lerp(other:NightmareVisionModchartVector, amount:Float):NightmareVisionModchartVector {
		return new NightmareVisionModchartVector(
			x + (other.x - x) * amount,
			y + (other.y - y) * amount,
			z + (other.z - z) * amount);
	}

	public static function distance(a:NightmareVisionModchartVector, b:NightmareVisionModchartVector):Float {
		var dx = a.x - b.x;
		var dy = a.y - b.y;
		var dz = a.z - b.z;
		return Math.sqrt(dx * dx + dy * dy + dz * dz);
	}
}
