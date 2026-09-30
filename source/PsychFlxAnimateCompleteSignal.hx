package;

import animate.FlxAnimateController;

typedef PsychFlxAnimateCompleteListener = {
	var listener:Dynamic;
	var wrapper:String->Void;
}

/** Psych's no-argument onComplete signal over Flixel's named onFinish signal. */
class PsychFlxAnimateCompleteSignal {
	final controller:FlxAnimateController;
	final listeners:Array<PsychFlxAnimateCompleteListener> = [];

	public function new(controller:FlxAnimateController) {
		this.controller = controller;
	}

	public function add(listener:Dynamic):Void {
		if (listener == null || has(listener)) return;
		if (!Reflect.isFunction(listener))
			throw '[psych-animate] onComplete listener must be a function';

		var wrapper:String->Void = function(_animationName:String):Void {
			Reflect.callMethod(null, listener, []);
		};
		listeners.push({listener:listener, wrapper:wrapper});
		controller.onFinish.add(wrapper);
	}

	public function has(listener:Dynamic):Bool {
		if (listener == null) return false;
		for (entry in listeners) if (entry.listener == listener) return true;
		return false;
	}

	public function remove(listener:Dynamic):Void {
		if (listener == null) return;
		for (entry in listeners.copy()) {
			if (entry.listener != listener) continue;
			controller.onFinish.remove(entry.wrapper);
			listeners.remove(entry);
		}
	}

	public function removeAll():Void {
		for (entry in listeners) controller.onFinish.remove(entry.wrapper);
		listeners.resize(0);
	}

	public function destroy():Void {
		removeAll();
	}
}
