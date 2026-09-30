package;

/** Mutable input sampled for a single authored Codename strumline. */
@:keep
class CodenameInputEvent extends CodenameGameEvent {
	public var pressed:Array<Bool>;
	public var justPressed:Array<Bool>;
	public var justReleased:Array<Bool>;
	public var strumLine:Dynamic;
	public var strumLineID:Int;

	public function new(pressed:Array<Bool>, justPressed:Array<Bool>,
		justReleased:Array<Bool>, strumLine:Dynamic, strumLineID:Int) {
		super();
		this.pressed = pressed;
		this.justPressed = justPressed;
		this.justReleased = justReleased;
		this.strumLine = strumLine;
		this.strumLineID = strumLineID;
	}
}
