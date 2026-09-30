package;

/** Selected-owner metadata with live access to the native chart.
 * The interpreter forwards field access here; native charts are never amended
 * with metadata from a foreign engine or a previous PlayState. */
class CodenameSongView {
	final chart:Void->Dynamic;
	var metadata:Dynamic;
	public function new(chart:Void->Dynamic, metadata:Dynamic) {
		this.chart = chart;
		this.metadata = metadata;
	}
	public function getField(name:String):Dynamic {
		return name == 'meta' ? metadata : Reflect.getProperty(chart(), name);
	}
	public function setField(name:String, value:Dynamic):Dynamic {
		if (name == 'meta') metadata = value;
		else Reflect.setProperty(chart(), name, value);
		return value;
	}
}
