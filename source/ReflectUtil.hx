package;

/**
	V-Slice's reflection helper (funkin.util.ReflectUtil) for imported scripts.

	The field helpers are the plain Haxe Reflect calls V-Slice wraps. Class names
	are where the two games differ: scripts compare `getClassNameOf(FlxG.state)`
	against V-Slice's qualified names to find out which menu or substate is
	open, so the engine's equivalent screens answer with those names. Class
	lookup by name and instance creation are left out, the same as everywhere
	else imported scripts run, so a script cannot build engine objects it was
	never handed.
**/
@:keep
class ReflectUtil {
	/** Engine screen class -> the V-Slice class a script expects in its place. */
	static var compatNames:Map<String, String> = [
		'StoryMenuState' => 'funkin.ui.story.StoryMenuState',
		'FreeplayState' => 'funkin.ui.freeplay.FreeplayState',
		'MainMenuState' => 'funkin.ui.mainmenu.MainMenuState',
		'TitleState' => 'funkin.ui.title.TitleState',
		'PlayState' => 'funkin.play.PlayState',
		'PauseSubState' => 'funkin.play.PauseSubState',
		'GameOverSubstate' => 'funkin.play.GameOverSubState',
		// The engine's song-end results screen.
		'VictoryLoopState' => 'funkin.play.ResultState'
	];

	/**
		The name a V-Slice script should see for an engine class name. Only the
		last path segment is compared so the table holds whatever package the
		engine class lives in.
	**/
	public static function compatClassName(className:String):String {
		if (className == null)
			return null;
		var dot = className.lastIndexOf('.');
		var shortName = dot < 0 ? className : className.substr(dot + 1);
		var mapped = compatNames.get(shortName);
		return mapped == null ? className : mapped;
	}

	public static function getClassNameOf(obj:Dynamic):String {
		if (obj == null)
			return 'Unknown';
		if (Std.isOfType(obj, String)) {
			var text:String = cast obj;
			for (known in compatNames)
				if (known == text)
					return text;
			if (Type.resolveClass(text) != null)
				return text;
		}
		var cls = Type.getClass(obj);
		if (cls == null)
			return 'Unknown';
		return compatClassName(Type.getClassName(cls));
	}

	public static function getClassName(cls:Dynamic):String
		return cls == null ? 'Unknown' : compatClassName(Type.getClassName(cls));

	public static function getAnonymousField(obj:Dynamic, name:String):Dynamic
		return obj == null || name == null ? null : Reflect.field(obj, name);

	public static function field(obj:Dynamic, name:String):Dynamic
		return getAnonymousField(obj, name);

	public static function getField(obj:Dynamic, name:String):Dynamic
		return getAnonymousField(obj, name);

	public static function setAnonymousField(obj:Dynamic, name:String, value:Dynamic):Void
		if (obj != null && name != null) Reflect.setField(obj, name, value);

	public static function setField(obj:Dynamic, name:String, value:Dynamic):Void
		setAnonymousField(obj, name, value);

	public static function getProperty(obj:Dynamic, name:String):Dynamic
		return obj == null || name == null ? null : Reflect.getProperty(obj, name);

	public static function setProperty(obj:Dynamic, name:String, value:Dynamic):Void
		if (obj != null && name != null) Reflect.setProperty(obj, name, value);

	public static function hasAnonymousField(obj:Dynamic, name:String):Bool
		return obj != null && name != null && Reflect.hasField(obj, name);

	public static function hasField(obj:Dynamic, name:String):Bool
		return hasAnonymousField(obj, name);

	public static function deleteAnonymousField(obj:Dynamic, name:String):Bool
		return obj != null && name != null && Reflect.deleteField(obj, name);

	public static function delete(obj:Dynamic, name:String):Bool
		return deleteAnonymousField(obj, name);

	public static function getAnonymousFieldsOf(obj:Dynamic):Array<String>
		return obj == null ? [] : Reflect.fields(obj);

	public static function fields(obj:Dynamic):Array<String>
		return getAnonymousFieldsOf(obj);

	public static function getFieldsOf(obj:Dynamic):Array<String>
		return getAnonymousFieldsOf(obj);

	public static function copyAnonymousFieldsOf(obj:Dynamic):Dynamic
		return obj == null ? null : Reflect.copy(obj);

	public static function copy(obj:Dynamic):Dynamic
		return copyAnonymousFieldsOf(obj);

	public static function callMethod(obj:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		if (obj == null || name == null)
			return null;
		return Reflect.callMethod(obj, Reflect.field(obj, name), args == null ? [] : args);
	}

	public static function compare(valueA:Dynamic, valueB:Dynamic):Int
		return Reflect.compare(valueA, valueB);

	public static function compareValues(valueA:Dynamic, valueB:Dynamic):Int
		return Reflect.compare(valueA, valueB);

	public static function compareMethods(functionA:Dynamic, functionB:Dynamic):Bool
		return Reflect.compareMethods(functionA, functionB);

	public static function isEnumValue(value:Dynamic):Bool
		return Reflect.isEnumValue(value);

	public static function isFunction(value:Dynamic):Bool
		return Reflect.isFunction(value);

	public static function isObject(value:Dynamic):Bool
		return Reflect.isObject(value);

	public static function getClassFields(cls:Dynamic):Array<String>
		return cls == null ? [] : Type.getClassFields(cls);

	public static function getClassFieldsOf(obj:Dynamic):Array<String> {
		var cls = obj == null ? null : Type.getClass(obj);
		return cls == null ? [] : Type.getClassFields(cls);
	}

	public static function getInstanceFields(cls:Dynamic):Array<String>
		return cls == null ? [] : Type.getInstanceFields(cls);

	public static function getInstanceFieldsOf(obj:Dynamic):Array<String> {
		var cls = obj == null ? null : Type.getClass(obj);
		return cls == null ? [] : Type.getInstanceFields(cls);
	}

	public static function makeVarArgs(f:Array<Dynamic>->Dynamic):Dynamic
		return Reflect.makeVarArgs(f);
}
