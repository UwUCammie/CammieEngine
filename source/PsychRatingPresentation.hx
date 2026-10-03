package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.tweens.FlxTween;

/** Classic Psych PlayState popup configuration. */
typedef PsychRatingPresentationConfig = {
	var image:String->Dynamic;
	var camera:FlxCamera;
	/** Attach the shared combo container to the owning state/display list. */
	var addDisplay:Dynamic->Dynamic;
	var hideHud:Void->Bool;
	var comboOffsets:Array<Int>;
	@:optional var ratings:Array<Dynamic>;
	@:optional var assetPrefix:String;
	@:optional var assetSuffix:String;
	@:optional var showRating:Bool;
	@:optional var showCombo:Bool;
	@:optional var showComboNum:Bool;
	@:optional var comboStacking:Bool;
	@:optional var playbackRate:Void->Float;
	@:optional var crochet:Void->Float;
	@:optional var isPixelStage:Bool;
	@:optional var pixelZoom:Float;
	@:optional var antialiasing:Bool;
	@:optional var randomInt:Int->Int->Int;
	@:optional var randomFloat:Float->Float->Float;
}

/** Classic Psych transient popup behavior: each judgement creates sprites
	with random physics and fade tweens. Nightmare Vision's persistent roots,
	recycling, and scale tweens live in NightmareVisionRatingPresentation. */
@:keep
class PsychRatingPresentation {
	public var comboGroup(default, null):FlxTypedGroup<FlxSprite>;
	public var showRating:Bool;
	public var showCombo:Bool;
	public var showComboNum:Bool;
	public var comboOffsets:Array<Int>;
	public var assetPrefix:String;
	public var assetSuffix:String;

	var image:String->Dynamic;
	var hideHud:Void->Bool;
	var ratings:Array<Dynamic>;
	var comboStacking:Bool;
	var playbackRate:Void->Float;
	var crochet:Void->Float;
	var isPixelStage:Bool;
	var pixelZoom:Float;
	var antialiasing:Bool;
	var randomInt:Int->Int->Int;
	var randomFloat:Float->Float->Float;
	var released:Bool = false;

	public function new(config:PsychRatingPresentationConfig) {
		if (config == null || config.image == null || config.camera == null
			|| config.addDisplay == null || config.hideHud == null)
			throw '[psych-hud] Rating presentation requires asset, camera, and host callbacks';
		image = config.image;
		hideHud = config.hideHud;
		ratings = config.ratings == null ? ['sick', 'good', 'bad', 'shit'] : config.ratings.copy();
		assetPrefix = config.assetPrefix == null ? '' : config.assetPrefix;
		assetSuffix = config.assetSuffix == null ? '' : config.assetSuffix;
		showRating = config.showRating == null ? true : config.showRating;
		showCombo = config.showCombo == null ? false : config.showCombo;
		showComboNum = config.showComboNum == null ? true : config.showComboNum;
		comboStacking = config.comboStacking == null ? true : config.comboStacking;
		comboOffsets = config.comboOffsets == null ? [0, 0, 0, 0] : config.comboOffsets.copy();
		if (comboOffsets.length < 4)
			throw '[psych-hud] comboOffsets must contain rating X/Y and digit X/Y offsets';
		playbackRate = config.playbackRate == null ? function():Float return 1 : config.playbackRate;
		crochet = config.crochet == null ? function():Float return 0 : config.crochet;
		isPixelStage = config.isPixelStage == null ? false : config.isPixelStage;
		pixelZoom = config.pixelZoom == null ? 6 : config.pixelZoom;
		antialiasing = config.antialiasing == null ? !isPixelStage : config.antialiasing;
		randomInt = config.randomInt == null ? function(min:Int, max:Int):Int return FlxG.random.int(min, max) : config.randomInt;
		randomFloat = config.randomFloat == null ? function(min:Float, max:Float):Float return FlxG.random.float(min, max) : config.randomFloat;

		comboGroup = new FlxTypedGroup<FlxSprite>();
		comboGroup.cameras = [config.camera];
		config.addDisplay(comboGroup);
	}

	/** Match classic Psych PlayState.cachePopUpScore's asset set. */
	@:keep public function cachePopUpScore():Void {
		ensureAlive();
		for (rating in ratings)
			image(assetPath(PsychRatingPresentationCommon.sourceRatingImage(rating)));
		for (i in 0...10)
			image(assetPath('num' + i));
	}

	/** Adapt the classic Psych per-hit sprite physics and destruction lifecycle. */
	@:keep public function popUpScore(rating:Dynamic, combo:Int, note:Dynamic):Void {
		ensureAlive();
		final rate = playbackRate();
		final hide = hideHud();
		if (!comboStacking && comboGroup.members.length > 0) {
			for (sprite in comboGroup.members.copy()) {
				if (sprite == null) continue;
				comboGroup.remove(sprite);
				sprite.destroy();
			}
		}

		final placement = FlxG.width * 0.35;
		final pixelScale = isPixelStage ? pixelZoom : 1.0;
		final ratingSprite = new FlxSprite();
		ratingSprite.loadGraphic(image(assetPath(PsychRatingPresentationCommon.sourceRatingImage(rating))));
		ratingSprite.screenCenter();
		PsychRatingPresentationCommon.positionRating(ratingSprite, placement, comboOffsets);
		ratingSprite.acceleration.y = 550 * rate * rate;
		ratingSprite.velocity.y -= randomInt(140, 175) * rate;
		ratingSprite.velocity.x -= randomInt(0, 10) * rate;
		ratingSprite.visible = !hide && showRating;
		ratingSprite.antialiasing = antialiasing;
		comboGroup.add(ratingSprite);

		final comboSprite = new FlxSprite().loadGraphic(image(assetPath('combo')));
		comboSprite.screenCenter();
		comboSprite.x = placement + comboOffsets[0];
		comboSprite.y -= comboOffsets[1];
		comboSprite.acceleration.y = randomInt(200, 300) * rate * rate;
		comboSprite.velocity.y -= randomInt(140, 160) * rate;
		comboSprite.visible = !hide && showCombo;
		comboSprite.antialiasing = antialiasing;
		comboSprite.y += 60;
		comboSprite.velocity.x += randomInt(1, 10) * rate;

		if (!isPixelStage) {
			ratingSprite.setGraphicSize(Std.int(ratingSprite.width * 0.7));
			comboSprite.setGraphicSize(Std.int(comboSprite.width * 0.7));
		} else {
			ratingSprite.setGraphicSize(Std.int(ratingSprite.width * pixelScale * 0.85));
			comboSprite.setGraphicSize(Std.int(comboSprite.width * pixelScale * 0.85));
		}
		comboSprite.updateHitbox();
		ratingSprite.updateHitbox();

		var digitIndex = 0;
		var rightmostX:Float = 0;
		if (showCombo) comboGroup.add(comboSprite);
		var scoreText = Std.string(combo);
		while (scoreText.length < 3) scoreText = '0' + scoreText;
		for (index in 0...scoreText.length) {
			var digitValue = Std.parseInt(scoreText.charAt(index));
			var digit = new FlxSprite().loadGraphic(image(assetPath('num' + digitValue)));
			digit.screenCenter();
			PsychRatingPresentationCommon.positionComboDigit(digit, placement, digitIndex, comboOffsets);
			if (!isPixelStage) digit.setGraphicSize(Std.int(digit.width * 0.5));
			else digit.setGraphicSize(Std.int(digit.width * pixelScale));
			digit.updateHitbox();
			digit.acceleration.y = randomInt(200, 300) * rate * rate;
			digit.velocity.y -= randomInt(140, 160) * rate;
			digit.velocity.x = randomFloat(-5, 5) * rate;
			digit.visible = !hide;
			digit.antialiasing = antialiasing;
			if (showComboNum) comboGroup.add(digit);
			final transientDigit = digit;
			FlxTween.tween(digit, {alpha:0}, 0.2 / rate, {
				startDelay:crochet() * 0.002 / rate,
				onComplete:function(_) transientDigit.destroy()
			});
			digitIndex++;
			if (digit.x > rightmostX) rightmostX = digit.x;
		}
		comboSprite.x = rightmostX + 50;

		FlxTween.tween(ratingSprite, {alpha:0}, 0.2 / rate,
			{startDelay:crochet() * 0.001 / rate});
		FlxTween.tween(comboSprite, {alpha:0}, 0.2 / rate, {
			startDelay:crochet() * 0.002 / rate,
			onComplete:function(_) {
				comboSprite.destroy();
				ratingSprite.destroy();
			}
		});
	}

	/** Release bridge references; the display owner destroys the group. */
	public function release():Void {
		if (released) return;
		released = true;
		comboGroup = null;
		image = null;
		hideHud = null;
		ratings = null;
		playbackRate = null;
		crochet = null;
		randomInt = null;
		randomFloat = null;
	}

	function ensureAlive():Void if (released) throw '[psych-hud] Rating presentation was released';
	function assetPath(name:String):String return assetPrefix + name + assetSuffix;

}
