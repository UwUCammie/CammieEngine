package;

import animate.FlxAnimate;
import animate.FlxAnimateFrames;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.util.FlxTimer;

using StringTools;

/** Owner-scoped subset of Nightmare Vision's Bopper stage API. */
@:keep
class NightmareVisionBopper extends FlxAnimate {
	/** Source Bopper exposes its FlxAnimate instance through this alias. */
	@:keep public var animateAtlas:FlxAnimate;

	public var ownerPaths(default, null):Null<NightmareVisionPaths>;
	public var danceEveryNumBeats:Int = 2;
	public var alternatingDance:Null<Bool>;
	public var canDance:Bool = true;
	public var idleSuffix:String = '';
	public var canPlayAnimations:Bool = true;
	public var onAnimationFinish(get, never):Dynamic;
	public var onAnimationFrameChange(get, never):Dynamic;
	public var onAnimationLoop(get, never):Dynamic;
	var forcedAnimationTimer:FlxTimer = new FlxTimer();
	function get_onAnimationFinish():Dynamic return animation.onFinish;
	function get_onAnimationFrameChange():Dynamic return animation.onFrameChange;
	function get_onAnimationLoop():Dynamic return animation.onLoop;
	var danced:Bool = false;

	public function new(?x:Float = 0, ?y:Float = 0, danceEveryNumBeats:Int = 2,
		?ownerPaths:NightmareVisionPaths) {
		super(x, y);
		animateAtlas = this;
		this.ownerPaths = ownerPaths;
		this.danceEveryNumBeats = danceEveryNumBeats;
	}

	/** Match source Bopper.loadAtlas for owner-local Animate or Flixel atlases. */
	@:keep public function loadAtlas(path:String):NightmareVisionBopper {
		var paths = requireOwnerPaths();
		var loaded:Array<FlxAtlasFrames> = [];
		for (part in path.split(',')) {
			var key = StringTools.trim(part);
			if (key == '') continue;
			loaded.push(paths.getTextureAtlas(key));
		}
		if (loaded.length == 0)
			throw '[nightmare-vision-asset] Bopper.loadAtlas needs an owner atlas path';
		frames = loaded.length == 1 ? loaded[0] : FlxAnimateFrames.combineAtlas(loaded);
		return this;
	}

	/** Match source FunkinSprite's symbol/frame-label-aware prefix helper. */
	@:keep public function addAnimByPrefix(name:String, prefix:String, fps:Int = 24,
		looping:Bool = true, flipX:Bool = false, flipY:Bool = false):Void {
		if (library != null && anim.findFrameLabelIndices(prefix).length > 0)
			anim.addByFrameLabel(name, prefix, fps, looping, flipX, flipY);
		else if (hasSymbol(library, prefix))
			anim.addBySymbol(name, prefix, fps, looping, flipX, flipY);
		else
			animation.addByPrefix(name, prefix, fps, looping, flipX, flipY);
	}

	/** Search merged Animate collections, matching Nightmare Vision's helper. */
	@:access(animate.FlxAnimateFrames)
	static function hasSymbol(atlas:FlxAnimateFrames, symbol:String):Bool {
		if (atlas == null) return false;
		if (atlas.existsSymbol(symbol)) return true;
		for (collection in atlas.addedCollections)
			if (collection.dictionary.exists(symbol)) return true;
		return false;
	}

	@:keep public function dance(?forced:Bool = false):Void {
		if (alternatingDance == null)
			recalculateDanceIdle();
		if (!canDance) return;
		if (alternatingDance) {
			danced = !danced;
			playBopperAnim((danced ? 'danceRight' : 'danceLeft') + idleSuffix, forced);
		} else
			playBopperAnim('idle' + idleSuffix, forced);
	}

	@:keep public function recalculateDanceIdle():Void
		alternatingDance = animation.exists('danceLeft' + idleSuffix)
			&& animation.exists('danceRight' + idleSuffix);

	@:keep public function onBeatHit(beat:Int):Void {
		if (danceEveryNumBeats > 0 && beat % danceEveryNumBeats == 0)
			dance();
	}

	function playBopperAnim(name:String, ?forced:Bool = false):Void {
		playAnim(name, forced);
	}

	/** FunkinSprite's animation helpers use the FlxAnimate controller through
	 * the same Flixel animation property for texture and ordinary atlases. */
	@:keep public function correctAnimationName(name:String):Null<String> {
		if (animation.exists(name)) return name;
		var suffix = name.lastIndexOf('-');
		return suffix < 0 ? null : correctAnimationName(name.substring(0, suffix));
	}

	@:keep public function playAnim(name:String, forced:Bool = false,
		reversed:Bool = false, frame:Int = 0):Void {
		if (!canPlayAnimations) return;
		var corrected = correctAnimationName(name);
		if (corrected != null) animation.play(corrected, forced, reversed, frame);
	}

	/** Match FunkinSprite's timed play helper for its Bopper subclass. */
	@:keep public function playAnimForDuration(animToPlay:String, duration:Float = 0.6,
		forced:Bool = false):Void {
		if (forced) canPlayAnimations = true;
		playAnim(animToPlay, true);
		if (forced) canPlayAnimations = false;
		forcedAnimationTimer.start(duration, function(_:FlxTimer):Void {
			if (forced) canPlayAnimations = true;
		});
	}

	@:keep public function pauseAnim():Void animation.pause();
	@:keep public function resumeAnim():Void animation.resume();

	function requireOwnerPaths():NightmareVisionPaths {
		if (ownerPaths == null)
			throw '[nightmare-vision-asset] Bopper is not bound to an imported owner';
		return ownerPaths;
	}

	override public function destroy():Void {
		forcedAnimationTimer.cancel();
		forcedAnimationTimer.destroy();
		ownerPaths = null;
		super.destroy();
	}
}
