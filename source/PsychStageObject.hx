package;

import hscript.ScriptClass;
import hscript.AbstractScriptClass;

/** Access native and source-class stage objects without replacing their identity. */
@:access(hscript.AbstractScriptClass)
class PsychStageObject {
	public static function read(object:Dynamic, field:String):Dynamic {
		if (Std.isOfType(object, ScriptClass)) return (cast object:AbstractScriptClass).fieldRead(field);
		return Reflect.getProperty(object, field);
	}
	public static function write(object:Dynamic, field:String, value:Dynamic):Void {
		if (Std.isOfType(object, ScriptClass)) (cast object:AbstractScriptClass).fieldWrite(field, value);
		else Reflect.setProperty(object, field, value);
	}
	public static function call(object:Dynamic, method:String, args:Array<Dynamic>):Void {
		if (Std.isOfType(object, ScriptClass)) (cast object:AbstractScriptClass).callFunction(method, args);
		else Reflect.callMethod(object, Reflect.getProperty(object, method), args);
	}
}
