package;

/**
	Psych 0.6 and older had a top-level `Boyfriend` class, a Character built as
	the player (`new Boyfriend(x, y, 'bf-car')`). Its HScript resolved it by
	class name without an import, so runHaxeCode often builds extra players with
	it. This type is only the name a script sees: constructing it makes the
	same player Character the host would make.
**/
@:keep
class PsychLegacyBoyfriend {
	public static function create(args:Array<Dynamic>):Dynamic {
		var x:Float = args != null && args.length > 0 && args[0] != null ? args[0] : 0;
		var y:Float = args != null && args.length > 1 && args[1] != null ? args[1] : 0;
		var character:String = args != null && args.length > 2 && args[2] != null ? Std.string(args[2]) : 'bf';
		// Resolved by name so this alias does not pull the whole character module
		// into every place that installs the Psych script preset.
		return Type.createInstance(Type.resolveClass('Character'), [x, y, character, true]);
	}
}
