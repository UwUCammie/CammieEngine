package;

import flixel.FlxSprite;
import flixel.math.FlxMath;

/**
 * A short-lived copy of a character's current frame.
 *
 * Modding Plus charts use the name "crossfade" for this afterimage effect,
 * rather than fading the note itself. Keeping it as a normal FlxSprite makes
 * it safe to recycle and keeps the effect independent of a particular chart
 * or character implementation.
 */
class CrossFade extends FlxSprite {
	/** Default time for an afterimage to fade out, in seconds. */
	public static var defaultDuration:Float = 0.35;
	/** Initial afterimage opacity relative to the source character. */
	public static var defaultAlpha:Float = 0.65;

	private var fadeElapsed:Float = 0;
	private var fadeDuration:Float = defaultDuration;
	private var startAlpha:Float = defaultAlpha;

	public function new() {
		super();
		visible = false;
		active = false;
	}

	/**
	 * Copy the visible state of a character without sharing its animation
	 * controller. The frame/atlas is shared read-only, so this does not decode
	 * another texture for every note.
	 */
	public function resetShit(character:Character, ?duration:Float = -1, ?alpha:Float = -1):Void {
		if (character == null || character.frame == null) {
			kill();
			return;
		}

		loadGraphicFromSprite(character);
		// loadGraphicFromSprite copies the current frame, but its cloned
		// controller would otherwise continue animating the afterimage.
		animation.pause();

		x = character.x;
		y = character.y;
		offset.copyFrom(character.offset);
		origin.copyFrom(character.origin);
		scale.copyFrom(character.scale);
		scrollFactor.copyFrom(character.scrollFactor);
		flipX = character.flipX;
		flipY = character.flipY;
		angle = character.angle;
		antialiasing = character.antialiasing;
		blend = character.blend;
		shader = character.shader;
		cameras = character.cameras;

		// Ported character scripts use crossFadeColor when the afterimage should
		// have a special tint (Cycles Wrath's Lord X uses red). Fall back to the
		// character's current tint so custom colour transforms are retained.
		color = character.crossFadeColor == null ? character.color : character.crossFadeColor;
		fadeDuration = duration > 0 ? duration : defaultDuration;
		startAlpha = FlxMath.bound((alpha > 0 ? alpha : defaultAlpha) * character.alpha, 0, 1);
		this.alpha = startAlpha;
		fadeElapsed = 0;
		revive();
		visible = character.visible && startAlpha > 0;
		active = visible;
	}

	override public function update(elapsed:Float):Void {
		if (!alive || !exists)
			return;
		fadeElapsed += elapsed;
		var progress = FlxMath.bound(fadeElapsed / fadeDuration, 0, 1);
		alpha = startAlpha * (1 - progress);
		if (progress >= 1) {
			kill();
			return;
		}
		super.update(elapsed);
	}
}
