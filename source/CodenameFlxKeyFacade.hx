package;

import flixel.input.keyboard.FlxKey;

/** Runtime values for FlxKey's compile-time enum abstract in owner scripts. */
class CodenameFlxKeyFacade {
	public static function snapshot():Dynamic {
		var codes:Dynamic = {};
		for (name in FlxKey.fromStringMap.keys())
			Reflect.setField(codes, name, cast(FlxKey.fromStringMap.get(name), Int));
		return codes;
	}
}
