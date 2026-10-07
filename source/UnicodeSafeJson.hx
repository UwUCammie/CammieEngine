package;

/**
 * TJSON-compatible printer that writes UTF-16 surrogate units as JSON escapes.
 * This avoids target StringBuf implementations replacing isolated units while
 * retaining TJSON's object traversal, class hooks, references, and formatting.
 */
class UnicodeSafeJson extends tjson.TJSON.TJSONEncoder {
	public static function stringify(value:Dynamic, ?fancy:Bool = true):String {
		return new UnicodeSafeJson().doEncode(value, fancy ? "fancy" : null);
	}

	/** Standard JSON form for persisted engine metadata that must not use TJSON's
	 * class markers or object-reference extensions. */
	public static function stringifyStandard(value:Dynamic, ?space:String):String {
		return UnicodeSafeStandardJsonPrinter.stringify(value, space);
	}

	public function new() {
		super();
	}

	override function encodeValue(value:Dynamic, style:tjson.TJSON.EncodeStyle, depth:Int):String {
		if (Std.isOfType(value, String)) return encodeString(cast value);
		return super.encodeValue(value, style, depth);
	}

	static function encodeString(value:String):String {
		return UnicodeSafeStandardJsonPrinter.quoteString(value);
	}
}

@:access(haxe.format.JsonPrinter)
private class UnicodeSafeStandardJsonPrinter extends haxe.format.JsonPrinter {
	public static function stringify(value:Dynamic, ?space:String):String {
		var printer = new UnicodeSafeStandardJsonPrinter(null, space);
		printer.write("", value);
		return printer.buf.toString();
	}

	public static function quoteString(value:String):String {
		var printer = new UnicodeSafeStandardJsonPrinter(null, null);
		printer.quote(value);
		return printer.buf.toString();
	}

	function new(replacer:(key:Dynamic, value:Dynamic) -> Dynamic, space:String) {
		super(replacer, space);
	}

	override function quote(value:String):Void {
		addChar('"'.code);
		var runStart = 0;
		var index = 0;
		while (index < value.length) {
			var code = StringTools.unsafeCodeAt(value, index);
			var escaped:Null<String> = switch (code) {
				case '"'.code: '\\"';
				case '\\'.code: '\\\\';
				case '\n'.code: '\\n';
				case '\r'.code: '\\r';
				case '\t'.code: '\\t';
				default:
					if (code < 0x20 || (code >= 0xD800 && code <= 0xDFFF))
						'\\u' + StringTools.hex(code, 4).toUpperCase();
					else
						null;
			};
			if (escaped != null) {
				add(value.substr(runStart, index - runStart));
				add(escaped);
				runStart = index + 1;
			}
			index++;
		}
		add(value.substr(runStart, value.length - runStart));
		addChar('"'.code);
	}
}
