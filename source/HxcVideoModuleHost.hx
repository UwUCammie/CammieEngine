package;

#if cpp
import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import flixel.util.FlxTimer;
import hxvlc.flixel.FlxVideoSprite;

private typedef HxcVideoModuleEntry = {
	var video:FlxVideoSprite;
	var bars:FlxSprite;
	var config:Dynamic;
}

/**
	Native owner for the complete HXC video-module pattern. It keeps hxvlc,
	Flixel sprites, and HUD transitions behind one engine boundary; generated
	HScript receives only the module-shaped methods below.
*/
class HxcVideoModuleHost {
	var state:PlayState;
	var assetRoot:String;
	var entries:Array<HxcVideoModuleEntry> = [];
	var fadeHUD:Bool = false;
	var fadeOutTween:FlxTween;
	var fadeInTween:FlxTween;
	var disposed:Bool = false;

	public function new(state:PlayState, assetRoot:String) {
		this.state = state;
		this.assetRoot = assetRoot;
	}

	public function getDefaultConfig():Dynamic {
		return {
			videoType: 1,
			disableControls: false,
			hudFadeDuration: 1,
			resync: true,
			zIndex: 300,
			mute: false,
			timestamp: Conductor.songPosition
		};
	}

	public function createVideo(filePath:Dynamic, ?config:Dynamic):Dynamic {
		if (disposed || state == null || filePath == null)
			return null;
		var cleanPath = state.hxcResolveImportedVideoPath(filePath, assetRoot);
		if (cleanPath == null)
			return null;

		var options = mergeConfig(config);
		var videoType = Std.int(numberField(options, 'videoType', 1));
		var fadeDuration = Math.max(0, numberField(options, 'hudFadeDuration', 1));
		if (videoType == 2)
			Reflect.setField(options, 'timestamp', numberField(options, 'timestamp', Conductor.songPosition)
				+ fadeDuration * 1000);

		var video = new FlxVideoSprite(null, 0, 0);
		var bars = new FlxSprite(0, 0).makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
		var entry:HxcVideoModuleEntry = {video: video, bars: bars, config: options};
		var camera:FlxCamera = videoType == 3 ? state.camCutscene : state.camHUD;
		video.cameras = [camera];
		bars.cameras = [camera];
		video.scrollFactor.set(0, 0);
		bars.scrollFactor.set(0, 0);
		HxcCompatRuntime.setZIndex(video, numberField(options, 'zIndex', 300));
		HxcCompatRuntime.setZIndex(bars, numberField(options, 'zIndex', 300) - 1);

		if (video.bitmap != null) {
			video.bitmap.onEncounteredError.add(function(_error:Dynamic) {
				if (entry.video != null) {
					removeEntry(entry);
					showPlaybackError();
				}
			}, true);
			video.bitmap.onEndReached.add(function() onEndReached(entry), true);
			video.bitmap.onFormatSetup.add(function() fitVideo(video));
		}

		state.add(bars);
		state.add(video);
		state.refresh();
		entries.push(entry);

		switch (videoType) {
			case 2:
				fadeHUD = true;
				if (state.camHUD != null) {
					FlxTween.cancelTweensOf(state.camHUD, ['alpha']);
					fadeOutTween = FlxTween.tween(state.camHUD, {alpha: 0}, fadeDuration, {
						ease: FlxEase.quadOut,
						onComplete: function(_tween:FlxTween) {
							if (entry.video != null && entry.bars != null && state.camCutscene != null) {
								entry.video.cameras = [state.camCutscene];
								entry.bars.cameras = [state.camCutscene];
							}
							startVideo(entry, cleanPath);
						}
					});
				} else {
					if (state.camCutscene != null) {
						video.cameras = [state.camCutscene];
						bars.cameras = [state.camCutscene];
					}
					startVideo(entry, cleanPath);
				}
			case 3:
				if (state.camHUD != null)
					state.camHUD.visible = false;
				startVideo(entry, cleanPath);
			default:
				startVideo(entry, cleanPath);
		}
		return video;
	}

	public function update(_event:Dynamic):Void {
		for (entry in entries.copy())
			if (entry != null && entry.video != null && entry.bars != null) {
				entry.bars.visible = entry.video.visible;
				entry.bars.alpha = entry.video.alpha;
			}
	}

	public function focusGained(_event:Dynamic):Void {
		if (state != null && state.isGamePaused)
			for (entry in entries.copy())
				if (entry != null && entry.video != null)
					entry.video.pause();
	}

	public function stepHit(_event:Dynamic):Void {
		for (entry in entries.copy())
			if (entry != null && entry.video != null && boolField(entry.config, 'resync', true)
				&& entry.video.bitmap != null && entry.video.bitmap.isPlaying)
				checkResync(entry.video, false, true);
	}

	public function pause(_event:Dynamic):Void {
		if (fadeOutTween != null)
			fadeOutTween.active = false;
		if (fadeInTween != null)
			fadeInTween.active = false;
		for (entry in entries.copy())
			if (entry != null && entry.video != null) {
				entry.video.pause();
				if (boolField(entry.config, 'resync', true))
					checkResync(entry.video, true, false);
			}
	}

	public function resume(_event:Dynamic):Void {
		if (fadeOutTween != null)
			fadeOutTween.active = true;
		if (fadeInTween != null)
			fadeInTween.active = true;
		for (entry in entries.copy())
			if (entry != null && entry.video != null)
				entry.video.resume();
	}

	public function songRetry(_event:Dynamic):Void {
		if (fadeHUD) {
			if (fadeOutTween != null)
				fadeOutTween.cancel();
			if (state != null && state.camHUD != null)
				fadeInTween = FlxTween.tween(state.camHUD, {alpha: 1}, 0.5, {ease: FlxEase.quadInOut});
			fadeHUD = false;
		} else if (state != null && state.camHUD != null)
			state.camHUD.visible = true;
		clearVideoSprites();
	}

	public function gameOver(_event:Dynamic):Void
		clearVideoSprites();

	public function songEnd(_event:Dynamic):Void
		clearVideoSprites();

	public function countdownStart(_event:Dynamic):Void
		clearVideoSprites();

	public function checkResync(video:Dynamic, ?instant:Bool = false, ?resumeAfter:Bool = true):Void {
		if (state == null || video == null)
			return;
		var entry = findEntry(video);
		if (entry == null || entry.video.bitmap == null)
			return;
		var expected = Conductor.songPosition - Conductor.offset
			- numberField(entry.config, 'timestamp', Conductor.songPosition);
		var actual = numberValue(entry.video.bitmap.time, Math.NaN);
		if (!Math.isFinite(expected) || !Math.isFinite(actual)
			|| (!instant && Math.abs(actual - expected) <= 550))
			return;
		entry.video.pause();
		entry.video.bitmap.time = Std.int(Math.max(0, expected));
		if (resumeAfter)
			entry.video.resume();
	}

	public function clearVideoSprites():Void {
		for (entry in entries.copy())
			removeEntry(entry);
		entries.resize(0);
	}

	public function destroy():Void {
		if (disposed)
			return;
		disposed = true;
		if (fadeOutTween != null)
			fadeOutTween.cancel();
		if (fadeInTween != null)
			fadeInTween.cancel();
		clearVideoSprites();
		// This finalizer runs while PlayState is transitioning out. Its camera may
		// already be in Flixel teardown, so do not write HUD properties here. The
		// live end/retry paths restore HUD state before the PlayState is destroyed.
		state = null;
	}

	public function blocksControls():Bool
		return !disposed && entries.length > 0 && hasControlDisablingVideo();

	function hasControlDisablingVideo():Bool {
		for (entry in entries)
			if (entry != null && boolField(entry.config, 'disableControls', false))
				return true;
		return false;
	}

	function startVideo(entry:HxcVideoModuleEntry, path:String):Void {
		if (disposed || state == null || entry == null || entry.video == null
			|| entry.video.bitmap == null)
			return;
		if (!entry.video.load(path)) {
			removeEntry(entry);
			showPlaybackError();
			return;
		}
		entry.video.play();
		entry.video.bitmap.volumeAdjust = boolField(entry.config, 'mute', false) ? 0 : 1;
	}

	function fitVideo(video:FlxVideoSprite):Void {
		if (video == null || video.bitmap == null || video.bitmap.bitmapData == null)
			return;
		var width = video.bitmap.bitmapData.width;
		var height = video.bitmap.bitmapData.height;
		if (width <= 0 || height <= 0)
			return;
		var scale = Math.min(FlxG.width / width, FlxG.height / height);
		video.setGraphicSize(width * scale + 10, height * scale);
		video.updateHitbox();
		video.screenCenter();
	}

	function onEndReached(entry:HxcVideoModuleEntry):Void {
		if (entry == null || entries.indexOf(entry) < 0)
			return;
		if (fadeHUD) {
			if (state != null && state.camHUD != null)
				fadeInTween = FlxTween.tween(state.camHUD, {alpha: 1}, 0.5, {ease: FlxEase.quadInOut});
			fadeHUD = false;
		}
		if (state != null && state.camHUD != null)
			state.camHUD.visible = true;
		removeEntry(entry);
	}

	function removeEntry(entry:HxcVideoModuleEntry):Void {
		if (entry == null)
			return;
		entries.remove(entry);
		if (state != null) {
			if (entry.bars != null) state.remove(entry.bars, true);
			if (entry.video != null) state.remove(entry.video, true);
			state.refresh();
		}
		entry.bars = null;
		entry.video = null;
	}

	function findEntry(video:Dynamic):HxcVideoModuleEntry {
		for (entry in entries)
			if (entry != null && entry.video == video)
				return entry;
		return null;
	}

	function showPlaybackError():Void {
		if (state == null)
			return;
		var message = new FlxText(140, 240, Math.max(0, FlxG.width - 280), ' AN ERROR OCCURED\nDURING VIDEO PLAYBACK!');
		message.setFormat(null, 24, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		message.cameras = [state.camHUD];
		HxcCompatRuntime.setZIndex(message, 5000);
		state.add(message);
		new FlxTimer().start(10, function(_timer:FlxTimer) {
			if (state != null) state.remove(message, true);
			else message.destroy();
		});
	}

	function mergeConfig(config:Dynamic):Dynamic {
		var output = getDefaultConfig();
		if (config != null)
			for (field in ['videoType', 'disableControls', 'hudFadeDuration', 'resync', 'zIndex', 'mute', 'timestamp']) {
				var value = Reflect.field(config, field);
				if (value != null)
					Reflect.setField(output, field, value);
			}
		return output;
	}

	static function boolField(source:Dynamic, name:String, fallback:Bool):Bool {
		if (source == null)
			return fallback;
		var value = Reflect.field(source, name);
		if (value == null)
			return fallback;
		if (Std.isOfType(value, Bool))
			return cast value;
		var normalized = StringTools.trim(Std.string(value)).toLowerCase();
		return normalized == 'true' || normalized == '1' || normalized == 'yes' || normalized == 'on';
	}

	static function numberField(source:Dynamic, name:String, fallback:Float):Float {
		return source == null ? fallback : numberValue(Reflect.field(source, name), fallback);
	}

	static function numberValue(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}
}
#else
/** A no-op type keeps generated HXC bridge references valid on non-native targets. */
class HxcVideoModuleHost {
	public function new(_state:PlayState, _assetRoot:String) {}
	public function getDefaultConfig():Dynamic return null;
	public function createVideo(_filePath:Dynamic, ?_config:Dynamic):Dynamic return null;
	public function update(_event:Dynamic):Void {}
	public function focusGained(_event:Dynamic):Void {}
	public function stepHit(_event:Dynamic):Void {}
	public function pause(_event:Dynamic):Void {}
	public function resume(_event:Dynamic):Void {}
	public function songRetry(_event:Dynamic):Void {}
	public function gameOver(_event:Dynamic):Void {}
	public function songEnd(_event:Dynamic):Void {}
	public function countdownStart(_event:Dynamic):Void {}
	public function checkResync(_video:Dynamic, ?_instant:Bool = false, ?_resumeAfter:Bool = true):Void {}
	public function clearVideoSprites():Void {}
	public function destroy():Void {}
	public function blocksControls():Bool return false;
}
#end
