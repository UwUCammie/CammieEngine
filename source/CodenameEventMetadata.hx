package;

import haxe.Json;

/** Optional native event row[4] for a converted Codename chart event.
 * row[0..3] remain [nativeName, v1, v2, v3]. The group owns the time.
 * `id` is source:ordinal within one difficulty, never a donor path. Runtime
 * readers must call read() so edited or malformed rows cannot claim an old
 * authored event. The chart editor updates time-only moves and removes this
 * slot when native name/values are changed by hand. */
class CodenameEventMetadata {
	public static inline var VERSION:Int = 1;

	public static function routeFingerprint(time:Float, row:Array<Dynamic>):String {
		return Json.stringify([time, row[0], row[1], row[2], row[3]]);
	}

	public static function create(name:String, time:Float, params:Array<Dynamic>,
			source:String, order:Int, global:Bool, row:Array<Dynamic>):Dynamic {
		if ((source != 'chart' && source != 'shared') || order < 0)
			throw '[codename-event] Invalid source identity';
		return {
			engine:'codename', version:VERSION, id:source + ':' + order,
			source:source, order:order, name:name, time:time,
			params:Json.parse(Json.stringify(params == null ? [] : params)),
			global:global, route:routeFingerprint(time, row)
		};
	}

	public static function marked(row:Array<Dynamic>):Bool {
		return row != null && row.length > 4 && row[4] != null
			&& Reflect.field(row[4], 'engine') == 'codename';
	}

	/** Return null unless both authored payload and native route still agree. */
	public static function read(row:Array<Dynamic>, time:Float):Dynamic {
		if (!marked(row) || row.length < 5 || Math.isNaN(time)) return null;
		var value:Dynamic = row[4];
		var source:Dynamic = Reflect.field(value, 'source');
		var order:Dynamic = Reflect.field(value, 'order');
		var name:Dynamic = Reflect.field(value, 'name');
		var authoredTime:Dynamic = Reflect.field(value, 'time');
		var global:Dynamic = Reflect.field(value, 'global');
		if (Reflect.field(value, 'version') != VERSION
			|| (source != 'chart' && source != 'shared')
			|| !Std.isOfType(order, Int) || order < 0
			|| Reflect.field(value, 'id') != source + ':' + order
			|| !Std.isOfType(name, String) || name == ''
			|| !(Std.isOfType(authoredTime, Int) || Std.isOfType(authoredTime, Float))
			|| authoredTime != time || !Std.isOfType(global, Bool)
			|| !Std.isOfType(Reflect.field(value, 'params'), Array)
			|| Reflect.field(value, 'route') != routeFingerprint(time, row)) return null;
		return value;
	}

	public static function moved(value:Dynamic, time:Float, row:Array<Dynamic>):Dynamic {
		var updated = Reflect.copy(value);
		Reflect.setField(updated, 'time', time);
		Reflect.setField(updated, 'route', routeFingerprint(time, row));
		return updated;
	}

	/** Distinct authored rows may intentionally share every native route slot. */
	public static function dedupeKey(value:Dynamic):String {
		return Json.stringify([Reflect.field(value, 'id'), Reflect.field(value, 'source'),
			Reflect.field(value, 'name'), Reflect.field(value, 'time'),
			Reflect.field(value, 'params'), Reflect.field(value, 'global'), Reflect.field(value, 'route')]);
	}
}
