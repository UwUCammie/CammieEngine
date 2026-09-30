package;

import flixel.FlxState;

/** HScript-facing event shape shared by transition creation and callbacks. */
class CodenameMusicBeatTransitionEvent {
	public var cancelled:Bool = false;
	public var canceled(get, set):Bool;
	public var transOut:Bool;
	public var newState:FlxState;

	public function new(transOut:Bool = false, ?newState:FlxState) {
		this.transOut = transOut;
		this.newState = newState;
	}

	inline function get_canceled():Bool return cancelled;
	inline function set_canceled(value:Bool):Bool return cancelled = value;
	public function cancel():Void cancelled = true;
}
