package;

import haxe.ds.ObjectMap;

/** Select native note sprites by their authored Codename source line. */
@:keep
class CodenameLineNoteQuery {
	/** Build once from the sorted unspawn queue. Gameplay keeps these object
	 * identities as notes move into and out of the active Flixel group. */
	public static function index(chartNotes:Array<Dynamic>):CodenameLineNoteIndex {
		var result = new CodenameLineNoteIndex();
		if (chartNotes == null) return result;
		for (note in chartNotes) {
			var lineIndex = sourceLineIndex(note);
			if (lineIndex < 0 || result.byObject.exists(note)) continue;
			result.byObject.set(note, true);
			var bucket = result.byLine.get(lineIndex);
			if (bucket == null) {
				bucket = [];
				result.byLine.set(lineIndex, bucket);
			}
			bucket.push(note);
		}
		// The source Codename NoteGroup sorts once when chart notes are loaded.
		// Keep the indexed line buckets in that stable order so runtime reads can
		// merge only newly-created notes instead of sorting the full chart every
		// frame.
		for (bucket in result.byLine) sortByTime(bucket);
		return result;
	}

	public static function collect(lineIndex:Int, unspawned:Array<Dynamic>, active:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (lineIndex < 0) return result;
		var seen:ObjectMap<Dynamic, Bool> = new ObjectMap();
		appendLineNotes(result, lineIndex, unspawned, seen);
		appendLineNotes(result, lineIndex, active, seen);
		sortByTime(result);
		return result;
	}

	/** Query the indexed chart objects and scan only active notes for dynamically
	 * created notes. This avoids traversing the entire chart on each script read. */
	public static function collectIndexed(lineIndex:Int, index:CodenameLineNoteIndex,
		active:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (lineIndex < 0) return result;
		var indexed = index == null || index.byLine == null ? null : index.byLine.get(lineIndex);
		if (indexed != null) for (note in indexed)
			if (isAlive(note)) result.push(note);
		var additions:Array<Dynamic> = [];
		var seenAdditions:ObjectMap<Dynamic, Bool> = new ObjectMap();
		if (active != null) for (note in active) {
			if (note == null || (index != null && index.byObject != null && index.byObject.exists(note))
				|| !belongsToLine(note, lineIndex) || !isAlive(note) || seenAdditions.exists(note)) continue;
			seenAdditions.set(note, true);
			additions.push(note);
		}
		if (additions.length == 0) return result;
		sortByTime(additions);
		return mergeByTime(result, additions);
	}

	static function mergeByTime(ordered:Array<Dynamic>, additions:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		var left = 0;
		var right = 0;
		while (left < ordered.length && right < additions.length) {
			if (noteTime(ordered[left]) <= noteTime(additions[right]))
				result.push(ordered[left++]);
			else
				result.push(additions[right++]);
		}
		while (left < ordered.length) result.push(ordered[left++]);
		while (right < additions.length) result.push(additions[right++]);
		return result;
	}

	static function sortByTime(result:Array<Dynamic>):Void {
		result.sort(function(left:Dynamic, right:Dynamic):Int {
			var leftTime = noteTime(left);
			var rightTime = noteTime(right);
			return leftTime < rightTime ? -1 : leftTime > rightTime ? 1 : 0;
		});
	}

	static function appendLineNotes(result:Array<Dynamic>, lineIndex:Int,
		notes:Array<Dynamic>, seen:ObjectMap<Dynamic, Bool>):Void {
		if (notes == null) return;
		for (note in notes) {
			if (!belongsToLine(note, lineIndex) || !isAlive(note) || seen.exists(note)) continue;
			seen.set(note, true);
			result.push(note);
		}
	}

	static function sourceLineIndex(note:Dynamic):Int {
		if (note == null) return -1;
		var origin:Dynamic = Reflect.field(note, 'codenameOrigin');
		if (origin == null || Reflect.field(origin, 'engine') != 'codename') return -1;
		var value:Dynamic = Reflect.field(origin, 'lineIndex');
		return Std.isOfType(value, Int) && value >= 0 ? cast value : -1;
	}

	static function belongsToLine(note:Dynamic, lineIndex:Int):Bool {
		return sourceLineIndex(note) == lineIndex;
	}

	static function isAlive(note:Dynamic):Bool {
		var alive:Dynamic = note == null ? null : Reflect.field(note, 'alive');
		return alive != false;
	}

	@:keep public static function noteTime(note:Dynamic):Float {
		var value:Dynamic = note == null ? null : Reflect.field(note, 'strumTime');
		var parsed = value == null ? Math.NaN : Std.parseFloat(Std.string(value));
		return Math.isFinite(parsed) ? parsed : 0;
	}
}
