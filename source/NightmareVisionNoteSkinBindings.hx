package;

/** Owner-local source NoteSkin import and constructor binding. */
@:keep
class NightmareVisionNoteSkinBindings {
	public static function install(interp:NightmareVisionScriptInterp, owner:String,
		resolve:String->NightmareVisionPaths):Void {
		if (interp == null || owner == null || resolve == null)
			throw '[nightmare-vision-note-skin] Invalid owner constructor binding';

		var skinType:Dynamic = NightmareVisionNoteSkin;
		interp.variables.set('NoteSkin', skinType);
		interp.bindImport('funkin.data.NoteSkin', skinType);
		interp.bindConstructorFactory(skinType, function(args:Array<Dynamic>):Dynamic {
			var paths = resolve(owner);
			if (paths == null)
				throw '[nightmare-vision-note-skin] No active owner paths: ' + owner;
			if (args == null || args.length == 0 || args[0] == null)
				throw '[nightmare-vision-note-skin] Source constructor requires a skin path';
			var name:Dynamic = args[0];
			if (!Std.isOfType(name, String))
				throw '[nightmare-vision-note-skin] Source skin path must be a string';
			var keys = constructorInt(args, 1, -1, 'keys');
			var id = constructorInt(args, 2, 0, 'id');
			return new NightmareVisionNoteSkin(paths, cast name, keys, id);
		}, null);
	}

	static function constructorInt(args:Array<Dynamic>, index:Int, fallback:Int, name:String):Int {
		if (index >= args.length || args[index] == null) return fallback;
		var value:Dynamic = args[index];
		var number:Float;
		if (Std.isOfType(value, Int)) number = cast value;
		else if (Std.isOfType(value, Float)) number = cast value;
		else throw '[nightmare-vision-note-skin] Source constructor ' + name + ' must be an integer';
		if (!Math.isFinite(number) || Math.isNaN(number) || number != Math.floor(number)
			|| number < -2147483648.0 || number > 2147483647.0)
			throw '[nightmare-vision-note-skin] Source constructor ' + name + ' must be an integer';
		return Std.int(number);
	}
}
