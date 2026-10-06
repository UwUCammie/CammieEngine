package nightmarevision.modchart;

/**
	Primitive snapshot/result carrier. The host copies these fields to and from
	FlxSprite/Note/StrumNote; this class itself has no engine-object dependency.
*/
class NightmareVisionModchartObject {
	public static inline var NOTE:String = 'note';
	public static inline var RECEPTOR:String = 'receptor';
	public static inline var NOTE_SPLASH:String = 'noteSplash';
	public static inline var SUSTAIN_SPLASH:String = 'sustainSplash';

	/** Real sprite and synchronization callbacks used only by the native adapter. */
	public var nativeObject:Dynamic;
	public var livePosition:NightmareVisionModchartVector;
	public var flushLive:Null<Void->Void>;
	public var readLive:Null<Void->Void>;
	public var kind:String = NOTE;
	/** Player field/lane: 0 player side, 1 opponent side. */
	public var player:Int = 0;
	/** Column/direction, corresponding to noteData. */
	public var data:Int = 0;
	public var active:Bool = true;
	public var isSustain:Bool = false;
	public var isSustainEnd:Bool = false;
	public var wasGoodHit:Bool = false;
	public var strumTime:Float = 0;
	public var multSpeed:Float = 1;
	public var width:Float = 0;
	public var height:Float = 0;
	public var frameWidth:Float = 0;
	public var frameHeight:Float = 0;
	/** Source-generated duration represented by this individual sustain segment. */
	public var sustainLength:Float = 0;
	public var baseScaleX:Float = 1;
	public var baseScaleY:Float = 1;
	public var scaleX:Float = 1;
	public var scaleY:Float = 1;
	public var x:Float = 0;
	public var y:Float = 0;
	public var alphaMod:Float = 1;
	public var rgbFlash:Float = 0;
	public var rgbAlpha:Float = 1;
	public var angle:Float = 0;
	public var garbage:Bool = false;
	public var typeOffsetX:Float = 0;
	public var typeOffsetY:Float = 0;
	public var spriteOffsetX:Float = 0;
	public var spriteOffsetY:Float = 0;
	/** Signal to the Flixel adapter to run source updateObject centering. */
	public var centerOriginAndOffsets:Bool = false;

	public function new(?kind:String) {
		if (kind != null) this.kind = kind;
	}
}
