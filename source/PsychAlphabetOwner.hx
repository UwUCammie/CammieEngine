package;

import flixel.graphics.frames.FlxAtlasFrames;

typedef PsychAlphabetOwner = {
	var atlas:String->FlxAtlasFrames;
	var getPath:String->String;
	var exists:String->Bool;
	var text:String->String;
	var antialiasing:Void->Bool;
}
