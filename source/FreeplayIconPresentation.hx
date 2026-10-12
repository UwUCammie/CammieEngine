package;

import flixel.FlxSprite;

/** Menu-only presentation shared by host and imported Freeplay portraits. */
class FreeplayIconPresentation {
	static function add(sprite:FlxSprite, name:String, prefix:String, rate:Int, loop:Bool):Void {
		var indices:Array<Int> = [];
		var pattern = new EReg('^' + prefix + '([0-9]+)([.].*)?$', '');
		var named:Array<{index:Int, number:Float}> = [];
		for (i in 0...sprite.frames.frames.length) {
			var frame = sprite.frames.frames[i];
			if (frame.name != null && pattern.match(frame.name)) named.push({index:i, number:Std.parseFloat(pattern.matched(1))});
		}
		named.sort(function(a,b) return a.number == b.number ? a.index - b.index : Reflect.compare(a.number,b.number));
		for (frame in named) indices.push(frame.index);
		if (indices.length > 0) sprite.animation.add(name, indices, rate, loop);
	}

	/** Pixel portraits use the source idle/confirm/confirm-hold atlas at 10 FPS. */
	public static function configureAtlas(sprite:FlxSprite, pixel:Bool):Void {
		if (pixel) {
			add(sprite, 'icon', 'idle', 10, true);
			if (!sprite.animation.exists('icon')) sprite.animation.add('icon', [0], 0, false);
		}
		add(sprite, 'confirm', 'confirm', pixel ? 10 : 24, false);
		add(sprite, 'confirm-hold', 'confirm-hold', pixel ? 10 : 24, true);
	}

	public static function reset(sprite:FlxSprite, animated:Bool):Void {
		if (sprite == null || sprite.animation == null || !sprite.animation.exists('icon')) return;
		sprite.animation.play('icon', true);
		if (!animated) sprite.animation.pause();
	}

	/** Return a bounded presentation duration; asset animation advances normally. */
	public static function confirm(sprite:FlxSprite, animated:Bool):Float {
		if (sprite == null || sprite.animation == null) return 0.35;
		for (name in ['confirm', 'winning', 'dying']) if (sprite.animation.exists(name)) {
			sprite.animation.play(name, true);
			var anim = sprite.animation.curAnim;
			return name != 'confirm' || anim.frameRate <= 0 ? 0.35
				: Math.max(0.35, Math.min(2, anim.numFrames / anim.frameRate));
		}
		// Static health strips encode normal, losing, poisoned, winning slots.
		// A duplicated neutral slot is not an authored winning face.
		var strip = sprite.animation.getByName('icon');
		if (!animated && strip != null && strip.frames.length > 0) {
			reset(sprite, false);
			for (slot in [3, 1]) if (strip.frames.length > slot && strip.frames[slot] != strip.frames[0]) {
				sprite.animation.curAnim.curFrame = slot;
				break;
			}
		}
		return 0.35;
	}

	public static function update(sprite:FlxSprite):Void {
		var anim = sprite.animation.curAnim;
		if (anim != null && anim.name == 'confirm' && anim.finished && sprite.animation.exists('confirm-hold'))
			sprite.animation.play('confirm-hold');
	}
}
