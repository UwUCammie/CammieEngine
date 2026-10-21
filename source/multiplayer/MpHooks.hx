package multiplayer;

/** What the song screens need from a lobby song that is being played (MpMatch implements it). */
interface MpActivePlay {
	var seed(default, null):Int;
	var stream(default, null):MpPlayStream;
	var begun(default, null):Bool;
	var ended(default, null):Bool;
	/** Latest live scores: {account_id, score, acc, combo, miss, quit}. */
	var live(default, null):Array<Dynamic>;
	var names(default, null):Map<String, String>;
	function countdownWait(countdownMs:Float):Float;
	function playBegin(lengthMs:Float, windows:Dynamic, offsetMs:Float):Void;
	function frame(score:Int, accuracy:Float, combo:Int, misses:Int):Void;
	function finishPlay(failed:Bool, ?result:ResultsModel.ResultsData):Void;
	function leaveSong(failed:Bool):Void;
	function release():Void;
}

/**
	The one place PlayState, the pause menu and the game over screen look for a lobby song.
	It depends on nothing but plain data types, so those screens never pull the network,
	lobby or Flixel-side multiplayer classes into anything that compiles them.
**/
class MpHooks {
	/** The lobby song being played, or null outside a match. */
	public static var current:Null<MpActivePlay> = null;
}
