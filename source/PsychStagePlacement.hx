package;

/** Shared scene phase for a selected source stage and its nested helpers. */
class PsychStagePlacement {
	final initialScene:Dynamic;
	var constructing:Bool;

	public function new(initialScene:Dynamic, constructing:Bool) {
		this.initialScene = initialScene;
		this.constructing = constructing;
	}

	public function beforeActors(scene:Dynamic):Bool
		return constructing && initialScene != null && scene == initialScene;

	public function beginPostCreate():Void constructing = false;
}
