package;

/** Historical actor event arguments over shared actor animation and cadence services. */
@:access(PlayState)
class NightmareVisionLegacyActorEvents {
	public static function apply(state:PlayState, name:String, value1:String, value2:String):Bool {
		switch (name) {
			case 'Hey!':
				// Preserve source string access while sharing Psych-family parsing/effects.
				var target = PsychHeyEventCompat.target(StringTools.trim(value1.toLowerCase()));
				state.sourceHeyEvent(target, PsychHeyEventCompat.duration(value2), true);
			case 'Set GF Speed':
				var speed:Int = Std.parseInt(value1);
				if (Math.isNaN(speed) || speed < 1) speed = 1;
				state.gfSpeed = speed;
			case 'Play Animation':
				state.playSourceEventAnimation(state.sourceAnimationEventActor(value2, true, true), value1, true);
			case 'Alt Idle Animation':
				state.applySourceAltIdleAnimation(value1, value2, true);
			default: return false;
		}
		return true;
	}
}
