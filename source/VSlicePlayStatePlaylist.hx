package;

/**
	V-Slice's `PlayStatePlaylist`. Story mode is the engine's own
	`PlayState.isStoryMode` flag (shared with the lowered
	`HxcCompatRuntime.playStatePlaylistIsStoryMode`), so a menu that sets it and
	then calls `LoadingState.loadPlayState` starts a real story run. The other
	fields are the campaign details that menus fill in before the first song.
*/
@:keep
class VSlicePlayStatePlaylist {
	public static var isStoryMode(get, set):Bool;
	/** Song ids still to play after the first one; story mode hands them to the engine playlist. */
	public static var playlistSongIds:Array<String> = [];
	public static var campaignScore:Int = 0;
	public static var campaignTitle:String = 'UNKNOWN';
	public static var campaignId:Null<String> = null;
	public static var campaignDifficulty:String = 'normal';

	static function get_isStoryMode():Bool
		return HxcCompatRuntime.playStatePlaylistIsStoryMode;

	static function set_isStoryMode(value:Bool):Bool
		return HxcCompatRuntime.playStatePlaylistIsStoryMode = value;

	/** Same reset V-Slice performs when a run ends or is abandoned. */
	public static function reset():Void {
		isStoryMode = false;
		playlistSongIds = [];
		campaignScore = 0;
		campaignTitle = 'UNKNOWN';
		campaignId = null;
		campaignDifficulty = StringTools.trim(VSliceRegistryCatalog.defaultDifficulty()).toLowerCase();
	}
}
