package;

/**
	What one note hit, miss or empty key press is about to do to the run.

	The game fills this in before any script hears about the note and reads it
	back afterwards.  Scripts get the real numbers instead of placeholders, and
	whatever they change is applied by the judgement code itself rather than by
	each script poking health or score directly.

	Every field remembers the value the game proposed.  The judgement only
	takes a field over when it was actually changed, so a note nobody touched
	is scored exactly as before.
*/
class NoteJudgementOutcome {
	/** Health the acting side gains (negative loses), before it is applied. */
	public var healthChange:Float = 0;
	/** Score this note adds (negative removes). */
	public var score:Int = 0;
	/** Rating name for a hit: sick, good, bad, shit. Null on a miss. */
	public var judgement:String = null;
	/** Whether the combo counter resets. */
	public var isComboBreak:Bool = false;
	/** Whether the miss sound plays. */
	public var playSound:Bool = true;
	/** Whether a note splash is shown for a hit. */
	public var doesNotesplash:Bool = false;
	/** Whether the character plays its miss animation. */
	public var playAnim:Bool = true;
	/** Signed distance from the note's time in milliseconds, read only. */
	public var hitDiff:Float = 0;
	/** Combo before this note, read only. */
	public var comboCount:Int = 0;
	/** For an empty press: whether a note was close enough to be aimed at. */
	public var hasPossibleNotes:Bool = false;

	var proposedHealthChange:Float = 0;
	var proposedScore:Int = 0;
	var proposedJudgement:String = null;
	var proposedComboBreak:Bool = false;
	var proposedPlaySound:Bool = true;
	var proposedNotesplash:Bool = false;
	var proposedPlayAnim:Bool = true;

	public function new() {}

	public static function hit(healthChange:Float, score:Int, judgement:String, isComboBreak:Bool,
		doesNotesplash:Bool, hitDiff:Float, comboCount:Int):NoteJudgementOutcome {
		var outcome = new NoteJudgementOutcome();
		outcome.healthChange = healthChange;
		outcome.score = score;
		outcome.judgement = judgement;
		outcome.isComboBreak = isComboBreak;
		outcome.doesNotesplash = doesNotesplash;
		outcome.hitDiff = hitDiff;
		outcome.comboCount = comboCount;
		outcome.propose();
		return outcome;
	}

	public static function miss(healthChange:Float, score:Int, isComboBreak:Bool, playSound:Bool,
		comboCount:Int, hasPossibleNotes:Bool = false):NoteJudgementOutcome {
		var outcome = new NoteJudgementOutcome();
		outcome.healthChange = healthChange;
		outcome.score = score;
		outcome.isComboBreak = isComboBreak;
		outcome.playSound = playSound;
		outcome.comboCount = comboCount;
		outcome.hasPossibleNotes = hasPossibleNotes;
		outcome.propose();
		return outcome;
	}

	/** Remember the current values as what the game itself would do. */
	public function propose():Void {
		proposedHealthChange = healthChange;
		proposedScore = score;
		proposedJudgement = judgement;
		proposedComboBreak = isComboBreak;
		proposedPlaySound = playSound;
		proposedNotesplash = doesNotesplash;
		proposedPlayAnim = playAnim;
	}

	public inline function healthChanged():Bool
		return healthChange != proposedHealthChange;

	public inline function scoreChanged():Bool
		return score != proposedScore;

	public inline function judgementChanged():Bool
		return judgement != proposedJudgement;

	public inline function comboBreakChanged():Bool
		return isComboBreak != proposedComboBreak;

	public inline function soundChanged():Bool
		return playSound != proposedPlaySound;

	public inline function notesplashChanged():Bool
		return doesNotesplash != proposedNotesplash;

	public inline function animChanged():Bool
		return playAnim != proposedPlayAnim;

	/** Score difference a script asked for on top of the proposed amount. */
	public inline function scoreDelta():Int
		return score - proposedScore;

	public function anyChanged():Bool {
		return healthChanged() || scoreChanged() || judgementChanged() || comboBreakChanged()
			|| soundChanged() || notesplashChanged() || animChanged();
	}

	/** Rating names the native judgement can score. Anything else is refused. */
	public static function acceptedJudgement(value:String):Null<String> {
		if (value == null)
			return null;
		return switch (StringTools.trim(value).toLowerCase()) {
			// The bot-only "perfect" is scored like the best manual rating.
			case 'sick' | 'perfect' | 'killer': 'sick';
			case 'good': 'good';
			case 'bad': 'bad';
			case 'shit': 'shit';
			default: null;
		};
	}
}
