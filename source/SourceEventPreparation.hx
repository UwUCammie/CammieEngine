package;

/**
	What one engine does while its chart events are prepared. Every hook is
	optional; the driver calls them in this order for each row.
**/
typedef SourceEventPreparationHooks = {
	/** Every row, before the first-push check (Psych precaches and fires eventPushedUnique here). */
	@:optional var beforeFirstPush:SourceEventNote->Void;
	/** Once per event name, on the first row that carries it. */
	@:optional var firstPush:SourceEventNote->Void;
	/**
		The scripts' early-trigger answer for this row, or null for no answer.
		Leave it out to defer offsets to applyEarlyOffsets (Psych asks only after
		its event and song scripts have loaded).
	**/
	@:optional var earlyOffset:SourceEventNote->Null<Float>;
	/** Every row, after its offset (when there is one) has been applied. */
	@:optional var push:SourceEventNote->Void;
}

/** The event preparation loop Psych and both Nightmare Vision revisions share. */
class SourceEventPreparation {
	/** Base-game early triggers for built-in events, in milliseconds. */
	public static function defaultEarlyOffset(name:String):Float {
		return switch (name) {
			// Plays the kill sound on the beat it was charted for.
			case 'Kill Henchmen': 280;
			default: 0;
		};
	}

	/**
		Both engines read a script answer of 0 the same as no answer (in NV it is
		literally the continue value), so the built-in default still applies.
	**/
	public static function earlyOffsetFor(name:String, answer:Null<Float>):Float {
		return answer == null || answer == 0 ? defaultEarlyOffset(name) : answer;
	}

	/**
		Build one view per row, appending it to `views` before its hooks run so
		scripts that read the event list mid-loop see every earlier row.
	**/
	public static function prepare(rows:Array<Dynamic>, noteOffset:Float, views:Array<SourceEventNote>,
		hooks:SourceEventPreparationHooks):Void {
		var pushedNames:Map<String, Bool> = new Map();
		for (row in rows) {
			var event = new SourceEventNote(row, noteOffset);
			views.push(event);
			pushView(event, pushedNames, hooks);
		}
	}

	/**
		One built view through the hooks, in the order every engine runs them.
		Historical Nightmare Vision builds its views itself over two admission
		passes, so it calls this directly. Without `pushedNames` no first push is
		tracked: its second pass must not record names the first pass never saw.
	**/
	public static function pushView(event:SourceEventNote, pushedNames:Null<Map<String, Bool>>,
		hooks:SourceEventPreparationHooks):Void {
		if (hooks.beforeFirstPush != null)
			hooks.beforeFirstPush(event);
		if (pushedNames != null && !pushedNames.exists(event.event)) {
			pushedNames.set(event.event, true);
			if (hooks.firstPush != null)
				hooks.firstPush(event);
		}
		if (hooks.earlyOffset != null) {
			// The time is read before any script runs: an early-trigger callback
			// that moves the event does not change what is subtracted from. The
			// name is read after: both Nightmare Vision revisions pick the built-in
			// default by the name the event has once its scripts have answered.
			var time = event.strumTime;
			var answer = hooks.earlyOffset(event);
			event.strumTime = time - earlyOffsetFor(event.event, answer);
		}
		if (hooks.push != null)
			hooks.push(event);
	}

	/** The deferred half of prepare, for engines that ask for offsets later. */
	public static function applyEarlyOffsets(views:Array<SourceEventNote>, earlyOffset:SourceEventNote->Null<Float>):Void {
		for (event in views)
			event.strumTime -= earlyOffsetFor(event.event, earlyOffset(event));
	}
}
