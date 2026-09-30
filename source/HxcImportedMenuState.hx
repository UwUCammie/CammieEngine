package;

/**
	Native materialization for an imported MusicBeatState main menu.

	The imported HXC file contributes only HxcMenuSpecData and a manifest root.
	MainMenuState owns the display list, camera, asset checks, input, routing, and
	teardown; donor state code is never evaluated by this wrapper.
*/
class HxcImportedMenuState extends MainMenuState {
	public var factoryEntry(default, null):HxcStateFactory.HxcStateFactoryEntry;

	public function new(entry:HxcStateFactory.HxcStateFactoryEntry) {
		super();
		factoryEntry = entry;
	}

	override function create():Void {
		super.create();
		if (factoryEntry != null && factoryEntry.menuSpec != null)
			HxcCompatRuntime.mountMainMenuOverlay(this, factoryEntry.menuSpec, factoryEntry.root);
	}

	override public function destroy():Void {
		HxcCompatRuntime.clearMainMenuOverlay(this);
		super.destroy();
	}
}
