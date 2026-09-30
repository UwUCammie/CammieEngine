package;

/** Validated selected-owner source, supplied before the actor visual is built. */
typedef CodenameCharacterConstruction = {
	var root:String;
	var authoredId:String;
	var nativeName:String;
	var xmlText:String;
	/** Source definition supplying XML and its optional companion script. */
	var sourceDefinitionId:String;
	var usedSourceFallback:Bool;
	var configuredSourceFallback:Bool;
	/** Source visual root. May point at a receipt-verified owner dependency. */
	@:optional var assetRoot:String;
	/** Exact image files allowed from assetRoot when the definition is a dependency. */
	@:optional var fallbackAssetFiles:Array<String>;
	var createRuntime:Character->CodenameCharacterRuntime;
}
