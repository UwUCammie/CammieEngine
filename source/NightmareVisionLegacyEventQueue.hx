package;

/** Historical source arrays stay authoritative, including callback replacement. */
class NightmareVisionLegacyEventQueue {
	static function read(event:Dynamic, field:String):Dynamic {
		if (event == null) throw '[nightmare-vision-event] Null queued event';
		return Reflect.getProperty(event, field);
	}

	public static function sort(events:Array<Dynamic>):Void {
		events.sort(function(a, b) {
			var left:Float = read(a, 'strumTime');var right:Float = read(b, 'strumTime');
			return left < right ? -1 : left > right ? 1 : 0;
		});
	}

	/** Shift the live array after firing, even if the callback replaced it.
	 * Do not add a reentrancy guard: source callbacks can intentionally re-enter. */
	public static function drain(events:Void->Array<Dynamic>, position:Void->Float,
		fire:Dynamic->Void, ?retired:Void->Void, exclusive:Bool = false):Void {
		while (events().length > 0) {
			var time:Float = read(events()[0], 'strumTime');
			if (exclusive ? position() <= time : position() < time) break;
			var value1:String = read(events()[0], 'value1');
			var value2:String = read(events()[0], 'value2');
			fire({time:time, name:read(events()[0], 'event'), v1:value1 == null ? '' : value1,
				v2:value2 == null ? '' : value2, v3:'', order:0});
			events().shift();
			if (retired != null) retired();
		}
	}

	public static function due(events:Array<Dynamic>, time:Float):Int {
		var count = 0;
		for (event in events) if (!(time < (cast read(event, 'strumTime'):Float))) count++;
		return count;
	}
}
