package;

import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxCamera;
import flixel.sound.FlxSound;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;

/** Freeze process-wide Flixel work while an imported Codename substate is open.
	This mirrors the bounded parent-disabler contract used by Codename pause
	menus. The object belongs to its host substate and restores the captured
	objects when that host is destroyed.
*/
class CodenameParentDisabler extends FlxBasic {
	var tweens:Array<FlxTween> = [];
	var timers:Array<FlxTimer> = [];
	// FlxBasic already exposes `cameras` as its assigned draw cameras.
	var capturedCameras:Array<FlxCamera> = [];
	var sounds:Array<FlxSound> = [];
	var restored:Bool = false;

	public function new() {
		super();
		@:privateAccess {
			if (FlxTween.globalManager != null) {
				tweens = FlxTween.globalManager._tweens.copy();
				FlxTween.globalManager._tweens = [];
			}
			if (FlxTimer.globalManager != null) {
				timers = FlxTimer.globalManager._timers.copy();
				FlxTimer.globalManager._timers = [];
			}
		}
		for (camera in FlxG.cameras.list)
			if (camera != null && camera.active) {
				capturedCameras.push(camera);
				camera.active = false;
			}
		if (FlxG.sound != null && FlxG.sound.list != null)
			for (sound in FlxG.sound.list)
				if (sound != null && sound.playing && !sound.persist) {
					sounds.push(sound);
					sound.pause();
				}
	}

	/** Discard captured parent work when the caller is replacing the PlayState. */
	public function reset():Void {
		tweens.resize(0);
		timers.resize(0);
		capturedCameras.resize(0);
		sounds.resize(0);
	}

	override public function destroy():Void {
		if (!restored) {
			restored = true;
			@:privateAccess {
				if (FlxTween.globalManager != null)
					for (tween in tweens)
						if (tween != null && FlxTween.globalManager._tweens.indexOf(tween) < 0)
							FlxTween.globalManager._tweens.push(tween);
				if (FlxTimer.globalManager != null)
					for (timer in timers)
						if (timer != null && FlxTimer.globalManager._timers.indexOf(timer) < 0)
							FlxTimer.globalManager._timers.push(timer);
			}
				for (camera in capturedCameras)
				if (camera != null && camera.exists)
					camera.active = true;
				for (sound in sounds)
					if (sound != null && sound.exists)
						sound.play();
			tweens.resize(0);
			timers.resize(0);
			capturedCameras.resize(0);
			sounds.resize(0);
		}
		super.destroy();
	}
}
