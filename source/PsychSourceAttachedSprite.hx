package;

import flixel.FlxSprite;

/** Psych 1.0.4 attachment sprite with owner-local construction. */
@:keep
class PsychSourceAttachedSprite extends FlxSprite
{
	public var sprTracker:FlxSprite;
	public var xAdd:Float = 0;
	public var yAdd:Float = 0;
	public var angleAdd:Float = 0;
	public var alphaMult:Float = 1;
	public var copyAngle:Bool = true;
	public var copyAlpha:Bool = true;
	public var copyVisible:Bool = false;

	public function new(?file:String = null, ?anim:String = null, ?parentFolder:String = null,
		?loop:Bool = false, ?owner:SourceAttachedSpriteOwner)
	{
		super();
		if (owner == null) throw '[source-attachment] Missing selected owner';
		if (anim != null) {
			frames = owner.sparrowAtlas(file, parentFolder);
			animation.addByPrefix('idle', anim, 24, loop);
			animation.play('idle');
		} else if (file != null) {
			loadGraphic(owner.image(file, parentFolder));
		}
		antialiasing = owner.antialiasing();
		scrollFactor.set();
	}

	override public function update(elapsed:Float)
	{
		super.update(elapsed);
		if (sprTracker != null) {
			setPosition(sprTracker.x + xAdd, sprTracker.y + yAdd);
			scrollFactor.set(sprTracker.scrollFactor.x, sprTracker.scrollFactor.y);
			if (copyAngle) angle = sprTracker.angle + angleAdd;
			if (copyAlpha) alpha = sprTracker.alpha * alphaMult;
			if (copyVisible) visible = sprTracker.visible;
		}
	}
}
