package;

/** Mutable creation event passed to Codename pause scripts. */
@:keep
class CodenamePauseCreationEvent {
	public var options:Array<String>;
	public var music:String;
	public var cancelled:Bool = false;
	public var canceled(get, never):Bool;
	inline function get_canceled():Bool return cancelled;

	public function new(options:Array<String>, music:String) {
		this.options = options == null ? [] : options.copy();
		this.music = music;
	}

	public function cancel():Void cancelled = true;
	public function preventDefault():Void cancelled = true;
}
