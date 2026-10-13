package;

/** A line an imported script draws only to name the engine it was written for,
 * such as "Psych Engine v0.7.0". This engine is not that one, so the label is
 * left blank. The text object itself stays, as scripts lay other things out
 * against it. */
class SourceEngineWatermark {
	static var label = ~/^[^a-z0-9]*([a-z0-9'.]+ ){0,3}engine[^a-z0-9]*(v|ver|version)?[^a-z0-9]*[0-9]+(\.[0-9a-z]+)*[^a-z0-9]*$/i;

	/** True when the whole text is an engine name followed by a version. */
	public static function matches(text:String):Bool {
		if (text == null) return false;
		var line = StringTools.trim(text);
		return line.length <= 48 && line.indexOf('\n') < 0 && label.match(line);
	}

	public static function clean(text:Dynamic):Dynamic
		return Std.isOfType(text, String) && matches(cast text) ? '' : text;
}
