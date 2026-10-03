package;

/** Decode a UTF-8 text signature at the asset boundary without changing
 * authored content, whitespace, or byte data returned by getBytes. */
class AssetTextEncoding {
	public static function stripBom(text:String):String {
		if (text == null || text == '') return text;
		if (text.charCodeAt(0) == 0xFEFF) return text.substr(1);
		// Byte-oriented targets can expose the UTF-8 signature as three chars.
		if (text.length >= 3 && text.charCodeAt(0) == 0xEF
			&& text.charCodeAt(1) == 0xBB && text.charCodeAt(2) == 0xBF)
			return text.substr(3);
		return text;
	}
}
