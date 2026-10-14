package;

import flixel.FlxG;
import flixel.sound.FlxSound;

/**
	Every source engine reaches a song with FlxG.sound.music already set: the
	title screen starts the menu track and nothing clears it before PlayState.
	Scripts rely on that (`FlxG.sound.music.volume = 0` in onCreate is common).
	A song launched straight from the command line, or after something destroyed
	the music, would otherwise hand those scripts a null. An empty FlxSound is
	silent, plays nothing and is replaced by the instrumental when the song starts.
**/
class SongMusicSlot {
	/** Returns true when it had to create the silent placeholder. */
	public static function ensure():Bool {
		if (FlxG.sound.music != null)
			return false;
		var music = new FlxSound();
		// Music survives state switches like the menu track it stands in for.
		music.persist = true;
		FlxG.sound.music = music;
		return true;
	}
}
