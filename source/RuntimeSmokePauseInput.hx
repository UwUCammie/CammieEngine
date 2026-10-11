package;

import flixel.FlxG;

/** Opt-in native keyboard regression, driven only inside a smoke process. */
@:access(RuntimeSmokeHarness)
@:access(PauseSubState)
class RuntimeSmokePauseInput {
	static var phase:Int = 0;
	static var cycles:Int = 0;
	static var nextAt:Float = 0;
	static var deadline:Float = 0;
	static var pausedTime:Float = 0;

	public static function install():Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || Sys.getEnv('CAMMIE_SMOKE_PAUSE_INPUT') != '1') return;
		deadline = Sys.time() + 60;
		FlxG.signals.postUpdate.add(update);
		#end
	}

	static function update():Void {
		#if sys
		if (RuntimeSmokeHarness.finished || cycles >= 2) return;
		var now = Sys.time();
		try {
			if (now > deadline) throw 'Pause input sequence timed out';
			if (now < nextAt || !RuntimeSmokeHarness.playStateReady || !Std.isOfType(FlxG.state, PlayState)) return;
			var play:PlayState = cast FlxG.state;
			var pause:PauseSubState = Std.isOfType(play.subState, PauseSubState) ? cast play.subState : null;
			switch (phase) {
				case 0:
					if (Conductor.songPosition < 1000) return;
					RuntimeSmokeHarness.simulateKey('escape');
				case 1:
					if (pause == null || !play.isGamePaused || pause.curSelected != 0) throw 'Native pause did not open';
					if (FlxG.sound.music.playing) throw 'Song audio still playing during pause';
					pausedTime = FlxG.sound.music.time;
					RuntimeSmokeHarness.simulateKey('down');
				case 2:
					if (pause == null || pause.curSelected != 1) throw 'Pause Down input did not move selection';
					RuntimeSmokeHarness.simulateKey('up');
				case 3:
					if (pause == null || pause.curSelected != 0) throw 'Pause Up input did not restore selection';
					if (Math.abs(FlxG.sound.music.time - pausedTime) > 50) throw 'Song clock advanced while paused';
					RuntimeSmokeHarness.simulateKey('enter');
				case 4:
					if (play.subState != null || play.isGamePaused || !FlxG.sound.music.playing) throw 'Pause Accept did not resume gameplay';
					cycles++;
					RuntimeSmokeHarness.emit('pause_input_cycle', {cycle:cycles, navigation:true, resumed:true});
			}
			phase = (phase + 1) % 5;
			nextAt = now + 0.35;
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('pause-input', Std.string(error));
		}
		#end
	}
}
