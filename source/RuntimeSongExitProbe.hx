package;

import flixel.FlxG;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextFormat;

/** Opt-in, muted smoke timing for the normal pause-to-menu lifecycle. */
@:access(PauseSubState)
@:access(flixel.text.FlxText)
class RuntimeSongExitProbe {
	static var enabled:Bool = false;
	public static var decodeMenuMusic(default, null):Bool = false;
	static var target:String;
	static var phase:Int = 0;
	static var started:Float = 0;
	static var previous:Float = 0;
	static var pauseAt:Float = 0;
	static var destinationAt:Float = 0;

	public static function install():Void {
		#if sys
		var args = Sys.args();
		var at = args.indexOf('--profile-song-exit');
		if (!RuntimeSmokeHarness.enabled() || at < 0 || at + 1 >= args.length) return;
		target = args[at + 1];
		if (['main', 'freeplay', 'options'].indexOf(target) < 0) throw 'Unknown song exit target';
		enabled = true;
		decodeMenuMusic = args.indexOf("--profile-song-exit-decoded-audio") >= 0;
		FlxG.signals.postUpdate.add(observe);
		FlxG.signals.postDraw.add(afterDraw);
		#end
	}

	public static function mark(name:String):Void {
		#if sys
		if (!enabled || started == 0) return;
		var now = haxe.Timer.stamp();
		Sys.println('SONG_EXIT|' + haxe.Json.stringify({phase:name, target:target,
			elapsedMs:(now - started) * 1000, phaseMs:(now - previous) * 1000}));
		previous = now;
		#end
	}

	static function key(down:Bool):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN
			: openfl.events.KeyboardEvent.KEY_UP, true, false, 13, 13));
	}

	static function checkScoreMarkup():Void {
		var label = new SourceScoreText();
		label.text = 'Accuracy: 96.42% [FC]\n';
		var authored = new FlxTextFormat(0xFF55FF55);
		label.addFormat(authored, 0, 8);
		label.applySourceFormat(0xFFF16439, 17, 19);
		if (label._formatRanges.length != 2) throw 'Missing native rank markup';
		Reflect.setProperty(label, 'text', 'Rating: EXCELLENT (96.42%) - FC');
		if (label._formatRanges.length != 1 || label._formatRanges[0].format != authored)
			throw 'Stale native rank markup survived text replacement';
		label.destroy();
		#if sys
		Sys.println('SCORE_MARKUP|native_pass');
		#end
	}

	static function observe():Void {
		FlxG.sound.muted = true;
		if (phase == 0) {
			if (!Std.isOfType(FlxG.state, PlayState) || Conductor.songPosition < 5000) return;
			checkScoreMarkup();
			key(true);
			pauseAt = haxe.Timer.stamp();
			phase = 1;
			return;
		}
		if (phase == 1) {
			key(false);
			if (!Std.isOfType(FlxG.state.subState, PauseSubState)) {
				if (haxe.Timer.stamp() - pauseAt > 5) throw 'Pause did not open';
				return;
			}
			if (haxe.Timer.stamp() - pauseAt < 0.5) return;
			started = previous = haxe.Timer.stamp();
			mark('request');
			phase = 2;
			switch (target) {
				case 'freeplay': (cast FlxG.state.subState:PauseSubState).exitPauseToMenu();
				case 'options':
					SaveDataState.prevPath = 'freeplay';
					LoadingState.loadAndSwitchState(new SaveDataState());
				default: LoadingState.loadAndSwitchState(new MainMenuState());
			}
			mark('request-returned');
		}
	}

	static function afterDraw():Void {
		if (phase != 2) return;
		var expected = switch (target) {
			case 'options': Std.isOfType(FlxG.state, SaveDataState);
			case 'freeplay': Std.isOfType(FlxG.state, FreeplayState);
			default: Std.isOfType(FlxG.state, MainMenuState);
		};
		if (!expected) return;
		if (destinationAt == 0) {
			destinationAt = haxe.Timer.stamp();
			mark('destination-first-draw');
		} else if (haxe.Timer.stamp() - destinationAt > 0.5) {
			mark('complete');
			#if sys
			Sys.println('MENU_AUDIO|' + haxe.Json.stringify({time:FlxG.sound.music.time, length:FlxG.sound.music.length, playing:FlxG.sound.music.playing, looped:FlxG.sound.music.looped, muted:FlxG.sound.muted}));
			#end
			#if sys
			Sys.exit(0);
			#end
		}
	}
}
