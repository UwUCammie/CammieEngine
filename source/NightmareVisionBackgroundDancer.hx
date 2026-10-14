package;

/**
	Nightmare Vision's `funkin.objects.stageobjects.BackgroundDancer`, bound to
	the owner that constructed it. It loads the source's limo dancer atlas and
	alternates its two dance halves.
*/
@:keep
class NightmareVisionBackgroundDancer extends NightmareVisionFlxSprite {
	var danceDir:Bool = false;

	public function new(x:Float = 0, y:Float = 0, ?ownerPaths:NightmareVisionPaths) {
		super(x, y, null, ownerPaths);
		if (ownerPaths == null)
			throw '[nightmare-vision-asset] BackgroundDancer requires its imported owner paths';
		frames = ownerPaths.getSparrowAtlas('backgrounds/limo/limoDancer');
		animation.addByIndices('danceLeft', 'bg dancer sketch PINK', [for (i in 0...15) i], '', 24, false);
		animation.addByIndices('danceRight', 'bg dancer sketch PINK', [for (i in 15...30) i], '', 24, false);
		animation.play('danceLeft');
	}

	@:keep public function dance():Void {
		danceDir = !danceDir;
		animation.play(danceDir ? 'danceRight' : 'danceLeft', true);
	}
}
