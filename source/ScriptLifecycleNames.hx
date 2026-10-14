package;

/** One lifecycle hook and every spelling a script family uses for it. */
typedef ScriptLifecycleEntry = {
	/** Name PlayState and the other hosts broadcast. */
	var canonical:String;
	/** Donor spellings tried after the canonical name, in this order. */
	var broadcast:Array<String>;
	/** Further spellings that resolve to the hook but are never broadcast. */
	var aliases:Array<String>;
	/** Method names a V-Slice script class uses; empty when V-Slice has no such hook. */
	var vslice:Array<String>;
};

/**
	The single table of script lifecycle hook names.

	EngineCompat (what a broadcast may call) and HxcCompat (which V-Slice methods
	are lifecycle hooks rather than helpers) both read this table, so a hook added
	here reaches every script family at once and the two can no longer disagree.
	Psych and Nightmare Vision spellings sit in the same rows as the V-Slice ones.
*/
class ScriptLifecycleNames {
	public static var ENTRIES(get, never):Array<ScriptLifecycleEntry>;

	static var entries:Array<ScriptLifecycleEntry> = null;
	static var engineIndex:Map<String, String> = null;
	static var vsliceIndex:Map<String, String> = null;
	static var broadcastIndex:Map<String, Array<String>> = null;
	static var vsliceMethods:Array<String> = null;

	static function get_ENTRIES():Array<ScriptLifecycleEntry> {
		build();
		return entries;
	}

	static inline function row(canonical:String, broadcast:Array<String>, ?aliases:Array<String>,
			?vslice:Array<String>):ScriptLifecycleEntry
		return {canonical: canonical, broadcast: broadcast, aliases: aliases == null ? [] : aliases,
			vslice: vslice == null ? [] : vslice};

	/** A V-Slice hook spelled `onX` in a class and broadcast as `x`. */
	static function vsliceRow(canonical:String, ?extraBroadcast:Array<String>, ?aliases:Array<String>,
			?extraVslice:Array<String>):ScriptLifecycleEntry {
		var on = 'on' + canonical.charAt(0).toUpperCase() + canonical.substr(1);
		var broadcast = [on];
		if (extraBroadcast != null)
			for (name in extraBroadcast) broadcast.push(name);
		var vslice = [on, canonical];
		if (extraVslice != null)
			for (name in extraVslice) vslice.push(name);
		return row(canonical, broadcast, aliases, vslice);
	}

	static function build():Void {
		if (entries != null)
			return;
		entries = [
			row('start', ['onCreate'], null, ['onCreate', 'create']),
			vsliceRow('createPost'),
			vsliceRow('songStart'),
			vsliceRow('update'),
			vsliceRow('updatePost'),
			vsliceRow('beatHit'),
			vsliceRow('stepHit', null, null, ['step']),
			vsliceRow('sectionHit'),
			vsliceRow('countdownTick'),
			vsliceRow('countdownStep'),
			vsliceRow('countdownEnd'),
			vsliceRow('startCountdown'),
			row('countdownStarted', ['onCountdownStarted']),
			vsliceRow('countdownStart'),
			row('customSubstateCreate', ['onCustomSubstateCreate']),
			row('customSubstateCreatePost', ['onCustomSubstateCreatePost']),
			row('customSubstateUpdate', ['onCustomSubstateUpdate']),
			row('customSubstateUpdatePost', ['onCustomSubstateUpdatePost']),
			row('customSubstateDestroy', ['onCustomSubstateDestroy']),
			vsliceRow('goodNoteHit'),
			vsliceRow('opponentNoteHit'),
			vsliceRow('noteHit'),
			vsliceRow('noteIncoming'),
			row('noteMiss', ['onNoteMiss', 'onMissNote'], ['missNote'], ['onNoteMiss', 'noteMiss']),
			row('noteMissPress', ['onNoteMissPress']),
			row('recalculateRating', ['onRecalculateRating']),
			vsliceRow('opponentNoteMiss'),
			vsliceRow('noteGhostMiss'),
			vsliceRow('noteHoldDrop'),
			row('songEnd', ['onEndSong', 'onSongEnd'], null, ['onSongEnd', 'onEndSong', 'songEnd']),
			vsliceRow('songRetry'),
			vsliceRow('songEvent'),
			row('tweenCompleted', ['onTweenCompleted']),
			row('timerCompleted', ['onTimerCompleted']),
			vsliceRow('pause'),
			vsliceRow('resume'),
			vsliceRow('subStateOpenEnd', ['onPauseSubstateOpen'], ['pauseSubstateOpen'],
				['onPauseSubstateOpen', 'pauseSubstateOpen']),
			vsliceRow('subStateCloseBegin', ['onPauseSubstateClose'], ['pauseSubstateClose'],
				['onPauseSubstateClose', 'pauseSubstateClose']),
			vsliceRow('songLoaded'),
			vsliceRow('stateChangeBegin'),
			vsliceRow('stateChangeEnd', ['onStateOpenEnd'], ['stateOpenEnd'], ['onStateOpenEnd', 'stateOpenEnd']),
			vsliceRow('subStateOpenBegin'),
			vsliceRow('subStateCloseEnd'),
			vsliceRow('playStateEnter'),
			vsliceRow('difficultySwitch'),
			vsliceRow('capsuleSelected'),
			vsliceRow('focusGained'),
			vsliceRow('focusLost'),
			row('gameOver', ['onGameOver', 'onGameOverStart'], ['gameOverStart'], ['onGameOver', 'gameOver']),
			vsliceRow('destroy'),
			// V-Slice hooks with no older engine spelling.  Modules receive
			// stateCreate once the state's scripts exist; scriptEvent is the
			// catch-all every event reaches before its own hook.
			vsliceRow('stateCreate'),
			vsliceRow('scriptEvent'),
			vsliceRow('songSelected'),
			vsliceRow('freeplayIntroDone'),
			vsliceRow('freeplayOutro'),
			vsliceRow('freeplayClose'),
			vsliceRow('characterSelect'),
			vsliceRow('characterDeselect'),
			vsliceRow('characterConfirm'),
			vsliceRow('dialogueStart'),
			vsliceRow('dialogueLine'),
			vsliceRow('dialogueCompleteLine'),
			vsliceRow('dialogueSkip'),
			vsliceRow('dialogueEnd')
		];
		engineIndex = new Map();
		vsliceIndex = new Map();
		broadcastIndex = new Map();
		vsliceMethods = [];
		for (entry in entries) {
			var lower = entry.canonical.toLowerCase();
			engineIndex.set(lower, entry.canonical);
			broadcastIndex.set(lower, entry.broadcast);
			for (name in entry.broadcast)
				engineIndex.set(name.toLowerCase(), entry.canonical);
			for (name in entry.aliases)
				engineIndex.set(name.toLowerCase(), entry.canonical);
			for (name in entry.vslice) {
				vsliceIndex.set(name.toLowerCase(), entry.canonical);
				if (StringTools.startsWith(name, 'on') && vsliceMethods.indexOf(name) < 0)
					vsliceMethods.push(name);
			}
		}
	}

	/** Canonical hook for any engine, Psych or Nightmare Vision spelling; null when unknown. */
	public static function canonical(lowerName:String):Null<String> {
		build();
		return lowerName == null ? null : engineIndex.get(lowerName);
	}

	/** Canonical hook for a V-Slice class method name; '' when the method is a helper. */
	public static function vsliceCanonical(name:String):String {
		if (name == null)
			return '';
		build();
		var found = vsliceIndex.get(name.toLowerCase());
		return found == null ? '' : found;
	}

	/** Donor spellings broadcast after a canonical hook name (lowercase lookup); null when none. */
	public static function broadcastSpellings(lowerCanonical:String):Null<Array<String>> {
		build();
		return lowerCanonical == null ? null : broadcastIndex.get(lowerCanonical);
	}

	/** Every V-Slice `onX` hook method, in table order. Shared list; callers only read it. */
	public static function vsliceHookMethods():Array<String> {
		build();
		return vsliceMethods;
	}
}
