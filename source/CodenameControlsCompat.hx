package;

/** Shared Codename menu bindings stored separately from legacy gameplay keys. */
class CodenameControlsCompat {
	public static function switchModPressed(controls:Controls):Bool
		return controls != null && controls.SWITCHMOD;

	public static function switchModKeyboardBindings(saveData:Dynamic, defaultKey:Int):Array<Int> {
		var menuKeys:Dynamic = saveData == null ? null : Reflect.field(saveData, 'codenameMenuKeys');
		var stored:Dynamic = menuKeys == null ? null : Reflect.field(menuKeys, 'switchmod');
		if (!Std.isOfType(stored, Array)) return defaultKey > 0 ? [defaultKey] : [];

		var result:Array<Int> = [];
		for (value in (cast stored:Array<Dynamic>)) {
			var key:Null<Int> = Std.isOfType(value, Int)
				? (cast value:Int) : Std.parseInt(Std.string(value));
			if (key != null && key > 0 && !result.contains(key)) result.push(key);
		}
		return result;
	}

	/** Save the Codename-only action without replacing legacy or other menu keys. */
	public static function saveSwitchModKeyboardBindings(saveData:Dynamic, keys:Array<Int>):Bool {
		if (saveData == null) return false;
		var menuKeys:Dynamic = Reflect.field(saveData, 'codenameMenuKeys');
		if (menuKeys == null) {
			menuKeys = {};
			Reflect.setField(saveData, 'codenameMenuKeys', menuKeys);
		}
		var cleaned:Array<Int> = [];
		if (keys != null) for (key in keys)
			if (key > 0 && !cleaned.contains(key)) cleaned.push(key);
		Reflect.setField(menuKeys, 'switchmod', cleaned);
		return true;
	}
}
