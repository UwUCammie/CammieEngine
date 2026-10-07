package;

import flixel.FlxBasic;
import flixel.FlxSprite;
import NightmareVisionStageDataSchema.NightmareVisionStageFile;

/** Captured IO and actual source module/class operations, never a global owner. */
typedef NightmareVisionStageOwner = {
 var requireActive:Void->Void;
 var paths:NightmareVisionPaths;
 var stageFile:String->Null<NightmareVisionStageFile>;
 var template:Void->NightmareVisionStageFile;
 var antialiasing:Void->Bool;
 var resolveClass:String->Null<Class<Dynamic>>;
 var createInstance:(Class<Dynamic>, Array<Dynamic>)->Dynamic;
 var setZIndex:(FlxBasic, Int)->Void;
 var setProperty:(Dynamic, String, Dynamic)->Void;
 var warn:String->Void;
 var scriptPath:String->String;
 var scriptExists:String->Bool;
 var fromFile:(String, Null<Map<String, Dynamic>>)->NightmareVisionScriptModule;
 var bopper:FlxSprite->Null<NightmareVisionStageBopper>;
}

/** Real operation bridge for the canonical Character's source Bopper family. */
typedef NightmareVisionStageBopper = {
 var loadAtlas:String->Void;
 var addAnimByPrefix:(String, String, Int, Bool, Bool, Bool)->Void;
 var addAnimByIndices:(String, String, Array<Int>, Int, Bool, Bool, Bool)->Void;
 var addOffset:(String, Float, Float)->Void;
 var playAnim:Null<String>->Void;
}
