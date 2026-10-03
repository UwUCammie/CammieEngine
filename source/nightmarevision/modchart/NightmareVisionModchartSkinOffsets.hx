package nightmarevision.modchart;

/** Primitive view of the selected source NoteSkin's per-lane visual offsets. */
class NightmareVisionModchartSkinOffsets {
	public var note:Array<NightmareVisionModchartVector> = [];
	public var receptor:Array<NightmareVisionModchartVector> = [];
	public var sustain:Array<NightmareVisionModchartVector> = [];
	public var sustainEnd:Array<NightmareVisionModchartVector> = [];
	public var noteSplash:Array<NightmareVisionModchartVector> = [];
	public var sustainSplash:Array<NightmareVisionModchartVector> = [];

	public function new(keys:Int = 4, ?sourceSkin:Dynamic) {
		var count = keys < 1 ? 1 : keys;
		note = readOffsets(sourceSkin, 'noteOffsets', count);
		receptor = readOffsets(sourceSkin, 'receptorOffsets', count);
		sustain = readOffsets(sourceSkin, 'sustainOffsets', count);
		sustainEnd = readOffsets(sourceSkin, 'susEndOffsets', count);
		noteSplash = readOffsets(sourceSkin, 'splashOffsets', count);
		sustainSplash = readOffsets(sourceSkin, 'sustainSplashOffsets', count);
	}

	public function get(kind:String, data:Int, isSustain:Bool = false):NightmareVisionModchartVector {
		var values = switch (kind) {
			case NightmareVisionModchartObject.NOTE: note;
			case NightmareVisionModchartObject.RECEPTOR: receptor;
			case NightmareVisionModchartObject.NOTE_SPLASH: noteSplash;
			case NightmareVisionModchartObject.SUSTAIN_SPLASH: sustainSplash;
			default: null;
		};
		var result = pointAt(values, data);
		if (kind == NightmareVisionModchartObject.NOTE && isSustain) {
			var hold = pointAt(sustain, data);
			result.x += hold.x;
			result.y += hold.y;
		}
		return result;
	}

	public function getSustainEnd(data:Int):NightmareVisionModchartVector
		return pointAt(sustainEnd, data);

	static function readOffsets(source:Dynamic, field:String, count:Int):Array<NightmareVisionModchartVector> {
		var values:Array<NightmareVisionModchartVector> = [];
		var table = source == null ? null : Reflect.field(source, field);
		for (index in 0...count) values.push(readPoint(table, index));
		return values;
	}

	static function readPoint(table:Dynamic, index:Int):NightmareVisionModchartVector {
		if (table == null) return new NightmareVisionModchartVector();
		var raw:Dynamic = null;
		try {
			if (Std.isOfType(table, Array)) {
				var values:Array<Dynamic> = cast table;
				if (index >= 0 && index < values.length) raw = values[index];
			} else {
				var getter = Reflect.field(table, 'get');
				if (getter != null && Reflect.isFunction(getter)) raw = Reflect.callMethod(table, getter, [index]);
				else raw = untyped table[index];
			}
		} catch (_:Dynamic) {}
		if (raw == null) return new NightmareVisionModchartVector();
		if (Std.isOfType(raw, Array)) {
			var coordinates:Array<Dynamic> = cast raw;
			return new NightmareVisionModchartVector(
				coordinates.length > 0 ? number(coordinates[0]) : 0,
				coordinates.length > 1 ? number(coordinates[1]) : 0, 0);
		}
		return new NightmareVisionModchartVector(number(Reflect.field(raw, 'x')),
			number(Reflect.field(raw, 'y')), 0);
	}

	static function pointAt(values:Array<NightmareVisionModchartVector>, index:Int):NightmareVisionModchartVector {
		if (values == null || values.length == 0) return new NightmareVisionModchartVector();
		var normalized = ((index % values.length) + values.length) % values.length;
		return values[normalized].copy();
	}

	static function number(value:Dynamic):Float {
		if (value == null) return 0;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isFinite(parsed) && !Math.isNaN(parsed) ? parsed : 0;
	}
}
