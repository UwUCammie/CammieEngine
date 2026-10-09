package;

/** Shared NV return flow; historical scripts preserve arbitrary non-null values. */
class NightmareVisionScriptBroadcast {
	public static function call<T>(members:Array<T>, invoke:T->Dynamic, ignoreStops:Bool = false,
		historical:Bool = false, ?excluded:T->Bool, skipNull:Bool = true):Dynamic {
		var result:Dynamic = 0;
		for (script in members) {
			if ((skipNull && script == null) || (excluded != null && excluded(script))) continue;
			var returned:Dynamic = invoke(script);
			if (returned == null || (!historical && !Std.isOfType(returned, Int))) continue;
			if (returned == 2) {
				if (!ignoreStops) return result;
			} else if (returned != 0) result = returned;
		}
		return result;
	}
}
