package;

typedef SourceHealthIconOwner = {
	var image:(String, Bool)->flixel.graphics.FlxGraphic;
	/** Source-relative full path, such as images/icons/icon-face.png. */
	var exists:String->Bool;
	var uiPrefix:Void->String;
	var antialiasing:Void->Bool;
}
