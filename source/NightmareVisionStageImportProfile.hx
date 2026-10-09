package;

import haxe.io.Path;

/** Resolve Stage API identity during import, never from donor paths at runtime. */
class NightmareVisionStageImportProfile {
	public static function capture(sourceRoot:String, installedRoot:String):String {
		var api = NightmareVisionStageProfile.UNKNOWN;
		#if sys
		var selected = NightmareVisionAssetCollector.retentionRoot(sourceRoot);
		// An explicitly selected core assets folder can inherit only its proven
		// NV game executable, never an arbitrary neighboring directory.
		if (Path.withoutDirectory(selected).toLowerCase() == 'assets') {
			var parent = Path.directory(selected);
			var inspected = ImportRootScanner.inspectRoot(parent, ImportEngine.AUTO);
			if (inspected != null && inspected.engine == ImportEngine.NIGHTMARE_VISION
				&& ImportRootScanner.hasNightmareVisionContainerProof(inspected.evidence)) selected = parent;
		}
		api = ImportRootScanner.nightmareVisionStageApi(selected);
		#end
		return haxe.Json.stringify({version:1, owner:installedRoot, stageApi:api});
	}

}
