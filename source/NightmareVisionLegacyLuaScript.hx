package;

/** A source handle delegates to one existing Lua interpreter; it owns no VM. */
@:keep
class NightmareVisionLegacyLuaScript {
	public var scriptName:String;
	public var scriptType(default, null):String = 'lua';
	public final interp:hscript.Interp;
	final dispatch:(String, Array<Dynamic>)->Dynamic;
	public function new(name:String, interp:hscript.Interp, dispatch:(String, Array<Dynamic>)->Dynamic) {
		scriptName = name;this.interp = interp;this.dispatch = dispatch;
	}
	public function call(event:String, args:Array<Dynamic>):Dynamic return dispatch(event, args);
	public function set(name:String, value:Dynamic):Void interp.variables.set(name, value);
	public function get(name:String):Dynamic return interp.variables.get(name);
	public function stop():Void interp.variables.set('__compatClosed', true);
}
