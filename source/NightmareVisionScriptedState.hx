package;

import NightmareVisionMusicBeatState.NightmareVisionMusicBeatStateHost;

/**
	Native state wrapper matching Nightmare Vision's ScriptedState lifecycle.
	The source script is executable state behavior, loaded through the captured
	family host rather than attached to a host title-state alias.
*/
@:keep
class NightmareVisionScriptedState extends NightmareVisionMusicBeatState {
	public function new(scriptName:String, host:NightmareVisionMusicBeatStateHost) {
		super(host);
		initStateScript(scriptName, false);
		// Donor ScriptedState binds the group parent before this constructor hook.
		scriptGroup.call('onLoad', []);
	}

	/** Donor ScriptedState calls onCreate after MusicBeatState.create finishes. */
	public override function create():Void {
		super.create();
		if (!scripted) {
			sourceHost.failedScriptState(scriptName);
			return;
		}
		scriptGroup.call('onCreate', []);
	}
}
