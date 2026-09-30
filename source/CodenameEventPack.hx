package;

typedef CodenameEventPackData = {
	var eventName:String;
	var script:String;
	var schema:String;
	var iconBase64:Null<String>;
}

typedef CodenameEventPackResult = {
	var pack:Null<CodenameEventPackData>;
	var error:Null<String>;
}

/** Reader for Codename's compact custom-event package format.
	The Haxe payload is data here: this class never compiles or evaluates it. */
class CodenameEventPack {
	public static inline var SEPARATOR:String = '________PACKSEP________';
	static inline var MAX_PACK_CHARS:Int = 16 * 1024 * 1024;

	public static function decode(content:String, expectedEventName:String):CodenameEventPackResult {
		if (content == null || content.length == 0)
			return failure('empty-pack');
		if (content.length > MAX_PACK_CHARS)
			return failure('pack-too-large');

		var parts = content.split(SEPARATOR);
		if (parts.length != 3 && parts.length != 4)
			return failure('invalid-pack-sections');

		var scriptFile = StringTools.trim(parts[0]);
		if (!StringTools.endsWith(scriptFile.toLowerCase(), '.hx'))
			return failure('invalid-script-filename');
		var eventName = scriptFile.substr(0, scriptFile.length - 3);
		if (!safeEventName(eventName))
			return failure('unsafe-event-name');
		if (expectedEventName != null && expectedEventName != ''
			&& eventName.toLowerCase() != expectedEventName.toLowerCase())
			return failure('event-name-mismatch');

		var script = parts[1];
		if (StringTools.trim(script) == '')
			return failure('empty-script');

		var schema = parts[2];
		try {
			var parsed:Dynamic = haxe.Json.parse(schema);
			if (parsed == null || Std.isOfType(parsed, String) || Std.isOfType(parsed, Array))
				return failure('invalid-schema-root');
			var params:Dynamic = Reflect.field(parsed, 'params');
			if (params != null && !Std.isOfType(params, Array))
				return failure('invalid-schema-params');
		} catch (_:Dynamic) {
			return failure('invalid-schema-json');
		}

		return {
			pack: {
				eventName: eventName,
				script: script,
				schema: schema,
				iconBase64: parts.length == 4 ? parts[3] : null
			},
			error: null
		};
	}

	static function safeEventName(value:String):Bool {
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0;
	}

	static function failure(error:String):CodenameEventPackResult {
		return {pack:null, error:error};
	}
}
