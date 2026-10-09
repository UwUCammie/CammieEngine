package;

/** Historical public event methods use the same preparation service as generation. */
class NightmareVisionLegacyEventBindings {
	public static function install(interp:NightmareVisionScriptInterp, state:Dynamic, stateClass:Dynamic, api:Dynamic):Void {
		for (name in ['getEvents', 'shouldPush', 'firstEventPush', 'eventNoteEarlyTrigger', 'checkEventNote']) {
			var callback = Reflect.field(api, name);
			var read = function():Dynamic return callback;
			interp.bindLiveValue(name, read, null, function() return state);
			interp.sourceClassScope().bindStaticField(state, name, read);
			interp.sourceClassScope().bindStaticField(stateClass, name, read);
		}
	}
}
