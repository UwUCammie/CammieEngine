package;

/** Shared authentication for imported Psych services. Paths and source origin
 * identify the caller; display names and arbitrary directories never do. */
@:access(PlayState)
class PsychSourceOwnerAccess {
	public static function resolve(host:PlayState, paths:Dynamic, origin:String):Null<{root:String, paths:Dynamic}> {
		if (host == null) return null;
		var root = host.compatPsychOwnerForScript(origin);
		var capturedRoot = '';
		if (paths != null) try capturedRoot = PsychOwnerPaths.ownerRoot(paths) catch (_:Dynamic) {}
		if (root == null && origin != null && capturedRoot != '')
			root = PsychModSettingCompat.ownerForScript(origin, capturedRoot);
		if (root == null) root = host.selectedPsychSkinRoot();
		root = PsychOwnerAssetPath.normalizeOwner(root);
		if (root == '') return null;
		if (CompatScriptManifest.destinationKey(capturedRoot) != CompatScriptManifest.destinationKey(root))
			paths = PsychOwnerPaths.create(root, host.psychStageLibrary);
		return {root:root, paths:paths};
	}

	public static function retainedRoots(play:PlayState):Array<String> {
		if (play == null) return [];
		var roots:Array<String> = [];
		var manifest = play.getCompatScriptManifest();
		if (manifest != null && manifest.roots != null) for (entry in manifest.roots) {
			if (entry == null || entry.engine != ImportEngine.PSYCH) continue;
			var root = PsychOwnerAssetPath.normalizeOwner(entry.path);
			if (root != '' && !roots.contains(root)) roots.push(root);
		}
		var provider = PsychOwnerAssetPath.normalizeOwner(PsychGlobalPackImporter.defaultProvider());
		if (provider != '' && !roots.contains(provider)) roots.push(provider);
		return roots;
	}
}
