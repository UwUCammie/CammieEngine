package;

/** Historical NV prepares fresh admitted events before and after event loading.
 * The host retains its native queue, media services and existing interpreters. */
class NightmareVisionLegacyEventPreparation {
	public static function prepare(rows:Void->Array<Dynamic>, noteOffset:Void->Float,
		scripts:Void->Map<String, Dynamic>, call:(Dynamic, String, Array<Dynamic>)->Dynamic,
		global:(String, Array<Dynamic>)->Dynamic, load:String->Void,
		publish:(Dynamic, SourceEventNote)->Void, builtin:SourceEventNote->Bool):Void {
		var invoke = function(event:SourceEventNote, callback:String):Dynamic {
			var script = scripts().get(event.event);
			if (script == null) throw '[nightmare-vision-event] Null script handle: ' + event.event;
			var args:Array<Dynamic> = Reflect.getProperty(script, 'scriptType') == 'lua'
				? [event.value1, event.value2] : [event];
			return call(script, callback, args);
		};
		var collect = function():Array<{row:Dynamic, event:SourceEventNote}> {
			var result:Array<{row:Dynamic, event:SourceEventNote}> = [];
			for (row in rows()) {
				var event = new SourceEventNote(row, noteOffset());
				if (scripts().exists(event.event) && invoke(event, 'shouldPush') == false) continue;
				result.push({row:row, event:event});
			}
			return result;
		};
		var names:Map<String, Bool> = [];
		for (entry in collect()) {
			var event = entry.event;
			if (!names.exists(event.event)) {
				names.set(event.event, true);
				if (scripts().exists(event.event)) invoke(event, 'firstPush');
			}
		}
		for (name in names.keys()) load(name);
		for (entry in collect()) {
			var event = entry.event;
			// Match compound-assignment evaluation: callbacks may mutate the view.
			var time = event.strumTime;
			var offset:Float = global('eventEarlyTrigger', [event.event, event.value1, event.value2]);
			if (scripts().exists(event.event)) offset = invoke(event, 'getOffset');
			if (offset == 0 && event.event == 'Kill Henchmen') offset = 280;
			event.strumTime = time - offset;
			publish(entry.row, event);
			if (!builtin(event) && scripts().exists(event.event)) invoke(event, 'onPush');
		}
	}
}
