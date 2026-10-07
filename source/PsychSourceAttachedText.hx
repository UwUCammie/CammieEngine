package;
import flixel.FlxSprite;

@:keep
class PsychSourceAttachedText extends PsychSourceAlphabet
{
	public var offsetX:Float = 0;
	public var offsetY:Float = 0;
	public var sprTracker:FlxSprite;
	public var copyVisible:Bool = true;
	public var copyAlpha:Bool = false;
	public function new(text:String = "", ?offsetX:Float = 0, ?offsetY:Float = 0, ?bold = false, ?scale:Float = 1, ?context:PsychAlphabetContext) {
		super(0, 0, text, bold, context);

		this.setScale(scale);
		this.isMenuItem = false;
		this.offsetX = offsetX;
		this.offsetY = offsetY;
	}

	override public function update(elapsed:Float) {
		if (sprTracker != null) {
			setPosition(sprTracker.x + offsetX, sprTracker.y + offsetY);
			if(copyVisible)
				visible = sprTracker.visible;

			if(copyAlpha)
				alpha = sprTracker.alpha;
		}

		super.update(elapsed);
	}
}