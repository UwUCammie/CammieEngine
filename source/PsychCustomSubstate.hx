package;

import flixel.FlxG;
import flixel.FlxObject;

/** Native Psych substate, with an explicit historical owner-clock adapter. */
@:access(PlayState)
class PsychCustomSubstate extends MusicBeatSubstate {
	@:keep public static var name:String = 'unnamed';
	@:keep public static var instance:PsychCustomSubstate;
	public var customName(default, null):String;
	public var pausesGame(default, null):Bool;
	public var lifecycleCreated(default, null):Bool = false;
	public var sourceLifecycle(default, null):Bool;
	var owner:PlayState;
	var destroyNotified:Bool = false;

	public function new(name:String, ?owner:PlayState, pauseGame:Bool = false, sourceLifecycle:Bool = true) {
		this.sourceLifecycle = sourceLifecycle;
		this.owner = owner;
		customName = name;
		pausesGame = pauseGame;
		if (sourceLifecycle) {
			PsychCustomSubstate.name = name;
			PsychRuntimeBindings.publish(PlayState.instance, 'customSubstateName', name, 'HScript');
		}
		super();
		bgColor = 0x00000000;
		if (sourceLifecycle || FlxG.cameras.list.length > 0)
			cameras = [FlxG.cameras.list[FlxG.cameras.list.length - 1]];
	}

	public static function openCustomSubstate(name:String, pauseGame:Bool = false):Void {
		if (pauseGame) {
			FlxG.camera.followLerp = 0;
			PlayState.instance.persistentUpdate = false;
			PlayState.instance.persistentDraw = true;
			PlayState.instance.paused = true;
			if (FlxG.sound.music != null) {
				FlxG.sound.music.pause();
				PlayState.instance.pauseVocals();
			}
		}
		PlayState.instance.compatOpenCustomSubstate(name, pauseGame, true);
	}

	public static function closeCustomSubstate():Bool {
		if (instance == null) return false;
		PlayState.instance.closeSubState();
		return true;
	}

	public static function insertToCustomSubstate(tag:String, pos:Int = -1):Bool {
		if (instance != null) {
			var object:FlxObject = cast(MusicBeatState.getVariables().get(tag), FlxObject);
			if (object != null) {
				if (pos < 0) instance.add(object); else instance.insert(pos, object);
				return true;
			}
		}
		return false;
	}

	override function create():Void {
		instance = this;
		lifecycleCreated = true;
		if (sourceLifecycle) {
			PsychRuntimeBindings.publish(PlayState.instance, 'customSubstate', instance, 'HScript');
			PsychRuntimeBindings.dispatch(PlayState.instance, 'onCustomSubstateCreate', [name]);
		} else if (owner != null) owner.psychCustomSubstateCreate(this);
		super.create();
		if (sourceLifecycle) PsychRuntimeBindings.dispatch(PlayState.instance, 'onCustomSubstateCreatePost', [name]);
		else if (owner != null) owner.psychCustomSubstateCreatePost(this);
	}

	override function update(elapsed:Float):Void {
		if (sourceLifecycle) PsychRuntimeBindings.dispatch(PlayState.instance, 'onCustomSubstateUpdate', [name, elapsed]);
		else if (owner != null) owner.psychCustomSubstateUpdate(this, elapsed);
		super.update(elapsed);
		if (sourceLifecycle) PsychRuntimeBindings.dispatch(PlayState.instance, 'onCustomSubstateUpdatePost', [name, elapsed]);
		else if (owner != null) owner.psychCustomSubstateUpdatePost(this, elapsed);
	}

	/** Parent teardown calls this before releasing its script interpreters. */
	public function notifyBeforeParentDestroy():Void {
		if (destroyNotified || !lifecycleCreated) return;
		destroyNotified = true;
		if (sourceLifecycle) {
			PsychRuntimeBindings.dispatch(PlayState.instance, 'onCustomSubstateDestroy', [name]);
			instance = null;
			name = 'unnamed';
			PsychRuntimeBindings.publish(PlayState.instance, 'customSubstate', null, 'HScript');
			PsychRuntimeBindings.publish(PlayState.instance, 'customSubstateName', name, 'HScript');
			if (owner != null) owner.psychCustomSubstateFinished(this);
		} else if (owner != null) owner.psychCustomSubstateDestroy(this);
	}

	/** Flixel 6 queues opens; replaced uncreated targets have no source callbacks. */
	public function cancelBeforeCreate():Void {
		if (lifecycleCreated) return;
		owner = null;
		super.destroy();
	}

	override function destroy():Void {
		// Directly constructed source instances also dispatch their destroy callback.
		if (sourceLifecycle) lifecycleCreated = true;
		notifyBeforeParentDestroy();
		if (!sourceLifecycle) instance = null;
		owner = null;
		super.destroy();
	}
}
