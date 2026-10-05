package;

/**
	Validated, scene-independent values for the source PlayField constructor.
	The host owns native FlxBasic identity, receptor creation and skin loading.
*/
typedef NightmareVisionFieldConstructorSpec = {
	var x:Float;
	var y:Float;
	var keyCount:Int;
	var owner:Dynamic;
	var isPlayer:Bool;
	var cpu:Bool;
	var playerControls:Bool;
	var player:Int;
	var skin:String;
	var skinInput:Dynamic;
}

/**
	Parses the positional arguments accepted by Nightmare Vision's PlayField.new.
	It intentionally does not allocate fields, receptors or skins.
*/
@:keep
class NightmareVisionFieldConstructor {
	static inline var ERROR_PREFIX = '[nightmare-vision-field-constructor] ';

	@:keep public static function parse(args:Array<Dynamic>, maxKeys:Int):NightmareVisionFieldConstructorSpec {
		if (args == null) fail('arguments must be an array');
		if (maxKeys < 0) fail('host key limit must be nonnegative');
		if (args.length < 1) fail('x is required');
		if (args.length < 2) fail('y is required');

		var x = finiteNumber(args[0], 'x');
		var y = finiteNumber(args[1], 'y');
		var keyCount = optionalInteger(args, 2, 4, 'keyCount');
		if (keyCount < 0) fail('keyCount must be nonnegative');
		if (keyCount > maxKeys)
			fail('keyCount ' + keyCount + ' exceeds host layout limit ' + maxKeys);

		var owner:Dynamic = optional(args, 3);
		var isPlayer = optionalBool(args, 4, false, 'isPlayer');
		var cpu = optionalBool(args, 5, false, 'cpu');
		var playerControls = optionalBool(args, 6, isPlayer, 'playerControls');
		var player = optionalInteger(args, 7, 0, 'player');
		var skin = optionalString(args, 8, 'default', 'skin');
		var skinInput:Dynamic = optional(args, 9);

		return {
			x: x,
			y: y,
			keyCount: keyCount,
			owner: owner,
			isPlayer: isPlayer,
			cpu: cpu,
			playerControls: playerControls,
			player: player,
			skin: skin,
			skinInput: skinInput
		};
	}

	static function optional(args:Array<Dynamic>, index:Int):Dynamic
		return index < args.length ? args[index] : null;

	static function optionalBool(args:Array<Dynamic>, index:Int, fallback:Bool, name:String):Bool {
		var value = optional(args, index);
		if (value == null) return fallback;
		if (Type.typeof(value) != TBool) fail(name + ' must be a boolean or null');
		return cast value;
	}

	static function optionalInteger(args:Array<Dynamic>, index:Int, fallback:Int, name:String):Int {
		var value = optional(args, index);
		if (value == null) return fallback;
		var number = finiteNumber(value, name);
		if (number != Math.floor(number)) fail(name + ' must be an integer');
		if (number < -2147483648.0 || number > 2147483647.0)
			fail(name + ' is outside the supported integer range');
		return Std.int(number);
	}

	static function optionalString(args:Array<Dynamic>, index:Int, fallback:String, name:String):String {
		var value = optional(args, index);
		if (value == null) return fallback;
		if (!Std.isOfType(value, String)) fail(name + ' must be a string or null');
		return cast value;
	}

	static function finiteNumber(value:Dynamic, name:String):Float {
		var kind = Type.typeof(value);
		if (kind != TInt && kind != TFloat) fail(name + ' must be a finite number');
		var number:Float = cast value;
		if (Math.isNaN(number) || number == Math.POSITIVE_INFINITY || number == Math.NEGATIVE_INFINITY)
			fail(name + ' must be a finite number');
		return number;
	}

	static function fail(message:String):Dynamic
		throw ERROR_PREFIX + message;
}
