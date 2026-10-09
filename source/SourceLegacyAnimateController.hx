package;

/** Playback contract of flxanimate 3.0.4, independent of the shared renderer.
 * Render callbacks receive a symbol timeline index and instance translation.
 * Source: official flxanimate 3.0.4 archive, FlxAnim.hx. */
@:keep
class SourceLegacyAnimateController {
	public var metadata(default, null):{name:String, frameRate:Float};
	public var isPlaying(default, null):Bool = false;
	public var onComplete:Void->Void;
	public var framerate:Float = 0;
	public var reversed(get, set):Bool;
	public var curFrame(get, set):Int;
	public var length(get, never):Int;
	public var finished(get, never):Bool;
	public var currentName(default, null):String;
	public var instanceX(get, never):Float;
	public var instanceY(get, never):Float;
	var symbols:Map<String, {length:Int, frame:Int}> = [];
	var definitions:Map<String, {symbol:String, indices:Null<Array<Int>>, frameRate:Float, looped:Bool, single:Bool, reverse:Bool, x:Float, y:Float, frame:Int}> = [];
	var selected:{symbol:String, indices:Null<Array<Int>>, frameRate:Float, looped:Bool, single:Bool, reverse:Bool, x:Float, y:Float, frame:Int};
	var mainSymbol:String;
	var stageDefinition:Dynamic;
	public var stageSelected(get, never):Bool;
	function get_stageSelected():Bool return selected == stageDefinition;
	var tick:Float = 0;
	var render:String->Int->Void;
	var requireActive:Void->Void;
	var report:String->Void;
	var released:Bool = false;

	public function new(render:String->Int->Void, requireActive:Void->Void, report:String->Void) {
		this.render = render; this.requireActive = requireActive; this.report = report;
	}
	function active():Void {
		if (released) throw '[legacy-animate] Animation controller has been destroyed';
		requireActive();
	}
	public function load(name:String, fps:Float, main:String, inventory:Array<{name:String, length:Int}>, firstFrame:Int = 0, loop:String = "LP", symbolType:String = "G"):Void {
		active();
		symbols.clear(); definitions.clear(); tick = 0; isPlaying = false;
		for (symbol in inventory) {
			if (symbol.length <= 0) throw '[legacy-animate] Empty symbol timeline: ' + symbol.name;
			symbols.set(symbol.name, {length:symbol.length, frame:0});
		}
		if (!symbols.exists(main)) throw '[legacy-animate] Missing main symbol: ' + main;
		metadata = {name:name, frameRate:fps}; framerate = fps; mainSymbol = main;
		var mode = loop == null ? "LP" : loop.split("R")[0];
		if (symbolType == "MC" || symbolType == "movieclip") mode = "LP";
		if (symbolType == "B" || symbolType == "button") mode = "SF";
		selected = {symbol:main, indices:null, frameRate:fps,
			looped:mode != "PO" && mode != "playonce" && mode != "SF" && mode != "singleframe",
			single:mode == "SF" || mode == "singleframe", reverse:loop != null && loop.indexOf("R") >= 0,
			x:0, y:0, frame:0};
		stageDefinition = selected;
		currentName = '';
		curFrame = firstFrame;
	}
	public function addBySymbol(name:String, prefix:String, frameRate:Float = 0, looped:Bool = true, x:Float = 0, y:Float = 0):Void {
		active();
		var exact = StringTools.endsWith(prefix, "\\");
		var key = exact ? prefix.substr(0, prefix.length - 1) : prefix;
		for (symbol in symbols.keys()) if (exact ? symbol == key : StringTools.startsWith(symbol, key)) {
			definitions.set(name, {symbol:symbol, indices:null, frameRate:frameRate, looped:looped, single:false, reverse:false, x:x, y:y, frame:0});
			return;
		}
		report('[legacy-animate] No symbol found: ' + prefix);
	}
	public function addBySymbolIndices(name:String, symbol:String, indices:Array<Int>, frameRate:Float = 0,
		looped:Bool = true, x:Float = 0, y:Float = 0):Void {
		active();
		if (!symbols.exists(symbol)) {report('[legacy-animate] Unknown symbol: ' + symbol); return;}
		if (indices == null || indices.length == 0) throw '[legacy-animate] Animation indices must not be empty';
		for (index in indices) if (index < 0 || index >= symbols.get(symbol).length)
			throw '[legacy-animate] Index outside symbol timeline: ' + index;
		definitions.set(name, {symbol:symbol, indices:indices.copy(), frameRate:frameRate, looped:looped, single:false, reverse:false, x:x, y:y, frame:0});
	}
	public function addByAnimIndices(name:String, indices:Array<Int>, frameRate:Float = 0):Void
		addBySymbolIndices(name, mainSymbol, indices, frameRate, stageDefinition.looped);
	public function play(name:String = '', force:Bool = false, reverse:Bool = false, frame:Int = 0):Void {
		active();
		if (selected == null) throw '[legacy-animate] No atlas loaded';
		pause();
		if (name != null && name != '') {
			var next = definitions.get(name);
			if (next == null && symbols.exists(name))
				next = selected.symbol == name && selected.indices == null ? selected : {symbol:name, indices:null, frameRate:metadata.frameRate, looped:true, single:false, reverse:false, x:0, y:0, frame:0};
			if (next == null) {report('[legacy-animate] No animation found: ' + name); isPlaying = true; return;}
			framerate = next.frameRate == 0 ? metadata.frameRate : next.frameRate;
			// Historical play resets the OLD symbol before changing instances.
			if (selected != next) curFrame = reverse ? frame - length : frame;
			selected = next; currentName = name;
		}
		if (force || finished) curFrame = reverse ? frame - length : frame;
		reversed = reverse; isPlaying = true; sync();
	}
	public function pause():Void {active(); isPlaying = false;}
	public function stop():Void {pause(); if (selected != null) curFrame = 0;}
	public function update(elapsed:Float):Void {
		active();
		if (selected == null || !isPlaying || finished || framerate == 0) return;
		// Negative/non-finite rates made the historical while-loop nonterminating.
		if (!Math.isFinite(framerate) || framerate < 0)
			throw '[legacy-animate] Frame rate must be finite and nonnegative';
		if (!Math.isFinite(elapsed) || elapsed < 0) throw '[legacy-animate] Invalid elapsed time';
		var delay = 1 / framerate;
		tick += elapsed;
		while (tick > delay) {curFrame += reversed ? -1 : 1; tick -= delay;}
		if (finished) {
			if (onComplete != null) onComplete();
			// Preserve source order: completion precedes pause, including reentrant play.
			if (!released) pause();
		}
	}
	function get_length():Int return selected == null ? 0 : selected.indices == null
		? symbols.get(selected.symbol).length : selected.indices.length;
	function get_curFrame():Int return selected == null ? 0 : selected.indices == null ? symbols.get(selected.symbol).frame : selected.frame;
	function set_curFrame(value:Int):Int {
		active();
		if (selected == null) throw '[legacy-animate] No atlas loaded';
		var result = selected.single ? value : selected.looped ? value % length : Std.int(Math.max(0, Math.min(length - 1, value)));
		if (selected.indices == null) symbols.get(selected.symbol).frame = result; else selected.frame = result;
		sync(); return result;
	}
	function get_finished():Bool return selected != null && !selected.looped && !selected.single && (reversed ? curFrame == 0 : curFrame >= length - 1);
	function get_reversed():Bool return selected != null && selected.reverse;
	function set_reversed(value:Bool):Bool {
		active();
		if (selected == null) throw '[legacy-animate] No atlas loaded';
		return selected.reverse = value;
	}
	function get_instanceX():Float return selected == null ? 0 : selected.x;
	function get_instanceY():Float return selected == null ? 0 : selected.y;
	function sync():Void {
		if (selected == null) return;
		var frame = curFrame;
		// Keep the negative source frame observable. Renderers must not dereference
		// a negative index; no valid source frame exists at that index.
		render(selected.symbol, frame < 0 || frame >= length ? -1 : selected.indices == null ? frame : selected.indices[frame]);
	}
	public function destroy():Void {
		if (released) return;
		released = true; isPlaying = false; onComplete = null;
		render = null; requireActive = null; report = null; selected = null; stageDefinition = null;
		symbols.clear(); definitions.clear();
	}
}
