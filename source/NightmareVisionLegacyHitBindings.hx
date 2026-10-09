package;

/** Historical script signatures over the same default handlers used by fields. */
class NightmareVisionLegacyHitBindings {
	public static function install(interp:NightmareVisionScriptInterp, state:Dynamic, stateClass:Dynamic,
		good:Dynamic, opponent:Dynamic):Void {
		for (entry in [{name:'goodNoteHit', callback:good}, {name:'opponentNoteHit', callback:opponent}]) {
			var callback = entry.callback;
			var read = function():Dynamic return callback;
			interp.bindLiveValue(entry.name, read, null, function() return state);
			interp.sourceClassScope().bindStaticField(state, entry.name, read);
			interp.sourceClassScope().bindStaticField(stateClass, entry.name, read);
		}
	}
}
