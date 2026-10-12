import flixel.FlxG;
import flixel.input.keyboard.FlxKey;

/** Shared type-to-search ownership: global shortcuts never become search text. */
class MenuSearchInput {
	public static function reserved(key:FlxKey):Bool {
		return FlxG.keys.pressed.CONTROL || FlxG.keys.pressed.ALT
			|| contains(FlxG.sound.muteKeys, key)
			|| contains(FlxG.sound.volumeUpKeys, key)
			|| contains(FlxG.sound.volumeDownKeys, key);
	}

	static function contains(keys:Array<FlxKey>, key:FlxKey):Bool {
		return keys != null && keys.indexOf(key) >= 0;
	}
}
