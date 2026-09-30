package;

import flixel.FlxG;
import flixel.FlxSubState;

/** Psych's script-owned substate. Its callbacks run from Flixel's substate
 * clock, which continues while PlayState's update is suspended. */
class PsychCustomSubstate extends FlxSubState {
	public var customName(default, null):String;
	public var pausesGame(default, null):Bool;
	public var lifecycleCreated(default, null):Bool = false;
	var owner:PlayState;
	var destroyNotified:Bool = false;

	public function new(owner:PlayState, name:String, pauseGame:Bool) {
		super();
		this.owner = owner;
		customName = name;
		pausesGame = pauseGame;
		bgColor = 0x00000000;
		if (FlxG.cameras.list.length > 0)
			cameras = [FlxG.cameras.list[FlxG.cameras.list.length - 1]];
	}

	override function create():Void {
		lifecycleCreated = true;
		if (owner != null) owner.psychCustomSubstateCreate(this);
		super.create();
		if (owner != null) owner.psychCustomSubstateCreatePost(this);
	}

	override function update(elapsed:Float):Void {
		if (owner != null) owner.psychCustomSubstateUpdate(this, elapsed);
		super.update(elapsed);
		if (owner != null) owner.psychCustomSubstateUpdatePost(this, elapsed);
	}

	/** Called by PlayState before its script runtimes are released. */
	public function notifyBeforeParentDestroy():Void {
		if (destroyNotified || !lifecycleCreated) return;
		destroyNotified = true;
		if (owner != null) owner.psychCustomSubstateDestroy(this);
	}

	/** A queued open can be replaced before Flixel calls create(). */
	public function cancelBeforeCreate():Void {
		if (lifecycleCreated) return;
		owner = null;
		super.destroy();
	}

	override function destroy():Void {
		notifyBeforeParentDestroy();
		owner = null;
		super.destroy();
	}
}
