package;

typedef SourceBarOwner = {
	var image:String->flixel.graphics.FlxGraphic;
	var antialiasing:Void->Bool;
	@:optional var spriteOwner:Null<NightmareVisionSpriteOwner>;
	@:optional var nightmarePaths:Null<NightmareVisionPaths>;
}
