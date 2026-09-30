package;

/** Live static PlayState fields exposed to a selected Codename song script. */
class CodenamePlayStateFacade {
	final host:PlayState;
	final songView:Void->CodenameSongView;

	public function new(host:PlayState, songView:Void->CodenameSongView) {
		this.host = host;
		this.songView = songView;
	}

	public var SONG(get, never):CodenameSongView;
	function get_SONG():CodenameSongView return songView();

	public var instance(get, never):PlayState;
	function get_instance():PlayState return host;

	/** The current native difficulty is the Codename chart selected for this
	 * play session. Imported Codename scripts use this when opening Charter. */
	public var difficulty(get, never):String;
	function get_difficulty():String return PlayState.storyDifficultyText;

	/** Native imports do not select Codename variants. Preserve the selected
	 * metadata value so the editor can reject unsupported variant charts clearly. */
	public var variation(get, never):Null<String>;
	function get_variation():Null<String> {
		var identity = host == null ? null : host.codenameCharterIdentity();
		return identity == null ? null : cast Reflect.field(identity, 'variation');
	}

	/** This engine has no charting playtest mode flag on PlayState. */
	public var chartingMode(get, never):Bool;
	function get_chartingMode():Bool return false;

	public var isStoryMode(get, set):Bool;
	function get_isStoryMode():Bool return PlayState.isStoryMode;
	function set_isStoryMode(value:Bool):Bool return PlayState.isStoryMode = value;

	public function resetSongInfos():Void PlayState.resetSongInfos();
	public function __loadSong(songName:String, ?difficulty:String):Void
		PlayState.__loadSong(songName, difficulty);
}
