package;

import flixel.FlxObject;

/** Retains the native base type with shared source callbacks and cleanup. */
@:build(SourceNativeClassAdapterMacro.build(false, true))
class PsychScriptClassObject extends FlxObject implements SourceNativeClassAdapter {
	public function new(x:Float = 0, y:Float = 0, width:Float = 0, height:Float = 0) {
		super(x, y, width, height);
	}
}
