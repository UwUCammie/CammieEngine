package nightmarevision.modchart;

/** Source-shaped render values retained when the host sprite has no matching field. */
class NightmareVisionModchartVisualState {
	public var position:NightmareVisionModchartVector = new NightmareVisionModchartVector();
	public var alphaMod:Float = 1;
	public var rgbFlash:Float = 0;
	public var rgbAlpha:Float = 1;
	/** Source base scale used to transform draw offsets independently of modifiers. */
	public var baseScaleX:Float = 1;
	public var baseScaleY:Float = 1;
	public var spriteOffsetX:Float = 0;
	public var spriteOffsetY:Float = 0;
	public var holdAngle:Float = 0;
	public var holdSegmentDistance:Float = 0;
	public var holdSegmentDuration:Float = 0;
	public var isSustainEnd:Bool = false;
	public var clipX:Float = 0;
	public var clipY:Float = 0;
	public var clipWidth:Float = 0;
	public var clipHeight:Float = 0;
	public var clipApplied:Bool = false;

	public function new() {}
}
