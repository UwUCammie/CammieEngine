package;

/**
	Nightmare Vision's `funkin.objects.stageobjects.BackgroundGirls`, bound to
	the owner that constructed it. The constructor loads the source's default
	week 6 atlas and the calm dance; scripts usually replace both afterwards,
	so a missing default atlas only leaves the sprite without frames.
*/
@:keep
class NightmareVisionBackgroundGirls extends NightmareVisionFlxSprite {
	var isPissed:Bool = true;
	var danceDir:Bool = false;

	public function new(x:Float = 0, y:Float = 0, ?ownerPaths:NightmareVisionPaths) {
		super(x, y, null, ownerPaths);
		if (ownerPaths == null)
			throw '[nightmare-vision-asset] BackgroundGirls requires its imported owner paths';
		frames = ownerPaths.getSparrowAtlas('backgrounds/weeb/bgFreaks');
		swapDanceType();
		animation.play('danceLeft');
	}

	/** Toggles between the calm and dissuaded dance, as the source does. */
	@:keep public function swapDanceType():Void {
		isPissed = !isPissed;
		var prefix = isPissed ? 'BG fangirls dissuaded' : 'BG girls group';
		animation.addByIndices('danceLeft', prefix, [for (i in 0...14) i], '', 24, false);
		animation.addByIndices('danceRight', prefix, [for (i in 15...30) i], '', 24, false);
		dance();
	}

	@:keep public function dance():Void {
		danceDir = !danceDir;
		animation.play(danceDir ? 'danceRight' : 'danceLeft', true);
	}
}
