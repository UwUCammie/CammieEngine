package;

/** Narrow captured Paths contract used by standalone source script handles. */
interface NightmareVisionScriptPaths {
	public var scriptExtensions(default, null):Array<String>;
	public var scriptInstances(default, null):Map<String, NightmareVisionScriptModule>;
	public function getPath(file:String, ?parentFolder:String, checkMods:Bool = false):String;
	public function exists(path:String):Bool;
	public function getModFolder(path:String, ?exclude:String):String;
}
