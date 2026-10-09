package;

/** All constructor and static entry points retain the selected script owner. */
class NightmareVisionLegacyVideoBindings {
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		owner:NightmareVisionSpriteOwner):Void {
		var scope = interp.sourceClassScope();
		var type = NightmareVisionLegacyVideoSprite;
		var state = interp.parent;
		scope.bindRuntimeClass('gameObjects.PsychVideoSprite', type);
		interp.bindImport('gameObjects.PsychVideoSprite', type);
		interp.variables.set('PsychVideoSprite', type);
		NightmareVisionLegacyVideoSprite.retainOwner(state, paths.root);
		interp.bindConstructorFactory(type, function(args) {
			owner.requireActive();
			return new NightmareVisionLegacyVideoSprite(state, paths, args.length > 0 ? args[0] : true);
		}, {release:function() NightmareVisionLegacyVideoSprite.releaseOwner(state, paths.root)}, true);
		var held = function() {owner.requireActive(); return NightmareVisionLegacyVideoSprite.forOwner(state, paths.root);};
		scope.bindStaticField(type, 'heldVideos', held, function(value) {
			owner.requireActive(); return NightmareVisionLegacyVideoSprite.replaceForOwner(state, paths.root, value);
		});
		scope.bindStaticField(type, 'globalPause', function() return function() {
			for (video in held().copy()) if (video != null && video.ownerState == state && video.ownerRoot == paths.root) video.pause();
		}, null);
		scope.bindStaticField(type, 'globalResume', function() return function() {
			for (video in held().copy()) if (video != null && video.ownerState == state && video.ownerRoot == paths.root) video.resume();
		}, null);
		var callbacks = {ONEND:'onEnd', ONSTART:'onStart', ONFORMAT:'onFormat'};
		interp.bindImport('gameObjects.PsychVideoSprite.VidCallbacks', callbacks);
		interp.variables.set('VidCallbacks', callbacks);
	}
}
