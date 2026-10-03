package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;

/** NMV owner-scoped inputs for its persistent PsychHUD popup roots. */
typedef NightmareVisionRatingPresentationConfig = {
	var paths:NightmareVisionPaths;
	var camera:FlxCamera;
	var addDisplay:Dynamic->Dynamic;
	var callScript:String->Array<Dynamic>->Dynamic;
	var hideHud:Void->Bool;
	var useEpicRankings:Void->Bool;
	var showRatings:Bool;
	var comboOffsets:Array<Int>;
	@:optional var ratingPrefix:String;
	@:optional var ratingSuffix:String;
	@:optional var comboPrefix:String;
	@:optional var comboTween:Bool;
}

/** Nightmare Vision's PsychHUD implementation keeps a single rating sprite
	and recyclable digit group, scaling/fading each popup with expo tweens. This
	intentionally does not inherit classic Psych's per-hit physics renderer. */
@:keep
class NightmareVisionRatingPresentation {
	public var ratingGraphic(default, null):FlxSprite;
	public var ratingNumGroup(default, null):FlxTypedGroup<FlxSprite>;
	public var showRating:Bool;
	public var showRatingNum:Bool;
	public var showCombo:Bool;
	public var ratingPrefix:String;
	public var ratingSuffix:String;
	public var comboPrefix(get, set):String;
	public var comboTween:Bool;
	public var comboOffsets:Array<Int>;

	var paths:NightmareVisionPaths;
	var camera:FlxCamera;
	var addDisplay:Dynamic->Dynamic;
	var callScript:String->Array<Dynamic>->Dynamic;
	var hideHud:Void->Bool;
	var useEpicRankings:Void->Bool;
	var released:Bool = false;
	// Older NMV HUDs use ratingPrefix for both ratings and digits. Keep that
	// live relationship until a script explicitly selects the newer API field.
	var comboPrefixOverride:Null<String> = null;

	public function new(config:NightmareVisionRatingPresentationConfig) {
		if (config == null || config.paths == null || config.camera == null
			|| config.addDisplay == null || config.callScript == null
			|| config.hideHud == null || config.useEpicRankings == null)
			throw '[nightmare-vision-hud] Rating presentation requires owner paths and host callbacks';

		paths = config.paths;
		camera = config.camera;
		addDisplay = config.addDisplay;
		callScript = config.callScript;
		hideHud = config.hideHud;
		useEpicRankings = config.useEpicRankings;
		showRating = config.showRatings;
		showRatingNum = config.showRatings;
		showCombo = config.showRatings;
		ratingPrefix = config.ratingPrefix == null ? paths.RATINGS_PREFIX : config.ratingPrefix;
		ratingSuffix = config.ratingSuffix == null ? '' : config.ratingSuffix;
		comboPrefixOverride = config.comboPrefix;
		comboTween = config.comboTween == null ? true : config.comboTween;
		comboOffsets = config.comboOffsets == null ? [0, 0, 0, 0] : config.comboOffsets.copy();
		if (comboOffsets.length < 4)
			throw '[nightmare-vision-hud] comboOffsets must contain rating X/Y and digit X/Y offsets';

		ratingGraphic = new FlxSprite();
		ratingGraphic.alpha = 0;
		ratingGraphic.cameras = [camera];
		addDisplay(ratingGraphic);

		ratingNumGroup = new FlxTypedGroup<FlxSprite>();
		ratingNumGroup.cameras = [camera];
		addDisplay(ratingNumGroup);
	}

	function get_comboPrefix():String {
		ensureAlive();
		return comboPrefixOverride != null ? comboPrefixOverride
			: paths.usesSharedRatingPrefix ? ratingPrefix : paths.COMBO_PREFIX;
	}
	function set_comboPrefix(value:String):String {
		ensureAlive();
		return comboPrefixOverride = value == null ? '' : value;
	}

	/** Match NMV PsychHUD.cachePopUpScore's owner-routed asset loads. */
	@:keep public function cachePopUpScore():Void {
		ensureAlive();
		var ratings = ['sick', 'good', 'bad', 'shit'];
		if (useEpicRankings()) ratings.push('epic');
		for (rating in ratings)
			ratingGraphic.loadGraphic(paths.image(ratingPrefix + rating + ratingSuffix));
		for (i in 0...10)
			paths.image(comboPrefix + 'num' + i + ratingSuffix);
	}

	/** Match NMV PsychHUD's persistent objects, digit recycling, and scale/fade tweens. */
	@:keep public function popUpScore(rating:Dynamic, combo:Int, note:Dynamic):Void {
		ensureAlive();
		var scriptRating = PsychRatingPresentationCommon.sourceRating(rating);
		var ratingImage = PsychRatingPresentationCommon.sourceRatingImage(scriptRating);
		if (hideHud()) return;

		callScript('onPopUpScore', [note, scriptRating, ratingGraphic, ratingNumGroup]);

		var posX = FlxG.width * 0.35;
		if (showRating) {
			FlxTween.cancelTweensOf(ratingGraphic, ['scale.x', 'scale.y', 'alpha']);
			ratingGraphic.alpha = 1;
			ratingGraphic.loadGraphic(paths.image(ratingPrefix + ratingImage + ratingSuffix));
			ratingGraphic.screenCenter();
			PsychRatingPresentationCommon.positionRating(ratingGraphic, posX, comboOffsets);

			if (comboTween) {
				ratingGraphic.scale.set(0.785, 0.785);
				FlxTween.tween(ratingGraphic.scale, {x:0.7, y:0.7}, 0.5, {ease:FlxEase.expoOut});
			}
			ratingGraphic.updateHitbox();
			FlxTween.tween(ratingGraphic, {alpha:0}, 0.5, {
				startDelay:Conductor.stepCrochet * 0.01,
				ease:FlxEase.expoOut
			});
		}

		// Source exposes showCombo but gates these digits with showRatingNum.
		if (showRatingNum) {
			for (digit in ratingNumGroup) {
				if (digit != null && digit.alive) digit.kill();
			}

			var separatedScore:Array<Int> = [];
			if (combo >= 1000) separatedScore.push(Math.floor(combo / 1000) % 10);
			separatedScore.push(Math.floor(combo / 100) % 10);
			separatedScore.push(Math.floor(combo / 10) % 10);
			separatedScore.push(combo % 10);

			var digitIndex = 0;
			for (digitValue in separatedScore) {
				var digit:FlxSprite = ratingNumGroup.recycle(FlxSprite);
				FlxTween.cancelTweensOf(digit);
				digit.loadGraphic(paths.image(comboPrefix + 'num' + digitValue + ratingSuffix));
				digit.alpha = 1;
				digit.screenCenter();
				PsychRatingPresentationCommon.positionComboDigit(digit, posX, digitIndex, comboOffsets);

				if (comboTween) {
					digit.scale.set(0.6, 0.6);
					FlxTween.cancelTweensOf(digit, ['scale.x', 'scale.y']);
					FlxTween.tween(digit.scale, {x:0.5, y:0.5}, 0.5, {ease:FlxEase.expoOut});
				}
				digit.updateHitbox();
				ratingNumGroup.add(digit);
				FlxTween.tween(digit, {alpha:0}, 0.5, {
					startDelay:Conductor.stepCrochet * 0.01,
					ease:FlxEase.expoOut
				});
				digitIndex++;
			}
		}

		callScript('onPopUpScorePost', [note, scriptRating, ratingGraphic, ratingNumGroup]);
	}

	/** Release references only. The owner state destroys its attached objects. */
	public function release():Void {
		if (released) return;
		released = true;
		ratingGraphic = null;
		ratingNumGroup = null;
		paths = null;
		camera = null;
		addDisplay = null;
		callScript = null;
		hideHud = null;
		useEpicRankings = null;
	}

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-hud] Rating presentation was released';
	}
}
