import flixel.util.FlxColor;

/** Typed access for FlxColor's Int-backed abstract properties in HScript. */
class PsychFlxColorScriptAccess {
	public static function isColorValue(value:Dynamic):Bool {
		if (value == null) return false;
		return switch (Type.typeof(value)) {
			case TInt: true;
			case _: false;
		};
	}

	public static function hasGetter(name:String):Bool {
		return switch (name) {
			case 'red' | 'green' | 'blue' | 'alpha' | 'redFloat' | 'greenFloat' | 'blueFloat' | 'alphaFloat'
				| 'cyan' | 'magenta' | 'yellow' | 'black' | 'rgb' | 'hue' | 'saturation'
				| 'brightness' | 'lightness' | 'luminance': true;
			case _: false;
		};
	}

	public static function hasSetter(name:String):Bool {
		return name != 'luminance' && hasGetter(name);
	}

	public static function get(value:Dynamic, name:String):Dynamic {
		var color:FlxColor = cast value;
		return switch (name) {
			case 'red': color.red;
			case 'green': color.green;
			case 'blue': color.blue;
			case 'alpha': color.alpha;
			case 'redFloat': color.redFloat;
			case 'greenFloat': color.greenFloat;
			case 'blueFloat': color.blueFloat;
			case 'alphaFloat': color.alphaFloat;
			case 'cyan': color.cyan;
			case 'magenta': color.magenta;
			case 'yellow': color.yellow;
			case 'black': color.black;
			case 'rgb': color.rgb;
			case 'hue': color.hue;
			case 'saturation': color.saturation;
			case 'brightness': color.brightness;
			case 'lightness': color.lightness;
			case 'luminance': color.luminance;
			case _: throw 'Invalid field:' + name;
		};
	}

	/** Return the changed Int-backed color; setters alone return the component. */
	public static function set(value:Dynamic, name:String, next:Dynamic):Dynamic {
		var color:FlxColor = cast value;
		switch (name) {
			case 'red': color.red = cast next;
			case 'green': color.green = cast next;
			case 'blue': color.blue = cast next;
			case 'alpha': color.alpha = cast next;
			case 'redFloat': color.redFloat = cast next;
			case 'greenFloat': color.greenFloat = cast next;
			case 'blueFloat': color.blueFloat = cast next;
			case 'alphaFloat': color.alphaFloat = cast next;
			case 'cyan': color.cyan = cast next;
			case 'magenta': color.magenta = cast next;
			case 'yellow': color.yellow = cast next;
			case 'black': color.black = cast next;
			case 'rgb': color.rgb = cast next;
			case 'hue': color.hue = cast next;
			case 'saturation': color.saturation = cast next;
			case 'brightness': color.brightness = cast next;
			case 'lightness': color.lightness = cast next;
			case _: throw 'Invalid field:' + name;
		}
		return color;
	}
}
