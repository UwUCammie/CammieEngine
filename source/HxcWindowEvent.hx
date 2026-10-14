package;

/**
	One window event (focus lost or gained) as scripts see it: the add, remove
	and has calls of lime's Event, holding script functions only.

	V-Slice scripts listen through `Application.current.window.onFocusOut` and
	`onFocusIn`. The HXC translation hands them these engine-owned events
	instead of lime's own, which forward the real window event and drop every
	listener on each state switch, so a script callback never runs after its
	song is gone.
**/
class HxcWindowEvent {
	static var focusOut:HxcWindowEvent;
	static var focusIn:HxcWindowEvent;
	static var stateSwitchHooked:Bool = false;

	var listeners:Array<Dynamic> = [];

	public function new() {}

	/** The shared focus event for 'out' (focus lost) or 'in' (focus gained). */
	public static function focus(kind:String):HxcWindowEvent {
		var gained = kind != null && kind.toLowerCase() == 'in';
		var event = gained ? focusIn : focusOut;
		if (event != null)
			return event;
		event = new HxcWindowEvent();
		if (gained)
			focusIn = event;
		else
			focusOut = event;
		#if flixel
		try {
			var window = openfl.Lib.application == null ? null : openfl.Lib.application.window;
			if (window != null) {
				if (gained)
					window.onFocusIn.add(event.dispatch);
				else
					window.onFocusOut.add(event.dispatch);
			}
		} catch (_:Dynamic) {}
		if (!stateSwitchHooked) {
			stateSwitchHooked = true;
			flixel.FlxG.signals.preStateSwitch.add(clearScriptListeners);
		}
		#end
		return event;
	}

	/** A script's listeners belong to its state; drop them before the next state starts. */
	public static function clearScriptListeners():Void {
		if (focusOut != null)
			focusOut.removeAll();
		if (focusIn != null)
			focusIn.removeAll();
	}

	/** lime's Event.add also takes once and priority; scripts only rely on the listener. */
	public function add(listener:Dynamic, ?once:Bool, ?priority:Int):Void {
		if (listener == null || !Reflect.isFunction(listener) || listeners.indexOf(listener) >= 0)
			return;
		listeners.push(listener);
	}

	public function remove(listener:Dynamic):Void {
		listeners.remove(listener);
	}

	public function has(listener:Dynamic):Bool
		return listeners.indexOf(listener) >= 0;

	public function removeAll():Void {
		listeners.resize(0);
	}

	public function dispatch():Void {
		if (listeners.length == 0)
			return;
		// A listener may remove itself while it runs, so walk a copy.
		for (listener in listeners.copy()) {
			try Reflect.callMethod(null, listener, [])
			catch (error:Dynamic) trace('[hxc-window] focus listener failed: ' + Std.string(error));
		}
	}
}
