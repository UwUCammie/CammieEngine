package;

/**
	NMV draw-state extension of Psych's identical RGB channel palette.

	Every note owns one of these, and a palette owns a compiled shader object
	(about 20 KB of collector-scanned memory). Creating one per note for a whole
	chart made long songs keep hundreds of megabytes of shader objects alive,
	which doubled every collection pause. A note now draws with a shader shared
	by all notes whose uniforms are exactly the same (same colours, mult, full
	alpha, no flash) and gets its own palette only when it needs different
	uniforms or when code asks for `palette` directly. A shared shader's
	uniforms never change, and OpenFL reads uniforms when the frame renders, so
	every note still renders with the values it would have had in its own
	shader. Released palettes are reused by the next note that needs one.
**/
@:keep
class NightmareVisionRGBGraphics {
	/** Reading this gives the graphic its own palette (see above). */
	public var palette(get, never):PsychRGBPalette;
	var own:PsychRGBPalette;
	/** Optional historical shader; RGB storage remains available to modern APIs. */
	public var legacyHSV:NightmareVisionLegacyColorSwap;
	public var legacyHSL:NightmareVisionHSLColorSwap;
	public var enabled:Bool = true;
	public var alpha:Float = 1;
	public var flash:Float = 0;
	public var r(get, set):Int;
	public var g(get, set):Int;
	public var b(get, set):Int;
	public var mult(get, set):Float;
	/** Values while no own palette exists; an own palette is the truth after. */
	var valueR:Int = 0xFFFF0000;
	var valueG:Int = 0xFF00FF00;
	var valueB:Int = 0xFF0000FF;
	var valueMult:Float = 1.0;
	/** The last shared palette used and the values it was picked for. */
	var shared:PsychRGBPalette;
	var sharedR:Int = 0;
	var sharedG:Int = 0;
	var sharedB:Int = 0;
	var sharedMult:Float = -1;

	public static inline var MAX_POOLED:Int = 512;
	/** Shared palettes are never dropped, so their number is capped. A script
		that tweens note colours or mult makes a new combination every frame;
		without the cap each one would build a shader and keep it for the rest of
		the session. Past the cap a note draws with its own palette, as before
		sharing existed. */
	public static inline var MAX_SHARED:Int = 128;
	static var sharedPalettes:Map<String, PsychRGBPalette> = new Map();
	static var sharedCount:Int = 0;
	static var pool:Array<PsychRGBPalette> = [];
	/** Replaceable for tests: builds a palette with its shader. */
	public static var makePalette:Void->PsychRGBPalette = function() return new PsychRGBPalette();

	function get_palette():PsychRGBPalette {
		if (own == null) {
			own = pool.length > 0 ? pool.pop() : makePalette();
			own.r = valueR;
			own.g = valueG;
			own.b = valueB;
			own.mult = valueMult;
		}
		return own;
	}
	function get_r():Int return own != null ? own.r : valueR;
	function set_r(value:Int):Int return own != null ? own.r = value : valueR = value;
	function get_g():Int return own != null ? own.g : valueG;
	function set_g(value:Int):Int return own != null ? own.g = value : valueG = value;
	function get_b():Int return own != null ? own.b : valueB;
	function set_b(value:Int):Int return own != null ? own.b = value : valueB = value;
	function get_mult():Float return own != null ? own.mult : valueMult;
	// Same clamp as PsychRGBPalette.set_mult, so a later own palette agrees.
	function set_mult(value:Float):Float return own != null ? own.mult = value : valueMult = Math.max(0, Math.min(1, value));

	public function new(?base:PsychRGBPalette) {
		if (base != null) copyValues(base);
	}

	/** Take another palette's colours and mult, like PsychRGBPalette.copyValues. */
	public function copyValues(other:PsychRGBPalette):Void {
		if (own != null) {
			own.copyValues(other);
			return;
		}
		if (other == null) {
			valueMult = 0.0;
			return;
		}
		valueR = other.r;
		valueG = other.g;
		valueB = other.b;
		valueMult = other.mult;
	}

	/** The palette in use without creating one; null while a shared one draws. */
	public function ownPalette():Null<PsychRGBPalette> return own;

	/** Hand an own palette back for reuse, keeping its values. Call when the
		sprite that drew with it is destroyed. */
	public function release():Void {
		if (own == null)
			return;
		valueR = own.r;
		valueG = own.g;
		valueB = own.b;
		valueMult = own.mult;
		if (pool.length < MAX_POOLED && pool.indexOf(own) < 0)
			pool.push(own);
		own = null;
	}

	function sharedPalette(effectiveMult:Float):PsychRGBPalette {
		if (shared != null && sharedR == valueR && sharedG == valueG && sharedB == valueB && sharedMult == effectiveMult)
			return shared;
		var key = valueR + ':' + valueG + ':' + valueB + ':' + effectiveMult;
		var found = sharedPalettes.get(key);
		if (found == null) {
			if (sharedCount >= MAX_SHARED)
				return null;
			sharedCount++;
			found = makePalette();
			found.r = valueR;
			found.g = valueG;
			found.b = valueB;
			found.mult = effectiveMult;
			found.shader.u_alpha.value = [1.0];
			found.shader.u_flash.value = [0.0];
			sharedPalettes.set(key, found);
		}
		shared = found;
		sharedR = valueR;
		sharedG = valueG;
		sharedB = valueB;
		sharedMult = effectiveMult;
		return found;
	}

	public function setColors(colors:Array<Int>):Void {
		if (colors == null || colors.length < 3) throw '[nightmare-vision-note] RGB needs three colors';
		r = colors[0]; g = colors[1]; b = colors[2];
	}
	public function getColors():Array<Int> return [r, g, b];

	/** Per-object uniforms are never written into the shared lane palette. */
	public function apply(sprite:flixel.FlxSprite):Void {
		if (legacyHSV != null) {
			legacyHSV.daAlpha = alpha;
			legacyHSV.flash = flash;
			sprite.shader = legacyHSV.shader;
			return;
		}
		if (legacyHSL != null) {
			sprite.shader = legacyHSL.shader;
			return;
		}
		if (own == null && alpha == 1 && flash == 0) {
			var common = sharedPalette(enabled ? valueMult : 0);
			if (common != null) {
				sprite.shader = common.shader;
				return;
			}
		}
		var mine = get_palette();
		// This runs for every note with its own palette on every frame. Writing
		// the one value in place keeps each uniform the same as a new
		// one-element array would, without the garbage. The palette's shader
		// belongs to this graphic alone, and OpenFL reads uniforms when the
		// frame renders.
		var multValue = mine.shader.mult.value;
		if (multValue != null && multValue.length == 1) multValue[0] = enabled ? mine.mult : 0;
		else mine.shader.mult.value = [enabled ? mine.mult : 0];
		var alphaValue = mine.shader.u_alpha.value;
		if (alphaValue != null && alphaValue.length == 1) alphaValue[0] = alpha;
		else mine.shader.u_alpha.value = [alpha];
		var flashValue = mine.shader.u_flash.value;
		if (flashValue != null && flashValue.length == 1) flashValue[0] = flash;
		else mine.shader.u_flash.value = [flash];
		sprite.shader = mine.shader;
	}
}
