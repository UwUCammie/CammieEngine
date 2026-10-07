package;

/** Native effects required to apply a source Nightmare Vision mod config.
	The host owns window, RPC, Paths, transition, state factory, and private save
	services. Config application calls these in donor order and lets exceptions
	propagate so already-applied effects remain visible. */
interface NightmareVisionModConfigHost {
	function defaultAppTitle():String;
	function defaultRpcId():String;
	/** Core-derived prefix used when the selected package does not override UI paths. */
	function defaultUiPrefix():String;
	function resolveSelectedPath(relativePath:String):String;
	function resolveSelectedFont(key:String):String;
	function pathExists(path:String):Bool;
	function selectedDirectoryExists(relativePath:String):Bool;
	function updateLiveConfig(selectedDirectory:String, selectedRoot:String, pack:Dynamic):Void;
	function initializeOptions(selectedDirectory:String, selectedRoot:String):Void;
	function setWindowTitle(title:String):Void;
	function setWindowIcon(path:String):Void;
	function reportMissingIcon(iconFile:String):Void;
	function setTransition(transition:NightmareVisionModTransition):Void;
	function setRpcId(clientId:String):Void;
	function setDefaultFont(path:String):Void;
	function setPrefix(field:String, value:String):Void;
}
