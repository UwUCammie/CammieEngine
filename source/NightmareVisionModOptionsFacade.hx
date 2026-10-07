package;

/** Source ModOptions signatures over the shared live option service. */
@:keep
class NightmareVisionModOptionsFacade {
	final backend:NightmareVisionSourceOptions;
	public function new(backend:NightmareVisionSourceOptions) this.backend = backend;
	public var currentMod(get, set):String;
	function get_currentMod():String return backend.currentMod;
	function set_currentMod(value:String):String return backend.assignCurrentMod(value);
	public var options(get, set):Map<String, NightmareVisionSourceModOption>;
	function get_options():Map<String, NightmareVisionSourceModOption> return backend.options;
	function set_options(value:Map<String, NightmareVisionSourceModOption>):Map<String, NightmareVisionSourceModOption>
		return backend.options = value;
	public var list(get, never):Array<NightmareVisionSourceModOption>;
	function get_list():Array<NightmareVisionSourceModOption> return backend.list;
	public function init(modName:String = 'NMV-Base-Game'):Void backend.init(modName);
	public function flush():Void backend.flush();
	public function add(mod:String, key:String, type:String = 'string', defaultValue:Dynamic = 'null', ?settings:Dynamic):Void
		backend.addForMod(mod, key, type, defaultValue, settings);
	public function get(key:String):NightmareVisionSourceModOption return backend.get(key);
	public function getValue(key:String):Dynamic return backend.getValue(key);
	public function setValue(key:String, value:Dynamic):Void backend.setValue(key, value);
}
