package;

/**
	V-Slice's player preferences (funkin.Preferences) answered from the
	engine's own options, for imported scripts that read them.

	Each field reads the matching engine option, so a script that hides
	flashing effects, picks a clean death line or flips its layout for
	downscroll follows the player's real settings. Fields the engine has no
	option for answer with V-Slice's default. Writes are ignored and return the
	current value: imported content must not change the player's saved
	options.
**/
@:keep
class Preferences {
	public static var naughtyness(get, set):Bool;
	public static var downscroll(get, set):Bool;
	public static var flashingLights(get, set):Bool;
	public static var zoomCamera(get, set):Bool;
	public static var autoPause(get, set):Bool;
	public static var subtitles(get, set):Bool;
	public static var globalOffset(get, set):Int;
	public static var framerate(get, set):Int;
	public static var strumlineBackgroundOpacity(get, set):Int;
	public static var hapticsMode(get, set):Int;
	public static var hapticsIntensityMultiplier(get, set):Float;
	public static var controlsScheme(get, set):String;
	public static var screenTimeout(get, set):Bool;
	public static var autoFullscreen(get, set):Bool;
	public static var unlockedFramerate(get, set):Bool;
	public static var enabledDiscordRPC(get, set):Bool;
	public static var shouldHideMouse(get, set):Bool;
	public static var debugDisplay(get, set):String;
	public static var debugDisplayBGOpacity(get, set):Int;

	/** One engine option, or `fallback` when the option file has no such field. */
	static function option(name:String, fallback:Dynamic):Dynamic {
		var options:Dynamic = null;
		try options = OptionsHandler.options catch (_:Dynamic) {}
		var value:Dynamic = options == null ? null : Reflect.field(options, name);
		return value == null ? fallback : value;
	}

	static function flag(name:String, fallback:Bool):Bool
		return option(name, fallback) == true;

	static function get_naughtyness():Bool
		return flag('naughtyness', true);

	static function get_downscroll():Bool
		return flag('downscroll', false);

	static function get_flashingLights():Bool
		return flag('flashingLights', true);

	static function get_zoomCamera():Bool
		return flag('zoomCamera', true);

	static function get_autoPause():Bool
		return flag('autoPause', true);

	// V-Slice subtitles are the lines shown over songs and cutscenes; the
	// engine's lyrics option is the same switch.
	static function get_subtitles():Bool
		return flag('lyricsEnabled', true);

	static function get_globalOffset():Int {
		var value:Dynamic = option('offset', 0);
		return Std.isOfType(value, Float) || Std.isOfType(value, Int) ? Std.int(value) : 0;
	}

	static function get_framerate():Int {
		var value:Dynamic = option('fpsCap', 60);
		return Std.isOfType(value, Int) ? value : 60;
	}

	// The engine draws no background under the notes, which is V-Slice's 0. A
	// script that adds its own lane backdrop when this is above 0 must not
	// draw one the player never chose.
	static function get_strumlineBackgroundOpacity():Int
		return 0;

	// HapticsMode.NONE: there is no vibration on this build.
	static function get_hapticsMode():Int
		return 0;

	static function get_hapticsIntensityMultiplier():Float
		return 1.0;

	// V-Slice's touch hitbox layout; only read on mobile, its default is the arrows layout.
	static function get_controlsScheme():String
		return 'Arrows';

	static function get_screenTimeout():Bool
		return false;

	static function get_autoFullscreen():Bool
		return false;

	static function get_unlockedFramerate():Bool
		return flag('unlimitedFPS', false);

	static function get_enabledDiscordRPC():Bool
		return true;

	static function get_shouldHideMouse():Bool
		return true;

	static function get_debugDisplay():String
		return 'Off';

	static function get_debugDisplayBGOpacity():Int
		return 50;

	static function set_naughtyness(_:Bool):Bool
		return get_naughtyness();

	static function set_downscroll(_:Bool):Bool
		return get_downscroll();

	static function set_flashingLights(_:Bool):Bool
		return get_flashingLights();

	static function set_zoomCamera(_:Bool):Bool
		return get_zoomCamera();

	static function set_autoPause(_:Bool):Bool
		return get_autoPause();

	static function set_subtitles(_:Bool):Bool
		return get_subtitles();

	static function set_globalOffset(_:Int):Int
		return get_globalOffset();

	static function set_framerate(_:Int):Int
		return get_framerate();

	static function set_strumlineBackgroundOpacity(_:Int):Int
		return get_strumlineBackgroundOpacity();

	static function set_hapticsMode(_:Int):Int
		return get_hapticsMode();

	static function set_hapticsIntensityMultiplier(_:Float):Float
		return get_hapticsIntensityMultiplier();

	static function set_controlsScheme(_:String):String
		return get_controlsScheme();

	static function set_screenTimeout(_:Bool):Bool
		return get_screenTimeout();

	static function set_autoFullscreen(_:Bool):Bool
		return get_autoFullscreen();

	static function set_unlockedFramerate(_:Bool):Bool
		return get_unlockedFramerate();

	static function set_enabledDiscordRPC(_:Bool):Bool
		return get_enabledDiscordRPC();

	static function set_shouldHideMouse(_:Bool):Bool
		return get_shouldHideMouse();

	static function set_debugDisplay(_:String):String
		return get_debugDisplay();

	static function set_debugDisplayBGOpacity(_:Int):Int
		return get_debugDisplayBGOpacity();
}
