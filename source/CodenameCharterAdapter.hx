package;

import flixel.FlxG;

/** Shared implementation for the Codename `funkin.editors.charter.Charter`
 * import. The editor is native ChartingState over the active imported chart. */
class CodenameCharterAdapter extends ChartingState {
	/** Codename's Charter writes playtestInfo when it is destroyed. This host
	 * reports only fields backed by the native editor and consumed by imported
	 * scripts: the playhead and its fixed playback speed. */
	public static var playtestInfo:Dynamic = null;

	var requestedSong:String;
	var requestedDifficulty:String;
	var requestedVariation:Null<String>;
	var activePlayState:PlayState;
	var activeChart:Dynamic;

	/** Match Codename's constructor so imported scripts can use the same call.
	 * `reload=false` has no native equivalent: ChartingState always reloads the
	 * authored note rows, so reject it instead of silently changing its meaning. */
	public function new(song:String, diff:String, variant:Null<String>, reload:Bool = true) {
		super();
		if (!reload)
			throw '[codename-charter] reload=false is unsupported by the native chart editor';
		if (PlayState.instance == null || FlxG.state != PlayState.instance)
			throw '[codename-charter] Charter requires the active PlayState';
		if (song == null || StringTools.trim(song) == '' || diff == null || StringTools.trim(diff) == '')
			throw '[codename-charter] Charter requires the active song and difficulty';

		requestedSong = song;
		requestedDifficulty = diff;
		requestedVariation = variant;
		activePlayState = PlayState.instance;
		activeChart = PlayState.SONG;
		validateActiveChart();
	}

	/** Recheck when Flixel enters the state; the active chart must still be the
	 * exact one validated at construction. */
	override public function create():Void {
		if (PlayState.instance != activePlayState || PlayState.SONG != activeChart)
			throw '[codename-charter] The active chart changed before Charter opened';
		validateActiveChart();
		super.create();
	}

	function validateActiveChart():Void {
		if (activePlayState == null || activeChart == null)
			throw '[codename-charter] No active Codename chart is available';
		var identity = activePlayState.codenameCharterIdentity();
		if (identity == null)
			throw '[codename-charter] The active chart has no validated Codename identity';
		if (Reflect.field(identity, 'song') != requestedSong
			|| Reflect.field(identity, 'difficulty') != requestedDifficulty)
			throw '[codename-charter] Requested song or difficulty does not match the active chart';
		if (hasVariant(requestedVariation) || hasVariant(Reflect.field(identity, 'variation')))
			throw '[codename-charter] Codename chart variants are not supported by the native editor';
	}

	static function hasVariant(value:Dynamic):Bool
		return value != null && StringTools.trim(Std.string(value)) != '';

	override public function destroy():Void {
		playtestInfo = {
			songPosition: Conductor.songPosition,
			playbackSpeed: 1.0
		};
		super.destroy();
	}
}
