package;

/** Mutable event passed through Codename's pre and post receptor creation hooks. */
@:keep
class CodenameStrumCreationEvent extends CodenameGameEvent {
	public var strum:Strumline.StrumNote;
	public var player:Int;
	public var strumID:Int;
	public var animPrefix:String;
	public var sprite:String;

	public function new(strum:Strumline.StrumNote, player:Int, strumID:Int,
		animPrefix:String, sprite:String) {
		super();
		this.strum = strum;
		this.player = player;
		this.strumID = strumID;
		this.animPrefix = animPrefix;
		this.sprite = sprite;
	}

	/** Suppress only the native receptor entrance tween. Gameplay press and
	 * confirm animations remain available after the line has entered. */
	@:keep public function cancelAnimation():Void {
		if (strum != null) strum.cancelCodenameIntroAnimation();
	}
}
