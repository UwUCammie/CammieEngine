package;

/** Source Nightmare Vision's quant grid and color selection in owner-safe values. */
@:keep
class NightmareVisionQuantColorCompat {
	static final ROWS_PER_BEAT:Int = 48;
	static final ROWS_PER_MEASURE:Int = 192;
	static final QUANTS:Array<Int> = [4, 8, 12, 16, 20, 24, 32, 48, 64, 96, 192];
	static final QUANT_COLORS:Array<Array<Int>> = [
		[0xFFE51919, 0xFFFFFF, 0xFF5B0A30],
		[0xFF193BE5, 0xFFFFFF, 0xFF0A3B5B],
		[0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B],
		[0xFF26D93E, 0xFFFFFF, 0xFF24560F],
		[0xFF0000B2, 0xFFFFFF, 0xFF002247],
		[0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B],
		[0xFFE5C319, 0xFFFFFF, 0xFF5B2A0A],
		[0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B],
		[0xFF13ECA4, 0xFFFFFF, 0xFF085D18],
		[0xFF3A3A6C, 0xFFFFFF, 0xFF17202B],
		[0xFF3A3A6C, 0xFFFFFF, 0xFF17202B]
	];

	/** Return the donor's first matching note subdivision for a beat position. */
	@:keep public static function getQuant(beat:Float):Int {
		var row = Math.round(beat * ROWS_PER_BEAT);
		for (quant in QUANTS) if (row % (ROWS_PER_MEASURE / quant) == 0) return quant;
		return QUANTS[QUANTS.length - 1];
	}

	/** Return a fresh copy of NoteUtil.quantDefaultColors for one subdivision. */
	@:keep public static function defaultColors(quant:Int):Array<Int> {
		var index = QUANTS.indexOf(quant);
		if (index < 0)
			throw '[nightmare-vision-quant] Unsupported quant subdivision: ' + quant;
		return QUANT_COLORS[index].copy();
	}

	/** Return the selected owner's source receptor-press palette as an isolated RGB triple. */
	@:keep public static function pressedColors(prefs:Dynamic):Array<Int> {
		if (prefs == null)
			throw '[nightmare-vision-quant] Missing owner preferences for arrowRGBquant';
		var table:Dynamic = Reflect.field(prefs, 'arrowRGBquant');
		if (!Std.isOfType(table, Array))
			throw '[nightmare-vision-quant] Owner arrowRGBquant must be an array';
		var palettes:Array<Dynamic> = cast table;
		if (palettes.length == 0 || !Std.isOfType(palettes[0], Array))
			throw '[nightmare-vision-quant] Owner arrowRGBquant[0] must be an RGB array';
		var row:Array<Dynamic> = cast palettes[0];
		if (row.length < 3)
			throw '[nightmare-vision-quant] Owner arrowRGBquant[0] must contain three colors';
		var colors:Array<Int> = [];
		for (index in 0...3) {
			var value:Dynamic = row[index];
			if (Std.isOfType(value, Int)) colors.push(cast value);
			else if ((Std.isOfType(value, Float)) && Math.isFinite(value) && !Math.isNaN(value)
				&& value == Math.floor(value) && value >= -2147483648.0 && value <= 2147483647.0)
				colors.push(Std.int(value));
			else throw '[nightmare-vision-quant] Owner arrowRGBquant[0][' + index + '] must be an integer color';
		}
		return colors;
	}
}
