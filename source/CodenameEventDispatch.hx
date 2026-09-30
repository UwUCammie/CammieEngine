package;

/** Shared structured-event ABI, independent of rendering and script discovery. */
class CodenameEventDispatch {
	/** Keep a runtime ChartEvent object per collected native row. In-place script
	 * edits remain visible on replay; replacing wrapper.event only affects that
	 * dispatch, as in Codename. Serialized import provenance stays untouched. */
	public static function fromNative(native:Dynamic):Dynamic {
		if (native == null) return null;
		var metadata = CodenameEventMetadata.read([
			native.name, native.v1, native.v2, native.v3, Reflect.field(native, 'codename')
		], native.time);
		if (metadata == null) return null;
		var event:Dynamic = Reflect.field(native, 'codenameRuntimeEvent');
		if (event == null) {
			event = {name:metadata.name, time:metadata.time,
				params:haxe.Json.parse(haxe.Json.stringify(metadata.params)), global:metadata.global};
			Reflect.setField(native, 'codenameRuntimeEvent', event);
		}
		return event;
	}

	public static function valid(event:Dynamic):Bool {
		if (event == null || !Std.isOfType(Reflect.field(event, 'name'), String)
			|| Reflect.field(event, 'name') == ''
			|| !Std.isOfType(Reflect.field(event, 'params'), Array)) return false;
		var time:Dynamic = Reflect.field(event, 'time');
		return (Std.isOfType(time, Int) || Std.isOfType(time, Float))
			&& Math.isFinite(time);
	}

	/** Cancellation skips both the default action and post callback. The same
	 * wrapper (including script data and replacement event) reaches onPostEvent. */
	public static function run(event:Dynamic,
		notify:(String, CodenameGameEvent)->Void, execute:Dynamic->Void):Void {
		if (!valid(event)) throw '[codename-event] Invalid chart event';
		var payload = new CodenameGameEvent(event);
		notify('onEvent', payload);
		if (payload.cancelled) return;
		if (!valid(payload.event)) throw '[codename-event] Script produced an invalid chart event';
		execute(payload.event);
		notify('onPostEvent', payload);
	}

	/** Only known Codename built-ins may enter the native event switch. Custom
	 * names belong to scripts even when they collide with another engine's API. */
	public static function nativeRoute(event:Dynamic):Dynamic {
		if (!valid(event) || !CodenameScriptDiscovery.isBuiltInEvent(event.name)) return null;
		var route = CodenameImporter.routeCodenameEvent(event.name, event.params);
		return route == null ? null : {time:event.time, name:route.name,
			v1:route.v1, v2:route.v2, v3:route.v3};
	}

	/** Apply the donor Play Animation contract to every actor on its selected
	 * strumline. Call only after `run` has delivered mutable callbacks and
	 * accepted the event, so script edits and cancellation govern the default. */
	public static function applyPlayAnimation<T>(event:Dynamic,
		charactersAt:Int->Array<T>, hasAnimation:(T, String)->Bool,
		play:(T, String, Null<Bool>, Dynamic)->Void):Bool {
		if (event == null || Reflect.field(event, 'name') != 'Play Animation')
			return false;
		var rawParams:Dynamic = Reflect.field(event, 'params');
		if (!Std.isOfType(rawParams, Array)) return true;
		var params:Array<Dynamic> = cast rawParams;
		if (params.length < 2) return true;

		var rawLine:Dynamic = params[0];
		if (!Std.isOfType(rawLine, Int) && !Std.isOfType(rawLine, Float)) return true;
		var lineNumber:Float = rawLine;
		if (!Math.isFinite(lineNumber) || lineNumber < 0 || lineNumber != Math.floor(lineNumber)) return true;

		var rawAnimation:Dynamic = params[1];
		if (!Std.isOfType(rawAnimation, String)) return true;
		var animationName:String = cast rawAnimation;
		var force:Null<Bool> = params.length > 2 && Std.isOfType(params[2], Bool)
			? cast params[2] : null;
		var context:Dynamic = params.length > 3 ? params[3] : null;
		if (context == 'NONE') context = null;

		var characters = charactersAt == null ? null : charactersAt(Std.int(lineNumber));
		if (characters != null && hasAnimation != null && play != null)
			for (character in characters)
				if (character != null && hasAnimation(character, animationName))
					play(character, animationName, force, context);
		return true;
	}
}
