package;

import flixel.FlxSprite;
import flixel.util.FlxColor;

/** Per-sprite view of a shared palette, with Psych-compatible copy-on-write. */
@:keep
class PsychRGBShaderReference {
	public var r(default, set):FlxColor;
	public var g(default, set):FlxColor;
	public var b(default, set):FlxColor;
	public var mult(default, set):Float;
	public var enabled(default, set):Bool = true;
	/** A per-note palette edited through the Psych-facing RGB setters. */
	public var hasCustomPalette(default, null):Bool = false;
	/** A script explicitly toggled this reference after construction. */
	public var explicitlyEnabled(default, null):Bool = false;
	public var parent:PsychRGBPalette;
	public var allowNew:Bool = true;

	var owner:FlxSprite;
	var original:PsychRGBPalette;

	public function new(owner:FlxSprite, palette:PsychRGBPalette) {
		this.owner = owner;
		parent = palette;
		original = palette;
		owner.shader = palette.shader;
		r = palette.r;
		g = palette.g;
		b = palette.b;
		mult = palette.mult;
	}

	/** Select a new built-in palette after the note lane or note kind changes. */
	public function usePalette(palette:PsychRGBPalette):Void {
		if (palette == null || palette == original)
			return;
		original = palette;
		parent = palette;
		allowNew = true;
		hasCustomPalette = false;
		r = palette.r;
		g = palette.g;
		b = palette.b;
		mult = palette.mult;
		if (enabled)
			owner.shader = palette.shader;
	}

	function set_r(value:FlxColor):FlxColor {
		if (value != original.r) {
			hasCustomPalette = true;
			if (allowNew) cloneOriginal();
		}
		return (r = parent.r = value);
	}

	function set_g(value:FlxColor):FlxColor {
		if (value != original.g) {
			hasCustomPalette = true;
			if (allowNew) cloneOriginal();
		}
		return (g = parent.g = value);
	}

	function set_b(value:FlxColor):FlxColor {
		if (value != original.b) {
			hasCustomPalette = true;
			if (allowNew) cloneOriginal();
		}
		return (b = parent.b = value);
	}

	function set_mult(value:Float):Float {
		if (value != original.mult) {
			hasCustomPalette = true;
			if (allowNew) cloneOriginal();
		}
		return (mult = parent.mult = value);
	}

	function set_enabled(value:Bool):Bool {
		explicitlyEnabled = value;
		owner.shader = value ? parent.shader : null;
		return enabled = value;
	}

	function cloneOriginal():Void {
		if (!allowNew)
			return;
		allowNew = false;
		if (original != parent)
			return;
		parent = parent.copy();
		if (enabled)
			owner.shader = parent.shader;
	}
}
