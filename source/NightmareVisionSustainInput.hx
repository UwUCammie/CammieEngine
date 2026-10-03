package;

/** Pure gates for the source PlayState sustain loop and late-miss grace. */
class NightmareVisionSustainInput {
	/** PlayState.processHolds checks boyfriend.stunned before this per-note gate. */
	public static function shouldProcessHold(playerStunned:Bool, noteAlive:Bool,
		isSustainNote:Bool, blockHit:Bool, tooLate:Bool, fieldAutoPlayed:Bool,
		fieldInControl:Bool, fieldPlayerControls:Bool):Bool {
		return !playerStunned && noteAlive && isSustainNote && !blockHit && !tooLate
			&& !fieldAutoPlayed && fieldInControl && fieldPlayerControls;
	}

	/** Source processHolds hits an eligible hold segment on or after its time. */
	public static function shouldHitHold(wasGoodHit:Bool, holding:Bool,
		songPosition:Float, strumTime:Float):Bool
		return !wasGoodHit && holding && songPosition >= strumTime;

	/** Source processHolds misses only an active, released tail after coyote grace. */
	public static function shouldMissHold(wasGoodHit:Bool, holding:Bool,
		ignoreNote:Bool, endingSong:Bool, coyoteTime:Float,
		tailActive:Bool, tailMissed:Bool):Bool {
		return !wasGoodHit && !holding && !ignoreNote && !endingSong
			&& coyoteTime <= 0 && tailActive && !tailMissed;
	}

	/**
	 * Inner source late-miss gate, evaluated after PlayState marks the note tooLate.
	 * The caller retains the outer !tooLate && !wasGoodHit && isLate test and marks
	 * tooLate even when this gate suppresses the miss callback.
	 */
	public static function shouldDispatchLateMiss(ignoreNote:Bool, canMiss:Bool,
		tailMissed:Bool, isSustainNote:Bool, coyoteTime:Float,
		endingSong:Bool):Bool {
		return !ignoreNote && !canMiss && !tailMissed
			&& (!isSustainNote || coyoteTime <= 0) && !endingSong;
	}

	/** StrumNote.update decrements grace only while the key is released. */
	public static function advanceCoyoteTime(coyoteTime:Float,
		elapsed:Float, holding:Bool):Float {
		return coyoteTime > 0 && !holding ? Math.max(coyoteTime - elapsed, 0) : coyoteTime;
	}
}
