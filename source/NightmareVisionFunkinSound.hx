package;

import flixel.FlxG;
import flixel.sound.FlxSound;

/**
 * Nightmare Vision's FunkinSound for one script owner. The source class is a
 * thin layer over FlxG.sound with the same defaults, so these calls go
 * straight to it. Each sound is handed to the owner, so it is released with
 * that owner's other script sounds exactly like one made through FlxG.sound.
 */
@:keep
class NightmareVisionFunkinSound {
	var ownSound:Dynamic->Void;

	public function new(?ownSound:Dynamic->Void) {
		this.ownSound = ownSound;
	}

	/** Same defaults as the source: full volume, looped. */
	public function playMusic(music:Dynamic, volume:Float = 1.0, looped:Bool = true, ?group:Dynamic):Void {
		FlxG.sound.playMusic(music, volume, looped, group);
		own(FlxG.sound.music);
	}

	public function play(sound:Dynamic, volume:Float = 1.0, looped:Bool = false, ?group:Dynamic,
		autoDestroy:Bool = true, ?onComplete:Void->Void):FlxSound {
		return own(FlxG.sound.play(sound, volume, looped, group, autoDestroy, onComplete));
	}

	public function load(?sound:Dynamic, volume:Float = 1.0, looped:Bool = false, ?group:Dynamic,
		autoDestroy:Bool = false, autoPlay:Bool = false, ?url:String, ?onComplete:Void->Void,
		?onLoad:Void->Void):FlxSound {
		return own(FlxG.sound.load(sound, volume, looped, group, autoDestroy, autoPlay, url, onComplete, onLoad));
	}

	function own(sound:FlxSound):FlxSound {
		if (sound != null && ownSound != null) ownSound(sound);
		return sound;
	}
}
