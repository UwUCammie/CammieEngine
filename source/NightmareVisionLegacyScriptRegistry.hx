package;

/** Historical writable registries over the existing script implementations. */
class NightmareVisionLegacyScriptRegistry {
	public var funkyScripts:Array<Dynamic> = [];
	public var hscriptArray:Array<Dynamic> = [];
	public var luaArray:Array<Dynamic> = [];
	public var eventScripts:Map<String, Dynamic> = [];
	public var events:Void->Map<String, Dynamic>;
	public var special:String->Bool;

	public function new(?events:Void->Map<String, Dynamic>, ?special:String->Bool) {
		this.events = events == null ? function() return this.eventScripts : events;
		this.special = special == null ? function(name) return this.eventScripts.exists(name) : special;
	}
	public function add(script:Dynamic, lua:Bool = false):Void {
		funkyScripts.push(script);
		(lua ? luaArray : hscriptArray).push(script);
	}
	public function remove(script:Dynamic):Void {
		funkyScripts.remove(script);hscriptArray.remove(script);luaArray.remove(script);
	}
	static function name(script:Dynamic):String {
		if (script == null) throw 'Null historical script registry entry';
		return Reflect.getProperty(script, 'scriptName');
	}
	public function callOnScripts(event:String, args:Array<Dynamic>, ignoreStops:Bool = false,
		?exclusions:Array<String>, ?scriptArray:Array<Dynamic>, ignoreSpecialShit:Bool = true):Dynamic {
		if (scriptArray == null) {
			scriptArray = funkyScripts;
			for (script in events()) scriptArray.push(script);
		}
		if (exclusions == null) exclusions = [];
		return NightmareVisionScriptBroadcast.call(scriptArray, function(script) return NightmareVisionScriptHandle.call(script, event, args),
			ignoreStops, true, function(script) {
				var key = name(script);
				return exclusions.indexOf(key) >= 0 || (ignoreSpecialShit && special(key));
			}, false);
	}
	public function callOnHScripts(event:String, args:Array<Dynamic>, ignoreStops:Bool = false, ?exclusions:Array<String>):Dynamic
		return callOnScripts(event, args, ignoreStops, exclusions, hscriptArray);
	public function callOnLuas(event:String, args:Array<Dynamic>, ignoreStops:Bool = false, ?exclusions:Array<String>):Dynamic
		return callOnScripts(event, args, ignoreStops, exclusions, luaArray);
	public function setOnScripts(variable:String, value:Dynamic, ?scriptArray:Array<Dynamic>):Void {
		if (scriptArray == null) scriptArray = funkyScripts;
		for (script in scriptArray) Reflect.callMethod(script, Reflect.field(script, 'set'), [variable, value]);
	}
	public function callScript(script:Dynamic, event:String, args:Array<Dynamic>):Dynamic {
		if (Std.isOfType(script, NightmareVisionScriptModule) || Std.isOfType(script, NightmareVisionLegacyLuaScript))
			return callOnScripts(event, args, true, [], [script], false);
		if (Std.isOfType(script, Array)) return callOnScripts(event, args, true, [], cast script, false);
		if (Std.isOfType(script, String)) {
			var selected:Array<Dynamic> = [];
			for (candidate in funkyScripts) if (name(candidate) == script) selected.push(candidate);
			return callOnScripts(event, args, true, [], selected, false);
		}
		return 0;
	}
}
