package;

typedef NightmareVisionTimelineCallbackErrorReporter = NightmareVisionCallbackEvent->Dynamic->Void;

/** Source EventTimeline's live queues, with an optional owner callback-error safeguard. */
@:keep
class NightmareVisionEventTimeline {
	public var modEvents:Map<String, Array<NightmareVisionModEvent>> = [];
	public var events:Array<NightmareVisionBaseEvent> = [];
	final reportError:Null<NightmareVisionTimelineCallbackErrorReporter>;
	var destroyed:Bool = false;

	public function new(?reportError:NightmareVisionTimelineCallbackErrorReporter) {
		this.reportError = reportError;
	}

	public function addMod(modName:String):Void {
		ensureAlive();
		modEvents.set(modName, []);
	}

	public function addEvent(event:NightmareVisionBaseEvent):Void {
		ensureAlive();
		if (Std.isOfType(event, NightmareVisionModEvent)) {
			var modEvent:NightmareVisionModEvent = cast event;
			var name = modEvent.modName;
			if (!modEvents.exists(name)) addMod(name);
			if (!modEvents.get(name).contains(modEvent)) modEvents.get(name).push(modEvent);
			modEvents.get(name).sort((a, b) -> Std.int(a.executionStep - b.executionStep));
		} else if (!events.contains(event)) {
			events.push(event);
			events.sort((a, b) -> Std.int(a.executionStep - b.executionStep));
		}
	}

	function updateSchedule(schedule:Array<NightmareVisionBaseEvent>, step:Float):Void {
		var i = 0;
		while (i < schedule.length) {
			var event = schedule[i];
			if (event.finished) {
				schedule.remove(event);
				continue;
			}
			if (event.ignoreExecution) {
				i++;
				continue;
			}
			if (step >= event.executionStep) {
				if (reportError != null && Std.isOfType(event, NightmareVisionCallbackEvent)) {
					try event.run(step) catch (error:Dynamic) {
						// Explicit gameplay policy; default construction retains source throws.
						event.finished = true;
						try reportError(cast event, error) catch (_:Dynamic) {}
					}
				} else event.run(step);
				if (event.finished) schedule.remove(event);
				else i++;
			} else break;
		}
	}

	public function update(step:Float):Void {
		if (destroyed) return;
		for (modName in modEvents.keys()) updateSchedule(cast modEvents.get(modName), step);
		updateSchedule(events, step);
	}

	/** Owner teardown is a host safeguard beyond the donor's scheduling surface. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		for (schedule in modEvents) {
			for (event in schedule) if (event != null) event.finished = true;
			schedule.resize(0);
		}
		for (event in events) if (event != null) event.finished = true;
		events.resize(0);
		modEvents.clear();
	}

	function ensureAlive():Void {
		if (destroyed) throw 'Nightmare Vision event timeline has been destroyed';
	}
}
