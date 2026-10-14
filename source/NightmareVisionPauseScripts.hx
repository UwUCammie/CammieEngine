package;

/**
 * Nightmare Vision's scripts/substates/PauseSubState on top of the native
 * pause menu. The source substate loads that script into its own group, calls
 * onLoad and onCreatePost, lets onExit, onOptions and onRestart return
 * STOP_FUNC to cancel the action, and reports onChangeSelection, onRegenMenu,
 * onUpdate and onDestroy.
 */
class NightmareVisionPauseScripts {
	public static inline var SCRIPT_PREFIX = 'substates';
	public static inline var SCRIPT_NAME = 'PauseSubState';

	/** Load the owner's pause script for this menu, or null when it has none. */
	public static function attach(session:NightmareVisionStateSession, menu:Dynamic):PauseMenuHooks {
		if (session == null || session.released) return null;
		var group:NightmareVisionScriptGroup = session.stateHost().createScriptGroup(menu);
		var handle:NightmareVisionScriptModule = null;
		switch (session.createScriptAt(SCRIPT_PREFIX, SCRIPT_NAME, menu, group)) {
			case Loaded(_, _, loaded): handle = loaded;
			case ParseFailed(_, failed): if (failed != null && !failed.released) failed.destroy();
			default:
		}
		if (handle == null || handle.released || !handle.initialized || handle.parsingFailed()) {
			if (handle != null && !handle.released) handle.destroy();
			group.destroy();
			return null;
		}
		// The script is built against the gameplay state; its fields then
		// resolve through the menu, as they do on the source substate.
		group.parent = menu;
		if (!group.addScript(handle)) {
			handle.destroy();
			group.destroy();
			return null;
		}
		group.call('onLoad', []);
		return hooksFor(function(name, args) return group.call(name, args), group.destroy);
	}

	/** The source callback name asked before a native leave action. */
	public static function callbackFor(action:String):String {
		return switch (action) {
			case PauseMenuHooks.EXIT: 'onExit';
			case PauseMenuHooks.OPTIONS: 'onOptions';
			case PauseMenuHooks.RESTART: 'onRestart';
			default: null;
		}
	}

	/** Map the native hooks onto one script group's calls. */
	public static function hooksFor(call:(String, Array<Dynamic>) -> Dynamic, release:Void->Void):PauseMenuHooks {
		var hooks = new PauseMenuHooks();
		var released = false;
		hooks.allowAction = function(action) {
			var name = callbackFor(action);
			return released || name == null || call(name, []) != NightmareVisionScriptGroup.STOP_FUNC;
		};
		hooks.created = function() if (!released) call('onCreatePost', []);
		hooks.regenerated = function() if (!released) call('onRegenMenu', []);
		hooks.selectionChanged = function(index) return released || call('onChangeSelection', [index]) != NightmareVisionScriptGroup.STOP_FUNC;
		hooks.update = function(elapsed) if (!released) call('onUpdate', [elapsed]);
		hooks.destroy = function() {
			if (released) return;
			released = true;
			try call('onDestroy', []) catch (error:Dynamic) {
				release();
				throw error;
			}
			release();
		};
		return hooks;
	}
}
