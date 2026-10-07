package;

import flixel.FlxCamera;
import flixel.FlxSprite;
import flixel.util.FlxColor;

/** The source PlayState owns one SCREEN overlay, independent of its fields. */
@:keep
class NightmareVisionScreenUnderlay {
	public static function createScreen(type:String, opacity:Float, camera:FlxCamera):Null<FlxSprite> {
		if (type != 'Screen Dim') return null;
		var sprite = new NightmareVisionFlxSprite().makeGraphic(1, 1, FlxColor.BLACK);
		sprite.alpha = opacity;
		sprite.scrollFactor.set();
		sprite.camera = camera;
		return sprite;
	}

	/** Source updates geometry before onUpdatePost; script color/alpha/camera remain live. */
	public static function updateScreen(type:String, sprite:FlxSprite):Void {
		if (type != 'Screen Dim' || sprite == null) return;
		sprite.scale.set(sprite.camera.width / sprite.camera.zoom, sprite.camera.height / sprite.camera.zoom);
		sprite.updateHitbox();
		sprite.screenCenter();
	}
}
