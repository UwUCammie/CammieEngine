package;

import PsychAchievementInfo;

/** An authenticated, owner-captured boundary for Psych achievement I/O. */
typedef PsychAchievementSource = {
	/** Already owner-resolved path, in source reload order. */
	var path:String;
	/** Null for the base `data/achievements.json` source. */
	var mod:Null<String>;
}

typedef PsychAchievementsHost = {
	var ownerActive:Void->Bool;
	/** Captured PsychOwnerPaths facade. It is checked against the constructor owner. */
	var paths:Dynamic;
	/** Base achievement file followed by enabled owner-authorized mod files. */
	var achievementSources:Void->Array<PsychAchievementSource>;
	/** Reads only paths returned by `achievementSources`. */
	var readText:String->Null<String>;
	var report:String->Void;
	var playConfirmSound:(String, Float)->Void;
	var nowMillis:Void->Int;
	var showingPopups:Void->Bool;
	var showPopup:(String, PsychAchievementInfo, Void->Void)->Void;
}
