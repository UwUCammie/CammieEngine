package;

import flixel.math.FlxPoint;

/** Borrowed owner-local construction and live scene dependencies. */
typedef NightmareVisionCharacterGroupOwner = {
 var construct:(String, Bool)->Character;
 var scene:Void->Null<NightmareVisionCharacterGroupScene>;
 @:optional var spriteOwner:Null<NightmareVisionSpriteOwner>;
}

typedef NightmareVisionCharacterGroupScene = {
 var gfPosition:Null<FlxPoint>;
 var playFields:Null<NightmareVisionPlayFields>;
}
