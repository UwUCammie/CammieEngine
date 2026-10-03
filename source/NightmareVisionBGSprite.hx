package;

/**
	Nightmare Vision's owner-scoped equivalent of its `funkin.objects.BGSprite`.
	The source class is a FlxSprite convenience for either a static image or a
	Sparrow atlas with a looping idle animation. It intentionally leaves
	antialiasing at the sprite default, matching the Nightmare Vision source.
*/
@:keep
class NightmareVisionBGSprite extends NightmareVisionFlxSprite {
	var idleAnim:Null<String> = null;

	public function new(?image:String, x:Float = 0, y:Float = 0, scrollX:Float = 1,
		scrollY:Float = 1, ?animArray:Array<String>, loop:Bool = false,
		?ownerPaths:NightmareVisionPaths) {
		super(x, y, null, ownerPaths);
		if (ownerPaths == null)
			throw '[nightmare-vision-asset] BGSprite requires its imported owner paths';

		if (animArray != null) {
			if (image == null)
				throw '[nightmare-vision-asset] BGSprite atlas path is missing';
			frames = ownerPaths.getSparrowAtlas(image);
			for (anim in animArray) {
				animation.addByPrefix(anim, anim, 24, loop);
				if (idleAnim == null) {
					idleAnim = anim;
					animation.play(anim);
				}
			}
		} else {
			if (image != null)
				loadGraphic(ownerPaths.image(image));
			active = false;
		}
		scrollFactor.set(scrollX, scrollY);
	}

	@:keep public function dance(forceplay:Bool = false):Void {
		if (idleAnim != null)
			animation.play(idleAnim, forceplay);
	}
}
