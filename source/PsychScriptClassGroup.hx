package;

import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;

/** Retains the native base type with shared source callbacks and cleanup. */
@:build(SourceNativeClassAdapterMacro.build(false))
class PsychScriptClassGroup extends FlxTypedGroup<FlxBasic> implements SourceNativeClassAdapter {
	public function new(maxSize:Int = 0) {
		super(maxSize);
	}
}
