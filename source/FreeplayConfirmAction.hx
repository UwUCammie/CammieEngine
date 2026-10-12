package;

/** Elapsed-time, one-shot confirmation owned by a concrete menu selection. */
class FreeplayConfirmAction {
	var gate = new SelectionActionGate();
	var token:Int = 0;
	var remaining:Float = 0;
	var ownerGeneration:Int = -1;
	public var active(get, never):Bool;
	function get_active():Bool return token != 0;
	public function new() {}
	public function start(key:String, generation:Int, duration:Float):Void {
		token = gate.armFor(key, generation);
		ownerGeneration = generation;
		remaining = Math.isFinite(duration) ? Math.max(0.35, Math.min(2, duration)) : 0.35;
	}
	public function cancel():Void { token = 0; remaining = 0; gate.clear(); }
	public function advance(key:String, generation:Int, elapsed:Float):Bool {
		if (!active) return false;
		if (generation != ownerGeneration || !gate.isArmedFor(key)) { cancel(); return false; }
		if (Math.isFinite(elapsed) && elapsed > 0) remaining -= elapsed;
		if (remaining > 0) return false;
		var ready = gate.consumeFor(key, generation, token);
		cancel();
		return ready;
	}
}
