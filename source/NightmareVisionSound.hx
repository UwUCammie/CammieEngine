package;

import flixel.FlxG;
import flixel.sound.FlxSound;

/** Nightmare Vision's sound-transform rule without changing Flixel's global
	FlxSound class or the host's ordinary sound instances. */
@:keep
class NightmareVisionSound extends FlxSound {
	public var muted(default, set):Bool = false;

	function set_muted(value:Bool):Bool {
		muted = value;
		updateTransform();
		return muted;
	}

	override function updateTransform():Void {
		_transform.volume = #if FLX_SOUND_SYSTEM ((FlxG.sound.muted || muted) ? 0 : 1) * FlxG.sound.volume * #end
			(group != null ? group.volume : 1) * _volume * _volumeAdjust;
		if (_channel != null) _channel.soundTransform = _transform;
	}
}
