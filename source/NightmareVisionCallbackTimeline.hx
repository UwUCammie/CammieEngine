package;

typedef NightmareVisionCallbackErrorReporter = NightmareVisionCallbackEvent->Dynamic->Void;

/** The callback-event subset of Nightmare Vision's EventTimeline. */
class NightmareVisionCallbackTimeline {
	public var events:Array<NightmareVisionCallbackEvent> = [];
	final reportError:NightmareVisionCallbackErrorReporter;
	var nextInsertionOrder:Int = 0;
	var destroyed:Bool = false;

	public function new(?reportError:NightmareVisionCallbackErrorReporter) {
		this.reportError = reportError == null ? defaultReport : reportError;
	}

	static function defaultReport(event:NightmareVisionCallbackEvent, error:Dynamic):Void {
		trace('[nightmare-vision-mod-callback-error] step=' + event.executionStep + ': ' + Std.string(error));
	}

	public function addEvent(event:NightmareVisionCallbackEvent):Void {
		if (destroyed)
			throw 'Nightmare Vision callback timeline has been destroyed';
		if (event == null || events.indexOf(event) >= 0)
			return;
		event.insertionOrder = nextInsertionOrder++;
		events.push(event);
		events.sort(compareEvents);
	}

	static function compareEvents(a:NightmareVisionCallbackEvent,
		b:NightmareVisionCallbackEvent):Int {
		if (a.executionStep < b.executionStep) return -1;
		if (a.executionStep > b.executionStep) return 1;
		if (a.insertionOrder < b.insertionOrder) return -1;
		if (a.insertionOrder > b.insertionOrder) return 1;
		return 0;
	}

	/**
	 * Match EventTimeline's update contract: all due events are drained in one
	 * pass; a one-shot callback receives the current step (including after a
	 * forward seek); queueFunc callbacks run on every update through endStep and
	 * are retired only once currentStep is strictly greater than endStep.
	 */
	public function update(currentStep:Float):Void {
		if (destroyed) return;
		var index = 0;
		while (index < events.length) {
			var event = events[index];
			if (event.finished) {
				events.splice(index, 1);
				continue;
			}
			if (event.ignoreExecution) {
				index++;
				continue;
			}
			if (!(currentStep >= event.executionStep))
				break;

			try {
				event.run(currentStep);
			} catch (error:Dynamic) {
				// A broken authored callback must not repeatedly abort gameplay on
				// every frame or prevent later due callbacks from running.
				event.finished = true;
				try reportError(event, error) catch (_:Dynamic) {}
			}

			if (event.finished) {
				var liveIndex = events.indexOf(event);
				if (liveIndex >= 0) events.splice(liveIndex, 1);
				// A callback may enqueue another event due at this current step.
				// Revisit this index so one-shots retain source same-update behavior.
				if (liveIndex < 0 || liveIndex <= index)
					continue;
			} else {
				// Repeating callbacks run at most once per timeline update.
				var liveIndex = events.indexOf(event);
				index = liveIndex < 0 ? index + 1 : liveIndex + 1;
			}
		}
	}

	/** Drop pending closures when the owning PlayState is released. */
	public function destroy():Void {
		if (destroyed) return;
		for (event in events) event.finished = true;
		events.resize(0);
		destroyed = true;
	}
}
