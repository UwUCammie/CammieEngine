package;

using StringTools;

/** Event and note type names one Psych-format chart refers to. */
typedef SourceChartReferenceNames = {
	var events:Array<String>;
	var noteTypes:Array<String>;
}

/**
	The one walk over a Psych-format chart that finds which custom event and
	note type scripts it needs. Psych and its forks store charts the same way
	and only disagree on three small points, which the caller passes in:

	- `noteTypeName`: the built-in name table a numeric note type indexes;
	- `legacyEventRow`: whether a section row is an old in-section event
	  (`[time, lane below zero, name, value1, value2]`) rather than a note. It
	  gets the row and whether the chart has an `events` list;
	- `clean`: how a name is made safe to look up below a mod folder.

	Nothing is skipped because the engine already knows a name: a mod may ship
	its own script for a built-in type, and a name with no file just finds no
	script.
*/
class SourceChartReferences {
	/** Charts are either `{song:{...}}` or the bare song object. */
	public static function songData(chart:Dynamic):Dynamic {
		if (chart == null) return null;
		var nested:Dynamic = Reflect.field(chart, 'song');
		return nested == null || Std.isOfType(nested, String) ? chart : nested;
	}

	/** The chart's own song name, trimmed, or '' when it has none. */
	public static function songName(chart:Dynamic):String {
		var data = songData(chart);
		var value:Dynamic = data == null ? null : Reflect.field(data, 'song');
		return value == null ? '' : Std.string(value).trim();
	}

	/**
		Collect every event and note type name of `chart`, then the event names
		of `companionEvents` (a separate events file, in any shape eventRows
		accepts). `report` is told about each section (row -1) and each row before
		the row is looked at, for callers that need coordinates of a bad row.
	*/
	public static function collect(chart:Dynamic, companionEvents:Dynamic, noteTypeName:Int->String,
		legacyEventRow:(Array<Dynamic>, Bool)->Bool, ?clean:String->String,
		?report:(String, Int, Int)->Void):SourceChartReferenceNames {
		if (clean == null) clean = cleanReference;
		var result:SourceChartReferenceNames = {events:[], noteTypes:[]};
		var seenTypes:Map<String, Bool> = new Map();
		var data = songData(chart);
		if (data != null) {
			var events:Dynamic = Reflect.field(data, 'events');
			if (events != null) addEventNames(result.events, listedRows(events), clean);
			walkRows(data, events != null, legacyEventRow, report, function(values:Array<Dynamic>, legacy:Bool):Void {
				if (legacy) {
					if (values.length >= 3) addEventNames(result.events, [values.slice(2)], clean);
					return;
				}
				if (values.length < 4) return;
				var value:Dynamic = values[3];
				var name:String = null;
				if (Std.isOfType(value, String)) name = cast value;
				else if (value != null && noteTypeName != null) {
					// Old charts store an index into the engine's built-in type list.
					var index = Std.parseInt(Std.string(value));
					if (index != null) name = noteTypeName(index);
				}
				name = name == null ? '' : clean(name);
				if (name == '' || seenTypes.exists(name.toLowerCase())) return;
				seenTypes.set(name.toLowerCase(), true);
				result.noteTypes.push(name);
			});
		}
		addEventNames(result.events, eventRows(companionEvents, legacyEventRow), clean);
		return result;
	}

	/**
		Every event of a chart, a bare song object, an events file or a plain event
		list, as `[name, value1, value2, ...]` rows. Accepts the modern
		`[time, [[name, v1, v2], ...]]` list, flat `[time, -1, name, ...]` rows,
		object records (`e`/`name`/`event`/`eventName`/`type`, values in `v`) and
		old in-section rows when `legacyEventRow` says so.
	*/
	public static function eventRows(payload:Dynamic, ?legacyEventRow:(Array<Dynamic>, Bool)->Bool):Array<Array<Dynamic>> {
		if (payload == null) return [];
		if (Std.isOfType(payload, Array) || Std.isOfType(payload, String)) return listedRows(payload);
		var data = songData(payload);
		var events:Dynamic = Reflect.field(data, 'events');
		var result:Array<Array<Dynamic>> = events == null ? [] : listedRows(events);
		if (Reflect.field(data, 'notes') != null) {
			if (legacyEventRow != null)
				walkRows(data, events != null, legacyEventRow, null, function(values:Array<Dynamic>, legacy:Bool):Void {
					if (legacy && values.length >= 3) result.push(values.slice(2));
				});
		} else if (events == null) {
			// Not a chart at all: a single loose event record.
			var row = recordRow(data);
			if (row != null) result.push(row);
		}
		return result;
	}

	/** Slash-separated relative name, or '' when it would leave its folder. */
	public static function cleanReference(value:String):String {
		if (value == null) return '';
		var result = value.replace('\\', '/').trim();
		while (result.startsWith('./')) result = result.substr(2);
		if (result == '' || result.startsWith('/') || result.indexOf(':') == 1) return '';
		for (part in result.split('/'))
			if (part == '' || part == '.' || part == '..') return '';
		return result;
	}

	public static function isScriptFile(value:String, extensions:Array<String>):Bool {
		if (value == null) return false;
		var lower = value.toLowerCase();
		for (extension in extensions) if (lower.endsWith(extension)) return true;
		return false;
	}

	public static function stripScriptExtension(value:String, extensions:Array<String>):String {
		if (value == null) return '';
		var lower = value.toLowerCase();
		for (extension in extensions)
			if (lower.endsWith(extension)) return value.substr(0, value.length - extension.length);
		return value;
	}

	static function walkRows(data:Dynamic, hasEvents:Bool, legacyEventRow:(Array<Dynamic>, Bool)->Bool,
		report:(String, Int, Int)->Void, onRow:(Array<Dynamic>, Bool)->Void):Void {
		var sections:Dynamic = Reflect.field(data, 'notes');
		if (!Std.isOfType(sections, Array)) return;
		var sectionIndex = 0;
		for (section in (cast sections:Array<Dynamic>)) {
			if (report != null) report('section', sectionIndex, -1);
			var rows:Dynamic = section == null ? null : Reflect.field(section, 'sectionNotes');
			if (Std.isOfType(rows, Array)) {
				var rowIndex = 0;
				for (row in (cast rows:Array<Dynamic>)) {
					// Reported before the row is touched, so a broken row still leaves its position behind.
					if (report != null) report('row', sectionIndex, rowIndex);
					rowIndex++;
					if (!Std.isOfType(row, Array)) continue;
					var values:Array<Dynamic> = cast row;
					onRow(values, values.length >= 2 && legacyEventRow != null && legacyEventRow(values, hasEvents));
				}
			}
			sectionIndex++;
		}
	}

	static function listedRows(value:Dynamic):Array<Array<Dynamic>> {
		var result:Array<Array<Dynamic>> = [];
		if (value == null) return result;
		if (!Std.isOfType(value, Array)) {
			if (!Std.isOfType(value, String) && Reflect.hasField(value, 'events'))
				return listedRows(Reflect.field(value, 'events'));
			var single = recordRow(value);
			if (single != null) result.push(single);
			return result;
		}
		for (item in (cast value:Array<Dynamic>)) {
			if (Std.isOfType(item, Array)) {
				var row:Array<Dynamic> = cast item;
				if (row.length >= 2 && Std.isOfType(row[1], Array)) {
					for (event in (cast row[1]:Array<Dynamic>)) {
						var listed = recordRow(event);
						if (listed != null) result.push(listed);
					}
					continue;
				}
				if (row.length >= 3 && Std.parseInt(Std.string(row[1])) == -1) {
					result.push(row.slice(2));
					continue;
				}
			}
			var record = recordRow(item);
			if (record != null) result.push(record);
		}
		return result;
	}

	static function recordRow(record:Dynamic):Array<Dynamic> {
		if (record == null) return null;
		if (Std.isOfType(record, String)) return [record];
		if (Std.isOfType(record, Array)) {
			var values:Array<Dynamic> = cast record;
			return values.length > 0 ? values : null;
		}
		// Newer charts write `e` (with `t` for time and `v` for values); older
		// wrappers spell the name out.
		for (fieldName in ['e', 'name', 'event', 'eventName', 'type']) {
			var value:Dynamic = Reflect.field(record, fieldName);
			if (value == null) continue;
			var row:Array<Dynamic> = [value];
			var values:Dynamic = Reflect.field(record, 'v');
			if (Std.isOfType(values, Array)) row = row.concat(cast values);
			return row;
		}
		return null;
	}

	static function addEventNames(names:Array<String>, rows:Array<Array<Dynamic>>, clean:String->String):Void {
		for (row in rows) {
			if (row.length == 0 || row[0] == null) continue;
			var name = clean(Std.string(row[0]));
			if (name != '' && names.indexOf(name) < 0) names.push(name);
		}
	}
}
