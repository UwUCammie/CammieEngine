package;

typedef SwagSection = {
	var sectionNotes:Array<Dynamic>;
	@:default(16) var lengthInSteps:Int;
	var mustHitSection:Bool;
	var bpm:Float;
	var changeBPM:Bool;
	var altAnim:Bool;
	var altAnimNum:Null<Int>;
	// Psych marks whole opponent sections as girlfriend vocals/camera focus.
	// Keep this optional so legacy Modding Plus sections retain their defaults.
	@:optional var gfSection:Null<Bool>;
	// Legacy Modding Plus/Denpa afterimage flags. These are optional because
	// older charts omit them entirely; missing values mean false.
	@:optional var crossfadeBf:Null<Bool>;
	@:optional var crossfadeDad:Null<Bool>;
	// Denpa charts also use one shared crossFade flag for both sides.
	@:optional var crossFade:Null<Bool>;
}

class Section {
	public var sectionNotes:Array<Dynamic> = [];
	public var lengthInSteps:Int = 16;
	public var mustHitSection:Bool = true;

	/**
	 *	Copies the first section into the second section!
	 */
	public static var COPYCAT:Int = 0;

	public function new(lengthInSteps:Int = 16) {
		this.lengthInSteps = lengthInSteps;
	}
}
