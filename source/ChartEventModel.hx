package;

/** UI-independent helpers for editing imported chart events and their timeline. */
class ChartEventModel {
	/** Move embedded legacy section events into the editable event list. */
	public static function normalizeSong(song:Dynamic):Void {
		var normalized = SongEvents.fromSong(song);
		var sections:Dynamic = Reflect.field(song, 'notes');
		if (Std.isOfType(sections, Array))
			for (section in (cast sections:Array<Dynamic>)) {
				var notes:Dynamic = Reflect.field(section, 'sectionNotes');
				if (!Std.isOfType(notes, Array))
					continue;
				var rows:Array<Dynamic> = cast notes;
				var index = rows.length - 1;
				while (index >= 0) {
					var row:Dynamic = rows[index];
					if (Std.isOfType(row, Array) && row.length >= 3 && row[1] == -1
						&& Std.isOfType(row[2], String))
						rows.splice(index, 1);
					index--;
				}
			}
		Reflect.setField(song, 'events', normalized);
	}

	/** Make companion events available for navigation and chart editing once. */
	public static function mergeCompanion(song:Dynamic, companion:Dynamic):Void {
		var groups:Array<Dynamic> = cast Reflect.field(song, 'events');
		if (groups == null)
			groups = [];
		var seen = new Map<String, Bool>();
		var suppressed = new Map<String, Bool>();
		for (entry in list(groups)) {
			var key = signature(entry);
			seen.set(key, true);
			var sourceKey = SongEvents.editorSidecarSourceKey(cast Reflect.field(entry, 'event'));
			if (sourceKey != null)
				suppressed.set(sourceKey, true);
		}
		// Tombstones are hidden from the editor event list, but remain in the
		// chart rows so the source sidecar stays suppressed after save/reload.
		for (group in groups)
			if (Std.isOfType(group, Array) && group.length >= 2 && Std.isOfType(group[1], Array))
				for (event in (cast group[1]:Array<Dynamic>))
					if (Std.isOfType(event, Array)) {
						var sourceKey = SongEvents.editorSidecarSourceKey(cast event);
						if (sourceKey != null)
							suppressed.set(sourceKey, true);
					}
		for (entry in list(SongEvents.fromSong(companion))) {
			var key = signature(entry);
			if (suppressed.exists(key))
				continue;
			if (seen.exists(key)) {
				// A chart can already contain an earlier export of this exact
				// companion event. Bind matching rows now so later edits retain the
				// ownership that exact-signature dedupe would otherwise hide.
				for (existing in list(groups))
					if (signature(existing) == key)
						SongEvents.markEditorSidecarEvent(cast Reflect.field(existing, 'event'), key);
				continue;
			}
			seen.set(key, true);
			var event:Array<Dynamic> = cast Reflect.field(entry, 'event');
			event = event.copy();
			SongEvents.markEditorSidecarEvent(event, key);
			var time:Float = Reflect.field(entry, 'time');
			var target:Array<Dynamic> = null;
			for (candidate in groups)
				if (Std.isOfType(candidate, Array) && candidate.length >= 2
					&& number(candidate[0]) == time && Std.isOfType(candidate[1], Array)) {
					target = candidate;
					break;
				}
			if (target == null) {
				target = [time, []];
				groups.push(target);
			}
			(cast target[1]:Array<Dynamic>).push(event);
		}
		groups.sort(compareGroups);
		Reflect.setField(song, 'events', groups);
	}

	static function signature(entry:Dynamic):String {
		var event:Array<Dynamic> = cast Reflect.field(entry, 'event');
		var time:Float = Reflect.field(entry, 'time');
		return SongEvents.eventSignature(event, time);
	}

	/** Section start in milliseconds, including BPM changes at section boundaries. */
	public static function sectionStart(sections:Array<Dynamic>, initialBpm:Float, index:Int):Float {
		var time = 0.0;
		var bpm = initialBpm > 0 ? initialBpm : 100.0;
		if (sections == null)
			return time;
		for (i in 0...Std.int(Math.min(index, sections.length))) {
			var section = sections[i];
			if (Reflect.field(section, 'changeBPM') == true && number(Reflect.field(section, 'bpm')) > 0)
				bpm = number(Reflect.field(section, 'bpm'));
			var length = number(Reflect.field(section, 'lengthInSteps'));
			time += (length > 0 ? length : 16) * 15000 / bpm;
		}
		return time;
	}

	/** Find the section containing a timestamp; an exact boundary belongs to the next section. */
	public static function sectionAtTime(sections:Array<Dynamic>, initialBpm:Float, time:Float):Int {
		if (sections == null || sections.length == 0)
			return 0;
		var elapsed = 0.0;
		var bpm = initialBpm > 0 ? initialBpm : 100.0;
		for (i in 0...sections.length) {
			var section = sections[i];
			if (Reflect.field(section, 'changeBPM') == true && number(Reflect.field(section, 'bpm')) > 0)
				bpm = number(Reflect.field(section, 'bpm'));
			var length = number(Reflect.field(section, 'lengthInSteps'));
			elapsed += (length > 0 ? length : 16) * 15000 / bpm;
			if (time < elapsed)
				return i;
		}
		return sections.length - 1;
	}
	/** Flatten event groups into sortable references without changing the chart. */
	public static function list(groups:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (groups == null)
			return result;

		for (group in groups) {
			if (!Std.isOfType(group, Array))
				continue;
			var values:Array<Dynamic> = cast group;
			if (values.length < 2 || !Std.isOfType(values[1], Array))
				continue;
			var time = number(values[0]);
			for (event in (cast values[1]:Array<Dynamic>)) {
				if (!Std.isOfType(event, Array) || (cast event:Array<Dynamic>).length == 0)
					continue;
				if (SongEvents.isEditorSidecarTombstone(cast event))
					continue;
				result.push({group: values, event: event, time: time, order: result.length});
			}
		}

		result.sort(function(left:Dynamic, right:Dynamic):Int {
			var leftTime:Float = Reflect.field(left, 'time');
			var rightTime:Float = Reflect.field(right, 'time');
			var leftOrder:Int = Reflect.field(left, 'order');
			var rightOrder:Int = Reflect.field(right, 'order');
			return leftTime < rightTime ? -1 : (leftTime > rightTime ? 1
				: leftOrder - rightOrder);
		});
		return result;
	}

	/** Add an event to its timestamp group, creating and sorting groups as needed. */
	public static function add(groups:Array<Dynamic>, time:Float, name:String,
		v1:String, v2:String, v3:String):Dynamic {
		if (groups == null)
			groups = [];

		var group:Array<Dynamic> = null;
		for (candidate in groups) {
			if (!Std.isOfType(candidate, Array))
				continue;
			var values:Array<Dynamic> = cast candidate;
			if (values.length >= 2 && number(values[0]) == time
				&& Std.isOfType(values[1], Array)) {
				group = values;
				break;
			}
		}

		if (group == null) {
			group = [time, []];
			groups.push(group);
		}
		var event:Array<Dynamic> = [name, v1, v2, v3];
		(cast group[1]:Array<Dynamic>).push(event);
		groups.sort(compareGroups);
		return {groups: groups, group: group, event: event};
	}

	/** Save the selected event fields and keep timestamp groups sorted. */
	public static function update(groups:Array<Dynamic>, reference:Dynamic, time:Float,
		name:String, v1:String, v2:String, v3:String):Bool {
		if (groups == null || reference == null)
			return false;
		var group:Array<Dynamic> = cast Reflect.field(reference, 'group');
		var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
		if (group == null || event == null || groups.indexOf(group) < 0
			|| group.length < 2 || !Std.isOfType(group[1], Array)
			|| (cast group[1]:Array<Dynamic>).indexOf(event) < 0)
			return false;
		var previousTime = number(group[0]);
		var authored = CodenameEventMetadata.read(event, previousTime);
		var nativeChanged = (event[0] == null ? '' : Std.string(event[0])) != name
			|| (event.length > 1 && event[1] != null ? Std.string(event[1]) : '') != v1
			|| (event.length > 2 && event[2] != null ? Std.string(event[2]) : '') != v2
			|| (event.length > 3 && event[3] != null ? Std.string(event[3]) : '') != v3;

		setField(event, 0, name);
		setField(event, 1, v1);
		setField(event, 2, v2);
		setField(event, 3, v3);
		if (CodenameEventMetadata.marked(event)) {
			if (nativeChanged || authored == null) {
				// Keep any extension columns at their authored indexes.
				if (event.length == 5) event.pop();
				else event[4] = null;
			}
			else if (previousTime != time)
				event[4] = CodenameEventMetadata.moved(authored, time, event);
		}
		if (number(group[0]) != time) {
			var originalEvents:Array<Dynamic> = cast group[1];
			originalEvents.remove(event);
			if (originalEvents.length == 0)
				groups.remove(group);
			var target:Array<Dynamic> = null;
			for (candidate in groups) {
				if (!Std.isOfType(candidate, Array))
					continue;
				var values:Array<Dynamic> = cast candidate;
				if (values.length >= 2 && number(values[0]) == time
					&& Std.isOfType(values[1], Array)) {
					target = values;
					break;
				}
			}
			if (target == null) {
				target = [time, []];
				groups.push(target);
			}
			(cast target[1]:Array<Dynamic>).push(event);
		}
		groups.sort(compareGroups);
		return true;
	}

	/** Delete one event and discard its now-empty timestamp group. */
	public static function remove(groups:Array<Dynamic>, reference:Dynamic):Bool {
		if (groups == null || reference == null)
			return false;
		var group:Array<Dynamic> = cast Reflect.field(reference, 'group');
		var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
		if (group == null || event == null || groups.indexOf(group) < 0
			|| group.length < 2 || !Std.isOfType(group[1], Array))
			return false;
		var events:Array<Dynamic> = cast group[1];
		if (!events.remove(event))
			return false;
		if (events.length == 0)
			groups.remove(group);
		return true;
	}

	/** Remove a visible row and retain an inert tombstone when it originated in
	 * a companion. The sidecar itself remains untouched. */
	public static function removeSongEvent(song:Dynamic, reference:Dynamic):Bool {
		if (song == null || reference == null)
			return false;
		var groups:Array<Dynamic> = cast Reflect.field(song, 'events');
		var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
		var sourceKey = SongEvents.editorSidecarSourceKey(event);
		var time:Float = Reflect.field(reference, 'time');
		if (!remove(groups, reference))
			return false;
		if (sourceKey != null)
			addSidecarTombstone(song, time, sourceKey);
		return true;
	}

	static function addSidecarTombstone(song:Dynamic, time:Float, sourceKey:String):Void {
		var groups:Array<Dynamic> = cast Reflect.field(song, 'events');
		if (groups == null)
			groups = [];
		for (group in groups)
			if (Std.isOfType(group, Array) && group.length >= 2 && number(group[0]) == time
				&& Std.isOfType(group[1], Array)) {
				var tombstone:Array<Dynamic> = [null, null, null, null];
				SongEvents.markEditorSidecarEvent(tombstone, sourceKey, true);
				(cast group[1]:Array<Dynamic>).push(tombstone);
				Reflect.setField(song, 'events', groups);
				return;
			}
		var tombstone:Array<Dynamic> = [null, null, null, null];
		SongEvents.markEditorSidecarEvent(tombstone, sourceKey, true);
		groups.push([time, [tombstone]]);
		groups.sort(compareGroups);
		Reflect.setField(song, 'events', groups);
	}

	static function setField(event:Array<Dynamic>, index:Int, value:String):Void {
		while (event.length <= index)
			event.push('');
		event[index] = value;
	}

	static function compareGroups(left:Dynamic, right:Dynamic):Int {
		if (!Std.isOfType(left, Array) || !Std.isOfType(right, Array))
			return 0;
		var leftValues:Array<Dynamic> = cast left;
		var rightValues:Array<Dynamic> = cast right;
		var leftTime = leftValues.length > 0 ? number(leftValues[0]) : 0;
		var rightTime = rightValues.length > 0 ? number(rightValues[0]) : 0;
		return leftTime < rightTime ? -1 : (leftTime > rightTime ? 1 : 0);
	}

	static function number(value:Dynamic):Float {
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			return value;
		var parsed = value == null ? 0.0 : Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : parsed;
	}
}
