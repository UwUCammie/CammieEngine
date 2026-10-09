package;

/** Source playVideo choreography over the shared owner-scoped decoder. */
class NightmareVisionLegacyEventVideo {
	public static function play(state:flixel.FlxState, paths:NightmareVisionPaths,
		camera:flixel.FlxCamera, name:String, visible:Bool = true):NightmareVisionLegacyVideoSprite {
		var video = new NightmareVisionLegacyVideoSprite(state, paths);
		video.shader = new NightmareVisionGreenScreenShader();
		video.addCallback('onFormat', function() {
			video.cameras = [camera];
			video.scrollFactor.set();
			video.setGraphicSize(0, flixel.FlxG.height);
			video.updateHitbox();
			video.visible = visible;
		});
		video.addCallback('onEnd', function() video.destroy());
		video.load(paths.video(name));
		video.play();
		state.add(video);
		return video;
	}
}
