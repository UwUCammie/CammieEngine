package;

/**
	The `StageData` class Nightmare Vision scripts see, narrowed to one owner.
	Lookups use the same owner-scoped rules gameplay stages load with
	(NightmareVisionStageData), and `resolveObjectInstance` uses the same
	built-in class rule as Stage's `customInstance` objects, so a script and
	the engine never disagree about which file or class a stage name means.
*/
@:keep
class NightmareVisionStageDataView {
	final ownerRoot:String;
	final builtinObject:String->Dynamic;

	public function new(ownerRoot:String, ?builtinObject:String->Dynamic) {
		this.ownerRoot = ownerRoot;
		this.builtinObject = builtinObject;
	}

	/**
		Source returns its second candidate even when neither exists; this
		returns null then, which source callers treat the same way because
		they always check that the path exists before reading it.
	*/
	public function getStageFromDir(dir:String, stage:String):Null<String>
		return NightmareVisionStageData.getStageFromDir(ownerRoot, dir, stage);

	public function getStageFile(stage:String):Dynamic
		return NightmareVisionStageData.getStageFile(ownerRoot, stage);

	public function getTemplateStageFile():Dynamic
		return NightmareVisionStageData.getTemplateStageFile();

	public function resolveObjectInstance(obj:String):Dynamic
		return obj == null || builtinObject == null ? null : builtinObject(obj);
}
