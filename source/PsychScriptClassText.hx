package;

import flixel.text.FlxText;

/** Native text layout, formatting and rendering with shared source callbacks. */
@:build(SourceSpriteClassAdapterMacro.build())
class PsychScriptClassText extends FlxText implements SourceSpriteClassAdapter {
	public function new(x:Float = 0, y:Float = 0, width:Float = 0, ?text:String, size:Int = 8, embeddedFont:Bool = true) {
		super(x, y, width, text, size, embeddedFont);
	}
}
