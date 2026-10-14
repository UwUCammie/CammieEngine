package;

using StringTools;

/**
	Which file a hit or miss sound plays from, and how loud a hit is.

	Every engine family asks the song owner first (a Psych or Nightmare Vision
	mod can ship its own hitsound and missnote1-3) and falls back to the
	engine's files. Kept free of flixel so the rules can be tested on their own.
**/
class GameplayFeedbackSounds {
	public static inline var HIT:String = 'hitsound';
	public static inline var MISS:String = 'missnote';

	/** The engine ships its hit sound under its own spelling. */
	static inline var NATIVE_HIT:String = 'assets/sounds/hitSound';

	// Built once, a miss happens mid song and should not make a new string each time.
	static final MISS_NAMES:Array<String> = [MISS + 1, MISS + 2, MISS + 3];

	public static function missName(index:Int):String
		return index >= 1 && index <= MISS_NAMES.length ? MISS_NAMES[index - 1] : MISS + index;

	/**
		A sound name as scripts write it (Psych's note.hitsound), reduced to a
		plain name under the sounds folder. Anything that tries to leave that
		folder or is empty gets the fallback instead.
	**/
	public static function safeName(name:String, fallback:String):String {
		if (name == null) return fallback;
		var clean = StringTools.replace(StringTools.trim(name), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0) return fallback;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..') return fallback;
		return clean;
	}

	public static function nativePath(name:String, soundExt:String):String {
		if (name.toLowerCase() == HIT) return NATIVE_HIT + soundExt;
		return 'assets/sounds/' + name + soundExt;
	}

	/** The owner's own file when it has one, the engine's otherwise. */
	public static function resolve(name:String, ownerLookup:Null<String->Null<String>>, nativeFile:String):String {
		var owned:Null<String> = null;
		if (ownerLookup != null) {
			try owned = ownerLookup(name) catch (_:Dynamic) owned = null;
		}
		return owned != null && owned != '' ? owned : nativeFile;
	}

	/**
		How loud a hit plays. `noteVolume` is what the note reports (the source
		preference, or the note's own volume when it forces the sound); when that
		is silent the engine's own hit sound switch still plays it at full volume,
		so turning hit sounds on in the engine works in every song.
	**/
	public static function hitVolume(noteVolume:Float, nativeEnabled:Bool):Float {
		if (Math.isFinite(noteVolume) && noteVolume > 0) return noteVolume;
		return nativeEnabled ? 1.0 : 0.0;
	}
}
