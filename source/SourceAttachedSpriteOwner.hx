package;

import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;

/** Asset and preference dependencies captured by a source constructor factory. */
typedef SourceAttachedSpriteOwner = {
	var image:(String, Null<String>)->FlxGraphic;
	var sparrowAtlas:(String, Null<String>)->FlxAtlasFrames;
	var antialiasing:Void->Bool;
}
