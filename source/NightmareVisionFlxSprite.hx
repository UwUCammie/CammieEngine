package;

import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxGraphicAsset;

using StringTools;

/** NMV's FlxSprite conveniences backed by the interpreter's selected owner. */
@:keep
class NightmareVisionFlxSprite extends FlxSprite {
	public var ownerPaths(default, null):Null<NightmareVisionPaths>;

	public function new(?x:Float = 0, ?y:Float = 0, ?simpleGraphic:Dynamic,
		?ownerPaths:NightmareVisionPaths) {
		super(x, y);
		this.ownerPaths = ownerPaths;
		if (simpleGraphic != null) loadGraphic(cast simpleGraphic);
	}

	/** NMV's FlxMacro.buildFlxSprite loadFromSheet implementation. */
	@:keep public function loadFromSheet(path:String, animName:String, fps:Int = 24,
		looped:Bool = true):NightmareVisionFlxSprite {
		var paths = requireOwnerPaths();
		frames = paths.getAtlasFrames(path);
		animation.addByPrefix(animName, animName, fps, looped);
		animation.play(animName);
		if (animation.curAnim == null || animation.curAnim.numFrames == 1)
			active = false;
		return this;
	}

	/** NMV's FlxMacro convenience used by imported stage scripts. */
	@:keep public function setScale(x:Float, y:Float, update:Bool = true):NightmareVisionFlxSprite {
		scale.set(x, y);
		if (update) updateHitbox();
		return this;
	}

	/** String graphics are looked up in this NMV package/core only. */
	override public function loadGraphic(graphic:FlxGraphicAsset, animated:Bool = false,
		frameWidth:Int = 0, frameHeight:Int = 0, unique:Bool = false, ?key:String):FlxSprite {
		if (ownerPaths != null && Std.isOfType(graphic, String)) {
			var imageKey:String = cast graphic;
			if (imageKey.toLowerCase().endsWith('.png'))
				imageKey = imageKey.substr(0, imageKey.length - 4);
			return super.loadGraphic(ownerPaths.image(imageKey), animated, frameWidth, frameHeight, unique, key);
		}
		return super.loadGraphic(graphic, animated, frameWidth, frameHeight, unique, key);
	}

	function requireOwnerPaths():NightmareVisionPaths {
		if (ownerPaths == null)
			throw '[nightmare-vision-asset] FlxSprite is not bound to an imported owner';
		return ownerPaths;
	}

	override public function destroy():Void {
		ownerPaths = null;
		super.destroy();
	}
}
