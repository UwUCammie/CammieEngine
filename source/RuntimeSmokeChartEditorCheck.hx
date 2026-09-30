package;

/** Generic event fixture and assertions shared by the offscreen editor smoke. */
class RuntimeSmokeChartEditorCheck {
	public static inline var SOURCE_EDIT:String = '__dp_chart_editor_smoke_edit__';
	public static inline var SOURCE_DELETE:String = '__dp_chart_editor_smoke_delete__';
	public static inline var EDITED_NAME:String = '__dp_chart_editor_smoke_edited__';
	public static inline var EDITED_TIME:Float = 1123;
	public static inline var EDITED_VALUE_1:String = 'edited-v1';
	public static inline var EDITED_VALUE_2:String = 'edited-v2';
	public static inline var EDITED_VALUE_3:String = 'edited-v3';

	/** Find one named editor reference and reject ambiguous fixture rows. */
	public static function uniqueEditorEvent(groups:Array<Dynamic>, name:String):Dynamic {
		var found:Dynamic = null;
		for (reference in ChartEventModel.list(groups)) {
			var event:Array<Dynamic> = cast Reflect.field(reference, 'event');
			if (event.length == 0 || event[0] != name)
				continue;
			if (found != null)
				throw 'duplicate editor smoke event: ' + name;
			found = reference;
		}
		return found;
	}

	/** Confirm fixture events were merged from the companion file for editing. */
	public static function validateLoaded(groups:Array<Dynamic>):String {
		var edit = uniqueEditorEvent(groups, SOURCE_EDIT);
		var deleted = uniqueEditorEvent(groups, SOURCE_DELETE);
		if (edit == null || deleted == null)
			return 'ChartingState did not merge both companion fixture events';
		var editEvent:Array<Dynamic> = cast Reflect.field(edit, 'event');
		var deletedEvent:Array<Dynamic> = cast Reflect.field(deleted, 'event');
		if (SongEvents.editorSidecarSourceKey(editEvent) == null
			|| SongEvents.editorSidecarSourceKey(deletedEvent) == null)
			return 'companion fixture rows lost their sidecar ownership markers';
		if (Reflect.field(edit, 'time') != 1000 || editEvent[1] != 'source-v1'
			|| editEvent[2] != 'source-v2' || editEvent[3] != 'source-v3')
			return 'editable companion event payload did not match its fixture';
		if (Reflect.field(deleted, 'time') != 2000 || deletedEvent[1] != 'delete-v1')
			return 'deletable companion event payload did not match its fixture';
		return '';
	}

	/** Validate editor visibility and the exact runtime event collection. */
	public static function validateRoundTrip(song:Dynamic, companion:Dynamic):String {
		var groups:Array<Dynamic> = cast Reflect.field(song, 'events');
		if (uniqueEditorEvent(groups, SOURCE_EDIT) != null
			|| uniqueEditorEvent(groups, SOURCE_DELETE) != null)
			return 'original companion event returned to the editor after edit/delete';
		var edited = uniqueEditorEvent(groups, EDITED_NAME);
		if (edited == null)
			return 'edited companion event is missing after autosave/reload';
		var editedEvent:Array<Dynamic> = cast Reflect.field(edited, 'event');
		if (Reflect.field(edited, 'time') != EDITED_TIME
			|| editedEvent[1] != EDITED_VALUE_1 || editedEvent[2] != EDITED_VALUE_2
			|| editedEvent[3] != EDITED_VALUE_3)
			return 'edited companion event payload or time changed after reload';

		var runtimeEvents = SongEvents.collect(SongEvents.fromSong(song), SongEvents.fromSong(companion));
		var editedCount = 0;
		for (runtimeEvent in runtimeEvents) {
			var name = Reflect.field(runtimeEvent, 'name');
			if (name == SOURCE_EDIT || name == SOURCE_DELETE)
				return 'runtime collection replayed a superseded or deleted companion event';
			if (name != EDITED_NAME)
				continue;
			editedCount++;
			if (Reflect.field(runtimeEvent, 'time') != EDITED_TIME
				|| Reflect.field(runtimeEvent, 'v1') != EDITED_VALUE_1
				|| Reflect.field(runtimeEvent, 'v2') != EDITED_VALUE_2
				|| Reflect.field(runtimeEvent, 'v3') != EDITED_VALUE_3)
				return 'runtime collection changed the edited companion event payload';
		}
		if (editedCount != 1)
			return 'runtime collection must contain exactly one edited companion event';
		return '';
	}
}
