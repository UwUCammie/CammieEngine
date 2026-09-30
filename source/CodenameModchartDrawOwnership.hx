package;

/** Structural gate for letting an attached FunkinModchart Manager own the
 * native note/receptor draw pass. Kept free of Flixel types for focused tests. */
class CodenameModchartDrawOwnership {
	public static function managerOwnsVisibleDraw(owner:Dynamic, manager:Dynamic):Bool {
		if (owner == null || manager == null
			|| Reflect.field(manager, 'exists') != true
			|| Reflect.field(manager, 'visible') != true)
			return false;
		var members:Dynamic = Reflect.field(owner, 'members');
		if (!Std.isOfType(members, Array))
			return false;
		return (cast members:Array<Dynamic>).indexOf(manager) >= 0;
	}
}
