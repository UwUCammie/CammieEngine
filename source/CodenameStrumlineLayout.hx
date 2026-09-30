package;

/** Native receptor placement from a Codename chart's line geometry. Codename's
 * normalized strumLinePos denotes the center of the active lane bank; this
 * fork keeps receptor sprites on its existing lane-width spacing. */
typedef CodenameStrumlinePlacement = {
	var x:Float;
	var y:Float;
	var spacing:Float;
	var scale:Float;
	var visible:Bool;
	var keyCount:Int;
}

class CodenameStrumlineLayout {
	/** Codename defaults player lines to the right bank and all other types to
	 * the left; explicit strumLinePos remains authoritative. */
	public static function defaultLinePosition(lineType:Null<Int>):Float
		return lineType == 1 ? 0.75 : 0.25;

	public static function resolve(line:Dynamic, screenWidth:Float, defaultY:Float,
		laneWidth:Float, nativeLaneCount:Int):CodenameStrumlinePlacement {
		if (line == null) return null;
		var type:Null<Int> = Reflect.field(line, 'type');
		var fallbackPos = defaultLinePosition(type);
		var keyCount = positiveInt(Reflect.field(line, 'keyCount'), nativeLaneCount);
		var spacing = positiveNumber(Reflect.field(line, 'strumSpacing'), 1);
		var scale = positiveNumber(Reflect.field(line, 'strumScale'), 1);
		var linePos = number(Reflect.field(line, 'strumLinePos'), fallbackPos);
		var strumPos:Dynamic = Reflect.field(line, 'strumPos');
		var offsetX = 0.0;
		var offsetY = defaultY;
		if (Std.isOfType(strumPos, Array)) {
			var offsets:Array<Dynamic> = cast strumPos;
			if (offsets.length >= 2) {
				offsetX = number(offsets[0], 0);
				offsetY = number(offsets[1], 50);
			}
		}
		// Match Codename StrumLine.calculateStartingXPos: line position is the
		// bank center, and the full authored key count determines its starting lane.
		var calculatedX = screenWidth * linePos
			- (laneWidth * scale * ((keyCount / 2) - 0.5) * spacing
				+ laneWidth * 0.5 * scale);
		// Codename treats a nonzero strumPos.x as an absolute receptor start;
		// zero opts into the normalized strumLinePos placement above.
		var x = offsetX == 0 ? calculatedX : offsetX;
		return {x:x, y:offsetY, spacing:spacing, scale:scale,
			visible:Reflect.field(line, 'visible') != false, keyCount:keyCount};
	}

	static function number(value:Dynamic, fallback:Float):Float {
		var parsed = if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			(cast value:Float) else if (Std.isOfType(value, String))
			Std.parseFloat(StringTools.trim(cast value)) else Math.NaN;
		return Math.isFinite(parsed) ? parsed : fallback;
	}

	static function positiveNumber(value:Dynamic, fallback:Float):Float {
		var parsed = number(value, fallback);
		return parsed > 0 ? parsed : fallback;
	}

	static function positiveInt(value:Dynamic, fallback:Int):Int {
		var parsed = number(value, fallback);
		return parsed > 0 ? Std.int(parsed) : fallback;
	}
}
