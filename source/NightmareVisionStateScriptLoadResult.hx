package;

/** Result of resolving and constructing one state or substate source script.
 * A parse-failed handle remains owned by the caller until it is destroyed. */
enum NightmareVisionStateScriptLoadResult {
	Missing(sourcePath:String);
	AlreadyLoaded(sourcePath:String);
	ParseFailed(sourcePath:String, handle:NightmareVisionScriptModule);
	Loaded(sourcePath:String, sourceName:String, handle:NightmareVisionScriptModule);
}
