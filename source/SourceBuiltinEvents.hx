package;

/**
	Built-in chart events Psych and Nightmare Vision share. Both dialects run
	the same body for each event; the profile only picks a branch where the
	sources really disagree (Set GF Speed rounding, the historical revision's
	strict reads, Play Sound being Psych only). Effects go through PlayState's
	own camera, actor and song speed functions.
**/
@:access(PlayState)
class SourceBuiltinEvents {
	public static inline var PSYCH:Int = 0;
	public static inline var NIGHTMARE:Int = 1;
	public static inline var NIGHTMARE_LEGACY:Int = 2;

	public static inline var UNHANDLED:Int = 0;
	public static inline var HANDLED:Int = 1;
	/** The source returned early, before scripts were told about the event. */
	public static inline var STOPPED:Int = 2;

	/** Names are matched exactly, like the source switches, so host aliases keep their own routes. */
	public static function apply(state:PlayState, profile:Int, name:String, value1:String, value2:String):Int {
		var legacy = profile == NIGHTMARE_LEGACY;
		switch (name) {
			case 'Hey!':
				// The historical revision lowercases before trimming and needs a real boyfriend.
				if (legacy)
					state.sourceHeyEvent(PsychHeyEventCompat.target(StringTools.trim(value1.toLowerCase())),
						PsychHeyEventCompat.duration(value2), true);
				else state.sourceHeyEvent(PsychHeyEventCompat.target(value1), PsychHeyEventCompat.duration(value2));
			case 'Set GF Speed':
				state.gfSpeed = gfSpeed(value1, profile == PSYCH);
			case 'Add Camera Zoom':
				if (state.sourceCameraZoomsEnabled())
					state.pulseCameraZoom(CameraEventValues.amount(value1, 0.015), CameraEventValues.amount(value2, 0.03), 1.35);
			case 'Play Animation':
				state.playSourceEventAnimation(state.sourceAnimationEventActor(value2, true, legacy), value1, true);
			case 'Camera Follow Pos':
				state.sourceCameraFollowPosition(value1, value2);
			case 'Alt Idle Animation':
				state.applySourceAltIdleAnimation(value1, value2, legacy);
			case 'Screen Shake':
				state.shakeCamerasFromEvent(value1, value2);
			case 'Change Scroll Speed':
				// Psych skips the body but still tells scripts; Nightmare Vision returns first.
				if (state.songSpeedType == 'constant') return profile == PSYCH ? HANDLED : STOPPED;
				var multiplier = Std.parseFloat(value1);
				var duration = Std.parseFloat(value2);
				if (Math.isNaN(multiplier)) multiplier = 1;
				if (Math.isNaN(duration)) duration = 0;
				var target = PlayState.SONG.speed * state.sourceScrollSpeedSetting() * multiplier;
				// The historical revision is the one source that does not scale by playback rate.
				state.setSongSpeed(target, legacy ? duration : duration / state.playbackRate);
			case 'Set Property':
				if (legacy) state.historicalSetProperty(value1, value2);
				else state.setEventProperty(value1, propertyValue(value2));
			case 'Play Sound':
				if (profile != PSYCH) return UNHANDLED;
				var volume = value2 == null ? Math.NaN : Std.parseFloat(value2);
				state.playEventSound(value1, Math.isNaN(volume) ? 1 : volume);
			default:
				return UNHANDLED;
		}
		return HANDLED;
	}

	/** Psych rounds a float; Nightmare Vision truncates with parseInt. Both floor at 1. */
	public static function gfSpeed(value:String, round:Bool):Int {
		if (round) {
			var parsed = value == null ? Math.NaN : Std.parseFloat(value);
			return Math.isNaN(parsed) || parsed < 1 ? 1 : Math.round(parsed);
		}
		var speed:Int = Std.parseInt(value);
		if (Math.isNaN(speed) || speed < 1) speed = 1;
		return speed;
	}

	/** Psych's Set Property value: true/false after trimming, then any leading number, else the text as written. */
	public static function propertyValue(value:String):Dynamic {
		if (value == null) return null;
		var trimmed = StringTools.trim(value);
		if (trimmed == 'true' || trimmed == 'false') return trimmed == 'true';
		var number = Std.parseFloat(value);
		return Math.isNaN(number) ? value : number;
	}
}
