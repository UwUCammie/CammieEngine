package nightmarevision.modchart;

typedef NightmareVisionModifierValueEvent = {
	var executionStep:Float;
	var sequence:Int;
	var modName:String;
	var player:Int;
	var endVal:Float;
	var endStep:Float;
	var style:Dynamic;
	var startVal:Null<Float>;
	var ignoreExecution:Bool;
	var finished:Bool;
	var isEase:Bool;
}

/**
	Pure value-event scheduler mirroring source EventTimeline's per-mod queues.
	Integrators should update this before the callback timeline: donor
	EventTimeline drains modifier events first and callback events afterward.
*/
class NightmareVisionModchartTimeline {
	public final registry:NightmareVisionModifierRegistry;
	public var modEvents(default, null):Map<String, Array<NightmareVisionModifierValueEvent>> = new Map();
	var queueOrder:Array<String> = [];
	var nextSequence:Int = 0;
	var destroyed:Bool = false;

	public function new(registry:NightmareVisionModifierRegistry) {
		if (registry == null) throw 'Nightmare Vision modifier timeline requires a registry';
		this.registry = registry;
		// Source EventTimeline has an empty schedule for every registered modifier
		// before any event is queued.
		for (definition in registry.definitions) {
			modEvents.set(definition.name, []);
			queueOrder.push(definition.name);
		}
	}

	public function queueSet(step:Float, modName:String, value:Float, player:Int = -1):Void {
		queue(step, modName, value, player, 0, 'linear', false);
	}

	public function queueSetP(step:Float, modName:String, percent:Float, player:Int = -1):Void
		queueSet(step, modName, percent * 0.01, player);

	public function queueEase(step:Float, endStep:Float, modName:String, value:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startValue:Float):Void {
		// Source ModManager accepts startVal but omits it when constructing EaseEvent;
		// EaseEvent therefore captures the live value on its first due update.
		queue(step, modName, value, player, endStep, style, true);
	}

	public function queueEaseP(step:Float, endStep:Float, modName:String, percent:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startPercent:Float):Void
		queueEase(step, endStep, modName, percent * 0.01, style, player);

	function queue(step:Float, modName:String, target:Float, player:Int,
		endStep:Float, style:Dynamic, isEase:Bool):Void {
		ensureAlive();
		if (!registry.isRegistered(modName))
			throw 'Nightmare Vision scripted or unknown modifier is unsupported: ' + Std.string(modName);
		if (player == -1) {
			for (index in 0...registry.players)
				queueOne(step, modName, target, index, endStep, style, isEase);
		} else {
			// Match source setValue's player-index bounds check at execution time,
			// but reject an invalid target before it is scheduled.
			if (player < 0 || player >= registry.players)
				throw 'Nightmare Vision modifier player index out of range: ' + player;
			queueOne(step, modName, target, player, endStep, style, isEase);
		}
	}

	function queueOne(step:Float, modName:String, target:Float, player:Int,
		endStep:Float, style:Dynamic, isEase:Bool):Void {
		var list = modEvents.get(modName);
		var event:NightmareVisionModifierValueEvent = {
			executionStep:step, sequence:nextSequence++, modName:modName, player:player, endVal:target,
			endStep:endStep, style:style == null ? 'linear' : style, startVal:null,
			ignoreExecution:false, finished:false, isEase:isEase
		};
		list.push(event);
		list.sort(function(a, b) {
			// Retain the donor's integer-difference comparator; sequence breaks ties
			// in a deterministic order for same-step authored Set->Ease pairs.
			var stepOrder = Std.int(a.executionStep - b.executionStep);
			if (stepOrder != 0) return stepOrder;
			return a.sequence - b.sequence;
		});
	}

	/** Drain every value event due at the live decimal song step. */
	public function update(step:Float):Void {
		if (destroyed) return;
		for (modName in queueOrder) {
			var list = modEvents.get(modName);
			if (list == null) continue;
			var index = 0;
			while (index < list.length) {
				var event = list[index];
				if (event.finished) {
					list.splice(index, 1);
					continue;
				}
				if (event.ignoreExecution) {
					index++;
					continue;
				}
				if (!(step >= event.executionStep)) break;
				if (!event.isEase) {
					registry.setValue(event.modName, event.endVal, event.player);
					event.finished = true;
				} else if (step <= event.endStep) {
					if (event.startVal == null) event.startVal = registry.value(event.modName, event.player);
					var duration = event.endStep - event.executionStep;
					var elapsed = step - event.executionStep;
					var t = elapsed / duration;
					var change = event.endVal - event.startVal;
					registry.setValue(event.modName,
						event.startVal + change * NightmareVisionModchartEase.apply(event.style, t), event.player);
				} else {
					registry.setValue(event.modName, event.endVal, event.player);
					event.finished = true;
				}
				if (event.finished) list.splice(index, 1);
				else index++;
			}
		}
	}

	public function pendingCount():Int {
		var count = 0;
		for (list in modEvents) count += list.length;
		return count;
	}

	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		for (list in modEvents) list.resize(0);
		modEvents = new Map();
		queueOrder.resize(0);
	}

	function ensureAlive():Void {
		if (destroyed) throw 'Nightmare Vision modifier timeline has been destroyed';
	}
}
