package;

import flixel.graphics.frames.FlxAtlasFrames;

typedef NightmareVisionAlphabetOwner = {
	var atlas:String->FlxAtlasFrames;
	@:optional var spriteOwner:Null<NightmareVisionSpriteOwner>;
}
