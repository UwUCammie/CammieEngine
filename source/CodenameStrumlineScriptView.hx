package;

import flixel.util.FlxSignal.FlxTypedSignal;

/** Script-facing Codename fields shared with a native receptor group without
 * replacing its geometry or Flixel member API. */
@:keep
class CodenameStrumlineScriptView<T> {
	public var onMiss:FlxTypedSignal<Dynamic->Void>;
	var inputLine:CodenameInputLine<T>;
	var cpuValue:Bool = false;
	var cpuWasSet:Bool = false;

	public var cpu(get, set):Bool;
	/** Scripts use `cpu` to detect who is receiving the judgment. Include the
	 * local autoplay/demo mode while preserving the source line's own ownership. */
	function get_cpu():Bool
		return inputLine == null || inputLine.released ? cpuValue
			: (inputLine.cpu || inputLine.botplay);

	function set_cpu(value:Bool):Bool {
		cpuValue = value;
		cpuWasSet = true;
		if (inputLine != null && !inputLine.released) inputLine.cpu = value;
		return value;
	}

	public function new(?onMiss:FlxTypedSignal<Dynamic->Void>) {
		this.onMiss = onMiss == null
			? new FlxTypedSignal<Dynamic->Void>() : onMiss;
	}

	/** Bind after the source line is initialized. A script assignment made
	 * earlier on the native group takes precedence over the source default. */
	public function bind(line:CodenameInputLine<T>):Void {
		if (line == null || line.released || inputLine == line) return;
		inputLine = line;
		if (cpuWasSet) inputLine.cpu = cpuValue;
		else cpuValue = inputLine.cpu;
	}

	/** Drop the source-line reference at state teardown. CodenameInputLine
	 * clears listeners from the shared signal when it is released. */
	public function unbind(?line:CodenameInputLine<T>):Void {
		if (line != null && inputLine != line) return;
		inputLine = null;
		cpuValue = false;
		cpuWasSet = false;
	}
}
