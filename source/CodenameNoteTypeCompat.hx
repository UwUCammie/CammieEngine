package;

/** Shared built-in note-type behavior from Codename's stock data/notes scripts.
 * Keep the authored noteType on the mutable event unchanged for song scripts. */
class CodenameNoteTypeCompat {
	static inline var NO_ANIM_NOTE:String = 'no anim note';

	/** Codename's stock No Anim Note script cancels singing in onNoteHit. */
	public static function applyHit(event:Dynamic):Void {
		cancelAnimation(event);
	}

	/** Codename's stock No Anim Note script also cancels the player-miss anim. */
	public static function applyPlayerMiss(event:Dynamic):Void {
		cancelAnimation(event);
	}

	static function cancelAnimation(event:Dynamic):Void {
		if (event == null) return;
		var noteType:Dynamic = Reflect.field(event, 'noteType');
		if (noteType == null || !Std.isOfType(noteType, String)) return;
		if (StringTools.trim(cast noteType).toLowerCase() == NO_ANIM_NOTE)
			Reflect.setField(event, 'animCancelled', true);
	}
}
