import haxe.ds.Vector;

/**
	Correct hold UV subdivision for the FlxUVRect contract in Flixel 6.1.2.
	FlxUVRect maps left/top/right/bottom to x/y/width/height.  The caller
	therefore needs (left, top, right, bottom), not (left, right, top, bottom).
*/
class ModchartHoldUVCompat {
	public static function getHoldUVT(left:Float, top:Float, right:Float, bottom:Float, frameAngle:Float, subdivisions:Int):Vector<Float> {
		if (subdivisions <= 0)
			throw '[funkin-modchart-uv] subdivisions must be positive';

		var uv = new Vector<Float>(12 * subdivisions);
		var width = right - left;
		var height = bottom - top;
		var inverseSubdivisions = 1.0 / subdivisions;
		var radians = frameAngle * (Math.PI / 180);
		var cosAngle = Math.cos(radians);
		var sinAngle = Math.sin(radians);

		for (subdivision in 0...subdivisions) {
			var v0 = subdivision * inverseSubdivisions;
			var v1 = (subdivision + 1) * inverseSubdivisions;
			var base = subdivision * 12;

			// Keep the triangle vertex order used by FunkinModchart's renderer:
			// top-left, top-right, bottom-left, bottom-right.
			putVertex(uv, base, left, top, width, height, 0, v0, frameAngle, cosAngle, sinAngle);
			putVertex(uv, base + 3, left, top, width, height, 1, v0, frameAngle, cosAngle, sinAngle);
			putVertex(uv, base + 6, left, top, width, height, 0, v1, frameAngle, cosAngle, sinAngle);
			putVertex(uv, base + 9, left, top, width, height, 1, v1, frameAngle, cosAngle, sinAngle);
		}
		return uv;
	}

	static inline function putVertex(uv:Vector<Float>, index:Int, left:Float, top:Float, width:Float, height:Float,
		u:Float, v:Float, frameAngle:Float, cosAngle:Float, sinAngle:Float):Void {
		var rotatedU:Float;
		var rotatedV:Float;
		switch (Std.int(frameAngle)) {
			case 0:
				rotatedU = u;
				rotatedV = v;
			case 90:
				rotatedU = 1 - v;
				rotatedV = u;
			case -90:
				rotatedU = v;
				rotatedV = 1 - u;
			default:
				var centeredU = u - 0.5;
				var centeredV = v - 0.5;
				rotatedU = centeredU * cosAngle - centeredV * sinAngle + 0.5;
				rotatedV = centeredU * sinAngle + centeredV * cosAngle + 0.5;
		}

		// A FlxFrame angle describes how the packed rectangle is rotated. Work
		// in unit-frame coordinates, then map into this frame's own atlas bounds.
		// This preserves the inverse angle supplied by upstream getHoldUVT and
		// prevents a non-square rotated frame from sampling adjacent atlas data.
		rotatedU = clampUnit(rotatedU);
		rotatedV = clampUnit(rotatedV);
		uv[index] = left + rotatedU * width;
		uv[index + 1] = top + rotatedV * height;
		uv[index + 2] = 1;
	}

	static inline function clampUnit(value:Float):Float {
		return value < 0 ? 0 : (value > 1 ? 1 : value);
	}
}
