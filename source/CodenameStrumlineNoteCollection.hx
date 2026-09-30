package;

/** Live source-facing note group for one authored Codename strumline. */
@:keep
class CodenameStrumlineNoteCollection {
	public static inline var DEFAULT_NOTE_MS_LIMIT:Float = 1500;
	@:keep public var limit:Float = DEFAULT_NOTE_MS_LIMIT;
	var lineIndex:Int;
	var resolveNotes:Int->Array<Dynamic>;
	var resolveSongPosition:Void->Float;
	var released:Bool = false;

	@:keep public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		if (released || resolveNotes == null) return [];
		var result = resolveNotes(lineIndex);
		return result == null ? [] : result;
	}

	@:keep public var length(get, never):Int;
	function get_length():Int return members.length;

	@:keep public function iterator():Iterator<Dynamic>
		return members.iterator();

	@:keep public function get(index:Int):Dynamic {
		var current = members;
		return index < 0 || index >= current.length ? null : current[index];
	}

	/** Match FlxTypedGroup's live-note callback surface used by Codename scripts. */
	@:keep public function forEachAlive(callback:Dynamic, ?recurse:Bool = false):Void {
		if (callback == null || !Reflect.isFunction(callback)) return;
		var current = members;
		var songPosition = resolveSongPosition == null ? 0 : resolveSongPosition();
		var latestVisibleNote = songPosition + limit;
		for (note in current) {
			if (note == null || Reflect.field(note, 'exists') == false) continue;
			// Codename NoteGroup only traverses notes through its visible lead-in
			// window. The members view still exposes the complete authored line.
			if (CodenameLineNoteQuery.noteTime(note) > latestVisibleNote) break;
			if (Reflect.field(note, 'alive') != false)
				Reflect.callMethod(null, callback, [note]);
		}
	}

	public function new(lineIndex:Int, resolveNotes:Int->Array<Dynamic>,
		?resolveSongPosition:Void->Float) {
		if (lineIndex < 0) throw 'Invalid Codename strumline note view';
		this.lineIndex = lineIndex;
		this.resolveNotes = resolveNotes;
		this.resolveSongPosition = resolveSongPosition;
	}

	public function release():Void {
		released = true;
		resolveNotes = null;
		resolveSongPosition = null;
	}
}
