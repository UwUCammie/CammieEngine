package;

/** Shared anchor resolution for source sprite and instance scene insertion. */
@:access(PlayState)
class PsychSceneAnchors {
	public static function lowestCharacter(host:PlayState):Dynamic {
		// Native host scenes may keep actors directly until source groups are mounted.
		var bf:Dynamic = host.boyfriendGroup == null ? host.boyfriend : host.boyfriendGroup;
		var dad:Dynamic = host.dadGroup == null ? host.dad : host.dadGroup;
		var gf:Dynamic = host.gfGroup == null ? host.gf : host.gfGroup;
		var hidden = host.curStage != null && host.curStage.stageData != null && host.curStage.stageData.hide_girlfriend == true;
		var group:Dynamic = hidden ? bf : gf;
		for (candidate in [bf, dad]) if (host.members.indexOf(candidate) < host.members.indexOf(group)) group = candidate;
		return group;
	}
}
