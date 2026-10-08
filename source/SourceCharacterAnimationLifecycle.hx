package;

using StringTools;

/** Small source-dialect gates for character animation state transitions. */
class SourceCharacterAnimationLifecycle {
	/** Psych and Nightmare Vision reset the special-animation latch whenever a
	 * new source animation starts. Codename and native playback keep their own
	 * animation contracts. */
	public static function specialAfterPlay(current:Bool, sourceMode:Int, nightmareVision:Bool,
		codename:Bool):Bool {
		return current && (codename || (sourceMode != 1 && sourceMode != 2 && !nightmareVision));
	}

	/** Nightmare Vision checks for an animation-specific return before falling
	 * back to its idle pose. Psych does not have this transition. */
	public static function returnAnimation(currentName:Null<String>, returnExists:Bool,
		nightmareVision:Bool, debugMode:Bool, specialAnim:Bool):Null<String> {
		if (!nightmareVision || debugMode || specialAnim || currentName == null
			|| currentName == '' || !returnExists)
			return null;
		return currentName + '-return';
	}

	/** NV keeps special animations latched while a source-controlled actor is
	 * held, then resumes the ordinary finish path after release. */
	public static function mayFinishSpecial(nightmareVision:Bool, holding:Bool):Bool {
		return !nightmareVision || !holding;
	}

	/** A completed NV return animation resumes the ordinary dance/idle choice. */
	public static function finishesReturn(nightmareVision:Bool, currentName:Null<String>,
		finished:Bool):Bool {
		return nightmareVision && finished && currentName != null
			&& currentName.endsWith('-return');
	}

	/** The source sing-duration fallback cannot interrupt an NV held animation. */
	public static function mayAdvanceSingDance(nightmareVision:Bool, holding:Bool):Bool {
		return !nightmareVision || !holding;
	}

	/** NV applies the sing-duration fallback to every actor role. The native
	 * host keeps its existing player-controlled split. */
	public static function usesSingDurationFallback(nightmareVision:Bool, beingControlled:Bool):Bool {
		return nightmareVision || !beingControlled;
	}

	/** NV accrues time while a sing or an authored manual hold is active.
	 * Other dialects preserve the host's existing sing/priority behavior. */
	public static function shouldAccumulateSingDuration(nightmareVision:Bool,
		currentAnimation:Null<String>, singPriority:Array<String>, holding:Bool):Bool {
		if (currentAnimation == null) return nightmareVision && holding;
		return currentAnimation.startsWith('sing')
			|| (nightmareVision ? holding : singPriority != null && singPriority.contains(currentAnimation));
	}

	/** Pinned NV suppresses regular sustain animation playback only when the
	 * selected CharacterData opts into V-Slice sustain handling. */
	public static function shouldPlayNightmareVisionNoteAnimation(nightmareVision:Bool,
		vSliceSustains:Bool, isSustainNote:Bool):Bool {
		return !nightmareVision || !vSliceSustains || !isSustainNote;
	}
}
