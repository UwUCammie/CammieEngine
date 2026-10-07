package;

import flixel.graphics.frames.FlxAtlasFrames;

/** Exact stock defaults only. Custom paths never borrow the native font atlas. */
class SourceAlphabetAssets
{
	public static function stockPath(relative:String):Null<String>
	{
		return switch (relative) {
			case 'images/alphabet.png': 'assets/images/source_compat/psych/alphabet.png';
			case 'images/alphabet.xml': 'assets/images/source_compat/psych/alphabet.xml';
			case 'images/alphabet.json': 'assets/images/source_compat/psych/alphabet.json';
			default: null;
		}
	}

	public static function atlas(ownerPath:String->Null<String>, load:(String, String)->FlxAtlasFrames):FlxAtlasFrames
	{
		var image = ownerPath('images/alphabet.png');
		var xml = ownerPath('images/alphabet.xml');
		// Psych resolves image and XML independently, allowing a one-channel override.
		if (image == null) image = stockPath('images/alphabet.png');
		if (xml == null) xml = stockPath('images/alphabet.xml');
		return load(image, xml);
	}
}
