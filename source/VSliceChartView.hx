package;

/**
	V-Slice's `PlayState.currentChart` (a SongDifficulty) as a read-only view of
	the engine chart being played. Header fields are copied once from the live
	chart; notes and events are built only when a script asks for them, and the
	engine never reads anything back from this view. There is no noteStyle: the
	engine's uiType names a different set of styles, so the HXC gate keeps
	scripts that read it out of execution instead of handing them a wrong id.
*/
@:keep
class VSliceChartView {
	public var songName(default, null):String;
	public var songArtist(default, null):String;
	public var charter(default, null):String = '';
	public var album(default, null):Null<String>;
	public var stage(default, null):String;
	public var scrollSpeed(default, null):Float;
	public var difficulty(default, null):String;
	public var variation(default, null):String;
	public var stickerPack(default, null):Null<String>;
	public var characters(default, null):Dynamic;
	public var timeChanges(default, null):Array<Dynamic>;
	/** V-Slice song identity (`currentChart.song.id`), the installed chart folder. */
	public var song(default, null):Dynamic;
	public var looped(default, null):Bool = false;
	public var difficultyRating(default, null):Int = 0;
	public var notes(get, never):Array<Dynamic>;
	public var events(get, never):Array<Dynamic>;

	var chart:Dynamic;
	var notesProvider:Void->Array<Dynamic>;
	var cachedNotes:Array<Dynamic>;
	var cachedEvents:Array<Dynamic>;

	/**
		`chart` is the engine's SwagSong and `storageFolder` its installed folder;
		`notesProvider` builds the V-Slice note list from it (PlayState passes its
		own copy routine).
	*/
	public function new(chart:Dynamic, storageFolder:String, difficulty:String, variation:String,
		?notesProvider:Void->Array<Dynamic>, ?displayName:String) {
		this.chart = chart;
		this.notesProvider = notesProvider;
		this.difficulty = difficulty == null ? '' : difficulty;
		this.variation = variation == null || variation == '' ? 'default' : variation;
		// V-Slice's songName is display text; the chart's own name is the folder id.
		songName = displayName != null && displayName != '' ? displayName : text('song');
		songArtist = text('songArtist');
		var albumText = text('album');
		album = albumText == '' ? null : albumText;
		var packText = text('stickerPack');
		stickerPack = packText == '' ? null : packText;
		stage = text('stage');
		scrollSpeed = number('speed', 1);
		characters = {
			player: text('player1'),
			opponent: text('player2'),
			girlfriend: text('gf'),
			instrumental: '',
			altInstrumentals: [],
			opponentVocals: null,
			playerVocals: null
		};
		timeChanges = [{t: 0, b: 0, bpm: number('bpm', 100), n: 4, d: 4}];
		song = {id: storageFolder == null ? '' : storageFolder};
	}

	/** True when this view still describes the given chart object. */
	public function describes(value:Dynamic, difficultyId:String, variationId:String):Bool
		return value == chart && difficultyId == difficulty
			&& (variationId == null || variationId == '' ? 'default' : variationId) == variation;

	public function getStartingBPM():Float
		return timeChanges.length == 0 ? 100 : timeChanges[0].bpm;

	public function getEvents():Array<Dynamic>
		return events.copy();

	function get_notes():Array<Dynamic> {
		if (cachedNotes == null) {
			var built:Array<Dynamic> = null;
			if (notesProvider != null)
				try built = notesProvider() catch (_:Dynamic) {}
			cachedNotes = built == null ? [] : built;
		}
		return cachedNotes;
	}

	/**
		V-Slice SongEventData records ({time, eventKind, value}) from the engine's
		event list. The importer stores each V-Slice value as JSON in the first
		event argument, so it is decoded back to the authored object.
	*/
	function get_events():Array<Dynamic> {
		if (cachedEvents != null)
			return cachedEvents;
		cachedEvents = [];
		var raw:Dynamic = chart == null ? null : Reflect.field(chart, 'events');
		if (!Std.isOfType(raw, Array))
			return cachedEvents;
		for (group in (cast raw:Array<Dynamic>)) {
			if (!Std.isOfType(group, Array) || (cast group:Array<Dynamic>).length < 2)
				continue;
			var time = Std.parseFloat(Std.string(group[0]));
			var list:Dynamic = group[1];
			if (Math.isNaN(time) || !Std.isOfType(list, Array))
				continue;
			for (item in (cast list:Array<Dynamic>)) {
				if (!Std.isOfType(item, Array) || (cast item:Array<Dynamic>).length == 0)
					continue;
				var kind = item[0] == null ? '' : Std.string(item[0]);
				var value:Dynamic = decode(item.length > 1 ? item[1] : null);
				cachedEvents.push({time: time, eventKind: kind, value: value, activated: false,
					t: time, e: kind, v: value});
			}
		}
		return cachedEvents;
	}

	static function decode(value:Dynamic):Dynamic {
		if (!Std.isOfType(value, String))
			return value;
		var source = StringTools.trim(cast value);
		if (source.length == 0)
			return value;
		var first = source.charAt(0);
		if (first != '{' && first != '[')
			return value;
		try return haxe.Json.parse(source) catch (_:Dynamic) return value;
	}

	function text(field:String):String {
		var value:Dynamic = chart == null ? null : Reflect.field(chart, field);
		return value == null ? '' : Std.string(value);
	}

	function number(field:String, fallback:Float):Float {
		var value:Dynamic = chart == null ? null : Reflect.field(chart, field);
		var parsed = value == null ? Math.NaN : Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? fallback : parsed;
	}
}
