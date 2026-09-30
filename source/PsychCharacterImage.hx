package;

using StringTools;

/** The Lua Character.imageFile property names the atlas currently used by an
 * actor. Keep the value as an extensionless, runtime-relative image path so
 * makeAnimatedLuaSprite can open the matching PNG and Sparrow XML. */
class PsychCharacterImage {
	static function atlasStem(value:String):String {
		if (value == null)
			return '';
		var clean = value.trim().replace('\\', '/');
		if (clean.endsWith('.png'))
			clean = clean.substr(0, clean.length - 4);
		if (!clean.startsWith('assets/') || clean.indexOf('..') >= 0 || clean.indexOf(':') >= 0)
			return '';
		return FNFAssets.exists(clean + '.png') && FNFAssets.exists(clean + '.xml') ? clean : '';
	}

	/** The loaded FlxGraphic key is authoritative for custom HScript sheets.
	 * Native JSON characters can have an opaque bitmap-cache key; in that case
	 * their selected visual root supplies the exact conventional char atlas. */
	public static function resolve(graphicKey:String, selectedAssetRoot:String):String {
		var loaded = atlasStem(graphicKey);
		if (loaded != '')
			return loaded;
		// A concrete graphic path which has no Sparrow XML must not be replaced
		// with some other atlas merely because the selected folder has one.
		if (graphicKey != null && graphicKey.trim().replace('\\', '/').startsWith('assets/'))
			return '';
		if (selectedAssetRoot == null || selectedAssetRoot.trim() == '')
			return '';
		var root = selectedAssetRoot.trim().replace('\\', '/');
		if (root.endsWith('/')) root = root.substr(0, root.length - 1);
		return atlasStem(root + '/char');
	}
}
