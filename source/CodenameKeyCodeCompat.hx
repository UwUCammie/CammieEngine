package;

import flixel.input.keyboard.FlxKey;

/** Display key codes through the same names used by FlxKey bindings. */
@:keep
class CodenameKeyCodeCompat {
	public static function keyToString(key:Dynamic):String {
		var code = Std.isOfType(key, Int) ? (cast key:Int) : Std.parseInt(Std.string(key));
		if (code == null || code <= 0) return 'NONE';
		var name = FlxKey.toStringMap.get(cast code);
		return name == null ? Std.string(code) : name;
	}
}
