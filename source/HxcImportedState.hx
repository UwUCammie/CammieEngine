package;

/** Native MusicBeatState shell for one manifest-owned HXC state. */
class HxcImportedState extends MusicBeatState {
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
		if (runtime.failed) {
			var text = new flixel.text.FlxText(40, 40, flixel.FlxG.width - 80,
				'Imported menu could not run: ' + factoryEntry.relativePath
				+ '\nEnter: default Freeplay   F10: Imported Mods', 22);
			add(text);
		}
	}

	override public function update(elapsed:Float) {
		if (ImportedMenuEntry.departing) return;
		if (flixel.FlxG.keys.justPressed.F10) {
			ImportedMenuEntry.leaveToPicker();
			return;
		}
		if (runtime.failed && flixel.FlxG.keys.justPressed.ENTER) {
			ImportedMenuEntry.openDefaultFreeplay(factoryEntry.root); return;
		}
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
