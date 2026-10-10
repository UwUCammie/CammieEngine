package;

import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Shared ownership surface for native Flixel subclass adapters. */
interface SourceNativeClassAdapter {
	public var sourceLifecycle(default, null):SourceNativeClassLifecycle;
	public function bind(owner:ScriptClass, scope:ScriptClassScope):Void;
	public function scriptOwner():ScriptClass;
	public function supportsNativeSuper(name:String):Bool;
	public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic;
}
