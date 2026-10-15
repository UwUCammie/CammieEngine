package;

import flixel.FlxG;
import flixel.util.FlxTimer;

/**
	The full-screen video players older Psych mods construct by name, mapped
	onto the engine's hxvlc playback:

	- hxCodec 3 `hxcodec.flixel.FlxVideo`: `play(path, loop)`, the
	  `onEndReached` / `onTextureSetup` signals, `stop`, `pause`, `resume`,
	  `dispose`.
	- hxCodec 2 `vlc.MP4Handler` and `VideoHandler`: `playVideo(path, loop)`
	  with `finishCallback` and `readyCallback`.

	Both draw over the game like the originals, read `bitmapData` for scripts
	that copy frames onto a sprite, and are removed when the state changes so a
	video a script never disposed cannot outlive its song.
**/
@:keep
class LegacyVideoHandler {
	/** Every import path and addHaxeLibrary name the old players were reached by. */
	public static final SCRIPT_PATHS:Array<String> = ['hxcodec.flixel.FlxVideo', 'hxcodec.VideoHandler',
		'vlc.MP4Handler', 'VideoHandler', 'MP4Handler'];

	/**
		Builds the decoder for a new player. Native builds use hxvlc; other
		targets (and tests) supply their own object with the same members.
	**/
	public static var backendFactory:Void->Dynamic = defaultBackend;

	static var live:Array<LegacyVideoHandler> = [];
	static var stateHookAdded:Bool = false;

	/** The decoder object (hxvlc FlxVideo on native builds). */
	public var backend(default, null):Dynamic;

	/** hxCodec 3 signals, the decoder's own events. */
	public var onEndReached(get, never):Dynamic;
	public var onTextureSetup(get, never):Dynamic;
	public var onOpening(get, never):Dynamic;

	/** hxCodec 2 callbacks. */
	public var finishCallback:Void->Void;
	public var readyCallback:Void->Void;

	/**
		hxCodec 2 players (MP4Handler, VideoHandler) close themselves when the
		video ends and only then call finishCallback; scripts written for them
		never dispose. hxCodec 3's FlxVideo leaves that to the script.
	**/
	var closeOnEnd:Bool = false;

	public var bitmapData(get, never):Dynamic;
	public var alpha(get, set):Float;
	public var visible(get, set):Bool;

	/** 0 to 1, or 0 to 100 as hxCodec 3 counted it; follows the game volume either way. */
	public var volume(default, set):Float = 1;

	public var isPlaying(get, never):Bool;
	public var disposed(default, null):Bool = false;

	var startTimer:FlxTimer;

	public function new() {
		backend = backendFactory();
		if (backend != null) {
			listen('onEndReached', function() {
				if (closeOnEnd)
					dispose();
				if (finishCallback != null) finishCallback();
			});
			listen('onFormatSetup', function() {
				if (readyCallback != null) readyCallback();
			});
		}
		live.push(this);
		if (!stateHookAdded) {
			stateHookAdded = true;
			FlxG.signals.preStateSwitch.add(disposeAll);
		}
	}

	/** hxCodec 3: load and start; returns 0 when the video was accepted, -1 otherwise. */
	public function play(location:String, shouldLoop:Bool = false):Int
		return start(location, shouldLoop) ? 0 : -1;

	/** hxCodec 2. `pauseMusic` is accepted and ignored, as the song keeps its own audio. */
	public function playVideo(path:String, repeat:Bool = false, pauseMusic:Bool = false):Void {
		closeOnEnd = true;
		start(path, repeat);
	}

	function start(location:String, loop:Bool):Bool {
		if (disposed || backend == null || location == null || location == '')
			return false;
		var accepted = false;
		try {
			accepted = call('load', [location, loop ? [':input-repeat=65535'] : null]) == true;
		} catch (error:Dynamic) {
			trace('[legacy-video] load failed for ' + location + ': ' + Std.string(error));
		}
		if (!accepted) {
			trace('[legacy-video] could not open ' + location);
			return false;
		}
		attach();
		if (startTimer != null)
			startTimer.cancel();
		// The decoder needs the frame after load before play() takes effect.
		startTimer = new FlxTimer().start(0.001, function(_) {
			startTimer = null;
			if (!disposed) call('play', []);
		});
		return true;
	}

	public function stop():Void
		if (!disposed) call('stop', []);

	public function pause():Void
		if (!disposed) call('pause', []);

	public function resume():Void
		if (!disposed) call('resume', []);

	/** hxCodec 2 spelling of dispose. */
	public function kill():Void
		dispose();

	public function dispose():Void {
		if (disposed)
			return;
		disposed = true;
		if (startTimer != null) {
			startTimer.cancel();
			startTimer = null;
		}
		live.remove(this);
		if (backend != null) {
			detach();
			try call('dispose', []) catch (_:Dynamic) {}
		}
	}

	/** Every player still open, closed before the next state is built. */
	public static function disposeAll():Void
		for (video in live.copy())
			video.dispose();

	function attach():Void {
		if (Reflect.field(backend, 'parent') != null)
			return;
		#if cpp
		if (Std.isOfType(backend, openfl.display.DisplayObject))
			FlxG.addChildBelowMouse(cast backend);
		#end
	}

	function detach():Void {
		#if cpp
		if (Std.isOfType(backend, openfl.display.DisplayObject) && (cast backend:openfl.display.DisplayObject).parent != null)
			FlxG.removeChild(cast backend);
		#end
	}

	function listen(signal:String, listener:Void->Void):Void {
		var event:Dynamic = Reflect.getProperty(backend, signal);
		if (event != null && Reflect.isFunction(Reflect.field(event, 'add')))
			Reflect.callMethod(event, Reflect.field(event, 'add'), [listener]);
	}

	function call(name:String, args:Array<Dynamic>):Dynamic {
		var method = Reflect.field(backend, name);
		return Reflect.isFunction(method) ? Reflect.callMethod(backend, method, args) : null;
	}

	function get_onEndReached():Dynamic
		return backend == null ? null : Reflect.getProperty(backend, 'onEndReached');

	function get_onTextureSetup():Dynamic
		return backend == null ? null : Reflect.getProperty(backend, 'onFormatSetup');

	function get_onOpening():Dynamic
		return backend == null ? null : Reflect.getProperty(backend, 'onOpening');

	function get_bitmapData():Dynamic
		return backend == null ? null : Reflect.getProperty(backend, 'bitmapData');

	function get_alpha():Float {
		var value:Dynamic = backend == null ? null : Reflect.getProperty(backend, 'alpha');
		return value == null ? 1 : value;
	}

	function set_alpha(value:Float):Float {
		if (backend != null) Reflect.setProperty(backend, 'alpha', value);
		return value;
	}

	function get_visible():Bool
		return backend != null && Reflect.getProperty(backend, 'visible') != false;

	function set_visible(value:Bool):Bool {
		if (backend != null) Reflect.setProperty(backend, 'visible', value);
		return value;
	}

	function set_volume(value:Float):Float {
		var share = value > 1 ? value / 100 : value;
		if (share < 0) share = 0;
		if (backend != null) Reflect.setProperty(backend, 'volumeAdjust', share);
		return volume = value;
	}

	function get_isPlaying():Bool
		return backend != null && Reflect.getProperty(backend, 'isPlaying') == true;

	static function defaultBackend():Dynamic {
		#if cpp
		return new hxvlc.flixel.FlxVideo();
		#else
		return null;
		#end
	}
}
