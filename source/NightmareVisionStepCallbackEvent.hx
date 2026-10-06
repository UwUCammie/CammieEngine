package;

/** Repeating callback event; its end step is inclusive, matching source. */
@:keep
class NightmareVisionStepCallbackEvent extends NightmareVisionCallbackEvent {
	public var endStep:Float = 0;

	public function new(step:Float, endStep:Float, callback:Dynamic, manager:NightmareVisionModManager) {
		super(step, callback, manager);
		this.endStep = endStep;
	}

	override public function run(currentStep:Float):Void {
		if (currentStep <= endStep) {
			Reflect.callMethod(null, callback, [this, currentStep]);
		} else {
			finished = true;
		}
	}
}
