package;

import flixel.FlxG;

/** Explicit, muted observation of the ordinary TitleState startup path. */
class RuntimeStartupProbe {
	static var requested:Null<Bool> = null;
	static var startedAt:Float = 0;
	static var previousAt:Float = 0;
	static var introReady:Bool = false;
	static var firstDraw:Bool = false;
	static var finished:Bool = false;
	static var logPath:String = '';
	static var observeMs:Float = 0;
	static var screenshotPath:String = '';
	static var menuEntryPhase:Int = 0;

	public static function enabled():Bool {
		#if sys
		if (requested == null) requested = Sys.args().indexOf('--profile-startup') >= 0;
		return requested;
		#else
		return false;
		#end
	}

	public static function begin():Void {
		if (!enabled()) return;
		startedAt = previousAt = haxe.Timer.stamp();
		#if sys
		var args = Sys.args();
		var at = args.indexOf('--profile-startup-log');
		logPath = at >= 0 && at + 1 < args.length ? args[at + 1] : 'startup-profile.log';
		var observeAt = args.indexOf('--profile-startup-observe-ms');
		if (observeAt >= 0 && observeAt + 1 < args.length) {
			var duration = Std.parseFloat(args[observeAt + 1]);
			if (Math.isFinite(duration) && duration > 0) observeMs = duration;
		}
		var screenshotAt = args.indexOf('--profile-startup-screenshot');
		if (screenshotAt >= 0 && screenshotAt + 1 < args.length) screenshotPath = args[screenshotAt + 1];
		#end
		mark('main_enter');
	}

	public static function mark(phase:String):Void {
		if (!enabled() || finished) return;
		var now = haxe.Timer.stamp();
		var line = 'STARTUP_PROFILE|' + haxe.Json.stringify({phase: phase,
			elapsedMs: (now - startedAt) * 1000, phaseMs: (now - previousAt) * 1000});
		previousAt = now;
		#if sys
		Sys.println(line);
		if (logPath != '') {
			var output = sys.io.File.append(logPath, false);
			output.writeString(line + '\n');
			output.close();
		}
		#end
	}

	public static function mute():Void {
		if (enabled()) FlxG.sound.muted = true;
	}

	public static function titleIntroReady():Void {
		if (!enabled()) return;
		mark('title_intro_ready');
		introReady = true;
	}

	public static function install():Void {
		if (!enabled()) return;
		FlxG.autoPause = false;
		mute();
		FlxG.signals.preUpdate.add(mute);
		FlxG.signals.postDraw.add(afterDraw);
		#if (sys && lime)
		if (Sys.args().indexOf('--profile-startup-enter-menu') >= 0) FlxG.signals.postUpdate.add(enterMenu);
		#end
	}

	#if (sys && lime)
	static function enterMenu():Void {
		if (finished || menuEntryPhase >= 4 || (haxe.Timer.stamp() - startedAt) < 6) return;
		if (!Std.isOfType(FlxG.state,TitleState)) return;
		var down = menuEntryPhase % 2 == 0;
		if (menuEntryPhase == 2 && Reflect.field(FlxG.state,'skippedIntro') != true) return;
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN
			: openfl.events.KeyboardEvent.KEY_UP,true,false,13,13));
		menuEntryPhase++;
	}
	#end

	static function afterDraw():Void {
		if (finished) return;
		if (!firstDraw) {
			firstDraw = true;
			mark('first_draw');
		}
		if (introReady) {
			if (observeMs > 0 && (haxe.Timer.stamp() - startedAt) * 1000 < observeMs) return;
			#if (sys && lime)
			if (observeMs > 0) {
				var music = FlxG.sound.music;
				Sys.println('STARTUP_STATE|' + haxe.Json.stringify({state:Type.getClassName(Type.getClass(FlxG.state)),
					beat:Reflect.field(FlxG.state,'curBeat'), skippedIntro:Reflect.field(FlxG.state,'skippedIntro'),
					musicTime:music == null ? null : music.time, musicPlaying:music != null && music.playing,
					elapsed:FlxG.elapsed, frameRate:FlxG.drawFramerate, muted:FlxG.sound.muted}));
				if (screenshotPath != '') {
					var pixels = lime.app.Application.current.window.readPixels();
					if (pixels != null) sys.io.File.saveBytes(screenshotPath,pixels.encode(lime.graphics.ImageFileFormat.PNG));
				}
			}
			#end
			mark('startup_complete');
			finished = true;
			#if sys
			Sys.exit(0);
			#end
		}
	}
}
