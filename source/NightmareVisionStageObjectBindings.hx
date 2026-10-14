package;

/**
	Binds Nightmare Vision's stage object classes (BackgroundGirls and
	BackgroundDancer) for one owner. Like Bopper and BGSprite, construction
	goes through a factory so the sprite loads from the owner that made it.
*/
class NightmareVisionStageObjectBindings {
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		owner:NightmareVisionSpriteOwner):Void {
		bindClass(interp, 'BackgroundGirls', 'funkin.objects.stageobjects.BackgroundGirls', NightmareVisionBackgroundGirls);
		bindClass(interp, 'BackgroundDancer', 'funkin.objects.stageobjects.BackgroundDancer', NightmareVisionBackgroundDancer);
		interp.bindConstructorFactory(NightmareVisionBackgroundGirls, function(args) {
			owner.requireActive();
			return new NightmareVisionBackgroundGirls(number(args, 0), number(args, 1), paths);
		}, null);
		interp.bindConstructorFactory(NightmareVisionBackgroundDancer, function(args) {
			owner.requireActive();
			return new NightmareVisionBackgroundDancer(number(args, 0), number(args, 1), paths);
		}, null);
	}

	static function bindClass(interp:NightmareVisionScriptInterp, name:String, path:String, type:Dynamic):Void {
		interp.variables.set(name, type);
		interp.bindImport(path, type);
		interp.sourceClassScope().bindRuntimeClass(path, type);
	}

	static inline function number(args:Array<Dynamic>, index:Int):Float
		return args.length > index && args[index] != null ? args[index] : 0;
}
