package;

#if cpp
import hxvlc.flixel.FlxVideoSprite;
import hxvlc.openfl.Location;
using StringTools;

/**
	Native FlxVideoSprite used by translated V-Slice HXC scripts.
	
	Unlike a cutscene host, this object stays alive when its media reaches the
	end. Source callbacks own looping, seeking, visibility, camera selection and
	playback; this class only bounds media access and supplies engine lifecycle
	cleanup.
*/
class HxcOwnedVideoSprite extends FlxVideoSprite {
	static var live:Array<HxcOwnedVideoSprite> = [];

	public var ownerState(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	var resolvedPath:String = null;
	var hostPaused:Bool = false;
	var disposed:Bool = false;

	public function new(ownerState:Dynamic, ownerRoot:String, x:Float = 0, y:Float = 0) {
		super(null, x, y);
		this.ownerState = ownerState;
		this.ownerRoot = ownerRoot;
		live.push(this);

		if (bitmap != null) {
			bitmap.onOpening.add(function() applySourcePlaybackRate());
			bitmap.onEncounteredError.add(function(error:String) {
				trace('[hxc-video-error] ' + resolvedPath + ': ' + error);
			});
		}
	}

	public static function create(ownerState:Dynamic, ownerRoot:String,
		x:Float = 0, y:Float = 0):HxcOwnedVideoSprite {
		return new HxcOwnedVideoSprite(ownerState, ownerRoot, x, y);
	}

	/** Resolve strings through the current imported owner's video boundary.
		Byte-backed video input is intentionally rejected: an HXC module must name
		media installed in its package or the shared native videos folder. */
	public override function load(location:Location, ?options:Array<String>):Bool {
		if (disposed || bitmap == null) {
			trace('[hxc-video-load-error] video sprite is no longer available');
			return false;
		}
		if (location == null || !Std.isOfType(location, String)) {
			trace('[hxc-video-rejected] byte-backed or unnamed media is not allowed for an imported HXC sprite');
			return false;
		}
		var resolution:Dynamic = HxcOwnedVideoPath.resolve(ownerRoot, cast location);
		var path:Dynamic = Reflect.field(resolution, 'path');
		if (path == null) {
			var code = Reflect.field(resolution, 'error');
			var detail = Reflect.field(resolution, 'detail');
			trace('[hxc-video-' + (code == null ? 'rejected' : Std.string(code)) + '] ' + detail);
			return false;
		}
		path = Std.string(path);
		resolvedPath = path;
		try {
			var loaded = super.load(path, options);
			if (!loaded)
				trace('[hxc-video-load-error] failed to load ' + path);
			return loaded;
		} catch (error:Dynamic) {
			trace('[hxc-video-load-error] ' + path + ': ' + Std.string(error));
			return false;
		}
	}

	/** Keep source playback-rate behavior without adding a second song clock. */
	function applySourcePlaybackRate():Void {
		if (bitmap == null || ownerState == null)
			return;
		var value:Dynamic = Reflect.getProperty(ownerState, 'playbackRate');
		if (value == null)
			return;
		var rate = Std.parseFloat(Std.string(value));
		if (!Math.isNaN(rate) && Math.isFinite(rate) && rate > 0)
			bitmap.rate = rate;
	}

	public override function play():Bool {
		if (disposed || bitmap == null) {
			trace('[hxc-video-play-error] video sprite is no longer available');
			return false;
		}
		try {
			var started = super.play();
			if (!started)
				trace('[hxc-video-play-error] unable to play ' + resolvedPath);
			return started;
		} catch (error:Dynamic) {
			trace('[hxc-video-play-error] ' + resolvedPath + ': ' + Std.string(error));
			return false;
		}
	}

	/** Pause only videos that were running when gameplay paused. */
	public static function pauseForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state || video.disposed || video.bitmap == null)
				continue;
			if (video.bitmap.isPlaying) {
				video.hostPaused = true;
				video.pause();
			}
		}
	}

	/** Resume only videos paused by the corresponding gameplay pause. */
	public static function resumeForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state || video.disposed || !video.hostPaused)
				continue;
			video.hostPaused = false;
			if (video.bitmap != null)
				video.resume();
		}
	}

	/** Dispose decoders and detach any top-level sprites owned by this state. */
	public static function destroyForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state)
				continue;
			var members:Dynamic = state == null ? null : Reflect.field(state, 'members');
			var attached = Std.isOfType(members, Array) && (cast members:Array<Dynamic>).indexOf(video) >= 0;
			if (attached) {
				var remove = Reflect.field(state, 'remove');
				if (Reflect.isFunction(remove))
					try Reflect.callMethod(state, remove, [video, true]) catch (_:Dynamic) {}
			}
			if (!video.disposed)
				video.destroy();
		}
	}

	public override function destroy():Void {
		if (disposed)
			return;
		disposed = true;
		hostPaused = false;
		live.remove(this);
		super.destroy();
	}
}
#else
/** Non-native targets fail clearly instead of leaving an unresolved HXC class. */
class HxcOwnedVideoSprite {
	public static function create(_state:Dynamic, _root:String, _x:Float = 0, _y:Float = 0):Dynamic {
		trace('[hxc-video-unsupported] native video playback is unavailable on this target');
		return null;
	}
	public static function pauseForState(_state:Dynamic):Void {}
	public static function resumeForState(_state:Dynamic):Void {}
	public static function destroyForState(_state:Dynamic):Void {}
}
#end
