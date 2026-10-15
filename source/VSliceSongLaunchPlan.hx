package;

import VSliceSongRegistry.VSliceSongEntry;

/**
	Which installed chart a V-Slice `loadPlayState` call means. Kept apart from
	the engine binding so the choice of folder, difficulty and story playlist
	can be checked without starting a song.
*/
class VSliceSongLaunchPlan {
	public var folder:String = '';
	public var difficulty:String = '';
	public var variation:String = 'default';
	/** Story mode: this song's folder followed by the remaining playlist folders. */
	public var storyFolders:Array<String> = [];
	/** Engine week key of PlayStatePlaylist.campaignId, when it names an imported level. */
	public var levelKey:Null<String> = null;
	public var error:Null<String> = null;

	function new() {}

	public static function resolve(params:Dynamic, storyMode:Bool):VSliceSongLaunchPlan {
		var plan = new VSliceSongLaunchPlan();
		if (params == null) {
			plan.error = 'loadPlayState was called without parameters';
			return plan;
		}
		var target:Dynamic = Reflect.field(params, 'targetSong');
		var entry:VSliceSongEntry = null;
		if (Std.isOfType(target, VSliceSongEntry))
			entry = cast target;
		else if (Std.isOfType(target, String))
			entry = VSliceSongRegistry.instance.fetchEntry(target);
		if (entry == null) {
			plan.error = 'targetSong does not name an installed song';
			return plan;
		}
		var requestedDifficulty = text(Reflect.field(params, 'targetDifficulty'));
		var requestedVariation = text(Reflect.field(params, 'targetVariation'));
		if (requestedVariation == '' && entry.variation != null)
			requestedVariation = entry.variation;
		var chart = entry.getDifficulty(requestedDifficulty == '' ? null : requestedDifficulty,
			requestedVariation == '' ? null : requestedVariation);
		// A menu may ask for a variation the import did not install; V-Slice then
		// plays the base chart for that difficulty, so fall back the same way.
		if (chart == null && requestedVariation != '' && requestedVariation != 'default')
			chart = entry.getDifficulty(requestedDifficulty == '' ? null : requestedDifficulty, 'default');
		if (chart == null) {
			plan.error = 'Song ' + entry.id + ' has no ' + (requestedDifficulty == '' ? 'default' : requestedDifficulty)
				+ ' chart' + (requestedVariation == '' ? '' : ' for variation ' + requestedVariation);
			return plan;
		}
		plan.folder = chart.storageFolder;
		plan.difficulty = chart.difficulty;
		plan.variation = chart.variation;
		if (storyMode) {
			plan.storyFolders.push(plan.folder);
			for (id in VSlicePlayStatePlaylist.playlistSongIds) {
				var next = VSliceSongRegistry.instance.fetchEntry(id);
				if (next == null)
					continue;
				var nextChart = next.getDifficulty(plan.difficulty, plan.variation);
				if (nextChart == null)
					nextChart = next.getDifficulty(plan.difficulty, 'default');
				if (nextChart != null)
					plan.storyFolders.push(nextChart.storageFolder);
			}
			var campaign = VSlicePlayStatePlaylist.campaignId;
			var levels = VSliceRegistryCatalog.levels();
			if (campaign != null && campaign != '')
				for (week in levels)
					if (VSliceLevelRegistry.levelId(week).toLowerCase() == campaign.toLowerCase()) {
						plan.levelKey = week.key;
						break;
					}
			// Menus that never set campaignId still start a level's songs in order;
			// the level whose playlist is exactly this one is the week being played.
			if (plan.levelKey == null)
				for (week in levels)
					if (week.songs.join('\n').toLowerCase() == plan.storyFolders.join('\n').toLowerCase()) {
						plan.levelKey = week.key;
						break;
					}
		}
		return plan;
	}

	static function text(value:Dynamic):String
		return value == null ? '' : StringTools.trim(Std.string(value)).toLowerCase();
}
