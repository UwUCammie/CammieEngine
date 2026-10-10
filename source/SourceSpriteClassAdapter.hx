package;

import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Shared ownership surface for native Flixel sprite subclass adapters. */
interface SourceSpriteClassAdapter {
	public var sourceLifecycle(default, null):SourceSpriteClassLifecycle;
	public function bind(owner:ScriptClass, scope:ScriptClassScope):Void;
	public function scriptOwner():ScriptClass;
	public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic;
}
