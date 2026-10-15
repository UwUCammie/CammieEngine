package;

/**
	V-Slice's `FunkinSound` statics for scripts whose calls were not already
	rewritten to the owner-scoped HxcCompatRuntime helpers. Every call goes to
	the same engine audio helpers those rewrites use.
*/
@:keep
class VSliceFunkinSound {
	public static function setMusic(sound:Dynamic):Void
		HxcCompatRuntime.setMusic(sound);

	public static function playOnce(path:Dynamic, ?volume:Float = 1):Dynamic
		return HxcCompatRuntime.freeplayPlaySound(path, volume);

	public static function playMusic(key:Dynamic, ?params:Dynamic):Dynamic
		return HxcCompatRuntime.freeplayPlayMusic(key, params);

	public static function stopAllAudio(?musicToo:Bool = false):Void
		HxcCompatRuntime.stopAllAudio();
}
