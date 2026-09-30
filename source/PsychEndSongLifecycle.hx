package;

/** Small end-song disposition shared by Psych script callbacks and PlayState. */
class PsychEndSongLifecycle {
	public static inline var CONTINUE_NATIVE:Int = 0;
	public static inline var HOLD_FOR_SCRIPT:Int = 1;
	public static inline var RELEASE_FOR_OUTRO:Int = 2;

	/**
		A Psych Function_Stop owns the native end gate until its later endSong()
		call. An HXC event-only cancellation hands control back to its outro flow.
	*/
	public static function selectedDisposition(eventCancelled:Bool,
		callbackStopped:Bool):Int {
		if (callbackStopped) return HOLD_FOR_SCRIPT;
		return eventCancelled ? RELEASE_FOR_OUTRO : CONTINUE_NATIVE;
	}

	/** A global results provider owns its cancelled end until its screen closes. */
	public static function providerDisposition(eventCancelled:Bool,
		callbackStopped:Bool):Int {
		return eventCancelled || callbackStopped ? HOLD_FOR_SCRIPT : CONTINUE_NATIVE;
	}
}
