package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup;
import flixel.tweens.FlxTween;

/** Source judgement presentation, deliberately separate from score bookkeeping.
 * Assets belong to the selected import; only the standard base score pack has
 * an explicit engine resource fallback. Tweens belong to this gameplay visit. */
@:keep
class CodenameNotePresentation extends FlxSpriteGroup {
	var paths:CodenamePaths;
	var fades:Map<FlxSprite, FlxTween> = [];
	var pausedFades:Array<FlxTween> = [];
	var missing:Map<String, Bool> = [];
	var cursor:Int = 0;
	var paused:Bool = false;

	public function new(root:String, x:Float, y:Float) {
		super(x, y, 25);
		paths = new CodenamePaths(root);
	}

	/** Codename scripts use this named pool operation; Flixel's inline recycle
		method is unavailable to HScript reflection. */
	public function recycleLoop(objectClass:Class<FlxSprite>):FlxSprite {
		var item = recycle(objectClass);
		var old = fades.get(item);
		if (old != null) {
			old.cancel();
			pausedFades.remove(old);
			fades.remove(item);
		}
		return item;
	}

	function sprite(event:CodenameNoteHitEvent, name:String, px:Float, py:Float,
		size:Float, antialias:Bool, delay:Float):FlxSprite {
		var key = event.ratingPrefix + name + event.ratingSuffix;
		var frames:flixel.graphics.frames.FlxFramesCollection = null;
		try frames = paths.getFrames(key) catch (error:Dynamic) {
			// Codename's bundled default score resources need not be in a mod.
			// Custom prefixes/suffixes never borrow a different owner's artwork.
			if (event.ratingPrefix == 'game/score/' && event.ratingSuffix == '') {
				var base = 'assets/images/' + name + '.png';
				if (FNFAssets.exists(base))
					frames = flixel.graphics.frames.FlxImageFrame.fromImage(FNFAssets.getBitmapData(base));
			}
			if (frames == null && !missing.exists(key)) {
				missing.set(key, true);
				trace('[codename-asset] Missing judgement graphic: ' + key + ' (' + error + ')');
			}
		}
		if (frames == null) return null;
		var item:FlxSprite = null;
		for (candidate in members) if (candidate != null && !candidate.exists) {
			item = candidate;
			break;
		}
		if (item == null) {
			if (length < maxSize) {
				item = new FlxSprite();
				add(item);
			} else {
				item = members[cursor++ % length];
			}
		}
		var old = fades.get(item);
		if (old != null) {
			old.cancel();
			pausedFades.remove(old);
		}
		item.revive();
		item.frames = frames;
		item.alpha = 1;
		item.angle = 0;
		item.velocity.set();
		item.acceleration.set();
		item.scale.set(size, size);
		item.antialiasing = antialias;
		item.updateHitbox();
		item.setPosition(x + px, y + py);
		var fade = FlxTween.tween(item, {alpha: 0}, 0.2, {
			startDelay: delay,
			onComplete: function(tween:FlxTween) {
				if (fades.get(item) == tween) {
					fades.remove(item);
					item.kill();
				}
			}
		});
		fades.set(item, fade);
		if (paused) {
			fade.active = false;
			pausedFades.push(fade);
		}
		return item;
	}

	public function display(event:CodenameNoteHitEvent, combo:Int, crochet:Float, minDigitDisplay:Int):Void {
		if (minDigitDisplay >= 0 && (combo == 0 || combo >= minDigitDisplay)) {
			if (event.displayCombo) {
				var label = sprite(event, 'combo', 0, 0, event.ratingScale,
					event.ratingAntialiasing, crochet * 0.001);
				if (label != null) {
					label.acceleration.y = 600;
					label.velocity.set(FlxG.random.int(1, 10), -150);
				}
			}
			var digits = Std.string(combo);
			while (digits.length < 3) digits = '0' + digits;
			for (i in 0...digits.length) {
				var digit = sprite(event, 'num' + digits.charAt(i), 43 * i - 90, 80,
					event.numScale, event.numAntialiasing, crochet * 0.002);
				if (digit != null) {
					digit.acceleration.y = FlxG.random.int(200, 300);
					digit.velocity.set(FlxG.random.float(-5, 5), -FlxG.random.int(140, 160));
				}
			}
		}
		if (event.displayRating) {
			var rating = sprite(event, event.rating, -40, -60, event.ratingScale,
				event.ratingAntialiasing, crochet * 0.001);
			if (rating != null) {
				rating.acceleration.y = 550;
				rating.velocity.set(-FlxG.random.int(0, 10), -FlxG.random.int(140, 175));
			}
		}
	}

	public function setPaused(value:Bool):Void {
		if (paused == value) return;
		paused = value;
		if (value) {
			for (fade in fades) if (fade.active) {
				fade.active = false;
				pausedFades.push(fade);
			}
		} else {
			for (fade in pausedFades) fade.active = true;
			pausedFades = [];
		}
	}

	override public function destroy():Void {
		for (fade in fades) fade.cancel();
		fades.clear();
		pausedFades = [];
		super.destroy();
	}
}
