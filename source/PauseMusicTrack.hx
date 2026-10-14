package;

/**
	Picks the pause menu track. The answer is remembered so the song loading
	pass can do the disk probe and the pause menu only reads the result.
**/
class PauseMusicTrack {
	static var rememberedKey:String = null;
	static var rememberedPath:String = null;

	/** A suffixed track wins when it exists, otherwise the stock one plays. */
	public static function resolve(suffix:String, ext:String, exists:String->Bool):String {
		var stock = 'assets/music/breakfast' + ext;
		if (suffix == null || suffix == '')
			return stock;
		var suffixed = 'assets/music/breakfast' + suffix + ext;
		return exists(suffixed) ? suffixed : stock;
	}

	/**
		Same answer as `resolve`, probing the disk only when the suffix, the
		extension or the library epoch differ from the remembered request.
	**/
	public static function pathFor(suffix:String, ext:String, epoch:Int, exists:String->Bool):String {
		var key = epoch + '|' + ext + '|' + (suffix == null ? '' : suffix);
		if (key != rememberedKey || rememberedPath == null) {
			rememberedPath = resolve(suffix, ext, exists);
			rememberedKey = key;
		}
		return rememberedPath;
	}

	public static function forget():Void {
		rememberedKey = null;
		rememberedPath = null;
	}

	/** Upper bound for the random start position, in milliseconds. A track that
		cannot report its length starts from the beginning. */
	public static function latestStart(lengthMs:Float):Int {
		return lengthMs > 0 ? Std.int(lengthMs / 2) : 0;
	}
}
