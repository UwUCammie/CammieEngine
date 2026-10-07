package;

/** The public record shape used by Psych 1.0.4's backend.Achievements. */
typedef PsychAchievementInfo = {
	var name:String;
	var description:String;
	@:optional var hidden:Bool;
	@:optional var maxScore:Float;
	@:optional var maxDecimals:Int;
	@:optional var mod:String;
	@:optional var ID:Int;
}
