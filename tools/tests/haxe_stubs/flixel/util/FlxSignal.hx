package flixel.util;

/** Interpreter-only stand-in for Flixel's typed signal. Production resolves
 * the real flixel.util.FlxSignal.FlxTypedSignal from the pinned haxelib. */
class FlxTypedSignal<T> {
	var listeners:Array<T> = [];
	var once:Array<T> = [];
	public var dispatch:T;
	public function new() {
		dispatch = cast function(value:Dynamic):Void {
			for (listener in listeners.copy()) {
				if (!listeners.contains(listener)) continue;
				if (once.contains(listener)) remove(listener);
				Reflect.callMethod(null, cast listener, [value]);
			}
		};
	}
	public function add(listener:T):Void if (!has(listener)) listeners.push(listener);
	public function addOnce(listener:T):Void {
		if (has(listener)) throw 'conflicting signal registration';
		listeners.push(listener);
		once.push(listener);
	}
	public function has(listener:T):Bool return listeners.contains(listener);
	public function remove(listener:T):Void {listeners.remove(listener); once.remove(listener);}
	public function removeAll():Void {listeners = []; once = [];}
}
