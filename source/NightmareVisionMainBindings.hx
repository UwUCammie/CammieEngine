package;

import openfl.display.Sprite;

/** Owner-local reflection bindings for the statics on the pinned source Main. */
@:keep
class NightmareVisionMainBindings {
	static final SOURCE_MAIN_FIELDS:Array<String> = [
		'PSYCH_VERSION', 'NMV_VERSION', 'FUNKIN_VERSION', 'startMeta', 'main', 'onResize', 'resetSpriteCache'
	];

	public static function install(interp:NightmareVisionScriptInterp, startMeta:Dynamic,
		runtime:NightmareVisionMainRuntime):Void {
		if (interp == null || startMeta == null || runtime == null)
			throw '[nightmare-vision-main] Main bindings require captured startMeta and runtime';
		var type:Dynamic = NightmareVisionMainMetadata;
		var scope = interp.sourceClassScope();
		interp.variables.set('Main', type);
		interp.bindImport('Main', type);
		scope.bindRuntimeClass('Main', type);
		scope.bindStaticField(type, 'PSYCH_VERSION', function() return NightmareVisionMainMetadata.PSYCH_VERSION);
		scope.bindStaticField(type, 'NMV_VERSION', function() return NightmareVisionMainMetadata.NMV_VERSION);
		scope.bindStaticField(type, 'FUNKIN_VERSION', function() return NightmareVisionMainMetadata.FUNKIN_VERSION);
		// Donor startMeta is a final struct reference with mutable fields.
		scope.bindStaticField(type, 'startMeta', function() return startMeta);
		scope.bindStaticField(type, 'resetSpriteCache', function() return function(sprite:Sprite):Void {
			runtime.resetSpriteCacheForOwner(sprite);
		});
		// Source onResize is private to Haxe code, but remains reachable through
		// Reflect/Type in the source interpreter, so route it to this owner.
		scope.bindStaticField(type, 'onResize', function() return function(width:Int, height:Int):Void {
			runtime.onResize(width, height);
		});
		scope.bindStaticField(type, 'main', function() return function():Void {
			unsupported('Main.main() cannot create a second OpenFL application in an imported source session');
		});
		// Constructor syntax has its own dispatch path in the source interpreter.
		// Bind it explicitly so `new Main()` cannot silently instantiate metadata.
		var unsupportedConstructor:Array<Dynamic>->Dynamic = function(_args:Array<Dynamic>):Dynamic {
			return unsupported('new Main() requires the original app host and is unsupported in an imported source session');
		};
		interp.bindConstructorFactory(type, unsupportedConstructor, null);
		scope.bindStaticField(type, 'new', function() return function():Dynamic {
			return unsupportedConstructor([]);
		});

		// Main.onResize is private in the donor. Keep its field discoverable to
		// owner-local Reflect and Type calls without changing process-global APIs.
		scope.bindStaticField(Reflect, 'fields', function() return function(value:Dynamic):Array<String> {
			var fields = Reflect.fields(value);
			return value == type ? appendMainFields(fields) : fields;
		});
		scope.bindStaticField(Reflect, 'hasField', function() return function(value:Dynamic, field:String):Bool {
			if (value == type && SOURCE_MAIN_FIELDS.indexOf(field) >= 0) return true;
			return Reflect.hasField(value, field);
		});
		scope.bindStaticField(Type, 'getClassFields', function() return function(value:Class<Dynamic>):Array<String> {
			var fields = Type.getClassFields(value);
			return value == type ? appendMainFields(fields) : fields;
		});
	}

	static function appendMainFields(fields:Array<String>):Array<String> {
		var result = fields == null ? [] : fields.copy();
		for (field in SOURCE_MAIN_FIELDS) if (result.indexOf(field) < 0) result.push(field);
		return result;
	}

	static function unsupported(message:String):Dynamic
		throw '[nightmare-vision-main] ' + message;
}
