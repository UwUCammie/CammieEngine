package;

/** Borrowed source-class services, independent of a particular interpreter. */
interface SourceClassAccess {
	function importClass(path:String):Dynamic;
	function handles(value:Dynamic):Bool;
	function isClass(value:Dynamic):Bool;
	function construct(type:Dynamic, args:Array<Dynamic>):Dynamic;
	function read(value:Dynamic, field:String):Dynamic;
	function write(value:Dynamic, field:String, item:Dynamic):Dynamic;
	function call(value:Dynamic, field:String, args:Array<Dynamic>):Dynamic;
	function nativeMethod(value:Dynamic, field:String, method:Dynamic):Dynamic;
	function nativeValue(value:Dynamic):Dynamic;
	function nativePropertyValue(receiver:Dynamic, name:String, value:Dynamic):Dynamic;
	function nativeArrayValue(collection:Dynamic, value:Dynamic):Dynamic;
	function classOf(value:Dynamic):Dynamic;
	function className(value:Dynamic):String;
}
