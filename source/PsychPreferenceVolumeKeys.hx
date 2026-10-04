package;

import flixel.FlxG;

/** Source volume shortcuts borrow the device for one scene and restore its keys. */
class PsychPreferenceVolumeKeys {
	var owner:PsychOwnerClientPrefs;
	var mute:Array<flixel.input.keyboard.FlxKey>;
	var up:Array<flixel.input.keyboard.FlxKey>;
	var down:Array<flixel.input.keyboard.FlxKey>;
	var sourceMute:Array<flixel.input.keyboard.FlxKey>;
	var sourceUp:Array<flixel.input.keyboard.FlxKey>;
	var sourceDown:Array<flixel.input.keyboard.FlxKey>;
	var released:Bool = false;

	public function new(owner:PsychOwnerClientPrefs) {
		this.owner = owner;
		mute = FlxG.sound.muteKeys;
		up = FlxG.sound.volumeUpKeys;
		down = FlxG.sound.volumeDownKeys;
		sourceMute = cast owner.keyBinds.get('volume_mute').copy();
		sourceUp = cast owner.keyBinds.get('volume_up').copy();
		sourceDown = cast owner.keyBinds.get('volume_down').copy();
		owner.bindRuntimeOperation('reloadVolumeKeys', function(_args) {
			if (released) throw '[psych-client-prefs] Volume key device has been released';
			sourceMute = cast owner.keyBinds.get('volume_mute').copy();
			sourceUp = cast owner.keyBinds.get('volume_up').copy();
			sourceDown = cast owner.keyBinds.get('volume_down').copy();
			toggle(true);
			return null;
		});
		owner.bindRuntimeOperation('toggleVolumeKeys', function(args) {
			toggle(args[0] == true);
			return null;
		});
	}

	function toggle(enabled:Bool):Void {
		if (released) throw '[psych-client-prefs] Volume key device has been released';
		FlxG.sound.muteKeys = enabled ? sourceMute : [];
		FlxG.sound.volumeUpKeys = enabled ? sourceUp : [];
		FlxG.sound.volumeDownKeys = enabled ? sourceDown : [];
	}

	public function release():Void {
		if (released) return;
		released = true;
		FlxG.sound.muteKeys = mute;
		FlxG.sound.volumeUpKeys = up;
		FlxG.sound.volumeDownKeys = down;
		if (owner != null && owner.canReuseFor(owner.ownerRoot)) {
			owner.bindRuntimeOperation('reloadVolumeKeys', null);
			owner.bindRuntimeOperation('toggleVolumeKeys', null);
		}
		owner = null;
	}
}
