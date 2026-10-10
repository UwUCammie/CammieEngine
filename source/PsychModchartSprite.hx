package;

import flixel.FlxSprite;
import flixel.graphics.frames.FlxFramesCollection;

/** Native sprite with Psych's script-visible animation offset surface. */
class PsychModchartSprite extends FlxSprite {
	public var sourceAtlasNames:Array<String> = null;
	public var animOffsets:Map<String, Array<Float>> = [];
	public function new(x:Float = 0, y:Float = 0, ?antialias:Bool) {
		super(x, y);
		antialiasing = antialias == null ? FlxSprite.defaultAntialiasing : antialias;
	}
	override function set_frames(value:FlxFramesCollection):FlxFramesCollection {
		sourceAtlasNames = null;
		return super.set_frames(value);
	}
	public function playAnim(name:String, forced:Bool = false, reverse:Bool = false, startFrame:Int = 0):Void {
		animation.play(name, forced, reverse, startFrame);
		if (animOffsets.exists(name)) {
			var value = animOffsets.get(name);
			offset.set(value[0], value[1]);
		}
	}
	public function addOffset(name:String, x:Float, y:Float):Void {animOffsets.set(name, [x, y]);}
}
