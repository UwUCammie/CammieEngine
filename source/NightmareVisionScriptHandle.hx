package;

/** One dispatch path for existing HScript modules and source language handles. */
class NightmareVisionScriptHandle {
	public static function call(script:Dynamic, event:String, args:Array<Dynamic>):Dynamic {
		if (script == null) throw '[nightmare-vision-script] Null script handle';
		if (Std.isOfType(script, NightmareVisionScriptModule)) return (cast script:NightmareVisionScriptModule).callValue(event, args);
		return Reflect.callMethod(script, Reflect.field(script, 'call'), [event, args]);
	}
	public static function get(script:Dynamic, field:String):Dynamic {
		if (script == null) throw '[nightmare-vision-script] Null script handle';
		if (Std.isOfType(script, NightmareVisionScriptModule)) return (cast script:NightmareVisionScriptModule).get(field);
		return Reflect.callMethod(script, Reflect.field(script, 'get'), [field]);
	}
}
