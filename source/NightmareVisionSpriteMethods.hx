package;

import flixel.FlxSprite;
import flixel.FlxObject;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.util.FlxAxes;
import flixel.util.FlxColor;

/** One implementation of the five pinned FlxMacro sprite conveniences. */
@:keep
class NightmareVisionSpriteMethods
{
	static inline var OWNER_FIELD:String = '__nightmareVisionSpriteOwner';
	public static function bind(sprite:FlxSprite, owner:Null<NightmareVisionSpriteOwner>):Void
	{
		// hxcpp class instances inherit Object.__HasField=false. Native class metadata
		// lists the kept cell independently of its nullable value, including inheritance.
		if (sprite == null || Type.getInstanceFields(Type.getClass(sprite)).indexOf(OWNER_FIELD) < 0)
			throw '[nightmare-vision-sprite] Receiver lacks the targeted owner cell';
		Reflect.setField(sprite, OWNER_FIELD, owner);
	}

	/** Clear the borrowed cell after source teardown, without releasing the provider. */
	public static function clear(sprite:FlxSprite):Void
	{
		if (Reflect.field(sprite, OWNER_FIELD) != null) Reflect.setField(sprite, OWNER_FIELD, null);
	}

	static function selected(sprite:FlxSprite):NightmareVisionSpriteOwner
	{
		var owner:NightmareVisionSpriteOwner = Reflect.field(sprite, OWNER_FIELD);
		if (owner == null) throw '[nightmare-vision-sprite] Receiver has no selected atlas owner';
		return owner;
	}

	public static function loadFromSheet(sprite:FlxSprite, path:String, animName:String, fps:Int = 24,
		looped:Bool = true):FlxSprite
	{
		sprite.frames = selected(sprite).atlasFrames(path);
		sprite.animation.addByPrefix(animName, animName, fps, looped);
		sprite.animation.play(animName);
		if (sprite.animation.curAnim == null || sprite.animation.curAnim.numFrames == 1) sprite.active = false;
		return sprite;
	}

	public static function loadAtlasFrames(sprite:FlxSprite, frames:FlxAtlasFrames):FlxSprite
	{
		sprite.frames = frames;
		return sprite;
	}

	public static function makeScaledGraphic(sprite:FlxSprite, width:Float, height:Float,
		color:FlxColor = FlxColor.WHITE):FlxSprite
	{
		sprite.makeGraphic(1, 1, color, false, 'solid#${color.toHexString(true, false)}');
		sprite.scale.set(width, height);
		sprite.updateHitbox();
		return sprite;
	}

	public static function setScale(sprite:FlxSprite, x:Float, y:Float, update:Bool = true):FlxSprite
	{
		sprite.scale.set(x, y);
		if (update) sprite.updateHitbox();
		return sprite;
	}

	public static function centerOnObject(sprite:FlxSprite, object:FlxObject, axes:FlxAxes = XY):FlxSprite
	{
		if (axes.x) sprite.x = object.x + (object.width - sprite.width) / 2;
		if (axes.y) sprite.y = object.y + (object.height - sprite.height) / 2;
		return sprite;
	}
}
