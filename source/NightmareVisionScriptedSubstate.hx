package;

import NightmareVisionMusicBeatSubstate.NightmareVisionMusicBeatSubstateHost;

/**
	Native substate wrapper matching Nightmare Vision's ScriptedSubstate lifecycle,
	so scripts can open their own pause menus, popups and death screens.
*/
@:keep
class NightmareVisionScriptedSubstate extends NightmareVisionMusicBeatSubstate {
	public function new(scriptName:String, host:NightmareVisionMusicBeatSubstateHost) {
		super(host);
		initStateScript(scriptName, false);
		// The donor rebinds the parent after loading, even when no script was found.
		scriptGroup.parent = this;
		scriptGroup.call('onLoad', []);
	}

	/** Donor ScriptedSubstate calls onCreate after the base create finishes. */
	public override function create():Void {
		super.create();
		if (!scripted) {
			sourceHost.failedScriptState(scriptName);
			return;
		}
		scriptGroup.call('onCreate', []);
	}
}
