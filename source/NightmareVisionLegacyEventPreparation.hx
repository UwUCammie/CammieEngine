package;

import SourceEventPreparation.SourceEventPreparationHooks;

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
		return SourceEventPreparation.earlyOffsetFor(Reflect.getProperty(event, 'event'),
			scriptEarlyTrigger(event, scripts, call, global));
	}

	/** The scripts' answer before the built-in default: the event's own module,
	 * when it has one, replaces the global answer. */
	static function scriptEarlyTrigger(event:Dynamic, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic, global:(String, Array<Dynamic>)->Dynamic):Null<Float> {
		var offset:Float = global('eventEarlyTrigger', [Reflect.getProperty(event, 'event'),
			Reflect.getProperty(event, 'value1'), Reflect.getProperty(event, 'value2')]);
		if (scripts().exists(Reflect.getProperty(event, 'event'))) offset = invoke(event, 'getOffset', scripts, call);
		return offset;
	}

	/** Public eventPushed and generation share builtin ownership and callback arguments. */
	public static function pushed(event:Dynamic, scripts:Void->Map<String, Dynamic>,
		call:(Dynamic, String, Array<Dynamic>)->Dynamic, builtin:Dynamic->Bool):Void {
		if (!builtin(event) && scripts().exists(Reflect.getProperty(event, 'event')))
			invoke(event, 'onPush', scripts, call);
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
		publish:(Dynamic, SourceEventNote)->Void, builtin:Dynamic->Bool, ?pushedNames:Void->Map<String, Bool>):Void {
		var names:Map<String, Bool> = [];
		if (pushedNames == null) pushedNames = function() return names;
		// Pass one only announces each event name once. The name map is read
		// again for every row because scripts may replace it.
		var announce:SourceEventPreparationHooks = {
			firstPush: function(event:SourceEventNote) firstPush(event, scripts, call)
		};
		for (entry in collect(visit, noteOffset, scripts, call))
			SourceEventPreparation.pushView(entry.event, pushedNames(), announce);
		for (name in pushedNames().keys()) load(name);
		// Pass two admits the rows again, now with every module loaded, and
		// offsets and publishes each one.
		var row:Dynamic = null;
		var publishRow:SourceEventPreparationHooks = {
			earlyOffset: function(event:SourceEventNote) return scriptEarlyTrigger(event, scripts, call, global),
			push: function(event:SourceEventNote) {
				publish(row, event);
				pushed(event, scripts, call, builtin);
			}
		};
		for (entry in collect(visit, noteOffset, scripts, call)) {
			row = entry.row;
			SourceEventPreparation.pushView(entry.event, null, publishRow);
		}
	}
}
