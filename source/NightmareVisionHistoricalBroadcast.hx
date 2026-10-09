package;

typedef HistoricalScriptCall = {
	var order:Int;
	var invoke:Void->Dynamic;
	var excluded:Void->Bool;
}

/** One historical broadcast across the existing Lua and HScript interpreters. */
class NightmareVisionHistoricalBroadcast {
	public static function call(entries:Array<HistoricalScriptCall>):Dynamic {
		entries.sort(function(a, b) return a.order - b.order);
		return NightmareVisionScriptBroadcast.call(entries, function(entry) return entry.invoke(),
			false, true, function(entry) return entry.excluded());
	}
}
