package;

import flixel.FlxBasic;

/** Retains the native base type with shared source callbacks and cleanup. */
@:build(SourceNativeClassAdapterMacro.build(false))
class PsychScriptClassBasic extends FlxBasic implements SourceNativeClassAdapter {
	public function new() {
		super();
	}
}
