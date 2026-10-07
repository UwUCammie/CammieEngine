package;

import NightmareVisionCharacterGroupOwner.NightmareVisionCharacterGroupScene;

/** Source arguments retain actual Class identity and a captured construction owner. */
class NightmareVisionCharacterGroupBindings {
	public static function owner(paths:NightmareVisionPaths,
		scene:Void->Null<NightmareVisionCharacterGroupScene>):NightmareVisionCharacterGroupOwner {
		var spriteOwner = NightmareVisionSpriteRegistry.capture(paths);
		var construction = new SourceCharacterConstruction(paths.root, ImportEngine.NIGHTMARE_VISION, spriteOwner, paths);
		return {
			construct:function(name, player) return new Character(0, 0, name, player, null, construction),
			scene:scene,
			spriteOwner:spriteOwner
		};
	}
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		scene:Void->Null<NightmareVisionCharacterGroupScene>):Void {
		var selected = owner(paths, scene);
		var construction = new SourceCharacterConstruction(paths.root, ImportEngine.NIGHTMARE_VISION, selected.spriteOwner, paths);
		interp.variables.set('CharacterGroup', NightmareVisionCharacterGroup);
		interp.variables.set('Character', Character);
		var types = {BF:0, DAD:1, GF:2};
		interp.variables.set('CharacterType', types);
		interp.bindImport('funkin.objects.CharacterGroup', NightmareVisionCharacterGroup);
		interp.bindImport('funkin.objects.CharacterGroup.CharacterType', types);
		interp.bindImport('funkin.objects.Character', Character);
		var scope = interp.sourceClassScope();
		scope.bindRuntimeClass('funkin.objects.CharacterGroup', NightmareVisionCharacterGroup);
		scope.bindRuntimeClass('funkin.objects.Character', Character);
		interp.bindConstructorFactory(NightmareVisionCharacterGroup, function(args) {
			return new NightmareVisionCharacterGroup(args.length > 0 ? args[0] : 0,
				args.length > 1 ? args[1] : 0, cast args[2], selected);
		}, null);
		interp.bindConstructorFactory(Character, function(args) {
			return new Character(args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0,
				args.length > 2 ? args[2] : 'bf', args.length > 3 ? args[3] : false, null, construction);
		}, null);
	}
}
