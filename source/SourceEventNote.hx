package;

/** Live source-engine view over the engine's native song-event row. */
class SourceEventNote {
	final row:Dynamic;

	@:keep public var strumTime(get, set):Float;
	@:keep public var event(get, set):String;
	@:keep public var value1(get, set):String;
	@:keep public var value2(get, set):String;

	/** Keep one backing object so a retained callback reference observes writes
	 * made through either the view or the native event pipeline. */
	public function new(row:Dynamic, noteOffset:Float = 0) {
		this.row = row;
		if (row != null && noteOffset != 0) {
			var rawTime:Dynamic = Reflect.field(row, 'time');
			var time = rawTime == null ? Math.NaN : Std.parseFloat(Std.string(rawTime));
			if (!Math.isNaN(time)) Reflect.setField(row, 'time', time + noteOffset);
		}
	}

	function get_strumTime():Float {
		if (row == null) return 0;
		var value:Dynamic = Reflect.field(row, 'time');
		return value == null ? 0 : Std.parseFloat(Std.string(value));
	}

	function set_strumTime(value:Float):Float {
		if (row != null) Reflect.setField(row, 'time', value);
		return value;
	}

	function get_event():String return readString('name');
	function set_event(value:String):String {
		write('name', value);
		return value;
	}

	function get_value1():String return readString('v1');
	function set_value1(value:String):String {
		write('v1', value);
		return value;
	}

	function get_value2():String return readString('v2');
	function set_value2(value:String):String {
		write('v2', value);
		return value;
	}

	function readString(name:String):String {
		if (row == null) return '';
		var value:Dynamic = Reflect.field(row, name);
		return value == null ? null : Std.string(value);
	}

	function write(name:String, value:Dynamic):Void {
		if (row != null) Reflect.setField(row, name, value);
	}
}
