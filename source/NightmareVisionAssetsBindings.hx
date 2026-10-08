package;

/** Bind Nightmare Vision's raw, compiled Lime/OpenFL Assets API to the
	selected import's receipt-verified Project identities. This remains separate
	from FunkinAssets and Paths, which provide the source mod-directory lookup. */
@:keep
class NightmareVisionAssetsBindings {
	public static function install(interp:NightmareVisionScriptInterp,
		paths:NightmareVisionPaths):Void {
		if (interp == null || paths == null)
			throw '[nightmare-vision-assets] Raw Assets bindings require a selected owner interpreter';

		// The donor preset uses the same global Assets and OpenFlAssets classes
		// for package and engine scripts. Its generated project includes the
		// selected package and engine/core declarations, so use the shared owner
		// context that resolves those authenticated scopes without consulting the
		// host process registry or loose package paths.
		var context = SourceOwnerAssetContext.nightmareVisionAssets(paths.root);
		var limeAssets = PsychOwnerLimeAssets.createForContext(context);
		var openFlAssets = PsychOwnerOpenFlAssets.createForContext(context);

		interp.variables.set('Assets', limeAssets);
		interp.variables.set('OpenFlAssets', openFlAssets);
		interp.bindImport('lime.utils.Assets', limeAssets);
		interp.bindImport('openfl.utils.Assets', openFlAssets);
		// OpenFL publishes `openfl.Assets` as a typedef to this same class.
		// Keep the source alias on the exact same owner proxy as the canonical
		// package path instead of letting Iris resolve the process-global type.
		interp.bindImport('openfl.Assets', openFlAssets);

		// Qualified imports and Type.resolveClass must reach these exact same
		// per-interpreter owner proxies, not the real process-global classes.
		var classScope = interp.sourceClassScope();
		classScope.bindRuntimeClass('lime.utils.Assets', limeAssets);
		classScope.bindRuntimeClass('openfl.utils.Assets', openFlAssets);
		classScope.bindRuntimeClass('openfl.Assets', openFlAssets);
	}
}
