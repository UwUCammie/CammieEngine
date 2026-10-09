package;

/** Historical NV event callbacks over shared native rows and script handles. */
class NightmareVisionLegacyEventPreparation {
	public static function invoke(event:Dynamic, callback:String, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic):Dynamic {
		var name:String = Reflect.getProperty(event, 'event');
		var script = scripts().get(name);
		if (script == null) throw '[nightmare-vision-event] Null script handle: ' + name;
		var args:Array<Dynamic> = Reflect.getProperty(script, 'scriptType') == 'lua'
			? [Reflect.getProperty(event, 'value1'), Reflect.getProperty(event, 'value2')] : [event];
		return call(script, callback, args);
	}

	public static function shouldPush(event:Dynamic, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic):Bool {
		return !scripts().exists(Reflect.getProperty(event, 'event')) || invoke(event, 'shouldPush', scripts, call) != false;
	}

	public static function firstPush(event:Dynamic, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic):Void {
		if (scripts().exists(Reflect.getProperty(event, 'event'))) invoke(event, 'firstPush', scripts, call);
	}

	public static function earlyTrigger(event:Dynamic, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic, global:(String, Array<Dynamic>)->Dynamic):Float {
		var offset:Float = global('eventEarlyTrigger', [Reflect.getProperty(event, 'event'),
			Reflect.getProperty(event, 'value1'), Reflect.getProperty(event, 'value2')]);
		if (scripts().exists(Reflect.getProperty(event, 'event'))) offset = invoke(event, 'getOffset', scripts, call);
		if (offset != 0) return offset;
		return Reflect.getProperty(event, 'event') == 'Kill Henchmen' ? 280 : 0;
	}

	/** Admission runs during traversal, before the next source row is read. */
	public static function collect(visit:(Dynamic->Void)->Void, noteOffset:Void->Float,
		scripts:Void->Map<String, Dynamic>, call:(Dynamic, String, Array<Dynamic>)->Dynamic):Array<{row:Dynamic, event:SourceEventNote}> {
		var result:Array<{row:Dynamic, event:SourceEventNote}> = [];
		visit(function(row) {
			var event = new SourceEventNote(row, noteOffset());
			if (shouldPush(event, scripts, call)) result.push({row:row, event:event});
		});
		return result;
	}

	public static function prepare(visit:(Dynamic->Void)->Void, noteOffset:Void->Float,
		scripts:Void->Map<String, Dynamic>, call:(Dynamic, String, Array<Dynamic>)->Dynamic,
		global:(String, Array<Dynamic>)->Dynamic, load:String->Void,
		publish:(Dynamic, SourceEventNote)->Void, builtin:SourceEventNote->Bool, ?pushedNames:Void->Map<String, Bool>):Void {
		var names:Map<String, Bool> = [];
		if (pushedNames == null) pushedNames = function() return names;
		for (entry in collect(visit, noteOffset, scripts, call)) {
			var event = entry.event;
			if (!pushedNames().exists(event.event)) {
				pushedNames().set(event.event, true);
				firstPush(event, scripts, call);
			}
		}
		for (name in pushedNames().keys()) load(name);
		for (entry in collect(visit, noteOffset, scripts, call)) {
			var event = entry.event;
			// Match compound-assignment evaluation: callbacks may mutate the view.
			var time = event.strumTime;
			event.strumTime = time - earlyTrigger(event, scripts, call, global);
			publish(entry.row, event);
			if (!builtin(event) && scripts().exists(event.event)) invoke(event, 'onPush', scripts, call);
		}
	}
}
