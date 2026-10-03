package;

/** Buffered keyboard view for fixed-rate script callbacks.
 * Held state follows the current host input sample. Edge state is latched until
 * a source tick consumes it, then exposed only on the last catch-up tick. */
class CompatScriptInputSnapshot {
	final keyNames:Array<String> = [];
	final keyCodes:Map<String, Int> = new Map();
	final keyNamesByCode:Map<Int, String> = new Map();
	final held:Map<String, Bool> = new Map();
	final released:Map<String, Bool> = new Map();
	final latchedPressed:Map<String, Bool> = new Map();
	final latchedReleased:Map<String, Bool> = new Map();
	final cachedKeyboards:Map<String, Dynamic> = new Map();

	public function new(keysByName:Map<String, Int>) {
		if (keysByName != null) {
			for (name in keysByName.keys()) {
				if (name == 'ANY' || name == 'NONE') continue;
				keyNames.push(name);
				var code = keysByName.get(name);
				keyCodes.set(name, code);
				keyNamesByCode.set(code, name);
			}
		}
		// FlxKeyboard inserts its key inputs in this same map iteration order.
		// Keep snapshots deterministic and firstJustPressed compatible.
	}

	/** Sample once per host update, including updates with no due source tick. */
	public function sample(nativeKeys:Dynamic):Void {
		var nativeHeld = Reflect.getProperty(nativeKeys, 'pressed');
		var nativeReleased = Reflect.getProperty(nativeKeys, 'released');
		var nativeJustPressed = Reflect.getProperty(nativeKeys, 'justPressed');
		var nativeJustReleased = Reflect.getProperty(nativeKeys, 'justReleased');
		for (name in keyNames) {
			held.set(name, readKey(nativeHeld, name));
			released.set(name, readKey(nativeReleased, name));
			if (readKey(nativeJustPressed, name)) latchedPressed.set(name, true);
			if (readKey(nativeJustReleased, name)) latchedReleased.set(name, true);
		}
	}

	/** Return the FlxG.keys-shaped facade for one source tick. */
	public function view(nativeKeys:Dynamic, tickIndex:Int, tickCount:Int):Dynamic {
		var cacheKey = tickCount + ':' + tickIndex;
		if (cachedKeyboards.exists(cacheKey)) return cachedKeyboards.get(cacheKey);
		var isNewestTick = tickCount > 0 && tickIndex == tickCount - 1;
		var pressedView = makeKeyList(held);
		var justPressedView = makeKeyList(isNewestTick ? latchedPressed : emptyValues());
		var justReleasedView = makeKeyList(isNewestTick ? latchedReleased : emptyValues());
		var releasedView = makeKeyList(released);
		var manager:Dynamic = {};
		Reflect.setField(manager, 'enabled', Reflect.getProperty(nativeKeys, 'enabled'));
		Reflect.setField(manager, 'preventDefaultKeys', Reflect.getProperty(nativeKeys, 'preventDefaultKeys'));
		Reflect.setField(manager, 'pressed', pressedView);
		Reflect.setField(manager, 'justPressed', justPressedView);
		Reflect.setField(manager, 'justReleased', justReleasedView);
		Reflect.setField(manager, 'released', releasedView);
		Reflect.setField(manager, 'anyPressed', function(keys:Dynamic):Bool return anyState(keys, held));
		Reflect.setField(manager, 'anyJustPressed', function(keys:Dynamic):Bool
			return anyState(keys, isNewestTick ? latchedPressed : emptyValues()));
		Reflect.setField(manager, 'anyJustReleased', function(keys:Dynamic):Bool
			return anyState(keys, isNewestTick ? latchedReleased : emptyValues()));
		Reflect.setField(manager, 'firstPressed', function():Int return firstState(held));
		Reflect.setField(manager, 'firstJustPressed', function():Int
			return firstState(isNewestTick ? latchedPressed : emptyValues()));
		Reflect.setField(manager, 'firstJustReleased', function():Int
			return firstState(isNewestTick ? latchedReleased : emptyValues()));
		Reflect.setField(manager, 'checkStatus', function(code:Dynamic, status:Dynamic):Bool
			return stateFor(code, status, held, released,
				isNewestTick ? latchedPressed : emptyValues(),
				isNewestTick ? latchedReleased : emptyValues()));
		Reflect.setField(manager, 'getIsDown', function():Dynamic
			return callNative(nativeKeys, 'getIsDown', []));
		Reflect.setField(manager, 'reset', function():Dynamic return callNative(nativeKeys, 'reset', []));
		Reflect.setField(manager, 'destroy', function():Dynamic return callNative(nativeKeys, 'destroy', []));
		cachedKeyboards.set(cacheKey, manager);
		return manager;
	}

	/** Consume edges only after both source callback phases have run. */
	public function finishSourceBatch():Void {
		latchedPressed.clear();
		latchedReleased.clear();
		cachedKeyboards.clear();
	}

	function makeKeyList(values:Map<String, Bool>):Dynamic {
		var list:Dynamic = {};
		var any = false;
		for (name in keyNames) {
			var value = values.get(name) == true;
			Reflect.setField(list, name, value);
			if (value) any = true;
		}
		Reflect.setField(list, 'ANY', any);
		Reflect.setField(list, 'NONE', !any);
		return list;
	}

	function anyState(keys:Dynamic, values:Map<String, Bool>):Bool {
		if (keys == null) return false;
		var length:Int = Reflect.field(keys, 'length');
		var keyArray:Array<Dynamic> = cast keys;
		for (index in 0...length) {
			var code:Int = cast keyArray[index];
			if (code == -2 && hasAny(values)) return true;
			if (code == -1 && !hasAny(values)) return true;
			var name = keyNamesByCode.get(code);
			if (name != null && values.get(name) == true) return true;
		}
		return false;
	}

	function firstState(values:Map<String, Bool>):Int {
		for (name in keyNames) if (values.get(name) == true) return keyCodes.get(name);
		return -1;
	}

	function stateFor(codeValue:Dynamic, statusValue:Dynamic, heldValues:Map<String, Bool>,
		releasedValues:Map<String, Bool>, pressedEdges:Map<String, Bool>, releasedEdges:Map<String, Bool>):Bool {
		var code:Int = cast codeValue;
		var status:Int = cast statusValue;
		var values:Map<String, Bool> = switch (status) {
			case -1: releasedEdges; // FlxInputState.JUST_RELEASED
			case 0: releasedValues; // FlxInputState.RELEASED
			case 1: heldValues; // FlxInputState.PRESSED
			case 2: pressedEdges; // FlxInputState.JUST_PRESSED
			default: return false;
		};
		if (code == -2) return hasAny(values);
		if (code == -1) return !hasAny(values);
		var name = keyNamesByCode.get(code);
		return name != null && values.get(name) == true;
	}

	function hasAny(values:Map<String, Bool>):Bool {
		for (name in keyNames) if (values.get(name) == true) return true;
		return false;
	}

	function readKey(keyList:Dynamic, name:String):Bool
		return keyList != null && Reflect.getProperty(keyList, name) == true;

	function callNative(target:Dynamic, methodName:String, args:Array<Dynamic>):Dynamic {
		var method:Dynamic = target == null ? null : Reflect.field(target, methodName);
		if (method == null) return null;
		return Reflect.callMethod(target, method, args);
	}

	static function emptyValues():Map<String, Bool> return new Map();
}
