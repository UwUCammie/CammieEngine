package nightmarevision.modchart;

typedef NightmareVisionModifierPathInfo = {
	var position:NightmareVisionModchartVector;
	var dist:Float;
	var start:Float;
	var end:Float;
}

/** Constructor latches and mutable source instance state, never registry-global. */
class NightmareVisionModifierFormulaState {
	public var prefix:String = '';
	public var origin:Null<NightmareVisionModchartVector>;
	public var halfOffset:Null<NightmareVisionModchartVector>;
	public var moveSpeed:Float = 0;
	public var fadeDistY:Float = 120;
	public var pathData:Array<Array<NightmareVisionModifierPathInfo>> = [];
	public var totalDists:Array<Float> = [];
	public var receptorCount:Null<Int->Int>;
	public var reverseValue:Null<Int->Int->Bool->Float>;
	public function new() {}
}
