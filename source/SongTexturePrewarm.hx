package;

/**
	Texture rules for graphics held for a song, kept apart from FNFAssets so
	they can be checked without a renderer.
**/
class SongTexturePrewarm {
	/** FNFAssets.retainForSongOnGpu drops the pixels only when they are there
		and readable (a graphic someone already made GPU-only is left alone),
		on the thread that owns the GL context, and only with a context to
		upload into. */
	public static inline function canReleasePixels(hasPixels:Bool, readable:Bool, ownerThread:Bool, hasContext:Bool):Bool
		return hasPixels && readable && ownerThread && hasContext;
}
