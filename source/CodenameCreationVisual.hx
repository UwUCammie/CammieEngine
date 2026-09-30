package;

import animate.FlxAnimateFrames;
import flixel.FlxSprite;
import flixel.graphics.frames.FlxFramesCollection;
import flixel.math.FlxMatrix;

/** Prefix animation setup shared by Codename note/receptor atlas overrides.
 * The owner-scoped resolver supplies frames so Sparrow trim/rotation metadata
 * survives; this helper never turns an atlas into a raw bitmap strip. */
@:keep
class CodenameCreationVisual {
	static var warnedAnimateAtlases:Map<String, Bool> = new Map<String, Bool>();

	/** Return the atlas selected by an active Codename creation event. The
	 * default sentinel is a real owner-scoped atlas key; callers should pass it
	 * through the same resolver as an authored replacement. */
	public static function selectedAtlasPath(ownerActive:Bool, requested:String,
		cancelled:Bool):Null<String> {
		if (!ownerActive || cancelled || requested == null || requested == '') return null;
		return requested;
	}

	public static function setNotePrefixes(sprite:FlxSprite, direction:String,
		suffix:String, sustain:Bool):Void {
		if (sprite == null || sprite.animation == null) return;
		sprite.animation.destroyAnimations();
		// Codename's animSuffix is a character sing suffix, not part of the
		// note atlas prefix. Atlas frames use prefixes such as `blue0` and
		// `blue hold piece` regardless of the hit animation suffix.
		var notePrefix = direction == null ? '' : direction;
		sprite.animation.addByPrefix('Scroll', notePrefix + '0');
		sprite.animation.addByPrefix('scroll', notePrefix + '0');
		if (sustain) {
			if (direction == 'purple') {
				// Codename's default atlas historically names the purple frame
				// `pruple end hold`; use its upstream fallback order so both that
				// atlas spelling and the corrected name resolve correctly.
				sprite.animation.addByPrefix('holdend', 'pruple end hold');
				if (!sprite.animation.exists('holdend'))
					sprite.animation.addByPrefix('holdend', 'purple hold end');
			} else
				sprite.animation.addByPrefix('holdend', direction + ' hold end');
			sprite.animation.addByPrefix('hold', direction + ' hold piece');
		}
	}

	/** Apply a Codename Sparrow/Packer/plain frames collection before a note's
	 * hitbox is measured. Passing the resolved collection preserves source atlas
	 * trim and rotation metadata. */
	public static function applyNoteAtlas(sprite:FlxSprite, frames:FlxFramesCollection,
		direction:String, suffix:String, sustain:Bool, noteScale:Float,
		?ownerRoot:String, ?atlasPath:String):Bool {
		if (sprite == null || frames == null
			|| !supportsStaticSpriteAtlas(frames, ownerRoot, atlasPath)) return false;
		sprite.frames = frames;
		setNotePrefixes(sprite, direction, suffix, sustain);
		sprite.scale.set(noteScale, noteScale);
		sprite.updateHitbox();
		return true;
	}

	/** Apply a receptor atlas and its normal static/press/confirm animation names. */
	public static function applyStrumAtlas(sprite:FlxSprite, frames:FlxFramesCollection,
		animPrefix:String, scale:Float, antialiasing:Bool = true,
		?ownerRoot:String, ?atlasPath:String):Bool {
		if (sprite == null || frames == null
			|| !supportsStaticSpriteAtlas(frames, ownerRoot, atlasPath)) return false;
		sprite.frames = frames;
		setStrumPrefixes(sprite, animPrefix);
		sprite.antialiasing = antialiasing;
		sprite.setGraphicSize(Std.int(sprite.width * scale));
		sprite.updateHitbox();
		return true;
	}

	/** A FlxAnimateFrames collection needs FlxAnimate's timeline renderer. These
	 * native note and receptor sprites use FlxSprite's frame-prefix controller,
	 * so reject the collection and let their callers use the native UI fallback. */
	static function supportsStaticSpriteAtlas(frames:FlxFramesCollection,
		ownerRoot:String, atlasPath:String):Bool {
		if (frames == null || Std.isOfType(frames, FlxAnimateFrames) == false) return frames != null;
		var key = (ownerRoot == null ? '' : ownerRoot) + '\n'
			+ (atlasPath == null ? '' : atlasPath);
		if (!warnedAnimateAtlases.exists(key)) {
			warnedAnimateAtlases.set(key, true);
			trace('[codename-atlas-unsupported] ' + (atlasPath == null ? '<unknown atlas>' : atlasPath)
				+ ' in ' + (ownerRoot == null || ownerRoot == '' ? '<selected owner>' : ownerRoot)
				+ ' uses Animate timeline data. Native FlxSprite notes/receptors cannot render that timeline; '
				+ 'the native UI fallback will be used. Atlas files remain available to the selected owner.');
		}
		return false;
	}

	/** Apply the Codename note frame nudge before the normal sprite transform. */
	public static inline function applyFrameOffset(matrix:FlxMatrix, x:Float, y:Float):Void
		matrix.translate(-x, -y);

	public static function noteDirection(strumId:Int):String {
		var lane = (strumId % 4 + 4) % 4;
		return switch (lane) {
			case 0: 'purple';
			case 1: 'blue';
			case 2: 'green';
			default: 'red';
		};
	}

	public static function setStrumPrefixes(sprite:FlxSprite, animPrefix:String,
		frameRate:Float = 24):Void {
		if (sprite == null || sprite.animation == null) return;
		sprite.animation.destroyAnimations();
		var prefix = animPrefix == null ? '' : StringTools.trim(animPrefix);
		sprite.animation.addByPrefix('static', 'arrow' + prefix.toUpperCase(), frameRate);
		sprite.animation.addByPrefix('pressed', prefix + ' press', frameRate, false);
		sprite.animation.addByPrefix('confirm', prefix + ' confirm', frameRate, false);
	}

	public static function strumAnimPrefix(strumId:Int):String {
		return switch (strumId % 4) {
			case 0: 'left';
			case 1: 'down';
			case 2: 'up';
			default: 'right';
		};
	}
}
