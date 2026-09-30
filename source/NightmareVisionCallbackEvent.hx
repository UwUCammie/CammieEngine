package;

/** Callback event shape used by the Nightmare Vision ModManager timeline. */
class NightmareVisionCallbackEvent {
	public var manager:NightmareVisionModManager;
	public var executionStep:Float = 0;
	public var ignoreExecution:Bool = false;
	public var finished:Bool = false;
	public var callback:Dynamic;

	/** Monotonic sequence used to keep equal-step callbacks in queue order. */
	@:allow(NightmareVisionCallbackTimeline)
	var insertionOrder:Int = 0;

	public function new(step:Float, callback:Dynamic, manager:NightmareVisionModManager) {
		this.manager = manager;
		this.executionStep = step;
		this.callback = callback;
	}

	public function run(currentStep:Float):Void {
		if (callback != null && Reflect.isFunction(callback))
			Reflect.callMethod(null, callback, [this, currentStep]);
		finished = true;
	}
}
