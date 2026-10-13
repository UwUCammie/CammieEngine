package;

import flixel.FlxG;
import flixel.input.keyboard.FlxKey;

/** Hold global audio shortcuts until search ends and their release is consumed. */
class FreeplaySearchSoundKeys {
	var mute:Array<FlxKey>; var up:Array<FlxKey>; var down:Array<FlxKey>;
	var owned:Bool = false;
	var draining:Bool = false;
	public function new() {}
	public function update(focused:Bool):Void {
		if (focused && draining) { FlxG.signals.postUpdate.remove(drain); draining = false; }
		if (focused && !owned) {
			mute = FlxG.sound.muteKeys; up = FlxG.sound.volumeUpKeys; down = FlxG.sound.volumeDownKeys;
			FlxG.sound.muteKeys = []; FlxG.sound.volumeUpKeys = []; FlxG.sound.volumeDownKeys = []; owned = true;
		}
		if (!focused && owned) {
			if (!held(mute) && !held(up) && !held(down)) restore();
			else if (!draining) { draining = true; FlxG.signals.postUpdate.add(drain); }
		}
	}
	function drain():Void {
		if (!held(mute) && !held(up) && !held(down)) restore();
	}
	function held(keys:Array<FlxKey>):Bool return keys != null && (FlxG.keys.anyPressed(keys) || FlxG.keys.anyJustReleased(keys));
	public function restore():Void {
		if (draining) { FlxG.signals.postUpdate.remove(drain); draining = false; }
		if (!owned) return;
		FlxG.sound.muteKeys = mute; FlxG.sound.volumeUpKeys = up; FlxG.sound.volumeDownKeys = down; owned = false;
	}
}
