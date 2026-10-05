package;

typedef NightmareVisionFieldUnderlayBounds = {
	var x:Float;
	var width:Float;
	var height:Float;
}

/** Pure layout and opacity calculations for the source FIELD underlay. */
@:keep
class NightmareVisionFieldUnderlay {
	public static inline var PADDING:Float = 15;

	/**
	 * Measure the horizontal span occupied by visible receptors and visible-on-screen
	 * alive notes. Null means there is no finite extent to draw.
	 */
	public static function measure(receptors:Array<Dynamic>, notes:Array<Dynamic>,
		viewWidth:Float, viewHeight:Float, scrollAngle:Float):Null<NightmareVisionFieldUnderlayBounds> {
		if (!Math.isFinite(viewWidth) || !Math.isFinite(viewHeight) || !Math.isFinite(scrollAngle))
			return null;

		var minX = Math.POSITIVE_INFINITY;
		var maxX = Math.NEGATIVE_INFINITY;
		if (receptors != null) for (strum in receptors) {
			if (strum == null || Reflect.field(strum, 'exists') != true
				|| Reflect.field(strum, 'visible') != true) continue;
			var x:Float = Reflect.field(strum, 'x');
			var width:Float = Reflect.field(strum, 'width');
			if (!includeExtent(x, width)) continue;
			minX = Math.min(minX, x);
			maxX = Math.max(maxX, x + width);
		}

		if (notes != null) for (note in notes) {
			if (note == null || Reflect.field(note, 'exists') != true
				|| Reflect.field(note, 'alive') != true) continue;
			var isOnScreen = Reflect.field(note, 'isOnScreen');
			if (isOnScreen == null || Reflect.callMethod(note, isOnScreen, []) != true) continue;
			var x:Float = Reflect.field(note, 'x');
			var width:Float = Reflect.field(note, 'width');
			if (!includeExtent(x, width)) continue;
			minX = Math.min(minX, x);
			maxX = Math.max(maxX, x + width);
		}

		if (!Math.isFinite(minX) || !Math.isFinite(maxX) || maxX < minX) return null;
		var angleRad = scrollAngle * Math.PI / 180;
		var cos = Math.abs(Math.cos(angleRad));
		var sin = Math.abs(Math.sin(angleRad));
		var rotatedHeight = viewWidth * sin + viewHeight * cos;
		if (!Math.isFinite(rotatedHeight)) return null;
		return {
			x: minX - PADDING,
			width: maxX - minX + PADDING * 2,
			height: rotatedHeight
		};
	}

	/** Source multiplies opacity by the field multiplier and alpha/dark complements. */
	public static inline function effectiveAlpha(opacity:Float, fieldAlphaMult:Float,
		managerAlpha:Float, managerDark:Float):Float
		return opacity * fieldAlphaMult * (1 - managerAlpha) * (1 - managerDark);

	static function includeExtent(x:Float, width:Float):Bool
		return Math.isFinite(x) && Math.isFinite(width) && Math.isFinite(x + width);
}
