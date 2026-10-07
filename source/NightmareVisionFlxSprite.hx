package;

import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxGraphicAsset;

using StringTools;

/** NMV's FlxSprite conveniences backed by the interpreter's selected owner. */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionFlxSprite extends FlxSprite {
	public var ownerPaths(default, null):Null<NightmareVisionPaths>;

	public function new(?x:Float = 0, ?y:Float = 0, ?simpleGraphic:Dynamic,
		?ownerPaths:NightmareVisionPaths) {
		super(x, y);
		this.ownerPaths = ownerPaths;
		NightmareVisionSpriteMethods.bind(this, NightmareVisionSpriteRegistry.capture(ownerPaths));
		if (simpleGraphic != null) loadGraphic(cast simpleGraphic);
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
