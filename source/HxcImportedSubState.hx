package;

/** Native MusicBeatSubstate shell for one manifest-owned HXC substate. */
class HxcImportedSubState extends MusicBeatSubstate {
	public var factoryEntry(default, null):HxcStateFactory.HxcStateFactoryEntry;
	var runtime:HxcImportedRuntime;

	public function new(entry:HxcStateFactory.HxcStateFactoryEntry) {
		super();
		factoryEntry = entry;
		runtime = new HxcImportedRuntime(this, entry);
	}

	override function create() {
		super.create();
		runtime.create();
	}

	override public function update(elapsed:Float) {
		runtime.update(elapsed);
		super.update(elapsed);
	}

	override public function stepHit():Void {
		runtime.step(hxcCurrentStep);
		super.stepHit();
	}

	override public function beatHit():Void {
		runtime.beat(hxcCurrentBeat);
		super.beatHit();
	}

	override public function destroy():Void {
		if (runtime != null) {
			runtime.destroy();
			runtime = null;
		}
		super.destroy();
	}
}
