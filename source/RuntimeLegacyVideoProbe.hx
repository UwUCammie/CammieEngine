package;

#if cpp
import flixel.FlxG;
import flixel.FlxState;

/** Opt-in native decoder fixture with private, generated owner directories. */
@:access(RuntimeSmokeHarness)
@:access(hxvlc.flixel.FlxInternalVideo)
class RuntimeLegacyVideoProbe {
	static var phase:Int = 0;
	static var since:Float = 0;
	static var began:Float = 0;
	static var first:NightmareVisionLegacyVideoSprite;
	static var other:NightmareVisionLegacyVideoSprite;
	static var otherState:FlxState;
	static var firstInterp:NightmareVisionScriptInterp;
	static var otherInterp:NightmareVisionScriptInterp;
	static var owners:Array<NightmareVisionSpriteOwner> = [];
	static var starts:Int = 0;
	static var formats:Int = 0;
	static var ends:Int = 0;
	static var pausedTime:Int = 0;
	static var restartTime:Int = 0;
	static var failures:Array<String> = [];
	static var eventFormats:Int = 0;
	static var eventShaderReady:Bool = false;
	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_LEGACY_VIDEO_SMOKE') == '1';
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function move(next:Int):Void {phase = next; since = haxe.Timer.stamp();}
	static function time(video:NightmareVisionLegacyVideoSprite):Int return haxe.Int64.toInt(video.bitmap.time);
	static function interpreter(state:FlxState, root:String):NightmareVisionScriptInterp {
		var paths = new NightmareVisionPaths(root);
		var owner = new NightmareVisionSpriteOwner(function(_) throw 'Unexpected atlas lookup');
		owners.push(owner);
		var interp = new NightmareVisionScriptInterp(state); interp.bindOwnerPaths(paths);
		NightmareVisionLegacyVideoBindings.install(interp, paths, owner);
		return interp;
	}
	static function control(name:String):Void {
		var fn = firstInterp.sourceClassScope().reflectFacade().field(NightmareVisionLegacyVideoSprite, name);
		Reflect.callMethod(null, fn, []);
	}
	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			var now = haxe.Timer.stamp();
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Muted private saves required');
				began = now; FlxG.autoPause = true;
				if (Sys.getEnv('CAMMIE_LEGACY_EVENT_VIDEO_SMOKE') == '1') {
					var paths = new NightmareVisionPaths('assets/imported_mods/generated-video-a');
					first = NightmareVisionLegacyEventVideo.play(FlxG.state, paths, FlxG.camera, 'clip', false);
					other = NightmareVisionLegacyEventVideo.play(FlxG.state, paths, FlxG.camera, 'clip');
					for (video in [first, other]) {
						video.addCallback('onFormat', function() eventFormats++);
						video.addCallback('onEnd', function() ends++);
						video.bitmap.onEncounteredError.add(function(error) failures.push(error));
					}
					move(10); return;
				}
				otherState = new FlxState(); FlxG.state.add(otherState);
				firstInterp = interpreter(FlxG.state, 'assets/imported_mods/generated-video-a');
				otherInterp = interpreter(otherState, 'assets/imported_mods/generated-video-b');
				first = cast firstInterp.createSourceInstance(NightmareVisionLegacyVideoSprite, [false]);
				other = cast otherInterp.createSourceInstance(NightmareVisionLegacyVideoSprite, [false]);
				FlxG.state.add(first); otherState.add(other);
				first.addCallback('onStart', function() starts++);
				first.addCallback('onFormat', function() formats++);
				first.addCallback('onEnd', function() ends++);
				first.bitmap.onEncounteredError.add(function(error) failures.push(error));
				other.bitmap.onEncounteredError.add(function(error) failures.push(error));
				check(first.load('clip', [NightmareVisionLegacyVideoSprite.muted]), 'First owner load');
				check(other.load('clip', [NightmareVisionLegacyVideoSprite.muted, NightmareVisionLegacyVideoSprite.looping]), 'Other owner load');
				check(first.play() && other.play(), 'Native play'); move(1); return;
			}
			check(failures.length == 0, 'Decoder error: ' + failures.join('; '));
			check(now - began < 55, 'Video lifecycle timed out in phase ' + phase + ' starts=' + starts + ' formats=' + formats + ' ends=' + ends);
			switch (phase) {
				case 1:
					if (time(first) < 2000 || !other.bitmap.isPlaying) return;
					check(starts == 1 && formats > 0, 'Native opening and format signals');
					control('globalPause'); move(2);
				case 2:
					if (now - since < 0.3) return;
					check(!first.bitmap.isPlaying && other.bitmap.isPlaying, 'Scoped pause changed foreign decoder');
					pausedTime = time(first); FlxG.signals.focusGained.dispatch(); move(3);
				case 3:
					if (now - since < 0.5) return;
					check(!first.bitmap.isPlaying && Math.abs(time(first) - pausedTime) < 150, 'Focus gain undid explicit pause');
					control('globalResume'); move(4);
				case 4:
					if (!first.bitmap.isPlaying || time(first) < pausedTime + 700) return;
					restartTime = time(first); first.restart([NightmareVisionLegacyVideoSprite.muted]); move(5);
				case 5:
					if (starts < 2 || !first.bitmap.isPlaying || time(first) < 100) return;
					check(time(first) < restartTime, 'Restart did not reset native playback'); move(6);
				case 6:
					if (ends == 0) return;
					check(ends == 1 && first.exists && first.bitmap != null, 'Reusable end lifetime');
					first.restart([NightmareVisionLegacyVideoSprite.muted]); move(7);
				case 7:
					if (starts < 3 || !first.bitmap.isPlaying) return;
					NightmareVisionVideoSprite.pauseForState(FlxG.state); move(8);
				case 8:
					if (now - since < 0.3) return;
					check(!first.bitmap.isPlaying && other.bitmap.isPlaying, 'Host pause ownership');
					NightmareVisionVideoSprite.resumeForState(FlxG.state); move(9);
				case 9:
					if (!first.bitmap.isPlaying) return;
					var decoder = first.bitmap;
					NightmareVisionVideoSprite.destroyForState(FlxG.state);
					check(first.bitmap == null && !first.exists && other.bitmap.isPlaying, 'Host teardown ownership');
					check(!FlxG.signals.focusGained.has(decoder.onFocusGained)
						&& !FlxG.signals.focusLost.has(decoder.onFocusLost), 'Decoder focus handlers survived teardown');
					check(NightmareVisionLegacyVideoSprite.forOwner(FlxG.state, 'assets/imported_mods/generated-video-a').length == 0, 'Destroyed owner registry');
					NightmareVisionVideoSprite.destroyForState(otherState);
					check(other.bitmap == null && !other.exists, 'Other host teardown');
					firstInterp.release(); otherInterp.release();
					for (owner in owners) owner.release();
					FlxG.state.remove(otherState, true); otherState.destroy();
					RuntimeSmokeHarness.emit('legacy_video_native_verified', {starts:starts, formats:formats, ends:ends,
						scopedPause:true, explicitPauseFocus:true, restart:true, restartAfterEnd:true, hostPauseResume:true,
						ownerTeardown:true, focusHandlersRemoved:true, elapsedSeconds:now-began});
					RuntimeSmokeHarness.succeed();
				case 10:
					if (eventFormats < 2) return;
					check(!first.visible && other.visible, 'Hidden preparation and visible playback');
					for (video in [first, other]) {
						check(video.cameras[0] == FlxG.camera && video.scrollFactor.x == 0 && video.scrollFactor.y == 0, 'Video camera and scroll factor');
						check(Math.abs(video.height - FlxG.height) < 1 && video.x == 0 && video.y == 0, 'Source height fit and position');
						check(Std.isOfType(video.shader, NightmareVisionGreenScreenShader), 'Source chroma-key shader');
					}
					if (Reflect.field(other.shader, 'glProgram') == null) return;
					eventShaderReady = true; move(11);
				case 11:
					if (ends < 2) return;
					check(!first.exists && first.bitmap == null && !other.exists && other.bitmap == null, 'End releases both decoders');
					check(NightmareVisionLegacyVideoSprite.forOwner(FlxG.state, 'assets/imported_mods/generated-video-a').length == 0, 'Event video registry released');
					RuntimeSmokeHarness.emit('legacy_event_video_native_verified', {formats:eventFormats, ends:ends,
						hiddenPreparation:true, visiblePlayback:true, sourceGeometry:true, shaderProgramReady:eventShaderReady,
						ownerTeardown:true, elapsedSeconds:now-began});
					RuntimeSmokeHarness.succeed();
				default:
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('legacy-video', Std.string(error));
	}
}
#end
