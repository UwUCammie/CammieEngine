package nightmarevision.modchart;

/**
	Direct calls into one modifier, beside the function fields of a
	NightmareVisionModifierExecution. The renderer runs every active modifier
	for every note and receptor each frame. Through a function field each Float
	argument and each Float result is boxed on the native target, which on a
	plain Nightmare Vision song was about half of all garbage made while
	playing. A typed method call passes the same values without boxing.

	An entry carrying `calls` must give the same answers through both routes:
	`calls.getPos` is its `getPosition`, `calls.updateObjectOfKind` its
	`updateObject`, `calls.getValue` its `value` and `calls.getSubmodValue` its
	`subValue`.
**/
interface NightmareVisionModifierCalls {
	function getPos(time:Float, diff:Float, tDiff:Float, beat:Float, pos:NightmareVisionModchartVector, data:Int, player:Int,
		obj:Dynamic):NightmareVisionModchartVector;
	function updateObjectOfKind(beat:Float, obj:Dynamic, pos:NightmareVisionModchartVector, player:Int, kind:String):Void;
	function getValue(player:Int):Float;
	function getSubmodValue(modName:String, player:Int):Float;
}
