package;

/** What the source song preparation needs from its owner and the base game. */
typedef NightmareVisionSongPreparationHost = {
	/** Source Paths.sanitize for a song name. */
	var sanitize:String->String;
	/** The owner's difficulty name for a source difficulty index. */
	var difficultyName:Int->String;
	/** Base-game chart choice for a song folder and difficulty name: chart file and native difficulty. */
	var resolve:(folder:String, difficulty:String) -> {chart:String, difficulty:Int};
	/** Load one of the owner's installed charts; throws when it has none. */
	var load:(chart:String, folder:String) -> Dynamic;
	/** Make the loaded chart the next song: chart, native difficulty, story mode. */
	var commit:(song:Dynamic, difficulty:Int, storyMode:Bool) -> Void;
}

/**
 * Nightmare Vision's StoryMeta (PlayState.storyMeta) plus the source
 * PlayState.prepareForSong and prepareForWeek. Scripted menus write the
 * week fields and then prepare the first song before switching to PlayState.
 * The chart is the owner's installed copy, picked through the base game's
 * difficulty-to-chart rule.
 */
@:keep
class NightmareVisionStoryMeta {
	public var curWeek:Int = 0;
	public var playlist:Array<String> = [];
	public var difficulty:Int = 1;
	public var score:Int = 0;
	public var misses:Int = 0;

	public function new() {}

	/** Source prepareForSong: null when the chart is ready, otherwise the error. */
	public static function prepareSong(meta:NightmareVisionStoryMeta, host:NightmareVisionSongPreparationHost,
		songName:String, ?difficultyIndex:Null<Int>, ?storyMode:Null<Bool>):Dynamic {
		var index:Int = difficultyIndex == null ? 1 : difficultyIndex;
		var story = storyMode == true;
		try {
			if (songName == null || StringTools.trim(songName) == '') throw 'No song name';
			var folder = host.sanitize(songName);
			var target = host.resolve(folder, host.difficultyName(index));
			var song:Dynamic = host.load(target.chart, folder);
			if (song == null) throw 'No chart for ' + folder;
			host.commit(song, target.difficulty, story);
			meta.difficulty = index;
			return null;
		} catch (error:Dynamic) {
			return error;
		}
	}

	/**
		Source endSong for one finished story song: count its score and misses,
		drop it from the playlist and prepare the next one. True when the next
		song is ready. False when the week is over, or when the next chart could
		not be prepared (that error goes to `report`); either way the caller goes
		back to the story menu, as the source does at the end of a week.
	*/
	public static function advanceWeek(meta:NightmareVisionStoryMeta, host:NightmareVisionSongPreparationHost,
		songScore:Int, songMisses:Int, ?report:(String, Dynamic) -> Void):Bool {
		meta.score += songScore;
		meta.misses += songMisses;
		if (meta.playlist == null || meta.playlist.length == 0) return false;
		meta.playlist.remove(meta.playlist[0]);
		if (meta.playlist.length == 0) return false;
		var next = meta.playlist[0];
		var error = next == null ? 'No song name' : prepareSong(meta, host, next.toLowerCase(), meta.difficulty, true);
		if (error != null && report != null) report(next, error);
		return error == null;
	}

	/** Source prepareForWeek: the first song is prepared and the playlist kept. */
	public static function prepareWeek(meta:NightmareVisionStoryMeta, host:NightmareVisionSongPreparationHost,
		songs:Array<String>, ?difficultyIndex:Null<Int>, ?storyMode:Null<Bool>):Dynamic {
		if (songs == null || songs.length == 0) return 'No songs in week';
		var error = prepareSong(meta, host, songs[0], difficultyIndex, storyMode);
		if (error == null) meta.playlist = songs;
		return error;
	}
}
