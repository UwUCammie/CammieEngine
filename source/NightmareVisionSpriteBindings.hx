package;

import flixel.group.FlxSpriteGroup;

/** Real constructor factories keep this preset's borrowed provider, while
 * preserving the existing native generic group Class for subtype checks. */
class NightmareVisionSpriteBindings {
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		owner:NightmareVisionSpriteOwner, ?antialiasing:Void->Bool):Void {
		var scope = interp.sourceClassScope();
		scope.bindRuntimeClass('flixel.FlxSprite', NightmareVisionFlxSprite);
		scope.bindRuntimeClass('gameObjects.SpriteFromSheet', NightmareVisionSpriteFromSheet);
		interp.bindImport('gameObjects.SpriteFromSheet', NightmareVisionSpriteFromSheet);
		interp.variables.set('SpriteFromSheet', NightmareVisionSpriteFromSheet);
		interp.bindConstructorFactory(NightmareVisionSpriteFromSheet, function(args) {
			owner.requireActive();
			if (args.length < 4) throw '[nightmare-vision-sprite] SpriteFromSheet requires an atlas and animation';
			return new NightmareVisionSpriteFromSheet(args[0], args[1], args[2], args[3], paths,
				antialiasing == null ? true : antialiasing());
		}, null);
		scope.bindRuntimeClass('funkin.objects.FunkinSprite', NightmareVisionFunkinSprite);
		interp.bindImport('funkin.objects.FunkinSprite', NightmareVisionFunkinSprite);
		interp.variables.set('FunkinSprite', NightmareVisionFunkinSprite);
		scope.bindRuntimeClass('funkin.objects.Bopper', NightmareVisionBopper);
		scope.bindRuntimeClass('funkin.objects.BGSprite', NightmareVisionBGSprite);
		scope.bindRuntimeClass('funkin.video.FunkinVideoSprite', NightmareVisionVideoSprite);
		scope.bindRuntimeClass('flixel.group.FlxTypedSpriteGroup', FlxSpriteGroup);
		interp.bindImport('flixel.FlxSprite', NightmareVisionFlxSprite);
		interp.bindImport('flixel.group.FlxSpriteGroup', FlxSpriteGroup);
		interp.bindImport('flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup', FlxSpriteGroup);
		interp.bindConstructorFactory(FlxSpriteGroup, function(args) return new NightmareVisionSpriteGroup(
			args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0,
			args.length > 2 ? args[2] : 0, owner), null);
		interp.bindConstructorFactory(NightmareVisionFlxSprite, function(args) {owner.requireActive(); return new NightmareVisionFlxSprite(
			args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0, args.length > 2 ? args[2] : null, paths);}, null);
		interp.bindConstructorFactory(NightmareVisionFunkinSprite, function(args) {
			owner.requireActive();
			return new NightmareVisionFunkinSprite(args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0,
				args.length > 2 ? args[2] : null, args.length > 3 ? args[3] : null, paths);
		}, null);
		interp.bindConstructorFactory(NightmareVisionBopper, function(args) {owner.requireActive(); return new NightmareVisionBopper(
			args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0, args.length > 2 ? args[2] : 2, paths);}, null);
		interp.bindConstructorFactory(NightmareVisionBGSprite, function(args) {owner.requireActive(); return new NightmareVisionBGSprite(
			args.length > 0 ? args[0] : null, args.length > 1 ? args[1] : 0, args.length > 2 ? args[2] : 0,
			args.length > 3 ? args[3] : 1, args.length > 4 ? args[4] : 1, args.length > 5 ? args[5] : null,
			args.length > 6 ? args[6] : false, paths);}, null);
		var state = interp.parent;
		interp.bindConstructorFactory(NightmareVisionVideoSprite, function(args) return new NightmareVisionVideoSprite(
			state, paths, args.length > 0 ? args[0] : 0, args.length > 1 ? args[1] : 0,
			args.length > 2 ? args[2] : true, args.length > 3 ? args[3] : false), null);
	}
}
