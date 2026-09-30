package;

/** Codename's mutable single-argument chart-event callback payload. */
@:keep
class CodenameGameEvent {
	public var event:Dynamic;
	public var data:Dynamic = {};
	public var cancelled:Bool = false;
	var continueCalls:Bool = true;

	public function new(?event:Dynamic) this.event = event;

	/** Reset a pooled callback before assigning its next payload. */
	public function recycleBase():Void {
		data = {};
		cancelled = false;
		continueCalls = true;
	}

	public function preventDefault(c:Bool = false):Void {
		cancelled = true;
		continueCalls = c;
	}

	public function cancel(c:Bool = true):Void preventDefault(c);

	public function stopsPropagation():Bool return cancelled && !continueCalls;
}
