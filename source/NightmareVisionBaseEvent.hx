package;

@:keep
class NightmareVisionBaseEvent
{
	public var manager:NightmareVisionModManager;
	public var executionStep:Float = 0;
	public var ignoreExecution:Bool = false;
	public var finished:Bool = false;

	public function new(step:Float, manager:NightmareVisionModManager)
	{
		this.manager = manager;
		this.executionStep = step;
	}

	public function run(curStep:Float) {}
}
