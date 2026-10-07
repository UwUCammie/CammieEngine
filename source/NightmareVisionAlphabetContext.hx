package;

/** Source character sets persist while atlas IO can be rebound between scenes. */
@:keep
class NightmareVisionAlphabetContext
{
	public var alphabet:String = 'abcdefghijklmnopqrstuvwxyz';
	public var numbers:String = '1234567890';
	public var symbols:String = "!#$%&'()*+,-.:;<=>?@[]^_|~";
	var owner:Null<NightmareVisionAlphabetOwner>;

	public function new(owner:NightmareVisionAlphabetOwner) this.owner = owner;
	public function getSpriteOwner():Null<NightmareVisionSpriteOwner> return owner == null ? null : owner.spriteOwner;
	public function rebindOwner(owner:NightmareVisionAlphabetOwner):Void this.owner = owner;
	public function release():Void owner = null;
	public function atlas(name:String):flixel.graphics.frames.FlxAtlasFrames
	{
		if (owner == null) throw '[nightmare-vision-alphabet] Selected owner has been released';
		return owner.atlas(name);
	}
}
