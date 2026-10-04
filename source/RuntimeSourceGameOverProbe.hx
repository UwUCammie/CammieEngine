package;

import flixel.FlxG;

/** Opt-in native smoke input; ordinary launches never install these listeners. */
@:access(RuntimeSmokeHarness)
@:access(PlayState)
class RuntimeSourceGameOverProbe {
	static var installed:Bool = false;
	static var action:String;
	static var elapsed:Float = 0;
	static var presses:Int = 0;
	static var observed:Bool = false;
	static var finished:Bool = false;

	public static function install():Void {
		#if sys
		if (installed || !RuntimeSmokeHarness.enabled()) return;
		action = Sys.args().indexOf('--source-gameover-probe-retry') >= 0 ? 'retry'
			: Sys.args().indexOf('--source-gameover-probe-back') >= 0 ? 'back' : null;
		if (action == null) return;
		installed = true;
		FlxG.signals.postUpdate.add(tick);
		#end
	}

	static function tick():Void {
		if (finished) return;
		var substate = GameOverSubstate.instance;
		if (substate != null) {
			observed = true;
			elapsed += FlxG.elapsed;
			var mode = PlayState.instance == null ? 0 : PlayState.instance.sourceGameOverMode();
			var next = presses == 0 ? 1.0 : 2.0;
			if (elapsed >= next && presses < (mode == 2 ? 2 : 1)) {
				presses++;
				RuntimeSmokeHarness.markGameOverPhase('probe_input', {action:action, press:presses});
				RuntimeSmokeHarness.simulateKey(action == 'retry' ? 'enter' : 'escape');
			}
			return;
		}
		if (!observed) return;
		var correctState = action == 'retry' ? Std.isOfType(FlxG.state, PlayState)
			: Std.isOfType(FlxG.state, FreeplayState) || Std.isOfType(FlxG.state, StoryMenuState);
		if (!correctState) return;
		if (action == 'retry' && (PlayState.instance.isDead || PlayState.instance.paused)) {
			RuntimeSmokeHarness.fail('source-gameover-probe', 'Retry retained a dead or paused song');
			return;
		}
		finished = true;
		RuntimeSmokeHarness.markGameOverPhase('probe_handoff', {action:action, presses:presses,
			state:Type.getClassName(Type.getClass(FlxG.state)), muted:FlxG.sound.muted});
		FlxG.signals.postUpdate.remove(tick);
		// This explicit probe ends at its verified handoff, before another
		// unplayed song can die and turn a bounded navigation check into a loop.
		// Retry initializes a new visit, resetting the request's death flag;
		// retain the death this listener already observed in the outgoing visit.
		RuntimeSmokeHarness.config().gameOverTriggered = true;
		RuntimeSmokeHarness.succeed();
	}
}
