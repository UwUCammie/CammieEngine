package;

import flixel.util.FlxColor;

/** One RGB palette and its shader. Default palettes are shared by lane and skin kind. */
class PsychRGBPalette {
	static var defaultPalettes:Map<String, PsychRGBPalette> = new Map();

	public var shader(default, null):PsychRGBShader;
	public var r(default, set):FlxColor;
	public var g(default, set):FlxColor;
	public var b(default, set):FlxColor;
	public var mult(default, set):Float;

	public function new() {
		shader = new PsychRGBShader();
		r = 0xFFFF0000;
		g = 0xFF00FF00;
		b = 0xFF0000FF;
		mult = 1.0;
	}

	/** Return the common palette for one Psych lane, pixel mode, and hurt mode. */
	public static function defaultFor(lane:Int, pixel:Bool, hurt:Bool = false):PsychRGBPalette {
		var normalizedLane = ((lane % 4) + 4) % 4;
		var key = (pixel ? 'pixel' : 'normal') + ':' + (hurt ? 'hurt' : 'note') + ':' + normalizedLane;
		var palette = defaultPalettes.get(key);
		if (palette == null) {
			palette = new PsychRGBPalette();
			palette.setPalette(normalizedLane, pixel, hurt);
			defaultPalettes.set(key, palette);
		}
		return palette;
	}

	/** Make an independent palette for a note whose RGB values are customized. */
	public function copy():PsychRGBPalette {
		var result = new PsychRGBPalette();
		result.r = r;
		result.g = g;
		result.b = b;
		result.mult = mult;
		return result;
	}

	public function copyValues(other:PsychRGBPalette):Void {
		if (other == null) {
			mult = 0.0;
			return;
		}
		r = other.r;
		g = other.g;
		b = other.b;
		mult = other.mult;
	}

	public function setPalette(lane:Int, pixel:Bool, hurt:Bool = false):Void {
		var palettes:Array<Array<Int>> = pixel ? [
			[0xFFE276FF, 0xFFFFF9FF, 0xFF60008D], [0xFF3DCAFF, 0xFFF4FFFF, 0xFF003060],
			[0xFF71E300, 0xFFF6FFE6, 0xFF003100], [0xFFFF884E, 0xFFFFFAF5, 0xFF6C0000]
		] : [
			[0xFFC24B99, 0xFFFFFFFF, 0xFF3C1F56], [0xFF00FFFF, 0xFFFFFFFF, 0xFF1542B7],
			[0xFF12FA05, 0xFFFFFFFF, 0xFF0A4447], [0xFFF9393F, 0xFFFFFFFF, 0xFF651038]
		];
		var colors = hurt ? [0xFF101010, 0xFFFF0000, 0xFF990022] : palettes[((lane % 4) + 4) % 4];
		r = colors[0];
		g = colors[1];
		b = colors[2];
		mult = 1.0;
	}

	function set_r(color:FlxColor):FlxColor {
		r = color;
		shader.r.value = components(color);
		return color;
	}

	function set_g(color:FlxColor):FlxColor {
		g = color;
		shader.g.value = components(color);
		return color;
	}

	function set_b(color:FlxColor):FlxColor {
		b = color;
		shader.b.value = components(color);
		return color;
	}

	function set_mult(value:Float):Float {
		mult = Math.max(0, Math.min(1, value));
		shader.mult.value = [mult];
		return mult;
	}

	static function components(color:FlxColor):Array<Float> {
		return [color.redFloat, color.greenFloat, color.blueFloat];
	}
}
