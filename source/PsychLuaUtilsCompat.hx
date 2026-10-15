package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.tweens.FlxTween.FlxTweenType;
import openfl.display.BlendMode;

/**
	The `psychlua.LuaUtils` helpers Psych 0.7 HScript files import for their own
	tweens and cameras. Each one answers through the engine's existing parser or
	camera route, so a script gets the same ease, blend or camera a Lua call with
	the same name would get.
**/
@:access(PlayState)
class PsychLuaUtilsCompat {
	public static function getTweenEaseByString(?ease:String = ''):Float->Float
		return CoolUtil.getEaseFromString(ease);

	public static function getTweenTypeByString(?type:String = ''):FlxTweenType {
		return switch (type == null ? '' : StringTools.trim(type).toLowerCase()) {
			case 'backward': FlxTweenType.BACKWARD;
			case 'looping' | 'loop': FlxTweenType.LOOPING;
			case 'persist': FlxTweenType.PERSIST;
			case 'pingpong': FlxTweenType.PINGPONG;
			default: FlxTweenType.ONESHOT;
		};
	}

	public static function blendModeFromString(blend:String):BlendMode
		return CoolUtil.getBlendFromString(blend);

	/** Game, HUD and Other by their Psych names, then a camera the scripts stored
	 * under that tag, else the game camera. */
	public static function cameraFromString(cam:String):FlxCamera {
		var state = PlayState.instance;
		return state == null ? FlxG.camera : state.compatCameraForName(cam);
	}

	public static function isOfTypes(value:Dynamic, types:Array<Dynamic>):Bool {
		if (types != null)
			for (type in types)
				if (Std.isOfType(value, type))
					return true;
		return false;
	}

	/** Psych's duck-typed map test: anything with `exists` and `keyValueIterator`. */
	public static function isMap(variable:Dynamic):Bool {
		if (variable == null)
			return false;
		if (Std.isOfType(variable, haxe.ds.StringMap) || Std.isOfType(variable, haxe.ds.IntMap)
			|| Std.isOfType(variable, haxe.ds.ObjectMap))
			return true;
		return Reflect.field(variable, 'exists') != null && Reflect.field(variable, 'keyValueIterator') != null;
	}

	public static function isLuaSupported(value:Dynamic):Bool
		return value == null || isOfTypes(value, [Bool, Int, Float, String, Array]) || Type.typeof(value) == Type.ValueType.TObject;

	/** Psych's `a.b.c` read on one object, maps allowed when asked. */
	public static function getGroupStuff(leArray:Dynamic, variable:String, allowMaps:Bool = false):Dynamic {
		// Psych's read also steps through maps on the way when they are allowed.
		var target = groupTarget(leArray, variable, allowMaps);
		var last = lastSegment(variable);
		if (allowMaps && isMap(target))
			return mapCall(target, 'get', [last]);
		return target == null ? null : Reflect.getProperty(target, last);
	}

	public static function setGroupStuff(leArray:Dynamic, variable:String, value:Dynamic, allowMaps:Bool = false):Dynamic {
		// Psych's write only treats the final holder as a map.
		var target = groupTarget(leArray, variable, false);
		var last = lastSegment(variable);
		if (allowMaps && isMap(target))
			mapCall(target, 'set', [last, value]);
		else if (target != null)
			Reflect.setProperty(target, last, value);
		return value;
	}

	static function groupTarget(leArray:Dynamic, variable:String, allowMaps:Bool):Dynamic {
		var split = variable == null ? [] : variable.split('.');
		var target = leArray;
		if (split.length > 1)
			for (i in 0...split.length - 1)
				target = target == null ? null : allowMaps && isMap(target) ? mapCall(target, 'get', [split[i]])
					: Reflect.getProperty(target, split[i]);
		return target;
	}

	/**
		isMap also accepts objects that only look like maps, so they are called
		dynamically; casting one to IMap is not safe on native builds.
	**/
	static function mapCall(target:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		var method = Reflect.field(target, name);
		return Reflect.isFunction(method) ? Reflect.callMethod(target, method, args) : null;
	}

	static function lastSegment(variable:String):String {
		if (variable == null)
			return '';
		var dot = variable.lastIndexOf('.');
		return dot < 0 ? variable : variable.substr(dot + 1);
	}

	/**
		`game`, `this` and `instance` are the song; any other name is a script
		variable of the current state first, then a field of that state, as in
		Psych. During a song the name goes through the same lookup Lua's
		getProperty uses (PlayState.getLuaObject), so objects tagged by Lua or
		HScript are found here too.
	**/
	public static function getObjectDirectly(objectName:String, allowMaps:Bool = false):Dynamic {
		switch (objectName) {
			case 'this' | 'instance' | 'game':
				return PlayState.instance;
			default:
				var state = Std.downcast(FlxG.state, MusicBeatState);
				if (state == null)
					return null;
				var game = PlayState.instance;
				if (game != null && state == game) {
					var tagged:Dynamic = game.getLuaObject(objectName, true);
					if (tagged != null)
						return tagged;
				}
				var found:Dynamic = state.variables.get(objectName);
				return found != null ? found : Reflect.getProperty(state, objectName);
		}
	}

	/** Lua's type numbers as names, the values Psych's Lua bridge reports. */
	public static function typeToString(type:Int):String {
		return switch (type) {
			case 1: 'boolean';
			case 3: 'number';
			case 4: 'string';
			case 5: 'table';
			case 6: 'function';
			default: type <= 0 ? 'nil' : 'unknown';
		};
	}
}
