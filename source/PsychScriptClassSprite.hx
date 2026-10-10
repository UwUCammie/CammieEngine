package;

import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxGraphicAsset;

/** Retains native FlxSprite storage and rendering for an authored subclass. */
@:build(SourceNativeClassAdapterMacro.build())
class PsychScriptClassSprite extends FlxSprite implements SourceNativeClassAdapter {
	public function new(x:Float = 0, y:Float = 0, ?graphic:FlxGraphicAsset) {
		super(x, y, graphic);
	}
}
