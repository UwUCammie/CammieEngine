package;

/** Import output records the discovered menu decision alongside retained code.
 * Runtime discovery revalidates these candidates before materialization. */
class ImportedMenuManifest {
	public static inline var FILE_NAME:String = '.cammie-menu-entry.json';
	public static function capture(root:String, engine:String, directory:String):String {
		var state = ''; var diagnostic = ''; var sources:Array<String> = [];
		if (engine == ImportEngine.PSYCH) {
			var plan = ImportedPsychMenuPlan.find(root);
			state = plan.state; diagnostic = plan.diagnostic;
			for (path in plan.sources) sources.push(path.substr(root.length + 1));
		} else if (engine == ImportEngine.NIGHTMARE_VISION) {
			var plan = ImportedNightmareMenuPlan.find(root, directory);
			state = plan.state; diagnostic = plan.diagnostic;
		}
		return haxe.Json.stringify({version:1, adapter:ImportRevision.current(engine), owner:root,
			engine:engine, state:state, sources:sources, diagnostic:diagnostic});
	}
}
