package;

/** NMV draw-state extension of Psych's identical RGB channel palette. */
class NightmareVisionRGBGraphics {
	public var palette(default, null):PsychRGBPalette;
	public var enabled:Bool = true;
	public var alpha:Float = 1;
	public var flash:Float = 0;
	public var r(get, set):Int;
	public var g(get, set):Int;
	public var b(get, set):Int;
	public var mult(get, set):Float;
	function get_r():Int return palette.r;
	function set_r(value:Int):Int return palette.r = value;
	function get_g():Int return palette.g;
	function set_g(value:Int):Int return palette.g = value;
	function get_b():Int return palette.b;
	function set_b(value:Int):Int return palette.b = value;
	function get_mult():Float return palette.mult;
	function set_mult(value:Float):Float return palette.mult = value;

	public function new(?base:PsychRGBPalette) {
		palette = base == null ? new PsychRGBPalette() : base.copy();
	}

	public function setColors(colors:Array<Int>):Void {
		if (colors == null || colors.length < 3) throw '[nightmare-vision-note] RGB needs three colors';
		r = colors[0]; g = colors[1]; b = colors[2];
	}
	public function getColors():Array<Int> return [r, g, b];

	/** Per-object uniforms are never written into the shared lane palette. */
	public function apply(sprite:flixel.FlxSprite):Void {
		palette.shader.mult.value = [enabled ? palette.mult : 0];
		palette.shader.u_alpha.value = [alpha];
		palette.shader.u_flash.value = [flash];
		sprite.shader = palette.shader;
	}
}
