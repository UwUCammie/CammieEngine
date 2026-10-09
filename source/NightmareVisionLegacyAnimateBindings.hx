package;

/** Constructor and reflected anim property share the interpreter's native routes. */
class NightmareVisionLegacyAnimateBindings {
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		owner:NightmareVisionSpriteOwner):Void {
		var scope = interp.sourceClassScope();
		scope.bindRuntimeClass('flxanimate.FlxAnimate', NightmareVisionLegacyFlxAnimate);
		interp.bindImport('flxanimate.FlxAnimate', NightmareVisionLegacyFlxAnimate);
		if (NightmareVisionStageProfile.read(paths.root) == NightmareVisionStageProfile.LEGACY)
			interp.variables.set('FlxAnimate', NightmareVisionLegacyFlxAnimate);
		var assets = PsychOwnerOpenFlAssets.createForContext(SourceOwnerAssetContext.nightmareVisionAssets(paths.root));
		interp.bindConstructorFactory(NightmareVisionLegacyFlxAnimate, function(args) {
			owner.requireActive();
			var sprite = new NightmareVisionLegacyFlxAnimate(args.length > 0 ? args[0] : 0,
				args.length > 1 ? args[1] : 0, args.length > 2 ? args[2] : null,
				args.length > 3 ? args[3] : null, assets, owner, paths.root);
			scope.bindStaticField(sprite, 'anim', function() return sprite.sourceAnim,
				function(value) {throw '[legacy-animate] anim is read-only'; return value;});
			sprite.releaseBinding = function() scope.unbindStaticFields(sprite);
			return sprite;
		}, null);
	}
}
