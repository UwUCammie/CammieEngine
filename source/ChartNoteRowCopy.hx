import haxe.Json;

/** Data-only chart row copying used by the chart editor. Note rows are JSON
	arrays whose optional columns are owned by different compatibility layers;
	copy the complete row and change only the timestamp. */
class ChartNoteRowCopy {
	public static function withTimestamp(row:Array<Dynamic>, timestamp:Float):Array<Dynamic> {
		if (row == null || row.length == 0)
			throw 'Cannot copy an empty chart note row';

		// Chart rows originate in JSON/JSONC, so a JSON round trip gives every
		// nested optional value independent ownership without interpreting fields
		// that may belong to another engine or to a future row extension.
		var copied:Dynamic = Json.parse(Json.stringify(row));
		if (!Std.isOfType(copied, Array) || (cast copied:Array<Dynamic>).length == 0)
			throw 'Chart note row did not copy as an array';
		var result:Array<Dynamic> = cast copied;
		result[0] = timestamp;
		return result;
	}
}
