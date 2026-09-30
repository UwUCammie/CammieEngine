package;

import haxe.io.Path;

/** Choose one encoding of each authored split vocal stem for the native mixer. */
class VocalStemSelection {
	public static function sameStem(first:String, second:String):Bool {
		return first != null && second != null
			&& Path.withoutExtension(first).toLowerCase() == Path.withoutExtension(second).toLowerCase();
	}

	public static function prefer(candidate:String, current:String, nativeExtension:String):Bool {
		if (candidate == null || current == null) return false;
		var wanted = nativeExtension == null ? '' : nativeExtension.toLowerCase();
		if (StringTools.startsWith(wanted, '.')) wanted = wanted.substr(1);
		return Path.extension(candidate).toLowerCase() == wanted
			&& Path.extension(current).toLowerCase() != wanted;
	}
}
