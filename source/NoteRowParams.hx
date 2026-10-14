package;

/** One named per-note parameter, as note-kind scripts read it. */
typedef NoteParam = {
	var name:String;
	var value:Dynamic;
}

/**
	Optional native note row column 14: named per-note parameters, the way
	V-Slice authors them (`p: [{n, v}]`). Columns 0..13 keep their meanings
	(13 is the Codename origin tag), and null padding keeps the slot readable
	beside them. A row without the column simply has no params.
*/
class NoteRowParams {
	public static inline var SLOT:Int = 14;
	static inline var KEY:String = 'noteParams';

	/** Valid params from an authored V-Slice `p` list, or null when there are none. */
	public static function fromVSlice(raw:Dynamic):Null<Array<NoteParam>> {
		if (raw == null || !Std.isOfType(raw, Array))
			return null;
		var result:Array<NoteParam> = [];
		for (entry in (cast raw:Array<Dynamic>)) {
			if (entry == null || Std.isOfType(entry, String) || Std.isOfType(entry, Array))
				continue;
			var name:Dynamic = Reflect.field(entry, 'n');
			if (name == null)
				name = Reflect.field(entry, 'name');
			if (!Std.isOfType(name, String) || StringTools.trim(name) == '')
				continue;
			var value:Dynamic = Reflect.hasField(entry, 'v') ? Reflect.field(entry, 'v') : Reflect.field(entry, 'value');
			result.push({name: name, value: value});
		}
		return result.length == 0 ? null : result;
	}

	/** A new row carrying params at SLOT. A row that already reaches SLOT is left alone. */
	public static function apply(row:Array<Dynamic>, params:Array<NoteParam>):Array<Dynamic> {
		if (row == null || params == null || params.length == 0 || row.length > SLOT)
			return row;
		var result = row.copy();
		while (result.length < SLOT)
			result.push(null);
		var tag:Dynamic = {};
		Reflect.setField(tag, KEY, [for (param in params) {name: param.name, value: param.value}]);
		result.push(tag);
		return result;
	}

	/** Params stored on a chart row, or null. Malformed entries are skipped. */
	public static function read(row:Array<Dynamic>):Null<Array<Dynamic>> {
		if (row == null || row.length <= SLOT)
			return null;
		var tag:Dynamic = row[SLOT];
		if (tag == null || Std.isOfType(tag, Array) || Std.isOfType(tag, String))
			return null;
		var list:Dynamic = Reflect.field(tag, KEY);
		if (list == null || !Std.isOfType(list, Array))
			return null;
		var result:Array<Dynamic> = [];
		for (entry in (cast list:Array<Dynamic>)) {
			if (entry == null || Std.isOfType(entry, String) || Std.isOfType(entry, Array))
				continue;
			var name:Dynamic = Reflect.field(entry, 'name');
			if (Std.isOfType(name, String) && name != '')
				result.push({name: name, value: Reflect.field(entry, 'value')});
		}
		return result.length == 0 ? null : result;
	}
}
