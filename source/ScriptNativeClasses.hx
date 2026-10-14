package;

/** One entry of the shared script class catalogue. */
typedef ScriptNativeClass = {
	var name:String;
	var path:String;
	var value:Dynamic;
}

/**
	Plain Flixel, OpenFL and Haxe classes that every script layer hands out under
	the same name. Each layer seeds these first and then puts its own adapters
	(owner sprites, colour facades, FlxG views) on top, so a class only lives in
	one list and the layers stop drifting apart. Naming the classes here also
	keeps them from being removed by dead code elimination.
*/
@:keep
class ScriptNativeClasses {
	static var cached:Array<ScriptNativeClass>;

	public static function all():Array<ScriptNativeClass> {
		if (cached != null) return cached;
		cached = [
			entry('Std', 'Std', Std),
			entry('Math', 'Math', Math),
			entry('StringTools', 'StringTools', StringTools),
			entry('StringMap', 'haxe.ds.StringMap', haxe.ds.StringMap),
			entry('IntMap', 'haxe.ds.IntMap', haxe.ds.IntMap),
			entry('ObjectMap', 'haxe.ds.ObjectMap', haxe.ds.ObjectMap),
			entry('FlxObject', 'flixel.FlxObject', flixel.FlxObject),
			entry('FlxMath', 'flixel.math.FlxMath', flixel.math.FlxMath),
			entry('FlxAngle', 'flixel.math.FlxAngle', flixel.math.FlxAngle),
			entry('FlxRect', 'flixel.math.FlxRect', flixel.math.FlxRect),
			entry('FlxTimer', 'flixel.util.FlxTimer', flixel.util.FlxTimer),
			entry('FlxSort', 'flixel.util.FlxSort', flixel.util.FlxSort),
			entry('FlxStringUtil', 'flixel.util.FlxStringUtil', flixel.util.FlxStringUtil),
			entry('FlxSpriteUtil', 'flixel.util.FlxSpriteUtil', flixel.util.FlxSpriteUtil),
			entry('FlxTween', 'flixel.tweens.FlxTween', flixel.tweens.FlxTween),
			entry('FlxEase', 'flixel.tweens.FlxEase', flixel.tweens.FlxEase),
			entry('FlxFlicker', 'flixel.effects.FlxFlicker', flixel.effects.FlxFlicker),
			entry('FlxEmitter', 'flixel.effects.particles.FlxEmitter', flixel.effects.particles.FlxEmitter.FlxTypedEmitter),
			entry('FlxBar', 'flixel.ui.FlxBar', flixel.ui.FlxBar),
			entry('FlxBarFillDirection', 'flixel.ui.FlxBar.FlxBarFillDirection', flixel.ui.FlxBar.FlxBarFillDirection),
			entry('FlxBackdrop', 'flixel.addons.display.FlxBackdrop', flixel.addons.display.FlxBackdrop),
			entry('FlxTiledSprite', 'flixel.addons.display.FlxTiledSprite', flixel.addons.display.FlxTiledSprite),
			entry('FlxTrail', 'flixel.addons.effects.FlxTrail', flixel.addons.effects.FlxTrail),
			entry('ShaderFilter', 'openfl.filters.ShaderFilter', openfl.filters.ShaderFilter)
		];
		return cached;
	}

	/** Seed bare names and, when the layer resolves imports itself, their qualified paths. */
	public static function seed(setName:(String, Dynamic)->Void, ?bindPath:(String, Dynamic)->Void):Void {
		for (item in all()) {
			setName(item.name, item.value);
			if (bindPath != null && item.path != item.name) bindPath(item.path, item.value);
		}
	}

	static inline function entry(name:String, path:String, value:Dynamic):ScriptNativeClass
		return {name:name, path:path, value:value};
}
