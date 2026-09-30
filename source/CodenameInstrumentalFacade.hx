package;

import flixel.FlxG;

/** Live Codename-style view of the instrumental sound used by song scripts. */
class CodenameInstrumentalFacade {
	final source:Dynamic;
	public var onComplete:Null<Void->Void>;

	public function new(source:Dynamic) this.source = source;

	public var length(get, never):Float;
	function get_length():Float {
		var music = FlxG.sound.music;
		if (music != null && music.length > 0) return music.length;
		var sourceLength:Dynamic = source == null ? null : Reflect.field(source, 'length');
		return sourceLength == null ? 0 : sourceLength;
	}

	public var time(get, set):Float;
	function get_time():Float return FlxG.sound.music == null ? 0 : FlxG.sound.music.time;
	function set_time(value:Float):Float {
		if (FlxG.sound.music != null) FlxG.sound.music.time = value;
		return value;
	}

	public function complete():Bool {
		if (onComplete == null) return false;
		onComplete();
		return true;
	}

	public function release():Void onComplete = null;
}
