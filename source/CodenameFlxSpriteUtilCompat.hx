package;

import flixel.FlxSprite;
import flixel.util.FlxSpriteUtil;
import hscript.ScriptClass;

@:access(hscript.ScriptClass)
/** Pass owner script sprites to native FlxSpriteUtil without losing their
 * script identity when a drawing method returns its sprite for chaining. */
class CodenameFlxSpriteUtilCompat {
	public static function facade():Dynamic {
		var result:Dynamic = {};
		for (name in Type.getClassFields(FlxSpriteUtil)) {
			var nativeMethod:Dynamic = Reflect.field(FlxSpriteUtil, name);
			if (!Reflect.isFunction(nativeMethod)) {
				Reflect.setField(result, name, nativeMethod);
				continue;
			}
			Reflect.setField(result, name, wrap(nativeMethod));
		}
		// Keep the two draw calls needed by owner textbox classes reflectable
		// even when a native release compiler strips unused class fields.
		Reflect.setField(result, 'drawRoundRect', wrap(FlxSpriteUtil.drawRoundRect));
		Reflect.setField(result, 'drawTriangle', wrap(FlxSpriteUtil.drawTriangle));
		return result;
	}

	static function wrap(nativeMethod:Dynamic):Dynamic {
		return Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
				if (args == null || args.length == 0 || !Std.isOfType(args[0], ScriptClass))
					return Reflect.callMethod(FlxSpriteUtil, nativeMethod, args);
				var proxy:ScriptClass = cast args[0];
				if (proxy._classScope == null)
					throw '[codename-flx-sprite-util] script sprite has no owner scope';
				var nativeSprite = proxy._classScope.unwrapNativeArgument(proxy);
				if (!Std.isOfType(nativeSprite, FlxSprite))
					throw '[codename-flx-sprite-util] script argument does not wrap a FlxSprite';
				var nativeArgs = args.copy();
				nativeArgs[0] = nativeSprite;
				var returned = Reflect.callMethod(FlxSpriteUtil, nativeMethod, nativeArgs);
				return returned == nativeSprite ? proxy : returned;
		});
	}
}
