package;

using StringTools;

/** Merge embedded and companion Psych/FPS/Kade events without replaying shared entries. */
class SongEvents {
	static inline var EDITOR_SIDECAR_MARKER:String = 'disappointingplus-chart-editor';
	static inline var EDITOR_SIDECAR_MARKER_VERSION:Int = 1;

	/** Stable identity for an event row at one timestamp, including Codename
	 * authored identity when present. Used by the editor to remember which
	 * companion event a changed chart row replaces. */
	public static function eventSignature(event:Array<Dynamic>, time:Float):String {
		if (event == null)
			return '';
		var authored = CodenameEventMetadata.read(event, time);
		if (authored != null)
			return 'codename:' + CodenameEventMetadata.dedupeKey(authored);
		var values:Array<Dynamic> = [time];
		for (index in 0...4)
			values.push(index < event.length && event[index] != null ? Std.string(event[index]) : '');
		return haxe.Json.stringify(values);
	}

	/** Source key carried by an editor-imported companion event or tombstone. */
	public static function editorSidecarSourceKey(event:Array<Dynamic>):String {
		if (event == null)
			return null;
		for (index in 4...event.length) {
			var metadata:Dynamic = event[index];
			if (Reflect.field(metadata, 'engine') != EDITOR_SIDECAR_MARKER
				|| Reflect.field(metadata, 'version') != EDITOR_SIDECAR_MARKER_VERSION)
				continue;
			var key:Dynamic = Reflect.field(metadata, 'sourceKey');
			if (Std.isOfType(key, String) && key != '')
				return key;
		}
		return null;
	}

	/** Tombstones are inert native rows retained only to suppress the unchanged
	 * companion event after a chart save/reload. */
	public static function isEditorSidecarTombstone(event:Array<Dynamic>):Bool {
		if (editorSidecarSourceKey(event) == null)
			return false;
		for (index in 4...event.length) {
			var metadata:Dynamic = event[index];
			if (Reflect.field(metadata, 'engine') == EDITOR_SIDECAR_MARKER
				&& Reflect.field(metadata, 'version') == EDITOR_SIDECAR_MARKER_VERSION
				&& Reflect.field(metadata, 'deleted') == true)
				return true;
		}
		return false;
	}

	/** Attach a source marker without shifting Codename metadata or any future
	 * extension columns. The original key remains stable when the chart row is
	 * edited or moved. */
	public static function markEditorSidecarEvent(event:Array<Dynamic>, sourceKey:String,
		deleted:Bool = false):Void {
		if (event == null || sourceKey == null || sourceKey == '')
			return;
		if (editorSidecarSourceKey(event) != null)
			return;
		while (event.length < 4)
			event.push('');
		event.push({
			engine:EDITOR_SIDECAR_MARKER,
			version:EDITOR_SIDECAR_MARKER_VERSION,
			sourceKey:sourceKey,
			deleted:deleted
		});
	}

	/**
		Convert the event sidecars used by FPS Plus and a few older Kade forks.

		Those files are commonly shaped as
		`{"events":{"events":[[section,time,kind,"name;value1;value2"]]}}`
		instead of the Psych `[time, [[name, value1, value2]]]` groups.  Modern
		Psych chart writers may also emit compact `{t, e, v}` records. Keeping
		this normalization here means imported charts can retain the donor sidecar
		unchanged while the native event pump receives its existing ABI.
	*/
	static function appendEventGroups(groups:Array<Dynamic>, value:Dynamic):Void {
		if (value == null || groups == null)
			return;
		if (Std.isOfType(value, Array)) {
			for (entry in (cast value:Array<Dynamic>)) {
				if (isNativeGroup(entry))
					groups.push(entry);
				else {
					var converted = legacyEventRow(entry);
					if (converted != null)
						groups.push(converted);
					else {
						// Psych 0.7+ exports can store one event per object rather
						// than using the older `[time, [[name, ...]]]` groups.
						// Keep this branch after the array-row adapters so a legacy
						// event whose payload happens to be an object is not changed.
						var objectEvent = objectEventGroup(entry);
						if (objectEvent != null)
							groups.push(objectEvent);
					}
				}
			}
			return;
		}
		// FPS Plus wraps its rows in an object named `events`.  Accept another
		// `song`/`data` wrapper as well; this costs no chart-specific knowledge and
		// covers legacy exporters which serialized the sidecar payload twice.
		var nestedEvents:Dynamic = Reflect.field(value, 'events');
		if (nestedEvents != null && nestedEvents != value) {
			appendEventGroups(groups, nestedEvents);
			return;
		}
		var nestedSong:Dynamic = Reflect.field(value, 'song');
		if (nestedSong != null && nestedSong != value) {
			appendEventGroups(groups, nestedSong);
			return;
		}
		var nestedData:Dynamic = Reflect.field(value, 'data');
		if (nestedData != null && nestedData != value)
			appendEventGroups(groups, nestedData);
		var objectEvent = objectEventGroup(value);
		if (objectEvent != null)
			groups.push(objectEvent);
	}

	/**
		Normalize the object event record used by newer Psych chart writers.

		The exact value spelling changed between Psych releases: `v` may be an
		array, a semicolon-delimited string, or an object carrying `value1`/`v1`
		fields.  Accept all three without treating arbitrary metadata objects as
		events.  The native event ABI remains `[time, [[name, v1, v2, v3]]]`.
	*/
	static function objectEventGroup(value:Dynamic):Array<Dynamic> {
		if (value == null || Std.isOfType(value, Array))
			return null;
		var timeValue:Dynamic = Reflect.field(value, 't');
		if (timeValue == null)
			timeValue = Reflect.field(value, 'time');
		if (timeValue == null)
			timeValue = Reflect.field(value, 'timestamp');
		var time = Std.parseFloat(Std.string(timeValue));
		if (timeValue == null || Math.isNaN(time))
			return null;
		var nameValue:Dynamic = null;
		for (fieldName in ['e', 'name', 'event', 'eventName', 'type']) {
			var candidate:Dynamic = Reflect.field(value, fieldName);
			if (candidate != null && StringTools.trim(Std.string(candidate)) != '') {
				nameValue = candidate;
				break;
			}
		}
		// Require both a timestamp and an event-name field. This keeps ordinary
		// metadata objects (which may contain a `value` member) out of the event
		// stream while accepting both compact Psych and descriptive legacy rows.
		var name = StringTools.trim(nameValue == null ? '' : Std.string(nameValue));
		if (name == '')
			return null;
		var event:Array<Dynamic> = [name];
		var payload:Dynamic = Reflect.field(value, 'v');
		if (payload == null)
			payload = Reflect.field(value, 'values');
		if (payload == null)
			payload = Reflect.field(value, 'value');
		if (payload == null) {
			// A few descriptive exporters place v1/v2/v3 directly on the event
			// object. Reuse the fixed-slot object path below when any is present.
			for (fieldName in ['v1', 'value1', 'v2', 'value2', 'v3', 'value3'])
				if (Reflect.hasField(value, fieldName)) {
					payload = value;
					break;
				}
		}
		if (Std.isOfType(payload, Array)) {
			for (item in (cast payload:Array<Dynamic>))
				if (event.length < 4)
					event.push(item == null ? '' : Std.string(item));
		} else if (payload != null && !Std.isOfType(payload, String)) {
			var slots:Array<Array<String>> = [
				['v1', 'value1', 'x', 'first'],
				['v2', 'value2', 'y', 'second'],
				['v3', 'value3', 'z', 'third']
			];
			for (aliases in slots) {
				var item:Dynamic = null;
				for (fieldName in aliases) {
					var candidate:Dynamic = Reflect.field(payload, fieldName);
					if (candidate != null) {
						item = candidate;
						break;
					}
				}
				event.push(item == null ? '' : Std.string(item));
			}
		} else if (payload != null) {
			var encoded = Std.string(payload);
			var parts = encoded.split(';');
			for (index in 0...parts.length)
				if (event.length < 4)
					event.push(parts[index]);
		}
		while (event.length < 4)
			event.push('');
		return [time, [event]];
	}

	static function isNativeGroup(value:Dynamic):Bool {
		if (!Std.isOfType(value, Array))
			return false;
		var row:Array<Dynamic> = cast value;
		return row.length >= 2 && Std.isOfType(row[1], Array)
			&& !Math.isNaN(Std.parseFloat(Std.string(row[0])));
	}

	/** Convert one old row to a native event group, or return null when it is
		not an event row.  The donor's section/type columns are ignored except for
		the FPS movement-toggle bit, which is part of that event's value contract. */
	static function legacyEventRow(value:Dynamic):Array<Dynamic> {
		if (!Std.isOfType(value, Array))
			return null;
		var row:Array<Dynamic> = cast value;
		if (row.length < 2)
			return null;
		var time:Float = Math.NaN;
		var name:String = null;
		var firstValue:Int = 1;
		var timeValue:Dynamic = row[0];
		// FPS Plus/Kade sidecars use [section, time, eventType, payload].
		if (row.length >= 4) {
			var candidateTime = Std.parseFloat(Std.string(row[1]));
			if (!Math.isNaN(candidateTime) && Std.isOfType(row[3], String)) {
				time = candidateTime;
				timeValue = row[3];
				firstValue = 4;
			}
		}
		// A small number of old exports omit section/type and use
		// [time, "eventName", value1, value2, value3].
		if (Math.isNaN(time)) {
			var directTime = Std.parseFloat(Std.string(row[0]));
			if (!Math.isNaN(directTime) && Std.isOfType(row[1], String)) {
				time = directTime;
				timeValue = row[1];
				firstValue = 2;
			}
		}
		if (Math.isNaN(time) || timeValue == null)
			return null;
		var encoded = Std.string(timeValue);
		var parts = encoded.split(';');
		name = StringTools.trim(parts.length == 0 ? encoded : parts[0]);
		if (name == '')
			return null;
		var event:Array<Dynamic> = [name];
		if (parts.length > 1) {
			for (index in 1...parts.length)
				if (event.length < 4)
					event.push(parts[index]);
		} else {
			// FPS Plus's overhead chart stores toggleCamMovement's boolean in
			// the otherwise-unused event-channel column: [section,time,1|0,
			// "toggleCamMovement"]. Preserve that authored bit at the native
			// ABI boundary; dropping it makes both rows indistinguishable.
			if (name.toLowerCase() == 'togglecammovement'
				&& row.length > 2 && row[2] != null)
				event.push(Std.string(row[2]));
			for (index in firstValue...row.length)
				if (event.length < 4)
					event.push(row[index] == null ? '' : Std.string(row[index]));
		}
		while (event.length < 4)
			event.push('');
		return [time, [event]];
	}

	/** Accept both song wrappers and bare song data, including legacy event rows. */
	public static function fromSong(data:Dynamic):Array<Dynamic> {
		if (data == null) return [];
		var song:Dynamic = Reflect.field(data, 'song');
		if (song == null || Std.isOfType(song, String)) song = data;
		var groups:Array<Dynamic> = [];
		var events:Dynamic = Reflect.field(song, 'events');
		appendEventGroups(groups, events);
		var sections:Dynamic = Reflect.field(song, 'notes');
		if (Std.isOfType(sections, Array)) {
			for (section in (cast sections:Array<Dynamic>)) {
				if (section == null) continue;
				var notes:Dynamic = Reflect.field(section, 'sectionNotes');
				if (!Std.isOfType(notes, Array)) continue;
				for (row in (cast notes:Array<Dynamic>)) {
					if (!Std.isOfType(row, Array) || row.length < 3 || row[1] != -1 || !Std.isOfType(row[2], String)) continue;
					var event:Array<Dynamic> = [row[2]];
					for (i in 3...6) event.push(row.length > i ? row[i] : '');
					groups.push([row[0], [event]]);
				}
			}
		}
		return groups;
	}

	public static function collect(embedded:Array<Dynamic>, companion:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		var seen = new Map<String, Bool>();
		var suppressedCompanion = new Map<String, Bool>();
		if (embedded != null)
			for (group in embedded) {
				if (!Std.isOfType(group, Array) || group.length < 2 || !Std.isOfType(group[1], Array))
					continue;
				var time:Float = group[0];
				if (Math.isNaN(time)) continue;
				for (event in (group[1]:Array<Dynamic>)) {
					if (!Std.isOfType(event, Array)) continue;
					var sourceKey = editorSidecarSourceKey(cast event);
					if (sourceKey != null)
						suppressedCompanion.set(sourceKey, true);
				}
			}
		for (sourceIndex in 0...2) {
			var groups = sourceIndex == 0 ? embedded : companion;
			if (groups == null) continue;
			for (group in groups) {
				if (!Std.isOfType(group, Array) || group.length < 2 || !Std.isOfType(group[1], Array)) continue;
				var time:Float = group[0];
				if (Math.isNaN(time)) continue;
				for (event in (group[1]:Array<Dynamic>)) {
					if (!Std.isOfType(event, Array) || event.length == 0 || event[0] == null) continue;
					var row:Array<Dynamic> = cast event;
					var key = eventSignature(row, time);
					if (sourceIndex == 1 && suppressedCompanion.exists(key))
						continue;
					var authored = CodenameEventMetadata.read(row, time);
					var name = Std.string(event[0]);
					var v1 = event.length > 1 && event[1] != null ? Std.string(event[1]) : '';
					var v2 = event.length > 2 && event[2] != null ? Std.string(event[2]) : '';
					var v3 = event.length > 3 && event[3] != null ? Std.string(event[3]) : '';
					if (seen.exists(key)) continue;
					seen.set(key, true);
					var nativeEvent:Dynamic = {time:time, name:name, v1:v1, v2:v2, v3:v3, order:result.length};
					if (authored != null) Reflect.setField(nativeEvent, 'codename', authored);
					result.push(nativeEvent);
				}
			}
		}
		result.sort(function(a, b) return a.time < b.time ? -1 : a.time > b.time ? 1 : a.order - b.order);
		return result;
	}
}
