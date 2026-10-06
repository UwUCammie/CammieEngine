package;

/** Callback event shape used by the Nightmare Vision ModManager timeline. */
@:keep
class NightmareVisionCallbackEvent extends NightmareVisionBaseEvent {
	public var callback:Dynamic;

	/** Legacy standalone CallbackTimeline ordering; unused by source EventTimeline. */
	@:allow(NightmareVisionCallbackTimeline)
	var insertionOrder:Int = 0;

	public function new(step:Float, callback:Dynamic, manager:NightmareVisionModManager) {
		super(step, manager);
		this.callback = callback;
	}

	override public function run(currentStep:Float):Void {
		Reflect.callMethod(null, callback, [this, currentStep]);
		finished = true;
	}
}
